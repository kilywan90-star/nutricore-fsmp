import { NextResponse } from "next/server";
import { db } from "@/db";
import { aggregatedOrders, orderItems } from "@/db/schema";
import type { OrderItemCategory, PaymentMethod } from "@/types";

const VALID_CATEGORIES = new Set<OrderItemCategory>([
  "dining", "transport", "entertainment", "shopping", "service_fee",
]);

interface AggregateRequest {
  sessionId: string;
  itineraryId?: number;
  items: Array<{
    itemCategory: string;
    itemTitle: string;
    itemDescription?: string;
    quantity?: number;
    unitPrice: number;
    refId?: number;
    refType?: string;
  }>;
  contactName?: string;
  contactPhone?: string;
  notes?: string;
}

function generateOrderNumber(): string {
  const ts = Date.now().toString(36).toUpperCase();
  const rand = Math.random().toString(36).substring(2, 6).toUpperCase();
  return `ORD-${ts}-${rand}`;
}

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as AggregateRequest;
    const { sessionId, itineraryId, items, contactName, contactPhone, notes } = body;

    if (!sessionId) {
      return NextResponse.json(
        { error: "缺少必要参数: sessionId" },
        { status: 400 }
      );
    }

    if (!items || !Array.isArray(items) || items.length === 0) {
      return NextResponse.json(
        { error: "订单至少需要一项明细" },
        { status: 400 }
      );
    }

    // 验证品类
    for (const item of items) {
      if (!VALID_CATEGORIES.has(item.itemCategory as OrderItemCategory)) {
        return NextResponse.json(
          { error: `无效的品类: ${item.itemCategory}` },
          { status: 400 }
        );
      }
    }

    // 计算总金额
    const totalAmount = items.reduce(
      (sum, item) => sum + (item.unitPrice * (item.quantity ?? 1)),
      0
    );

    const orderNumber = generateOrderNumber();

    // 创建主订单
    const [order] = await db.insert(aggregatedOrders).values({
      sessionId,
      itineraryId: itineraryId ?? null,
      orderNumber,
      totalAmount,
      discountAmount: 0,
      finalAmount: totalAmount,
      status: "pending",
      contactName: contactName ?? null,
      contactPhone: contactPhone ?? null,
      notes: notes ?? null,
    }).returning();

    // 创建订单明细
    const createdItems = [];
    for (const item of items) {
      const quantity = item.quantity ?? 1;
      const subtotal = item.unitPrice * quantity;
      const [created] = await db.insert(orderItems).values({
        orderId: order.id,
        itemCategory: item.itemCategory,
        itemTitle: item.itemTitle,
        itemDescription: item.itemDescription ?? null,
        quantity,
        unitPrice: item.unitPrice,
        subtotal,
        refId: item.refId ?? null,
        refType: item.refType ?? null,
      }).returning();
      createdItems.push(created);
    }

    return NextResponse.json({
      data: { ...order, items: createdItems },
    });
  } catch (err) {
    console.error("[orders/aggregate] Error:", err);
    return NextResponse.json(
      { error: "创建订单失败" },
      { status: 500 }
    );
  }
}
