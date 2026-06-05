import { db } from "@/db";
import { userPreferences } from "@/db/schema";
import { eq } from "drizzle-orm";

export interface MemoryBoost {
  cuisineType?: string;
  privacyLevel?: string;
  boostFactor: number;
  reason: string;
}

export async function getMemoryBoosts(sessionId: string | undefined): Promise<MemoryBoost[]> {
  if (!sessionId) return [];

  const rows = await db
    .select()
    .from(userPreferences)
    .where(eq(userPreferences.sessionId, sessionId))
    .limit(1)
    .all();

  if (rows.length === 0) return [];

  const prefs = rows[0];
  const boosts: MemoryBoost[] = [];

  if (prefs.preferredCuisines && prefs.preferredCuisines.length > 0) {
    for (const cuisine of prefs.preferredCuisines) {
      boosts.push({
        cuisineType: cuisine,
        boostFactor: 1.2,
        reason: `偏好菜系: ${cuisine}`,
      });
    }
  }

  if (prefs.preferredPrivacy) {
    boosts.push({
      privacyLevel: prefs.preferredPrivacy,
      boostFactor: 1.15,
      reason: `偏好私密性: ${prefs.preferredPrivacy}`,
    });
  }

  return boosts;
}
