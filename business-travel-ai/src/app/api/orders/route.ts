import { NextResponse } from "next/server";
import { db } from "@/db";
import { aggregatedOrders, orderItems } from "@/db/schema";
import { eq, and, desc, inArray } from "drizzle-orm";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const sessionId = url.searchParams.get("sessionId");
  const status = url.searchParams.get("status");

  if (!sessionId) {
    return NextResponse.json(
      { error: "缺少必要参数: sessionId" },
      { status: 400 }
    );
  }

  try {
    const conditions = [eq(aggregatedOrders.sessionId, sessionId)];
    if (status) conditions.push(eq(aggregatedOrders.status, status));

    const orders = await db.select().from(aggregatedOrders)
      .where(and(...conditions))
      .orderBy(desc(aggregatedOrders.createdAt))
      .limit(20)
      .all();

    // 批量获取所有订单明细 (避免N+1)
    const orderIds = orders.map(o => o.id);
    let itemsMap: Record<number, typeof orderItems.$inferSelect[]> = {};
    if (orderIds.length > 0) {
      const allItems = await db.select().from(orderItems)
        .where(inArray(orderItems.orderId, orderIds))
        .all();
      for (const item of allItems) {
        if (!itemsMap[item.orderId]) itemsMap[item.orderId] = [];
        itemsMap[item.orderId].push(item);
      }
    }

    const result = orders.map(order => ({
      ...order,
      items: itemsMap[order.id] || [],
    }));

    return NextResponse.json({ data: result, total: result.length });
  } catch (err) {
    console.error("[orders] Error:", err);
    return NextResponse.json(
      { error: "查询订单失败" },
      { status: 500 }
    );
  }
}
