import { queryDatabase } from "@/lib/matching/path-a-database";
import { getLLMRecommendations } from "@/lib/matching/path-b-llm";
import { getMemoryBoosts } from "@/lib/matching/path-c-memory";
import { crossValidate } from "@/lib/matching/cross-validator";
import { rankRestaurants } from "@/lib/matching/ranker";
import { attachCulturalStories } from "@/lib/cultural/cultural-repository";
import { chatCompletion } from "@/lib/llm/client";
import { buildResponsePrompt } from "@/lib/llm/prompts";
import type { DomainResponse, DomainHandler } from "./types";
import type { SearchConstraints, ExtendedNLUSlots, MatchedRestaurant } from "@/types";

// ============================================================
// 餐饮域处理器
// 从 route.ts 提取的完整 3-path 推荐管线
// ============================================================

export const handleDining: DomainHandler = async (nluResult, sessionId): Promise<DomainResponse> => {
  const slots = nluResult.slots as ExtendedNLUSlots;

  // 1. 构建搜索约束
  const constraints: SearchConstraints = {
    city: slots.city || "上海",
    guestCount: slots.guestCount || 2,
    date: slots.date,
    time: slots.time,
    budgetPerPerson: slots.budgetPerPerson,
    budgetMax: slots.budgetMax,
    cuisine: slots.cuisine,
    privacyMin: slots.privacy,
    scene: slots.scene,
    dietaryRestrictions: slots.dietaryRestrictions,
  };

  // 2. 多路匹配 (并行A路+B路+C路)
  const [dbCandidates, llmRecs, memoryBoosts] = await Promise.all([
    queryDatabase(constraints),
    getLLMRecommendations(constraints, undefined),
    getMemoryBoosts(sessionId),
  ]);

  // 3. 交叉验证
  const validated = await crossValidate(llmRecs, dbCandidates, constraints.city);

  // 4. 排序 Top 8
  const ranked = rankRestaurants(validated, dbCandidates, constraints, memoryBoosts, 8);

  // 5. 附加文化故事 (P0-3隔离层)
  const enriched = await attachCulturalStories(ranked);

  // 6. 生成自然语言回复
  let reply: string;
  try {
    const promptMessages = buildResponsePrompt(enriched, nluResult.slots, null);
    reply = await chatCompletion(promptMessages, { temperature: 0.7, timeout: 8000 });
  } catch {
    if (enriched.length > 0) {
      reply = `为您找到${enriched.length}家推荐餐厅：\n${enriched.map((r, i) => `${i + 1}. ${r.restaurant.name}（${r.restaurant.cuisineType}，${r.restaurant.privacyLevel}，人均¥${r.restaurant.priceRangeMin}-${r.restaurant.priceRangeMax}）`).join("\n")}`;
    } else {
      reply = "抱歉，暂时没有找到符合您需求的餐厅。请尝试调整条件。";
    }
  }

  return {
    reply,
    data: enriched as MatchedRestaurant[],
  };
};
