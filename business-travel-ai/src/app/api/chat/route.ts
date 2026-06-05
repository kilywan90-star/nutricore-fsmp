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
import type { ChatMessage, RecommendResponse, MultiIntentResponse, SubResult, NLUResult, MultiNLUResult, ExtendedNLUSlots, ExtendedIntent } from "@/types";

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
      return NextResponse.json({ error: "消息不能为空" }, { status: 400 });
    }

    const historySlots = extractSlotsFromHistory(history);
    const short = message.trim();

    const shortNum = /^\d+$/.test(short);
    const shortCuisine = /^(火锅|川菜|粤菜|湘菜|日料|西餐|烧烤|海鲜|素食|清真)$/.test(short);
    const shortPref = /^(包间|大厅|安静|随便)$/.test(short);
    const isShortAnswer = shortNum || shortCuisine || shortPref;

    if (isShortAnswer && historySlots.city) {
      const fullSlots: ExtendedNLUSlots = { ...historySlots };
      if (shortNum) fullSlots.guestCount = parseInt(short);
      if (shortCuisine) fullSlots.cuisine = short;
      if (shortPref && short === "包间") fullSlots.privacy = "L3";
      if (shortPref && short === "大厅") fullSlots.privacy = "L1";

      const nlu: NLUResult = { intent: "dining_recommend", confidence: 0.9, slots: fullSlots, method: "regex", missingSlots: [] };
      const domainResult = await routeToDomain(nlu, sessionId);
      const recs = isDiningData(domainResult.data) ? domainResult.data : [];
      const cards = toContentCards(domainResult.data, "dining_recommend");
      const resp: RecommendResponse = {
        reply: domainResult.reply, recommendations: recs, cards,
        followupQuestion: domainResult.followupQuestion ?? null,
        nluDebug: { intent: "dining_recommend", slots: fullSlots, method: "regex", confidence: 0.9 },
      };
      await saveHistory(sessionId, message, domainResult.reply, nlu);
      return NextResponse.json(resp);
    }

    const nluResult = await parseUserInput(message, { sessionId, currentSlots: historySlots, history });

    if (isMultiIntent(nluResult)) {
      return handleMultiIntent(nluResult, sessionId, message);
    }

    const singleResult = nluResult as NLUResult;
    const mergedSlots = { ...historySlots, ...singleResult.slots } as ExtendedNLUSlots;
    const followUp = generateFollowUp(singleResult.intent, mergedSlots);

    if (followUp.question) {
      const reply = followUp.question;
      const response: RecommendResponse = {
        reply, recommendations: [], followupQuestion: null,
        nluDebug: { intent: singleResult.intent, slots: mergedSlots, method: singleResult.method, confidence: singleResult.confidence },
      };
      await saveHistory(sessionId, message, reply, { ...singleResult, slots: mergedSlots });
      return NextResponse.json(response);
    }

    const domainResult = await routeToDomain(singleResult, sessionId);
    const recommendations = isDiningData(domainResult.data) ? domainResult.data : [];
    const cards = toContentCards(domainResult.data, singleResult.intent);
    const response: RecommendResponse = {
      reply: domainResult.reply, recommendations, cards,
      followupQuestion: domainResult.followupQuestion ?? followUp.question ?? null,
      nluDebug: { intent: singleResult.intent, slots: mergedSlots, method: singleResult.method, confidence: singleResult.confidence },
    };
    await saveHistory(sessionId, message, domainResult.reply, { ...singleResult, slots: mergedSlots });
    return NextResponse.json(response);
  } catch (err) {
    console.error("[chat] Error:", err);
    return NextResponse.json({ error: "服务暂时不可用，请稍后重试" }, { status: 500 });
  }
}

async function saveHistory(sessionId: string, userMessage: string, assistantReply: string, nluResult: unknown) {
  try {
    await db.insert(conversationHistory).values([
      { sessionId, role: "user", content: userMessage },
      { sessionId, role: "assistant", content: assistantReply, nluResult: nluResult as never },
    ]);
  } catch (err) { console.error("[chat] Failed to save history:", err); }
}

async function handleMultiIntent(multiResult: MultiNLUResult, sessionId: string, originalMessage: string): Promise<NextResponse> {
  const subResults: SubResult[] = await Promise.all(
    multiResult.subIntents.map(async (si) => {
      const nluForSub: NLUResult = { intent: si.intent, confidence: si.confidence, slots: si.slots, method: "llm", missingSlots: si.missingSlots };
      const domainResponse = await routeToDomain(nluForSub, sessionId);
      return domainResponseToSubResult(domainResponse, si.intent as ExtendedIntent);
    })
  );
  let itinerary = null;
  if (multiResult.subIntents.length >= 3) {
    try { itinerary = await generateItinerary(sessionId, multiResult, subResults); } catch {}
  }
  const reply = composeMultiIntentReply(subResults, itinerary);
  const response: MultiIntentResponse = {
    reply, isMultiIntent: true, subResults, itinerary: itinerary ?? undefined, followupQuestion: null,
    nluDebug: { sharedContext: multiResult.sharedContext, subIntents: multiResult.subIntents.map(si => ({ intent: si.intent, confidence: si.confidence, sourceSegment: si.sourceSegment })), method: multiResult.method },
  };
  await saveHistory(sessionId, originalMessage, reply, multiResult);
  return NextResponse.json(response);
}

function composeMultiIntentReply(subResults: SubResult[], itinerary: { itineraryId: number; items: Array<Record<string, unknown>> } | null): string {
  const parts: string[] = [];
  for (const sr of subResults) {
    const label = getIntentLabel(sr.intent);
    if (sr.status === "success") {
      const data = sr.data as Record<string, unknown> | unknown[] | null;
      if (Array.isArray(data) && data.length > 0) parts.push(`- ${label}: 已为您找到${data.length}个结果`);
      else if (data && typeof data === "object" && "routes" in data) parts.push(`- ${label}: 已为您找到${(data as { routes: unknown[] }).routes.length}条线路`);
      else if (data && typeof data === "object" && "message" in data) parts.push(`- ${label}: ${(data as { message: string }).message}`);
      else parts.push(`- ${label}: 已处理`);
    } else parts.push(`- ${label}: ${sr.error || "处理失败"}`);
  }
  let reply = `已为您处理${subResults.length}项需求：\n${parts.join("\n")}`;
  if (itinerary) reply += `\n\n已为您生成行程时间轴（共${itinerary.items.length}项），行程ID: ${itinerary.itineraryId}`;
  return reply;
}

function extractSlotsFromHistory(history: ChatMessage[]): ExtendedNLUSlots {
  const accumulated: ExtendedNLUSlots = {};
  for (const msg of history.filter(m => m.role === "user")) {
    try {
      const result = regexParse(msg.content);
      if (result.slots) {
        for (const [key, value] of Object.entries(result.slots)) {
          if (value !== undefined && value !== null && value !== "") (accumulated as Record<string, unknown>)[key] = value;
        }
      }
    } catch {}
  }
  return accumulated;
}
