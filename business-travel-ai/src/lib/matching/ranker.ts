import type { MatchedRestaurant, SearchConstraints } from "@/types";
import type { CrossValidatedResult } from "./cross-validator";
import type { DatabaseCandidate } from "./path-a-database";
import type { MemoryBoost } from "./path-c-memory";

const PRIVACY_ORDER: Record<string, number> = { L1: 1, L2: 2, L3: 3, L4: 4 };

interface RankerInput {
  candidate: CrossValidatedResult;
  dbMatchScore: number;
  memoryBoosts: MemoryBoost[];
}

export function rankRestaurants(
  validated: CrossValidatedResult[],
  dbCandidates: DatabaseCandidate[],
  constraints: SearchConstraints,
  memoryBoosts: MemoryBoost[],
  topN: number = 3
): MatchedRestaurant[] {
  const inputs: RankerInput[] = validated.map((v) => {
    const dbCandidate = dbCandidates.find(
      (c) => c.restaurant.id === v.restaurant.id
    );
    return {
      candidate: v,
      dbMatchScore: dbCandidate?.matchScore ?? 0,
      memoryBoosts,
    };
  });

  // 添加纯DB候选 (不在LLM推荐中的)
  const validatedIds = new Set(validated.map((v) => v.restaurant.id));
  for (const dc of dbCandidates) {
    if (!validatedIds.has(dc.restaurant.id)) {
      inputs.push({
        candidate: {
          restaurant: dc.restaurant,
          verified: true,
          source: "database",
        },
        dbMatchScore: dc.matchScore,
        memoryBoosts,
      });
    }
  }

  const scored: MatchedRestaurant[] = inputs.map((input) => {
    const { candidate, dbMatchScore, memoryBoosts: boosts } = input;
    const r = candidate.restaurant;

    // 基础分: rating * 20 (0-100)
    const baseScore = (r.rating ?? 3.0) * 20;

    // 验证乘数 (P0-2核心)
    const verifiedMultiplier = candidate.verified ? 1.5 : 0.3;

    // 记忆乘数
    let memoryBonus = 1.0;
    for (const boost of boosts) {
      if (boost.cuisineType && boost.cuisineType === r.cuisineType) {
        memoryBonus *= boost.boostFactor;
      }
      if (boost.privacyLevel && boost.privacyLevel === r.privacyLevel) {
        memoryBonus *= boost.boostFactor;
      }
    }

    // 字段匹配乘数
    let fieldMatch = 1.0;
    if (constraints.cuisine && r.cuisineType === constraints.cuisine) {
      fieldMatch *= 1.1;
    }
    if (constraints.privacyMin) {
      const minLevel = PRIVACY_ORDER[constraints.privacyMin] ?? 0;
      const rLevel = PRIVACY_ORDER[r.privacyLevel] ?? 0;
      if (rLevel >= minLevel) {
        fieldMatch *= 1.1;
      }
    }
    if (constraints.scene && r.sceneTags?.includes(constraints.scene)) {
      fieldMatch *= 1.15;
    }

    // DB匹配分加成
    const dbBonus = 1.0 + dbMatchScore / 100;

    const finalScore = baseScore * verifiedMultiplier * memoryBonus * fieldMatch * dbBonus;

    return {
      restaurant: r,
      culturalStories: [], // 后续由cultural-repository附加
      llmReason: candidate.llmReason,
      verified: candidate.verified,
      source: candidate.source,
      score: Math.round(finalScore * 100) / 100,
    };
  });

  // 排序取Top N
  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, topN);
}
