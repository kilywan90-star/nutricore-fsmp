"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import ChatWindow from "@/components/chat/ChatWindow";
import InputBar from "@/components/chat/InputBar";
import type { ChatMessage, MatchedRestaurant } from "@/types";

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedRestaurantId, setSelectedRestaurantId] = useState<number | null>(null);
  const sessionIdRef = useRef<string>("");

  useEffect(() => {
    let sid = sessionStorage.getItem("chatSessionId");
    if (!sid) {
      sid = "xxxx-xxxx-xxxx-xxxx".replace(/x/g, () =>
        ((Math.random() * 16) | 0).toString(16)
      );
      sessionStorage.setItem("chatSessionId", sid);
    }
    sessionIdRef.current = sid;

    setMessages([
      {
        role: "assistant",
        content:
          "您好！我是差序，您的商务出行助手。告诉我您的用餐需求，我来为您推荐最合适的餐厅。\n\n比如试试：\"帮我找个上海请客户吃饭的地方，4个人，要有包间\"",
        timestamp: new Date().toISOString(),
      },
    ]);
  }, []);

  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  const handleSend = useCallback(
    async (text: string) => {
      const userMsg: ChatMessage = {
        role: "user",
        content: text,
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);

      try {
        const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
        const currentMessages = messagesRef.current;
        const res = await fetch(`${basePath}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: text,
            sessionId: sessionIdRef.current,
            history: [...currentMessages, userMsg],
          }),
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        const assistantMsg: ChatMessage = {
          role: "assistant",
          content: data.reply,
          recommendations: data.recommendations as MatchedRestaurant[],
          cards: data.cards || [],
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch {
        const errorMsg: ChatMessage = {
          role: "assistant",
          content: "抱歉，服务暂时不可用。请稍后重试。",
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, errorMsg]);
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const handleSelectRestaurant = useCallback((id: number) => {
    setSelectedRestaurantId((prev) => (prev === id ? null : id));
  }, []);

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto w-full">
      <header className="flex items-center justify-center h-14 border-b border-[var(--border)] bg-white px-4 shrink-0">
        <h1 className="text-lg font-semibold text-[var(--foreground)]">
          差序 · 商务出行AI智能助手
        </h1>
      </header>
      <ChatWindow
        messages={messages}
        isLoading={isLoading}
        selectedRestaurantId={selectedRestaurantId}
        onSelectRestaurant={handleSelectRestaurant}
      />
      <InputBar onSend={handleSend} disabled={isLoading} />
    </div>
  );
}
