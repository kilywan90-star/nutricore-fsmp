import { queryDatabase } from "@/lib/matching/path-a-database";
import { getLLMRecommendations } from "@/lib/matching/path-b-llm";
import { getMemoryBoosts } from "@/lib/matching/path-c-memory";
import { crossValidate } from "@/lib/matching/cross-validator";
import { rankRestaurants } from "@/lib/matching/ranker";
import { attachCulturalStories } from "@/lib/cultural/cultural-repository";
import { chatCompletion } from "@/lib/llm/client";
import { buildResponsePrompt } from "@/lib/llm/prompts";
import { searchAmapRestaurants } from "@/lib/amap/client";
import type { DomainResponse, DomainHandler } from "./types";
import type { SearchConstraints, ExtendedNLUSlots, MatchedRestaurant, Restaurant, CulturalStory } from "@/types";

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

  // 2. 多路匹配: A路(DB) + B路(LLM) + C路(记忆) + D路(高德API)
  const [dbCandidates, llmRecs, memoryBoosts, amapResults] = await Promise.all([
    queryDatabase(constraints),
    getLLMRecommendations(constraints, undefined),
    getMemoryBoosts(sessionId),
    searchAmapRestaurants(constraints.city, undefined, constraints.cuisine),
  ]);

  // 2.5 将高德结果合并为 DB 候选格式
  const amapCandidates = amapResults.map((ar): Restaurant => ({
    id: -(Math.abs(hashName(ar.name)) % 100000),
    name: ar.name,
    city: ar.city,
    district: ar.district,
    address: ar.address,
    latitude: ar.latitude,
    longitude: ar.longitude,
    cuisineType: ar.subCategory || ar.category || "未知",
    cuisineTags: [],
    priceRangeMin: ar.avgCost ? Math.round(ar.avgCost * 0.8) : null,
    priceRangeMax: ar.avgCost ? Math.round(ar.avgCost * 1.2) : null,
    privacyLevel: "L2",
    privateRoomMin: null,
    privateRoomMax: null,
    privateRoomCount: null,
    rating: ar.rating,
    sceneTags: [],
    businessTopics: [],
    photoTips: null,
    signatureDishes: [],
    contactPhone: ar.tel,
    openingHours: null,
    reservationNote: null,
  }));
  const allDbCandidates = [
    ...dbCandidates,
    ...amapCandidates.map((r, i) => ({
      restaurant: r,
      matchScore: 30, // 高德结果基础匹配分
      matchedFields: ["amap"],
    })),
  ];

  // 3. 交叉验证
  let validated = await crossValidate(llmRecs, allDbCandidates, constraints.city);

  // 交叉验证后如果没有结果，直接使用DB候选（跳过有问题的LLM推荐）
  if (validated.length === 0 && dbCandidates.length > 0) {
    validated = dbCandidates.map(dc => ({
      restaurant: dc.restaurant,
      verified: true,
      source: "database" as const,
    }));
  }

  // 4. 排序 Top 8
  const ranked = rankRestaurants(validated, allDbCandidates, constraints, memoryBoosts, 8);

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

function hashName(name: string): number {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = ((hash << 5) - hash) + name.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}
