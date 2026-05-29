"""新闻智能体主流水线 — 编排采集、去重、改写、配图、存储、通知全流程。

支持三种模式：
  python -m news_agent                 正常模式（实时采集+处理）
  python -m news_agent --collect-only  仅采集，缓存到 data/raw_cache.json
  python -m news_agent --from-cache    离线模式，从缓存读取，无需代理
  python -m news_agent --no-image      纯文字，跳过配图
"""

import asyncio
import json
from datetime import datetime, timezone

from news_agent.collectors.newsapi import NewsAPICollector
from news_agent.collectors.google_news import GoogleNewsCollector
from news_agent.config import config
from news_agent.filter.dedup import deduplicate, register_fingerprints
from news_agent.filter.relevance import score_and_rank
from news_agent.imager.seedream_client import SeedreamClient
from news_agent.notifier.lark_notifier import send_run_summary
from news_agent.rewriter.deepseek_client import DeepSeekRewriter
from news_agent.storage.database import init_db, cleanup_old_fingerprints
from news_agent.storage.draft_store import save_draft
from news_agent.storage.models import Article, RunLog
from news_agent.utils.logger import logger


class NewsPipeline:

    def __init__(self):
        cfg = config.pipeline
        logger.info(
            f"NewsPipeline initialized | "
            f"max_articles={cfg.max_articles_per_run} | "
            f"dedup_threshold={cfg.dedup_similarity_threshold}"
        )

    def collect_only(self) -> int:
        """仅采集原始文章并缓存到本地 JSON 文件。返回采集条数。"""
        logger.info("=" * 60)
        logger.info("Collect-only mode: fetching and caching raw articles")

        articles = self._collect_live()
        if not articles:
            logger.error("Collection returned zero articles")
            return 0

        cache_path = config.pipeline.cache_path
        from pathlib import Path
        Path(cache_path).parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "count": len(articles),
            "articles": articles,
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        logger.info(f"Cached {len(articles)} articles → {cache_path}")
        return len(articles)

    def run(self, from_cache: bool = False, skip_images: bool = False) -> RunLog:
        """Execute the full pipeline. If from_cache=True, skip live collection. If skip_images=True, no image generation."""
        run_log = RunLog(
            run_at=datetime.now(timezone.utc),
            status="success",
        )
        errors: list[str] = []
        drafts: list[str] = []

        logger.info("=" * 60)
        source_label = "CACHE" if from_cache else "LIVE"
        img_label = "NO_IMAGE" if skip_images else "FULL"
        logger.info(f"News Pipeline START (source={source_label}, mode={img_label})")

        init_db()
        cleanup_old_fingerprints(config.pipeline.fingerprint_ttl_days)

        # ---- 1. 采集 ----
        logger.info("Phase 1: Collection")
        if from_cache:
            raw_articles = self._load_from_cache()
        else:
            raw_articles = self._collect_live()
        run_log.collected = len(raw_articles)
        if not raw_articles:
            msg = "采集阶段返回零条新闻" if not from_cache else "缓存为空或不存在，请先运行 --collect-only"
            errors.append(msg)
            run_log.status = "failed"
            run_log.errors = errors
            self._notify(run_log, drafts)
            return run_log

        # ---- 2. 去重 ----
        logger.info("Phase 2: Deduplication")
        deduped = deduplicate(raw_articles)
        run_log.after_dedup = len(deduped)
        if not deduped:
            logger.info("All articles filtered out by dedup")
            run_log.status = "partial"
            run_log.errors = ["去重后无剩余文章（均为已发布或高度相似内容）"]
            self._notify(run_log, drafts)
            return run_log

        # ---- 2.5 日期过滤（仅当天） ----
        from news_agent.filter.dedup import filter_today
        deduped = filter_today(deduped, max_hours=24)
        run_log.after_dedup = len(deduped)
        if not deduped:
            logger.info("All articles filtered out by date filter (only today)")
            run_log.status = "partial"
            run_log.errors = ["日期过滤后无剩余文章（无当天发布的新闻）"]
            self._notify(run_log, drafts)
            return run_log

        # ---- 3. 评分排序 ----
        logger.info("Phase 3: Relevance ranking")
        selected = score_and_rank(deduped)
        if not selected:
            errors.append("相关性评分后无合格文章")
            run_log.status = "failed"
            run_log.errors = errors
            self._notify(run_log, drafts)
            return run_log

        # ---- 4. 改写 + 配图 + 存储 (异步并发) ----
        phase_label = "Rewriting only" if skip_images else "Rewriting + Imaging"
        logger.info(f"Phase 4: {phase_label} ({len(selected)} articles, concurrency={config.pipeline.max_concurrency})")

        generated, failed, gen_errors, gen_drafts = asyncio.run(
            self._process_articles_async(selected, skip_images)
        )

        run_log.generated = generated
        run_log.failed = failed
        errors.extend(gen_errors)
        drafts.extend(gen_drafts)

        # ---- 5. 注册指纹 ----
        register_fingerprints(selected)

        # ---- 6. 汇总 ----
        if run_log.failed > 0:
            run_log.status = "partial" if run_log.generated > 0 else "failed"

        if run_log.generated == 0:
            run_log.status = "failed"
            if not errors:
                errors.append("所有文章改写或配图均失败")

        run_log.errors = errors
        run_log.save()

        logger.info(
            f"Pipeline END | collected={run_log.collected} "
            f"deduped={run_log.after_dedup} generated={run_log.generated} "
            f"failed={run_log.failed} status={run_log.status}"
        )

        self._notify(run_log, drafts)
        return run_log

    def _collect_live(self) -> list[dict]:
        articles: list[dict] = []
        limit = config.pipeline.max_collect_per_source

        if config.pipeline.newsapi_key:
            try:
                c = NewsAPICollector(config.pipeline.newsapi_key)
                articles.extend(c.collect(max_results=limit))
            except Exception as e:
                logger.error(f"NewsAPI collector failed: {e}")

        try:
            c = GoogleNewsCollector()
            articles.extend(c.collect(max_results=limit))
        except Exception as e:
            logger.error(f"GoogleNews collector failed: {e}")

        return articles

    def _load_from_cache(self) -> list[dict]:
        cache_path = config.pipeline.cache_path
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            articles = data.get("articles", [])
            cached_at = data.get("cached_at", "unknown")
            logger.info(f"Loaded {len(articles)} articles from cache ({cache_path})")
            logger.info(f"Cache timestamp: {cached_at}")
            return articles
        except FileNotFoundError:
            logger.error(f"Cache file not found: {cache_path}")
            return []
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            return []

    async def _process_articles_async(self, selected: list[dict], skip_images: bool):
        """并发改写 + 配图 + 存储。返回 (generated, failed, errors, drafts)。"""
        sem = asyncio.Semaphore(config.pipeline.max_concurrency)
        db_lock = asyncio.Lock()
        rewriter = DeepSeekRewriter()
        imager = None if skip_images else SeedreamClient()

        errors: list[str] = []
        drafts: list[str] = []
        generated = 0
        failed = 0
        completed = 0
        total = len(selected)

        async def process_one(a: dict):
            nonlocal generated, failed, completed
            title_orig = a.get("title", "")
            content = a.get("description", "") or a.get("content", "")
            published = a.get("publishedAt", "")
            category = a.get("category", "other")

            async with sem:
                rewritten = await rewriter.rewrite_async(title_orig, content, published, category)

            if not rewritten:
                async with db_lock:
                    errors.append(f"改写失败: {title_orig[:60]}")
                    failed += 1
                return

            image_path = None
            if imager:
                image_path = imager.generate(rewritten.get("title", title_orig), category)

            article = Article(
                url=a.get("url", ""),
                title_original=title_orig,
                title_rewritten=rewritten.get("title", ""),
                body_rewritten=rewritten.get("body", ""),
                image_path=image_path,
                source=a.get("source", ""),
                category=category,
                fingerprint=a.get("fingerprint", ""),
                collected_at=datetime.fromisoformat(
                    published.replace("Z", "+00:00")
                ) if published else datetime.now(timezone.utc),
                status="draft",
            )

            async with db_lock:
                article.save()
                draft_path = save_draft(article)
                if draft_path:
                    drafts.append(draft_path)
                generated += 1
                completed += 1
                if completed % 10 == 0 or completed == total:
                    logger.info(f"Progress: {completed}/{total} completed, {failed} failed")

        tasks = [process_one(a) for a in selected]
        await asyncio.gather(*tasks, return_exceptions=True)

        return generated, failed, errors, drafts

    def _notify(self, run_log: RunLog, drafts: list[str]) -> None:
        try:
            send_run_summary({
                "status": run_log.status,
                "collected": run_log.collected,
                "after_dedup": run_log.after_dedup,
                "generated": run_log.generated,
                "failed": run_log.failed,
                "errors": run_log.errors,
                "drafts": drafts,
            })
        except Exception as e:
            logger.error(f"Notification failed: {e}")
