"use client";

import { useState } from "react";
import type { MatchedRestaurant } from "@/types";

const PRIVACY_LABELS: Record<string, string> = {
  L1: "大厅",
  L2: "半隔断",
  L3: "包间",
  L4: "顶级私密",
};

const STORY_TYPE_LABELS: Record<string, string> = {
  "菜品": "招牌菜品",
  "历史": "历史典故",
  "文化": "文化故事",
  "建筑": "建筑特色",
};

interface RestaurantCardProps {
  match: MatchedRestaurant;
  index: number;
  isSelected?: boolean;
  onSelect?: (id: number) => void;
}

export default function RestaurantCard({ match, index, isSelected, onSelect }: RestaurantCardProps) {
  const [storiesExpanded, setStoriesExpanded] = useState(false);
  const r = match.restaurant;

  const rankClass =
    index === 0 ? "rank-gold" : index === 1 ? "rank-silver" : index === 2 ? "rank-bronze" : "";

  const storyTypeClass = (type: string) => {
    if (type === "菜品") return "story-type-dish";
    if (type === "历史") return "story-type-history";
    if (type === "建筑") return "story-type-architecture";
    return "story-type-culture";
  };

  return (
    <div className="restaurant-card">
      {/* 头部: 排名 + 名称 + 验证 */}
      <div className="card-header">
        <div className={`card-rank ${rankClass}`}>{index + 1}</div>
        <div className="flex-1 min-w-0">
          <div className="card-title">{r.name}</div>
          <div className="card-subtitle">
            {r.district && `${r.district} · `}
            {r.address && r.address}
          </div>
        </div>
        <span className={`badge ${match.verified ? "badge-verified" : "badge-unverified"}`}>
          {match.verified ? "已验证" : "待验证"}
        </span>
      </div>

      {/* 卡片主体 */}
      <div className="card-body">
        {/* 标签行 */}
        <div className="card-meta">
          <span className="badge badge-cuisine">{r.cuisineType}</span>
          <span className="badge badge-privacy">{PRIVACY_LABELS[r.privacyLevel] || r.privacyLevel}</span>
          {r.priceRangeMin && r.priceRangeMax && (
            <span className="badge badge-price">
              人均 ¥{r.priceRangeMin}-{r.priceRangeMax}
            </span>
          )}
          {r.rating && (
            <span className="badge badge-rating">
              {r.rating} 分
            </span>
          )}
        </div>

        {/* 招牌菜 */}
        {r.signatureDishes && r.signatureDishes.length > 0 && (
          <div className="dishes-section">
            <div className="dishes-title">招牌菜</div>
            <div className="dishes-list">{r.signatureDishes.slice(0, 4).join(" · ")}</div>
          </div>
        )}

        {/* 场景标签 */}
        {r.sceneTags && r.sceneTags.length > 0 && (
          <div className="meta-item" style={{ marginBottom: 8 }}>
            <span className="meta-label">适合场景</span>
            <span>{r.sceneTags.join("、")}</span>
          </div>
        )}

        {/* 预订提示 */}
        {r.reservationNote && (
          <div className="meta-item">
            <span className="meta-label">预订</span>
            <span>{r.reservationNote}</span>
          </div>
        )}

        {/* LLM 推荐理由 */}
        {match.llmReason && (
          <div className="card-llm-reason">
            {match.llmReason}
          </div>
        )}
      </div>

      {/* 文化故事区 */}
      {match.culturalStories && match.culturalStories.length > 0 && (
        <div className="cultural-stories-section">
          <button
            className="cultural-stories-toggle"
            onClick={() => setStoriesExpanded(!storiesExpanded)}
          >
            <span className={`toggle-icon ${storiesExpanded ? "expanded" : ""}`}>▶</span>
            文化谈资 ({match.culturalStories.length} 篇)
            <span style={{ fontWeight: 400, color: "#9ca3af", fontSize: 12 }}>
              — 用餐时的话题素材
            </span>
          </button>

          {storiesExpanded && (
            <div style={{ padding: "0 4px 12px" }}>
              {match.culturalStories.map((story, i) => (
                <div key={i} className="cultural-story">
                  {/* 故事标题区 */}
                  <div className="story-header">
                    <span className={`story-type-badge ${storyTypeClass(story.storyType)}`}>
                      {STORY_TYPE_LABELS[story.storyType] || story.storyType}
                    </span>
                    <div className="story-title">{story.title}</div>
                  </div>

                  {/* 故事正文 */}
                  <div className="story-content">{story.content}</div>

                  {/* 谈资要点 */}
                  {story.talkingPoints && story.talkingPoints.length > 0 && (
                    <div className="talking-points">
                      <div className="talking-points-title">谈资要点</div>
                      {story.talkingPoints.map((point, j) => (
                        <div key={j} className="talking-point">
                          <span className="point-marker">●</span>
                          <span>{point}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 操作按钮 */}
      <div className="card-footer">
        {isSelected ? (
          <div className="card-selected-panel">
            <div className="card-selected-summary">
              <span className="card-selected-check">&#10003;</span>
              <span className="card-selected-name">{r.name}</span>
            </div>
            <div className="card-selected-details">
              {r.cuisineType} · 人均 ¥{r.priceRangeMin}-{r.priceRangeMax} · {PRIVACY_LABELS[r.privacyLevel] || r.privacyLevel}
            </div>
            <div className="card-selected-actions">
              <button className="card-btn-reserve" onClick={() => alert("预订功能即将上线")}>
                确认预订
              </button>
              <button className="card-btn-cancel" onClick={() => onSelect?.(r.id)}>
                取消选择
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => onSelect?.(r.id)}
            className="px-5 py-2 text-sm rounded-lg bg-[var(--primary)] text-white hover:opacity-90 transition-opacity"
            style={{ fontWeight: 600 }}
          >
            选择这家
          </button>
        )}
      </div>
    </div>
  );
}
