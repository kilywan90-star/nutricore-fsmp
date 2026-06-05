import { NextResponse } from "next/server";
import { db } from "@/db";
import { conversationHistory, bookings } from "@/db/schema";
import { desc } from "drizzle-orm";

export async function GET() {
  try {
    // Mock data for now — will be replaced with real reception tracking
    const records = [
      {
        id: 1,
        sessionId: "demo-001",
        date: "2026-06-03",
        city: "成都",
        guestName: "深圳某科技公司CTO",
        guestLevel: "VIP",
        diningName: "锦城舞殿",
        entertainmentName: "纯K",
        totalCost: 3500,
        status: "completed",
        notes: "签约后接待，效果很好",
      },
      {
        id: 2,
        sessionId: "demo-002",
        date: "2026-06-01",
        city: "成都",
        guestName: "北京投资人",
        guestLevel: "VIP",
        diningName: "蜀韵汤泉",
        entertainmentName: "白天鹅舞厅",
        totalCost: 5200,
        status: "completed",
        notes: "投资尽调后的商务宴请",
      },
      {
        id: 3,
        sessionId: "demo-003",
        date: "2026-05-28",
        city: "成都",
        guestName: "上海合作方经理",
        guestLevel: "important",
        diningName: "诺亚方舟",
        entertainmentName: "常乐足道",
        totalCost: 2100,
        status: "completed",
        notes: "季度合作复盘",
      },
    ];

    return NextResponse.json({ records });
  } catch (err) {
    console.error("[admin/records] Error:", err);
    return NextResponse.json(
      { error: "查询失败" },
      { status: 500 }
    );
  }
}
