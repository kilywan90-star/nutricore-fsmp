"""新闻智能体入口

用法:
  python -m news_agent                  正常模式（实时采集+全流程处理）
  python -m news_agent --collect-only   仅采集，缓存到 data/raw_cache.json（需代理，约20秒）
  python -m news_agent --from-cache     离线模式，从缓存读取（无需代理，纯国内API）
"""

import sys
from pathlib import Path

from news_agent.config import config
from news_agent.pipeline import NewsPipeline
from news_agent.utils.logger import logger

PROJECT_DIR = Path(__file__).resolve().parent.parent


def main() -> int:
    collect_only = "--collect-only" in sys.argv
    from_cache = "--from-cache" in sys.argv
    skip_images = "--no-image" in sys.argv

    print_header(collect_only, from_cache, skip_images)

    env_file = PROJECT_DIR / ".env"
    if not env_file.exists():
        print_no_env()
        return 1

    # collect-only mode doesn't need API key validation (only needs proxy for RSS)
    if not collect_only:
        missing = config.validate()
        if missing:
            print_missing_config(missing)
            return 1

    logger.info(f"News Agent 启动 | mode={'collect-only' if collect_only else 'from-cache' if from_cache else 'live'}")
    pipeline = NewsPipeline()

    if collect_only:
        count = pipeline.collect_only()
        print()
        print("=" * 50)
        print(f"  采集完成: {count} 条")
        print(f"  缓存路径: {config.pipeline.cache_path}")
        print("=" * 50)
        print()
        print("  下一步: 断开代理/VPN，运行: python -m news_agent --from-cache")
        print()
        return 0 if count > 0 else 1

    run_log = pipeline.run(from_cache=from_cache, skip_images=skip_images)
    print_result(run_log)
    return 0 if run_log.status != "failed" else 1


def print_header(collect_only: bool = False, from_cache: bool = False, skip_images: bool = False):
    print()
    print("=" * 50)
    print("  新闻智能体 News Agent v0.2")
    if collect_only:
        print("  [采集模式] 采集 -> 缓存到本地 (约20秒，需代理)")
    elif from_cache:
        mode = "仅文字" if skip_images else "改写+配图"
        print(f"  [离线模式] 从缓存读取 -> DeepSeek改写 -> {mode}")
    else:
        mode = "仅文字" if skip_images else "改写+配图"
        print(f"  采集 -> 筛选 -> DeepSeek改写 -> {mode}")
    print("=" * 50)
    print()


def print_no_env():
    print("=" * 50)
    print("  未找到 .env 配置文件")
    print("=" * 50)
    print()
    print("  请按以下步骤配置:")
    print()
    print("  1. 复制模板:")
    print("     cp .env.example .env")
    print()
    print("  2. 编辑 .env 填入API密钥:")
    print("     DEEPSEEK_API_KEY=sk-xxx        DeepSeek API密钥")
    print("     ARK_API_KEY=xxx               火山引擎(豆包) API密钥")
    print("     NEWSAPI_KEY=xxx               NewsAPI.org 密钥 (免费注册)")
    print()
    print("  3. 保存后重新运行")
    sys.exit(1)


def print_missing_config(missing_keys: list[str]):
    print("=" * 50)
    print("  配置缺失")
    print("=" * 50)
    print()
    for k in missing_keys:
        name_map = {
            "DEEPSEEK_API_KEY": "DeepSeek API密钥 (改写服务)",
            "ARK_API_KEY": "火山引擎 API密钥 (豆包配图)",
            "NEWSAPI_KEY": "NewsAPI.org 密钥 (新闻采集)",
        }
        print(f"  缺少: {name_map.get(k, k)}")
    print()
    print(f"  请编辑 {PROJECT_DIR / '.env'} 填入上述密钥后重新运行")


def print_result(run_log):
    print()
    print("=" * 50)
    print("  运行结果")
    print("=" * 50)
    print(f"  采集: {run_log.collected} 条")
    print(f"  去重+日期过滤后: {run_log.after_dedup} 条")
    print(f"  生成草稿: {run_log.generated} 篇")
    print(f"  失败: {run_log.failed} 篇")
    print(f"  状态: {run_log.status}")
    print(f"  草稿目录: {PROJECT_DIR / 'drafts'}")
    if run_log.errors:
        print(f"  错误: {run_log.errors[:3]}")
    print("=" * 50)
    print()


if __name__ == "__main__":
    sys.exit(main())
