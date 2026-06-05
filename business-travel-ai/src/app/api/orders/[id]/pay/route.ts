import { NextResponse } from "next/server";
import { db } from "@/db";
import { aggregatedOrders } from "@/db/schema";
import { eq } from "drizzle-orm";
import type { PaymentMethod } from "@/types";

const VALID_METHODS = new Set<PaymentMethod>([
  "mock_alipay", "mock_wechat", "mock_corporate", "manual",
]);

interface PayRequest {
  paymentMethod: string;
}

export async function POST(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const orderId = parseInt(id, 10);

  if (isNaN(orderId)) {
    return NextResponse.json(
      { error: "无效的订单ID" },
      { status: 400 }
    );
  }

  try {
    const [order] = await db.select().from(aggregatedOrders)
      .where(eq(aggregatedOrders.id, orderId))
      .limit(1)
      .all();

    if (!order) {
      return NextResponse.json(
        { error: "订单不存在" },
        { status: 404 }
      );
    }

    if (order.status !== "pending") {
      return NextResponse.json(
        { error: `订单状态为 ${order.status}，无法支付` },
        { status: 409 }
      );
    }

    const body = (await _request.json()) as PayRequest;
    const paymentMethod = body.paymentMethod as PaymentMethod;

    if (!paymentMethod || !VALID_METHODS.has(paymentMethod)) {
      return NextResponse.json(
        { error: `无效的支付方式: ${paymentMethod}，可选: ${[...VALID_METHODS].join(", ")}` },
        { status: 400 }
      );
    }

    // 模拟支付: 直接更新状态为 paid
    const [updated] = await db.update(aggregatedOrders)
      .set({
        status: "paid",
        paymentMethod,
      })
      .where(eq(aggregatedOrders.id, orderId))
      .returning();

    return NextResponse.json({
      data: updated,
      message: `模拟支付成功（${paymentMethod}），订单金额: ${updated.finalAmount}元`,
    });
  } catch (err) {
    console.error("[orders/[id]/pay] Error:", err);
    return NextResponse.json(
      { error: "支付处理失败" },
      { status: 500 }
    );
  }
}
