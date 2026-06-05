import { NextResponse } from "next/server";
import { searchTransport } from "@/lib/services/transport-search";
import type { TransportType } from "@/types";

const VALID_TYPES = new Set<TransportType>(["flight", "train", "private_car"]);

export async function GET(request: Request) {
  const url = new URL(request.url);
  const origin = url.searchParams.get("origin");
  const dest = url.searchParams.get("dest");
  const type = url.searchParams.get("type") as TransportType | null;

  if (!origin || !dest) {
    return NextResponse.json(
      { error: "缺少必要参数: origin 和 dest" },
      { status: 400 }
    );
  }

  if (type && !VALID_TYPES.has(type)) {
    return NextResponse.json(
      { error: `无效的交通类型: ${type}，可选: ${[...VALID_TYPES].join(", ")}` },
      { status: 400 }
    );
  }

  try {
    const result = await searchTransport(origin, dest, type ?? undefined);
    return NextResponse.json(result);
  } catch (err) {
    console.error("[transport] Error:", err);
    return NextResponse.json(
      { error: "交通搜索失败，请稍后重试" },
      { status: 500 }
    );
  }
}
