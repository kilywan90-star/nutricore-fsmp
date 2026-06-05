import { segmentCompoundSentence } from "./segmenter";
import { regexParse } from "./regex-fallback";
import { classifyIntent } from "./intent-classifier";
import type {
  ExtendedIntent,
  ExtendedNLUSlots,
  SubIntent,
  SharedContext,
  MultiNLUResult,
  ConversationContext,
} from "@/types";

// ============================================================
// 多意图分解器
// 将复合句拆解为多个独立子意图，共享上下文传播
// ============================================================

// 非服务意图的片段 (时间约束、会议等) — 不作为独立子意图
const NON_SERVICE_INTENTS: Set<ExtendedIntent> = new Set([
  "chitchat",
  "query_restaurant",
  "modify_plan",
  "booking",
]);

// 会议/时间约束关键词
const MEETING_PATTERNS = [
  /开会|会议|会面|洽谈|签约|面试|汇报/,
  /\d+点|([一二三四五六七八九十]+)点/,
];

function isMeetingConstraint(text: string): boolean {
  return MEETING_PATTERNS.every((p) => p.test(text));
}

/**
 * 从完整输入中提取共享上下文
 */
function extractSharedContext(input: string, segments: string[]): SharedContext {
  const ctx: SharedContext = { extractedFromOriginalInput: input };

  // 从完整输入提取城市 (优先用完整输入，覆盖面更广)
  const fullRegex = regexParse(input);
  const fullSlots = fullRegex.slots as ExtendedNLUSlots;

  if (fullSlots.city) ctx.city = fullSlots.city;
  if (fullSlots.arrivalCity) ctx.city = fullSlots.arrivalCity;
  if (fullSlots.date) ctx.date = fullSlots.date;
  if (fullSlots.guestProfile) ctx.guestProfile = fullSlots.guestProfile;

  // 提取目的
  if (/(出差|商务|出行)/.test(input)) ctx.purpose = "商务出行";
  else if (/(旅行|旅游|度假)/.test(input)) ctx.purpose = "休闲旅行";

  // 提取会议时间约束
  for (const seg of segments) {
    if (isMeetingConstraint(seg)) {
      const timeMatch = seg.match(/([一二两三四五六七八九十\d]+)点/);
      if (timeMatch) {
        const segResult = regexParse(seg);
        if (segResult.slots.time) {
          ctx.meetingTime = segResult.slots.time;
        }
      }
    }
  }

  return ctx;
}

/**
 * 对单个子句进行意图分类和槽位提取
 */
async function classifySegment(
  segment: string
): Promise<{ intent: ExtendedIntent; confidence: number; slots: ExtendedNLUSlots } | null> {
  // 并行: LLM + regex
  const [llmResult, regexResult] = await Promise.all([
    classifyIntent(segment),
    Promise.resolve(regexParse(segment)),
  ]);

  if (llmResult && llmResult.confidence >= 0.6) {
    return {
      intent: llmResult.intent,
      confidence: llmResult.confidence,
      slots: regexResult.slots as ExtendedNLUSlots,
    };
  }

  // regex 兜底
  if (regexResult.confidence > 0.3) {
    return {
      intent: regexResult.intent as ExtendedIntent,
      confidence: regexResult.confidence,
      slots: regexResult.slots as ExtendedNLUSlots,
    };
  }

  return null;
}

/**
 * 将共享上下文前向填充到子意图槽位 (不覆盖已有值)
 */
function forwardFillContext(
  slots: ExtendedNLUSlots,
  ctx: SharedContext
): ExtendedNLUSlots {
  const filled = { ...slots };

  if (!filled.city && ctx.city) filled.city = ctx.city;
  if (!filled.date && ctx.date) filled.date = ctx.date;
  if (!filled.guestProfile && ctx.guestProfile) filled.guestProfile = ctx.guestProfile;

  // 到达城市作为餐饮/娱乐的城市
  if (!filled.city && ctx.arrivalCity) filled.city = ctx.arrivalCity;

  return filled;
}

/**
 * 主入口: 分解多意图输入
 * @returns MultiNLUResult 如果不是复合句则返回 null
 */
export async function decomposeMultiIntent(
  input: string,
  _context?: ConversationContext
): Promise<MultiNLUResult | null> {
  // Step 1: 分割句子
  const { segments, wasCompound } = segmentCompoundSentence(input);
  if (!wasCompound) return null;

  // Step 2: 提取共享上下文
  const sharedContext = extractSharedContext(input, segments);

  // Step 3: 并行分类每个子句
  const classifications = await Promise.all(
    segments.map((seg) => classifySegment(seg))
  );

  // Step 4: 构建子意图列表 (过滤掉非服务意图和会议约束)
  const subIntents: SubIntent[] = [];
  let siCounter = 0;

  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i];
    const cls = classifications[i];

    // 跳过分类失败的片段
    if (!cls) continue;

    // 会议约束片段: 不生成子意图，上下文已提取
    if (isMeetingConstraint(seg) && !cls.slots.cuisine && !cls.slots.entertainmentType) {
      continue;
    }

    // 跳过非服务意图 (chitchat等)
    if (NON_SERVICE_INTENTS.has(cls.intent)) continue;

    siCounter++;
    const filledSlots = forwardFillContext(cls.slots, sharedContext);

    subIntents.push({
      id: `si-${siCounter}`,
      intent: cls.intent,
      confidence: cls.confidence,
      slots: filledSlots,
      sourceSegment: seg,
      missingSlots: [],
      status: "pending",
    });
  }

  // 如果有效子意图 < 2，不算多意图
  if (subIntents.length < 2) return null;

  // Step 5: 去重 (相同意图+重叠槽位)
  const deduped = deduplicateIntents(subIntents);

  // Step 6: 如果 3+ 子意图或含行程关键词，添加 trip_plan 元意图
  if (deduped.length >= 3 || /(安排行程|出差计划|行程安排|帮我安排.{5,})/.test(input)) {
    // trip_plan 作为响应格式的提示，不额外加入 subIntents
    // 调用方通过 subIntents.length 判断是否需要生成行程
  }

  return {
    isMultiIntent: true,
    subIntents: deduped,
    sharedContext,
    method: "hybrid",
    rawInput: input,
  };
}

/**
 * 去重: 合并相同意图+重叠槽位的子意图
 */
function deduplicateIntents(intents: SubIntent[]): SubIntent[] {
  const seen = new Map<string, SubIntent>();

  for (const si of intents) {
    const key = si.intent;
    const existing = seen.get(key);

    if (!existing) {
      seen.set(key, si);
      continue;
    }

    // 保留置信度更高的
    if (si.confidence > existing.confidence) {
      // 合并槽位 (新值覆盖空值)
      const mergedSlots = { ...existing.slots };
      for (const [k, v] of Object.entries(si.slots)) {
        if (v !== undefined && (mergedSlots as Record<string, unknown>)[k] === undefined) {
          (mergedSlots as Record<string, unknown>)[k] = v;
        }
      }
      seen.set(key, { ...si, slots: mergedSlots });
    }
  }

  return Array.from(seen.values());
}
