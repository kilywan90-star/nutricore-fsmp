"use client";

import { useEffect } from "react";

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function Error({ error, reset }: ErrorProps) {
  useEffect(() => {
    console.error("[ErrorBoundary]", error);
  }, [error]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] p-8">
      <div className="text-5xl mb-4" style={{ color: "var(--text-secondary)" }}>
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>
      <h2 className="text-lg font-semibold mb-2" style={{ color: "var(--text)" }}>
        页面出错了
      </h2>
      <p className="text-sm mb-6 text-center" style={{ color: "var(--text-secondary)", maxWidth: 400 }}>
        {error.message || "应用遇到了意外错误，请尝试重新加载。"}
      </p>
      <button
        onClick={reset}
        className="px-6 py-2 text-sm font-medium rounded-lg text-white"
        style={{ background: "var(--primary)" }}
      >
        重试
      </button>
    </div>
  );
}
