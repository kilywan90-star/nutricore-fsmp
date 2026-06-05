import { NextResponse } from "next/server";
import { db } from "@/db";
import { restaurants } from "@/db/schema";
import { eq, and, desc } from "drizzle-orm";
import { rowToRestaurant } from "@/lib/matching/path-a-database";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const city = url.searchParams.get("city");
  const cuisine = url.searchParams.get("cuisine");
  const privacy = url.searchParams.get("privacy");
  const page = parseInt(url.searchParams.get("page") || "1", 10);
  const pageSize = parseInt(url.searchParams.get("pageSize") || "20", 10);

  const conditions = [];
  if (city) conditions.push(eq(restaurants.city, city));
  if (cuisine) conditions.push(eq(restaurants.cuisineType, cuisine));
  if (privacy) conditions.push(eq(restaurants.privacyLevel, privacy));

  const where = conditions.length > 0 ? and(...conditions) : undefined;

  const [data, countResult] = await Promise.all([
    db
      .select()
      .from(restaurants)
      .where(where)
      .orderBy(desc(restaurants.rating))
      .limit(pageSize)
      .offset((page - 1) * pageSize)
      .all(),
    db
      .select({ count: restaurants.id })
      .from(restaurants)
      .where(where)
      .all(),
  ]);

  return NextResponse.json({
    data: data.map(rowToRestaurant),
    total: countResult.length,
    page,
    pageSize,
  });
}
