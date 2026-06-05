import { NextResponse } from "next/server";
import { db } from "@/db";
import { itineraries, itineraryItems } from "@/db/schema";
import { eq, asc } from "drizzle-orm";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const itineraryId = parseInt(id, 10);

  if (isNaN(itineraryId)) {
    return NextResponse.json(
      { error: "无效的行程ID" },
      { status: 400 }
    );
  }

  try {
    const [itinerary] = await db.select().from(itineraries)
      .where(eq(itineraries.id, itineraryId))
      .limit(1)
      .all();

    if (!itinerary) {
      return NextResponse.json(
        { error: "行程不存在" },
        { status: 404 }
      );
    }

    const items = await db.select().from(itineraryItems)
      .where(eq(itineraryItems.itineraryId, itineraryId))
      .orderBy(asc(itineraryItems.sortOrder))
      .all();

    return NextResponse.json({ data: { itinerary, items } });
  } catch (err) {
    console.error("[itinerary/[id]] Error:", err);
    return NextResponse.json(
      { error: "查询行程失败" },
      { status: 500 }
    );
  }
}
