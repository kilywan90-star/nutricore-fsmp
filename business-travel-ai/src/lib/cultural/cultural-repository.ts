import { db } from "@/db";
import { culturalStories } from "@/db/schema";
import { eq, inArray } from "drizzle-orm";
import type { MatchedRestaurant, CulturalStory } from "@/types";

function rowToStory(row: typeof culturalStories.$inferSelect): CulturalStory {
  return {
    id: row.id,
    restaurantId: row.restaurantId,
    storyType: row.storyType as CulturalStory["storyType"],
    title: row.title,
    content: row.content,
    talkingPoints: row.talkingPoints ?? [],
    relatedTopics: row.relatedTopics ?? [],
  };
}

/**
 * P0-3 文化故事隔离层 — 唯一入口
 * 在排序完成后，为Top推荐附加文化故事
 */
export async function attachCulturalStories(
  recommendations: MatchedRestaurant[]
): Promise<MatchedRestaurant[]> {
  // 只对已验证且有真实ID的餐厅查询
  const validIds = recommendations
    .filter((r) => r.verified && r.restaurant.id > 0)
    .map((r) => r.restaurant.id);

  if (validIds.length === 0) return recommendations;

  // 查询所有相关故事
  const rows = await db
    .select()
    .from(culturalStories)
    .where(inArray(culturalStories.restaurantId, validIds))
    .all();

  // 按餐厅ID分组 (每家最多2条)
  const storyMap = new Map<number, CulturalStory[]>();
  for (const row of rows) {
    const stories = storyMap.get(row.restaurantId) ?? [];
    if (stories.length < 2) {
      stories.push(rowToStory(row));
    }
    storyMap.set(row.restaurantId, stories);
  }

  // 附加到推荐结果
  return recommendations.map((rec) => ({
    ...rec,
    culturalStories: storyMap.get(rec.restaurant.id) ?? [],
  }));
}

export async function getStoriesByRestaurantId(
  restaurantId: number
): Promise<CulturalStory[]> {
  const rows = await db
    .select()
    .from(culturalStories)
    .where(eq(culturalStories.restaurantId, restaurantId))
    .all();
  return rows.map(rowToStory);
}
