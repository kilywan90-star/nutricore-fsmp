import { NextResponse } from "next/server";
import { db } from "@/db";
import { restaurants } from "@/db/schema";
import { sql } from "drizzle-orm";

export async function GET() {
  let dbStatus: "ok" | "error" = "ok";
  let llmStatus: "ok" | "error" | "skipped" = "skipped";

  try {
    await db.select({ id: restaurants.id }).from(restaurants).limit(1).all();
  } catch {
    dbStatus = "error";
  }

  return NextResponse.json({
    status: dbStatus === "ok" ? "ok" : "error",
    db: dbStatus,
    llm: llmStatus,
    timestamp: new Date().toISOString(),
  });
}
