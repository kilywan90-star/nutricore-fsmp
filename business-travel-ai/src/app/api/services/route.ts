import { NextResponse } from "next/server";
import { searchServices } from "@/lib/services/service-search";
import type { ServiceCategory } from "@/types";

const VALID_CATEGORIES = new Set<ServiceCategory>([
  "bath", "massage", "ktv", "dance_hall", "business_shopping",
]);

export async function GET(request: Request) {
  const url = new URL(request.url);
  const city = url.searchParams.get("city");
  const category = url.searchParams.get("category") as ServiceCategory | null;

  if (!city) {
    return NextResponse.json(
      { error: "缺少必要参数: city" },
      { status: 400 }
    );
  }

  if (category && !VALID_CATEGORIES.has(category)) {
    return NextResponse.json(
      { error: `无效的品类: ${category}，可选: ${[...VALID_CATEGORIES].join(", ")}` },
      { status: 400 }
    );
  }

  try {
    const results = await searchServices(city, category ?? "bath");
    return NextResponse.json({ data: results, total: results.length, city, category });
  } catch (err) {
    console.error("[services] Error:", err);
    return NextResponse.json(
      { error: "服务搜索失败，请稍后重试" },
      { status: 500 }
    );
  }
}
