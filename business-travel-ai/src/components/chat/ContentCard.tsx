"use client";

import { useState } from "react";
import type { ContentCard as ContentCardType, CulturalStory, ServiceCulturalStory } from "@/types";

const PRIVACY_LABELS: Record<string, string> = {
  L1: "大厅",
  L2: "半隔断",
  L3: "包间",
  L4: "顶级私密",
};

const CATEGORY_LABELS: Record<string, string> = {
  restaurant: "餐厅",
  dance_hall: "舞厅",
  ktv: "KTV",
  bath: "洗浴",
  massage: "按摩",
  hotel: "酒店",
  attraction: "景点",
  shopping: "购物",
};

interface ContentCardProps {
  data: ContentCardType;
  index: number;
  isSelected?: boolean;
  onSelect?: (id: number) => void;
}

function isCulturalStory(s: CulturalStory | ServiceCulturalStory): s is CulturalStory {
  return "restaurantId" in s;
}

export default function ContentCard({ data, index, isSelected, onSelect }: ContentCardProps) {
  const [storiesExpanded, setStoriesExpanded] = useState(false);
  const { title, subtitle, rating, priceRangeMin, priceRangeMax, privacyLevel, sceneTags, description, highlights, culturalStories, contactPhone, openingHours, category } = data;

  const rankClass =
    index === 0 ? "rank-gold" : index === 1 ? "rank-silver" : index === 2 ? "rank-bronze" : "";

  const starDisplay = category === "hotel" && data.extras?.starLevel
    ? "★".repeat(Number(data.extras.starLevel)) + "☆".repeat(5 - Number(data.extras.starLevel))
    : null;

  return (
    <div className={`content-card ${category}`}>
      {/* Header */}
      <div className="card-header">
        <div className={`card-rank ${rankClass}`}>{index + 1}</div>
        <div className="flex-1 min-w-0">
          <div className="card-title">
            {title}
            {starDisplay && <span style={{ color: "#f59e0b", marginLeft: 8, fontSize: 14 }}>{starDisplay}</span>}
          </div>
          <div className="card-subtitle">{subtitle}</div>
        </div>
        <span className="badge badge-category">{CATEGORY_LABELS[category] || category}</span>
      </div>

      {/* Body */}
      <div className="card-body">
        <div className="card-meta">
          {data.extras?.cuisineType && (
            <span className="badge badge-cuisine">{String(data.extras.cuisineType)}</span>
          )}
          {privacyLevel && (
            <span className="badge badge-privacy">{PRIVACY_LABELS[privacyLevel] || privacyLevel}</span>
          )}
          {priceRangeMin != null && priceRangeMax != null && (
            <span className="badge badge-price">人均 ¥{priceRangeMin}-{priceRangeMax}</span>
          )}
          {rating > 0 && (
            <span className="badge badge-rating">{rating} 分</span>
          )}
          {category === "attraction" && data.extras?.durationMin && (
            <span className="badge" style={{ background: "#e0f2fe", color: "#0369a1" }}>
              约 {String(data.extras.durationMin)} 分钟
            </span>
          )}
          {category === "hotel" && data.extras?.meetingRooms != null && (
            <span className="badge" style={{ background: "#ede9fe", color: "#5b21b6" }}>
              {String(data.extras.meetingRooms)} 间会议室
            </span>
          )}
        </div>

        {highlights.length > 0 && (
          <div className="dishes-section">
            <div className="dishes-title">
              {["restaurant", "shopping"].includes(category) ? "招牌菜" : "特色亮点"}
            </div>
            <div className="dishes-list">{highlights.slice(0, 4).join(" · ")}</div>
          </div>
        )}

        {sceneTags.length > 0 && (
          <div className="meta-item" style={{ marginBottom: 8 }}>
            <span className="meta-label">适合场景</span>
            <span>{sceneTags.join("、")}</span>
          </div>
        )}

        {category === "attraction" && data.extras?.tips && (
          <div className="meta-item" style={{ marginBottom: 8 }}>
            <span className="meta-label">游览贴士</span>
            <span style={{ color: "#166534" }}>{String(data.extras.tips)}</span>
          </div>
        )}

        {openingHours && (
          <div className="meta-item">
            <span className="meta-label">营业时间</span>
            <span>{openingHours}</span>
          </div>
        )}

        {description && (
          <div className="card-llm-reason">{description}</div>
        )}
      </div>

      {/* Cultural Stories */}
      {culturalStories && culturalStories.length > 0 && (
        <div className="cultural-stories-section">
          <button
            className="cultural-stories-toggle"
            onClick={() => setStoriesExpanded(!storiesExpanded)}
          >
            <span className={`toggle-icon ${storiesExpanded ? "expanded" : ""}`}>▶</span>
            文化谈资 ({culturalStories.length} 篇)
            <span style={{ fontWeight: 400, color: "#9ca3af", fontSize: 12 }}>
              {" "}— 用餐时的话题素材
            </span>
          </button>

          {storiesExpanded && (
            <div style={{ padding: "0 4px 12px" }}>
              {culturalStories.map((story, i) => (
                <div key={i} className="cultural-story">
                  <div className="story-header">
                    <span className={`story-type-badge story-type-${String(story.storyType)}`}>
                      {String(story.storyType)}
                    </span>
                    <div className="story-title">{story.title}</div>
                  </div>
                  <div className="story-content">{story.content}</div>
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

      {/* Footer */}
      <div className="card-footer">
        {isSelected ? (
          <div className="card-selected-panel">
            <div className="card-selected-summary">
              <span className="card-selected-check">&#10003;</span>
              <span className="card-selected-name">{title}</span>
            </div>
            <div className="card-selected-actions">
              <button className="card-btn-reserve" onClick={() => alert("预订功能即将上线")}>
                确认预订
              </button>
              <button className="card-btn-cancel" onClick={() => onSelect?.(data.id)}>
                取消选择
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => onSelect?.(data.id)}
            className="select-btn"
          >
            选择这家
          </button>
        )}
      </div>
    </div>
  );
}
