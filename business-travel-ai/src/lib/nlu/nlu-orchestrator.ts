import { classifyIntent } from "./intent-classifier";
import { extractSlots } from "./slot-extractor";
import { regexParse } from "./regex-fallback";
import { generateFollowUp } from "./followup";
import { decomposeMultiIntent } from "./multi-intent-decomposer";
import type { NLUResult, MultiNLUResult, ConversationContext } from "@/types";

/**
 * NLU编排器 — 唯一入口
 * 策略: 多意图检测 → LLM优先 → 正则兜底 → 结果合并
 */
export async function parseUserInput(
  userInput: string,
  context?: ConversationContext
): Promise<NLUResult | MultiNLUResult> {
  const trimmed = userInput.trim();
  if (!trimmed) {
    return {
      intent: "chitchat",
      confidence: 1.0,
      slots: {},
      method: "regex",
      missingSlots: [],
    };
  }

  // === 多意图检测 (优先) ===
  const multiResult = await decomposeMultiIntent(trimmed, context);
  if (multiResult && multiResult.subIntents.length >= 2) {
    return multiResult;
  }

  // === 单意图路径 (原有逻辑不变) ===
  const historyContext = context?.history
    ?.slice(-4)
    .map((m) => `${m.role}: ${m.content}`)
    .join("\n");

  // 并行: LLM意图分类 + 正则解析
  const [llmIntentResult, regexResult] = await Promise.all([
    classifyIntent(trimmed, historyContext),
    Promise.resolve(regexParse(trimmed)),
  ]);

  let result: NLUResult;

  // 服务意图集合 (非 chitchat 的具体业务意图)
  const SERVICE_INTENTS = new Set([
    "dining_recommend", "entertainment_recommend", "flight_search",
    "train_search", "car_service", "pickup_service", "shopping_recommend",
    "booking", "trip_plan",
  ]);

  // 交叉验证: LLM说chitchat但regex发现高置信度服务意图 → 信任regex
  const llmSaysChitchat = llmIntentResult?.intent === "chitchat";
  const regexFoundService = SERVICE_INTENTS.has(regexResult.intent) && regexResult.confidence >= 0.6;

  if (llmIntentResult && llmIntentResult.confidence >= 0.6 && !(llmSaysChitchat && regexFoundService)) {
    // LLM成功 且 没有被regex交叉验证否决 → 尝试LLM槽位提取
    const llmSlots = await extractSlots(trimmed, llmIntentResult.intent);

    if (llmSlots) {
      // LLM意图+槽位都成功: 用LLM结果, regex填补缺失
      // regex的隐私等级优先(LLM对中文隐私描述识别不如regex敏感)
      const mergedSlots = { ...regexResult.slots, ...llmSlots };
      if (regexResult.slots.privacy) {
        mergedSlots.privacy = regexResult.slots.privacy;
      }
      result = {
        intent: llmIntentResult.intent,
        confidence: llmIntentResult.confidence,
        slots: mergedSlots,
        method: "llm",
        missingSlots: [],
      };
    } else {
      // LLM意图成功, 槽位失败: 用LLM意图 + regex槽位
      result = {
        intent: llmIntentResult.intent,
        confidence: llmIntentResult.confidence,
        slots: regexResult.slots,
        method: "llm",
        missingSlots: [],
      };
    }
  } else {
    // LLM失败/置信度低/被交叉验证否决 → 完全使用regex
    result = { ...regexResult };
  }

  // modify_plan时合并上下文槽位
  if (result.intent === "modify_plan" && context?.currentSlots) {
    result.slots = { ...context.currentSlots, ...result.slots };
  }

  // 计算缺失槽位
  const followUp = generateFollowUp(result.intent, result.slots);
  result.missingSlots = followUp.missingSlots;

  return result;
}
