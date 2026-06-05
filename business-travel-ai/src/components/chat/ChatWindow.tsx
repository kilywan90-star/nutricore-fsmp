"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import MessageBubble from "./MessageBubble";
import type { ChatMessage } from "@/types";

interface ChatWindowProps {
  messages: ChatMessage[];
  isLoading: boolean;
  selectedRestaurantId?: number | null;
  onSelectRestaurant?: (id: number) => void;
}

export default function ChatWindow({ messages, isLoading, selectedRestaurantId, onSelectRestaurant }: ChatWindowProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const isNearBottomRef = useRef(true);

  const scrollToBottom = useCallback((smooth = false) => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: smooth ? "smooth" : "auto",
      });
    }
  }, []);

  // MutationObserver: auto-scroll only if user is near bottom
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;

    const observer = new MutationObserver(() => {
      if (isNearBottomRef.current) {
        el.scrollTop = el.scrollHeight;
      }
    });

    observer.observe(el, {
      childList: true,
      subtree: true,
      characterData: true,
    });

    return () => observer.disconnect();
  }, []);

  // IntersectionObserver on sentinel: track if bottom is visible
  useEffect(() => {
    const sentinel = sentinelRef.current;
    const el = scrollRef.current;
    if (!sentinel || !el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        isNearBottomRef.current = entry.isIntersecting;
        setShowScrollBtn(!entry.isIntersecting);
      },
      { root: el, rootMargin: "100px" }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, []);

  // Scroll on new messages or loading state change (force scroll for user-initiated sends)
  useEffect(() => {
    scrollToBottom();
  }, [messages.length, isLoading, scrollToBottom]);

  return (
    <div className="relative flex-1 min-h-0">
      <div
        ref={scrollRef}
        className="absolute inset-0 overflow-y-auto p-4 space-y-4 chat-scroll"
      >
        {messages.map((msg, i) => (
          <MessageBubble
            key={i}
            message={msg}
            selectedRestaurantId={selectedRestaurantId}
            onSelectRestaurant={onSelectRestaurant}
          />
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="msg-assistant" style={{ padding: "12px 16px", width: "100%", maxWidth: 520 }}>
              <div className="skeleton-card">
                <div className="skeleton-header">
                  <div className="skeleton-circle skeleton-shimmer" />
                  <div style={{ flex: 1 }}>
                    <div className="skeleton-line skeleton-shimmer" style={{ width: "60%", height: 16, marginBottom: 6 }} />
                    <div className="skeleton-line skeleton-shimmer" style={{ width: "40%", height: 10 }} />
                  </div>
                </div>
                <div className="skeleton-body">
                  <div className="skeleton-line skeleton-shimmer" style={{ width: "80%", height: 12, marginBottom: 8 }} />
                  <div className="skeleton-line skeleton-shimmer" style={{ width: "100%", height: 12, marginBottom: 8 }} />
                  <div className="skeleton-line skeleton-shimmer" style={{ width: "50%", height: 12 }} />
                </div>
              </div>
            </div>
          </div>
        )}
        <div ref={sentinelRef} style={{ height: 1 }} />
      </div>

      {showScrollBtn && (
        <button
          className="scroll-to-bottom-btn"
          onClick={() => scrollToBottom(true)}
          aria-label="回到底部"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
            <path d="M10 4v12m0 0l-4-4m4 4l4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      )}
    </div>
  );
}
