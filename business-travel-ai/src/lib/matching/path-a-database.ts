import { db } from "@/db";
import { restaurants } from "@/db/schema";
import { eq, and, gte, lte, like, or, isNull, desc, sql } from "drizzle-orm";
import type { SearchConstraints, Restaurant } from "@/types";

const PRIVACY_ORDER: Record<string, number> = { L1: 1, L2: 2, L3: 3, L4: 4 };

export interface DatabaseCandidate {
  restaurant: Restaurant;
  matchScore: number;
  matchedFields: string[];
}

function rowToRestaurant(row: typeof restaurants.$inferSelect): Restaurant {
  return {
    id: row.id,
    name: row.name,
    city: row.city,
    district: row.district,
    address: row.address,
    latitude: row.latitude,
    longitude: row.longitude,
    cuisineType: row.cuisineType,
    cuisineTags: row.cuisineTags ?? [],
    priceRangeMin: row.priceRangeMin,
    priceRangeMax: row.priceRangeMax,
    privacyLevel: row.privacyLevel as Restaurant["privacyLevel"],
    privateRoomMin: row.privateRoomMin,
    privateRoomMax: row.privateRoomMax,
    privateRoomCount: row.privateRoomCount,
    rating: row.rating,
    sceneTags: row.sceneTags ?? [],
    businessTopics: row.businessTopics ?? [],
    photoTips: row.photoTips,
    signatureDishes: row.signatureDishes ?? [],
    contactPhone: row.contactPhone,
    openingHours: row.openingHours,
    reservationNote: row.reservationNote,
  };
}

function computeMatchScore(
  row: typeof restaurants.$inferSelect,
  constraints: SearchConstraints
): { score: number; fields: string[] } {
  let score = 0;
  const fields: string[] = ["city"];

  if (constraints.cuisine && row.cuisineType === constraints.cuisine) {
    score += 20;
    fields.push("cuisine");
  }
  if (constraints.privacyMin) {
    const minLevel = PRIVACY_ORDER[constraints.privacyMin] ?? 0;
    const rowLevel = PRIVACY_ORDER[row.privacyLevel] ?? 0;
    if (rowLevel >= minLevel) {
      score += 15;
      fields.push("privacy");
    }
  }
  if (constraints.budgetPerPerson && row.priceRangeMin && row.priceRangeMax) {
    const budget = constraints.budgetPerPerson;
    if (budget >= row.priceRangeMin && budget <= row.priceRangeMax * 1.2) {
      score += 15;
      fields.push("budget");
    }
  }
  if (constraints.scene && row.sceneTags?.includes(constraints.scene)) {
    score += 10;
    fields.push("scene");
  }
  if (constraints.guestCount && row.privateRoomMax && row.privateRoomMax >= constraints.guestCount) {
    score += 10;
    fields.push("guestCount");
  }

  return { score, fields };
}

async function queryWithConditions(
  constraints: SearchConstraints,
  options: { withCuisine: boolean; withScene: boolean; budgetTolerance: number }
): Promise<(typeof restaurants.$inferSelect)[]> {
  const conditions = [eq(restaurants.city, constraints.city)];

  if (options.withCuisine && constraints.cuisine) {
    conditions.push(eq(restaurants.cuisineType, constraints.cuisine));
  }
  if (options.withScene && constraints.scene) {
    conditions.push(like(restaurants.sceneTags, `%${constraints.scene}%`));
  }
  if (constraints.privacyMin) {
    const minLevel = PRIVACY_ORDER[constraints.privacyMin] ?? 0;
    const validLevels = Object.entries(PRIVACY_ORDER)
      .filter(([, v]) => v >= minLevel)
      .map(([k]) => k);
    conditions.push(
      or(...validLevels.map((l) => eq(restaurants.privacyLevel, l)))!
    );
  }
  if (constraints.budgetPerPerson) {
    const budget = constraints.budgetPerPerson;
    conditions.push(
      lte(restaurants.priceRangeMin, Math.round(budget * (1 + options.budgetTolerance)))
    );
    conditions.push(
      or(
        gte(restaurants.priceRangeMax, Math.round(budget * (1 - options.budgetTolerance))),
        isNull(restaurants.priceRangeMax)
      )!
    );
  }
  if (constraints.guestCount) {
    conditions.push(
      or(
        gte(restaurants.privateRoomMax, constraints.guestCount),
        isNull(restaurants.privateRoomMax)
      )!
    );
  }

  return db
    .select()
    .from(restaurants)
    .where(and(...conditions))
    .orderBy(desc(restaurants.rating))
    .limit(20)
    .all();
}

export async function queryDatabase(
  constraints: SearchConstraints
): Promise<DatabaseCandidate[]> {
  // 渐进放松策略
  const attempts = [
    { withCuisine: true, withScene: true, budgetTolerance: 0.2 },
    { withCuisine: true, withScene: false, budgetTolerance: 0.2 },
    { withCuisine: false, withScene: false, budgetTolerance: 0.2 },
    { withCuisine: false, withScene: false, budgetTolerance: 0.5 },
  ];

  for (const opts of attempts) {
    const rows = await queryWithConditions(constraints, opts);
    if (rows.length >= 5) {
      return rows.map((row) => {
        const { score, fields } = computeMatchScore(row, constraints);
        return {
          restaurant: rowToRestaurant(row),
          matchScore: score,
          matchedFields: fields,
        };
      });
    }
  }

  // 最后兜底: 只按城市查询
  const rows = await db
    .select()
    .from(restaurants)
    .where(eq(restaurants.city, constraints.city))
    .orderBy(desc(restaurants.rating))
    .limit(20)
    .all();

  return rows.map((row) => {
    const { score, fields } = computeMatchScore(row, constraints);
    return {
      restaurant: rowToRestaurant(row),
      matchScore: score,
      matchedFields: fields,
    };
  });
}

export { rowToRestaurant };
