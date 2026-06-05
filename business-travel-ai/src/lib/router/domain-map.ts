import type { Domain } from "./types";

// ============================================================
// 意图 → 业务域映射 (单一事实来源)
// ============================================================

export const INTENT_DOMAIN_MAP: Record<string, Domain> = {
  // 餐饮域
  dining_recommend: "DINING",

  // 休闲娱乐域
  entertainment_recommend: "ENTERTAINMENT",

  // 交通出行域
  flight_search: "TRANSPORT",
  train_search: "TRANSPORT",
  car_service: "TRANSPORT",
  pickup_service: "TRANSPORT",

  // 商务购物域
  shopping_recommend: "SHOPPING",

  // 简单回复域 (静态话术)
  chitchat: "SIMPLE",
  booking: "SIMPLE",
  query_restaurant: "SIMPLE",
  modify_plan: "SIMPLE",

  // 规划/订单域 (占位)
  trip_plan: "PLANNING",
  order_create: "PLANNING",
  order_pay: "PLANNING",
  order_list: "PLANNING",
};

// ============================================================
// 意图中文标签 (替代 route.ts 中的 INTENT_LABELS)
// ============================================================

const INTENT_LABELS: Record<string, string> = {
  dining_recommend: "餐饮推荐",
  entertainment_recommend: "休闲娱乐",
  flight_search: "机票搜索",
  train_search: "火车票搜索",
  car_service: "专车服务",
  pickup_service: "接驳服务",
  shopping_recommend: "商务购物",
  trip_plan: "行程规划",
  booking: "预订",
  query_restaurant: "查询餐厅",
  modify_plan: "修改计划",
  order_create: "创建订单",
  order_pay: "支付订单",
  order_list: "查询订单",
  chitchat: "闲聊",
};

export function getIntentLabel(intent: string): string {
  return INTENT_LABELS[intent] ?? intent;
}
