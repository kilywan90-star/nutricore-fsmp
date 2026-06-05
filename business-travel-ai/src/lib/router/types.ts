import type { NLUResult } from "@/types";

// ============================================================
// 业务域分层路由 — 类型定义
// ============================================================

export type Domain =
  | "DINING"
  | "ENTERTAINMENT"
  | "TRANSPORT"
  | "SHOPPING"
  | "SIMPLE"
  | "PLANNING"
  | "UNKNOWN";

export interface DomainResponse {
  reply: string;
  data?: unknown;
  followupQuestion?: string | null;
}

export type DomainHandler = (
  nluResult: NLUResult,
  sessionId: string
) => Promise<DomainResponse>;
