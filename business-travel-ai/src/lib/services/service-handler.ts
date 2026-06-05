import { searchServices } from "./service-search";
import { searchTransport } from "./transport-search";
import type {
  ExtendedIntent,
  ExtendedNLUSlots,
  SubResult,
  ServiceCategory,
  TransportType,
} from "@/types";

// ============================================================
// 统一服务处理器注册表
// 将 ExtendedIntent 路由到对应的服务处理函数
// ============================================================

type ServiceHandler = (slots: ExtendedNLUSlots, sessionId: string) => Promise<SubResult>;

/**
 * 休闲娱乐推荐
 */
const handleEntertainment: ServiceHandler = async (slots) => {
  try {
    const city = slots.city;
    const category = (slots.entertainmentType || "bath") as ServiceCategory;
    if (!city) {
      return { intent: "entertainment_recommend", status: "failed", error: "缺少城市信息" };
    }
    const results = await searchServices(city, category, slots);
    return { intent: "entertainment_recommend", status: "success", data: results };
  } catch (err) {
    return { intent: "entertainment_recommend", status: "failed", error: String(err) };
  }
};

/**
 * 机票搜索
 */
const handleFlightSearch: ServiceHandler = async (slots) => {
  try {
    const origin = slots.departureCity;
    const dest = slots.arrivalCity || slots.city;
    if (!origin || !dest) {
      return { intent: "flight_search", status: "failed", error: "缺少出发或到达城市" };
    }
    const result = await searchTransport(origin, dest, "flight");
    result.date = slots.date || slots.departureDate || null;
    return { intent: "flight_search", status: "success", data: result };
  } catch (err) {
    return { intent: "flight_search", status: "failed", error: String(err) };
  }
};

/**
 * 火车票搜索
 */
const handleTrainSearch: ServiceHandler = async (slots) => {
  try {
    const origin = slots.departureCity;
    const dest = slots.arrivalCity || slots.city;
    if (!origin || !dest) {
      return { intent: "train_search", status: "failed", error: "缺少出发或到达城市" };
    }
    const result = await searchTransport(origin, dest, "train");
    result.date = slots.date || slots.departureDate || null;
    return { intent: "train_search", status: "success", data: result };
  } catch (err) {
    return { intent: "train_search", status: "failed", error: String(err) };
  }
};

/**
 * 专车服务 (目前返回空结果，需要种子数据)
 */
const handleCarService: ServiceHandler = async (slots) => {
  return {
    intent: "car_service",
    status: "success",
    data: { message: "专车接送服务已记录", city: slots.city, date: slots.date },
  };
};

/**
 * 接机/接站服务
 */
const handlePickup: ServiceHandler = async (slots) => {
  return {
    intent: "pickup_service",
    status: "success",
    data: {
      message: "接驳服务已记录",
      pickupLocation: slots.pickupLocation,
      city: slots.city,
      date: slots.date,
      routeNumber: slots.routeNumber,
    },
  };
};

/**
 * 商务购物推荐
 */
const handleShopping: ServiceHandler = async (slots) => {
  try {
    const city = slots.city;
    if (!city) {
      return { intent: "shopping_recommend", status: "failed", error: "缺少城市信息" };
    }
    const results = await searchServices(city, "business_shopping", slots);
    return { intent: "shopping_recommend", status: "success", data: results };
  } catch (err) {
    return { intent: "shopping_recommend", status: "failed", error: String(err) };
  }
};

// 意图 → 处理器映射
const HANDLER_MAP: Record<string, ServiceHandler> = {
  entertainment_recommend: handleEntertainment,
  flight_search: handleFlightSearch,
  train_search: handleTrainSearch,
  car_service: handleCarService,
  pickup_service: handlePickup,
  shopping_recommend: handleShopping,
};

/**
 * 根据意图分发到对应的服务处理器
 */
export function getServiceHandler(intent: ExtendedIntent): ServiceHandler | null {
  return HANDLER_MAP[intent] ?? null;
}

/**
 * 执行服务处理器的便捷函数
 */
export async function executeServiceHandler(
  intent: ExtendedIntent,
  slots: ExtendedNLUSlots,
  sessionId: string
): Promise<SubResult> {
  const handler = getServiceHandler(intent);
  if (!handler) {
    return { intent, status: "failed", error: `不支持的意图: ${intent}` };
  }
  return handler(slots, sessionId);
}
