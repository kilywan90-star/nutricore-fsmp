import { NextResponse } from "next/server";
import { db } from "@/db";
import { itineraries, itineraryItems } from "@/db/schema";
import { eq, and } from "drizzle-orm";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const sessionId = url.searchParams.get("sessionId");
  const status = url.searchParams.get("status");

  try {
    let rows;
    if (sessionId && status) {
      rows = await db.select().from(itineraries)
        .where(and(eq(itineraries.sessionId, sessionId), eq(itineraries.status, status)))
        .limit(20).all();
    } else if (sessionId) {
      rows = await db.select().from(itineraries)
        .where(eq(itineraries.sessionId, sessionId))
        .limit(20).all();
    } else if (status) {
      rows = await db.select().from(itineraries)
        .where(eq(itineraries.status, status))
        .limit(20).all();
    } else {
      rows = await db.select().from(itineraries).limit(20).all();
    }

    return NextResponse.json({ data: rows, total: rows.length });
  } catch (err) {
    console.error("[itinerary] Error:", err);
    return NextResponse.json(
      { error: "查询行程失败" },
      { status: 500 }
    );
  }
}
