import { NextResponse } from "next/server";
import { parseUserInput } from "@/lib/nlu/nlu-orchestrator";
import { generateFollowUp } from "@/lib/nlu/followup";
import { db } from "@/db";
import { conversationHistory } from "@/db/schema";
import { isMultiIntent } from "@/types";
import { generateItinerary } from "@/lib/itinerary/itinerary-engine";
import { regexParse } from "@/lib/nlu/regex-fallback";
import { routeToDomain, domainResponseToSubResult, isDiningData, toContentCards } from "@/lib/router/domain-router";
import { getIntentLabel } from "@/lib/router/domain-map";
import type { ChatMessage, RecommendResponse, MultiIntentResponse, SubResult, NLUResult, MultiNLUResult, ExtendedNLUSlots, ExtendedIntent, ContentCard } from "@/types";

interface ChatRequest {
  message: string;
  sessionId: string;
  history?: ChatMessage[];
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as ChatRequest;
    const { message, sessionId: rawSessionId, history = [] } = body;
    const sessionId = rawSessionId || `anon-${Date.now()}`;

    if (!message?.trim()) {
      return NextResponse.json(
        { error: "消息不能为空" },
        { status: 400 }
      );
    }

    // 从对话历史中提取累积槽位
    const accumulatedSlots = extractSlotsFromHistory(history);

    // 1. NLU解析
    const nluResult = await parseUserInput(message, {
      sessionId,
      currentSlots: accumulatedSlots,
      history,
    });

    // === 多意图分支 ===
    if (isMultiIntent(nluResult)) {
      return handleMultiIntent(nluResult, sessionId, message);
    }

    // 2. 追问检查 (单意图路径)
    const singleResult = nluResult as NLUResult;
    const mergedSlots = { ...accumulatedSlots, ...singleResult.slots } as ExtendedNLUSlots;
    const followUp = generateFollowUp(singleResult.intent, mergedSlots);

    if (followUp.question) {
      const reply = followUp.question;
      const response: RecommendResponse = {
        reply,
        recommendations: [],
        followupQuestion: null,
        nluDebug: {
          intent: singleResult.intent,
          slots: mergedSlots,
          method: singleResult.method,
          confidence: singleResult.confidence,
        },
      };
      await saveHistory(sessionId, message, reply, { ...singleResult, slots: mergedSlots });
      return NextResponse.json(response);
    }

    // 3. 域路由分发
    const domainResult = await routeToDomain(singleResult, sessionId);

    // 4. 构建前端兼容的响应
    const recommendations = isDiningData(domainResult.data)
      ? domainResult.data
      : [];
    const cards = toContentCards(domainResult.data, singleResult.intent);

    const response: RecommendResponse = {
      reply: domainResult.reply,
      recommendations,
      cards,
      followupQuestion: domainResult.followupQuestion ?? followUp.question ?? null,
      nluDebug: {
        intent: singleResult.intent,
        slots: mergedSlots,
        method: singleResult.method,
        confidence: singleResult.confidence,
      },
    };

    await saveHistory(sessionId, message, domainResult.reply, { ...singleResult, slots: mergedSlots });
    return NextResponse.json(response);
  } catch (err) {
    console.error("[chat] Error:", err);
    return NextResponse.json(
      { error: "服务暂时不可用，请稍后重试" },
      { status: 500 }
    );
  }
}

// ============================================================
// 辅助函数
// ============================================================

async function saveHistory(
  sessionId: string,
  userMessage: string,
  assistantReply: string,
  nluResult: unknown
) {
  try {
    await db.insert(conversationHistory).values([
      { sessionId, role: "user", content: userMessage },
      {
        sessionId,
        role: "assistant",
        content: assistantReply,
        nluResult: nluResult as never,
      },
    ]);
  } catch (err) {
    console.error("[chat] Failed to save history:", err);
  }
}

// ============================================================
// 多意图处理逻辑
// ============================================================

async function handleMultiIntent(
  multiResult: MultiNLUResult,
  sessionId: string,
  originalMessage: string
): Promise<NextResponse> {
  // 1. 并行执行所有子意图的域路由
  const subResults: SubResult[] = await Promise.all(
    multiResult.subIntents.map(async (si) => {
      const nluForSub: NLUResult = {
        intent: si.intent,
        confidence: si.confidence,
        slots: si.slots,
        method: "llm",
        missingSlots: si.missingSlots,
      };
      const domainResponse = await routeToDomain(nluForSub, sessionId);
      return domainResponseToSubResult(domainResponse, si.intent as ExtendedIntent);
    })
  );

  // 2. 如果子意图 >= 3，生成行程时间轴
  let itinerary = null;
  if (multiResult.subIntents.length >= 3) {
    try {
      itinerary = await generateItinerary(sessionId, multiResult, subResults);
    } catch (err) {
      console.error("[chat] Itinerary generation failed:", err);
    }
  }

  // 3. 组合回复
  const reply = composeMultiIntentReply(subResults, itinerary);

  const response: MultiIntentResponse = {
    reply,
    isMultiIntent: true,
    subResults,
    itinerary: itinerary ?? undefined,
    followupQuestion: null,
    nluDebug: {
      sharedContext: multiResult.sharedContext,
      subIntents: multiResult.subIntents.map((si) => ({
        intent: si.intent,
        confidence: si.confidence,
        sourceSegment: si.sourceSegment,
      })),
      method: multiResult.method,
    },
  };

  await saveHistory(sessionId, originalMessage, reply, multiResult);
  return NextResponse.json(response);
}

function composeMultiIntentReply(
  subResults: SubResult[],
  itinerary: { itineraryId: number; items: Array<Record<string, unknown>> } | null
): string {
  const parts: string[] = [];

  for (const sr of subResults) {
    const label = getIntentLabel(sr.intent);
    if (sr.status === "success") {
      const data = sr.data as Record<string, unknown> | unknown[] | null;
      if (Array.isArray(data) && data.length > 0) {
        parts.push(`- ${label}: 已为您找到${data.length}个结果`);
      } else if (data && typeof data === "object" && "routes" in data) {
        const routes = (data as { routes: unknown[] }).routes;
        parts.push(`- ${label}: 已为您找到${routes.length}条线路`);
      } else if (data && typeof data === "object" && "message" in data) {
        parts.push(`- ${label}: ${(data as { message: string }).message}`);
      } else {
        parts.push(`- ${label}: 已处理`);
      }
    } else {
      parts.push(`- ${label}: ${sr.error || "处理失败"}`);
    }
  }

  let reply = `已为您处理${subResults.length}项需求：\n${parts.join("\n")}`;

  if (itinerary) {
    reply += `\n\n已为您生成行程时间轴（共${itinerary.items.length}项），行程ID: ${itinerary.itineraryId}`;
  }

  return reply;
}

// ============================================================
// 从对话历史中提取累积槽位
// ============================================================

function extractSlotsFromHistory(history: ChatMessage[]): ExtendedNLUSlots {
  const accumulated: ExtendedNLUSlots = {};

  const userMessages = history.filter((m) => m.role === "user");
  for (const msg of userMessages) {
    try {
      const result = regexParse(msg.content);
      if (result.slots) {
        const slots = result.slots as Record<string, unknown>;
        for (const [key, value] of Object.entries(slots)) {
          if (value !== undefined && value !== null && value !== "") {
            (accumulated as Record<string, unknown>)[key] = value;
          }
        }
      }
    } catch {
      // 忽略解析错误
    }
  }

  return accumulated;
}
