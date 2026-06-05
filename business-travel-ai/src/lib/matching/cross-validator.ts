import { db } from "@/db";
import { restaurants } from "@/db/schema";
import { eq, and } from "drizzle-orm";
import type { MatchedRestaurant } from "@/types";
import type { LLMRecommendation } from "./path-b-llm";
import type { DatabaseCandidate } from "./path-a-database";
import { rowToRestaurant } from "./path-a-database";

export interface CrossValidatedResult {
  restaurant: MatchedRestaurant["restaurant"];
  llmReason?: string;
  verified: boolean;
  source: MatchedRestaurant["source"];
}

function normalizeName(name: string): string {
  return name
    .trim()
    .replace(/\s+/g, "")
    .replace(/(餐厅|饭店|饭馆|馆子|酒楼|酒家|食府|餐厅|小馆)$/g, "");
}

async function lookupInDB(
  name: string,
  city: string
): Promise<typeof restaurants.$inferSelect | null> {
  const rows = await db
    .select()
    .from(restaurants)
    .where(and(eq(restaurants.name, name), eq(restaurants.city, city)))
    .limit(1)
    .all();
  return rows.length > 0 ? rows[0] : null;
}

export async function crossValidate(
  llmRecs: LLMRecommendation[],
  dbCandidates: DatabaseCandidate[],
  city: string
): Promise<CrossValidatedResult[]> {
  const results: CrossValidatedResult[] = [];

  for (const rec of llmRecs) {
    // 1. 精确匹配DB候选
    const exactMatch = dbCandidates.find(
      (c) => c.restaurant.name === rec.name
    );
    if (exactMatch) {
      results.push({
        restaurant: exactMatch.restaurant,
        llmReason: rec.reason,
        verified: true,
        source: "llm_verified",
      });
      continue;
    }

    // 2. 归一化匹配DB候选
    const normalizedRec = normalizeName(rec.name);
    const normMatch = dbCandidates.find(
      (c) => normalizeName(c.restaurant.name) === normalizedRec
    );
    if (normMatch) {
      results.push({
        restaurant: normMatch.restaurant,
        llmReason: rec.reason,
        verified: true,
        source: "llm_verified",
      });
      continue;
    }

    // 3. 直接查DB (可能不在Path A结果中但存在于DB)
    const dbRow = await lookupInDB(rec.name, city);
    if (dbRow) {
      results.push({
        restaurant: rowToRestaurant(dbRow),
        llmReason: rec.reason,
        verified: true,
        source: "llm_verified",
      });
      continue;
    }

    // 4. 归一化直查DB
    // (尝试模糊匹配DB中的餐厅)
    const allInCity = await db
      .select()
      .from(restaurants)
      .where(eq(restaurants.city, city))
      .all();

    const fuzzyMatch = allInCity.find(
      (r) => normalizeName(r.name) === normalizedRec
    );
    if (fuzzyMatch) {
      results.push({
        restaurant: rowToRestaurant(fuzzyMatch),
        llmReason: rec.reason,
        verified: true,
        source: "llm_verified",
      });
      continue;
    }

    // 5. 未找到 → unverified
    results.push({
      restaurant: {
        id: -1,
        name: rec.name,
        city,
        district: null,
        address: "未知地址",
        latitude: null,
        longitude: null,
        cuisineType: "未知",
        cuisineTags: [],
        priceRangeMin: null,
        priceRangeMax: null,
        privacyLevel: "L2",
        privateRoomMin: null,
        privateRoomMax: null,
        privateRoomCount: null,
        rating: 3.0,
        sceneTags: [],
        businessTopics: [],
        photoTips: null,
        signatureDishes: [],
        contactPhone: null,
        openingHours: null,
        reservationNote: null,
      },
      llmReason: rec.reason,
      verified: false,
      source: "llm_unverified",
    });
  }

  // 过滤掉LLM幻觉（非当前城市、未验证的非DB推荐）
  const cityResults = results.filter(r => {
    if (r.verified || r.source === "database") return r.restaurant.city === city;
    return false;
  });
  // 如果交叉验证没有结果，但DB有候选，回退到DB
  if (cityResults.length === 0 && dbCandidates.length > 0) {
    return dbCandidates
      .filter(dc => dc.restaurant.city === city)
      .slice(0, 5)
      .map(dc => ({
        restaurant: dc.restaurant,
        verified: true,
        source: "database" as const,
      }));
  }
  return cityResults;
}
