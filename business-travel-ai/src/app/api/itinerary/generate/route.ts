import { NextResponse } from "next/server";
import { db } from "@/db";
import { itineraries, itineraryItems } from "@/db/schema";
import { eq, asc } from "drizzle-orm";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { sessionId } = body as { sessionId?: string };

    if (!sessionId) {
      return NextResponse.json(
        { error: "缺少必要参数: sessionId" },
        { status: 400 }
      );
    }

    // 查找该 session 最新的行程
    const rows = await db.select().from(itineraries)
      .where(eq(itineraries.sessionId, sessionId))
      .limit(1)
      .all();

    if (rows.length === 0) {
      return NextResponse.json(
        { error: "未找到行程记录，请先通过聊天生成行程" },
        { status: 404 }
      );
    }

    const itinerary = rows[0];
    const items = await db.select().from(itineraryItems)
      .where(eq(itineraryItems.itineraryId, itinerary.id))
      .orderBy(asc(itineraryItems.sortOrder))
      .all();

    return NextResponse.json({ data: { itinerary, items } });
  } catch (err) {
    console.error("[itinerary/generate] Error:", err);
    return NextResponse.json(
      { error: "生成行程失败" },
      { status: 500 }
    );
  }
}
