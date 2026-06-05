"use client";

import RestaurantCard from "./RestaurantCard";
import ContentCard from "./ContentCard";
import type { ChatMessage } from "@/types";

interface MessageBubbleProps {
  message: ChatMessage;
  selectedRestaurantId?: number | null;
  onSelectRestaurant?: (id: number) => void;
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return "刚刚";
  if (diffMin < 60) return `${diffMin}分钟前`;

  const h = date.getHours().toString().padStart(2, "0");
  const m = date.getMinutes().toString().padStart(2, "0");
  return `${h}:${m}`;
}

export default function MessageBubble({ message, selectedRestaurantId, onSelectRestaurant }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={isUser ? "msg-user" : "msg-assistant"}>
        <p className="whitespace-pre-wrap text-sm leading-relaxed">
          {message.content}
        </p>
        {message.recommendations && message.recommendations.length > 0 && (
          <div className="mt-3 space-y-3">
            {message.recommendations.map((rec, i) => (
              <RestaurantCard
                key={i}
                match={rec}
                index={i}
                isSelected={selectedRestaurantId === rec.restaurant.id}
                onSelect={onSelectRestaurant}
              />
            ))}
          </div>
        )}
        {message.cards && message.cards.length > 0 && (
          <div className="mt-3 space-y-3">
            {message.cards.map((card, i) => (
              <ContentCard
                key={`card-${i}`}
                data={card}
                index={i}
                isSelected={selectedRestaurantId === card.id}
                onSelect={onSelectRestaurant}
              />
            ))}
          </div>
        )}
        <div className={`msg-timestamp ${isUser ? "msg-timestamp-right" : ""}`}>
          {formatTimestamp(message.timestamp)}
        </div>
      </div>
    </div>
  );
}
