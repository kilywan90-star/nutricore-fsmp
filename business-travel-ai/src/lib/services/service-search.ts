import { db } from "@/db";
import { services, serviceCulturalStories } from "@/db/schema";
import { eq, and, desc } from "drizzle-orm";
import type {
  ServiceCategory,
  ExtendedNLUSlots,
  ServiceRecommendation,
  Service,
  ServiceCulturalStory,
  PrivacyLevel,
} from "@/types";

// ============================================================
// 休闲娱乐 + 商务购物 POI 搜索
// 模式: 渐进松弛查询 (类似 path-a-database.ts)
// ============================================================

function rowToService(row: typeof services.$inferSelect): Service {
  return {
    id: row.id,
    name: row.name,
    city: row.city,
    district: row.district,
    address: row.address,
    latitude: row.latitude,
    longitude: row.longitude,
    serviceCategory: row.serviceCategory as ServiceCategory,
    serviceTags: row.serviceTags ?? [],
    priceRangeMin: row.priceRangeMin,
    priceRangeMax: row.priceRangeMax,
    rating: row.rating,
    privacyLevel: row.privacyLevel as PrivacyLevel,
    capacity: row.capacity,
    sceneTags: row.sceneTags ?? [],
    description: row.description,
    highlights: row.highlights ?? [],
    contactPhone: row.contactPhone,
    openingHours: row.openingHours,
    reservationNote: row.reservationNote,
  };
}

function rowToStory(row: typeof serviceCulturalStories.$inferSelect): ServiceCulturalStory {
  return {
    id: row.id,
    serviceId: row.serviceId,
    storyType: row.storyType as ServiceCulturalStory["storyType"],
    title: row.title,
    content: row.content,
    talkingPoints: row.talkingPoints ?? [],
    relatedTopics: row.relatedTopics ?? [],
  };
}

export async function searchServices(
  city: string,
  category: ServiceCategory,
  slots?: ExtendedNLUSlots
): Promise<ServiceRecommendation[]> {
  // 渐进松弛查询
  const attempts = [
    // 1. 精确: 城市 + 品类 + 价格范围
    async () => {
      let query = db.select().from(services)
        .where(and(
          eq(services.city, city),
          eq(services.serviceCategory, category),
        ))
        .orderBy(desc(services.rating))
        .limit(10);
      return query;
    },
    // 2. 宽松: 仅城市 + 品类
    async () => {
      return db.select().from(services)
        .where(and(
          eq(services.city, city),
          eq(services.serviceCategory, category),
        ))
        .orderBy(desc(services.rating))
        .limit(10);
    },
    // 3. 兜底: 仅城市
    async () => {
      return db.select().from(services)
        .where(eq(services.city, city))
        .orderBy(desc(services.rating))
        .limit(10);
    },
  ];

  let rows: (typeof services.$inferSelect)[] = [];
  for (const attempt of attempts) {
    rows = await attempt();
    if (rows.length >= 3) break;
  }

  // 价格过滤 (如果有预算约束)
  if (slots?.budgetPerPerson) {
    const budget = slots.budgetPerPerson;
    const filtered = rows.filter((r) => {
      if (r.priceRangeMin && r.priceRangeMax) {
        return r.priceRangeMin <= budget * 1.5 && r.priceRangeMax >= budget * 0.5;
      }
      return true;
    });
    if (filtered.length >= 1) rows = filtered;
  }

  // 取 Top 5
  const topRows = rows.slice(0, 5);

  // 附加文化故事
  const results: ServiceRecommendation[] = [];
  for (const row of topRows) {
    const service = rowToService(row);
    const stories = await db.select().from(serviceCulturalStories)
      .where(eq(serviceCulturalStories.serviceId, row.id))
      .limit(2);

    results.push({
      service,
      culturalStories: stories.map(rowToStory),
      score: row.rating * 20,
    });
  }

  return results;
}
