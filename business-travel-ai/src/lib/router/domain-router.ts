import { INTENT_DOMAIN_MAP } from "./domain-map";
import { handleDining } from "./dining-handler";
import { handleEntertainment, handleTransport, handleShopping } from "./service-adapter";
import { handleSimple } from "./simple-handler";
import { handleReception } from "./reception-handler";
import type { Domain, DomainResponse, DomainHandler } from "./types";
import type { NLUResult, ExtendedIntent, SubResult, ContentCard, MatchedRestaurant, ServiceRecommendation, TransportSearchResult } from "@/types";
import { getIntentLabel } from "./domain-map";

function toContentCards(data: unknown, intent: string): ContentCard[] {
  if (!data) return [];

  // 餐饮推荐
  if (isDiningData(data)) {
    return (data as MatchedRestaurant[]).map((m, i) => ({
      id: m.restaurant.id,
      category: "restaurant" as const,
      title: m.restaurant.name,
      subtitle: [m.restaurant.district, m.restaurant.address].filter(Boolean).join(" · "),
      rating: m.restaurant.rating,
      priceRangeMin: m.restaurant.priceRangeMin,
      priceRangeMax: m.restaurant.priceRangeMax,
      privacyLevel: m.restaurant.privacyLevel,
      sceneTags: m.restaurant.sceneTags ?? [],
      description: m.llmReason ?? null,
      highlights: m.restaurant.signatureDishes ?? [],
      culturalStories: m.culturalStories ?? [],
      contactPhone: m.restaurant.contactPhone,
      openingHours: m.restaurant.openingHours,
      extras: { cuisineType: m.restaurant.cuisineType, verified: m.verified, source: m.source },
    }));
  }

  // 服务/娱乐推荐
  if (isServiceData(data)) {
    return (data as ServiceRecommendation[]).map((s, i) => {
      const svc = s.service;
      return {
        id: svc.id,
        category: svc.serviceCategory as ContentCard["category"],
        title: svc.name,
        subtitle: [svc.district, svc.address].filter(Boolean).join(" · "),
        rating: svc.rating,
        priceRangeMin: svc.priceRangeMin,
        priceRangeMax: svc.priceRangeMax,
        privacyLevel: svc.privacyLevel,
        sceneTags: svc.sceneTags ?? [],
        description: svc.description,
        highlights: svc.highlights ?? [],
        culturalStories: s.culturalStories ?? [],
        contactPhone: svc.contactPhone,
        openingHours: svc.openingHours,
        extras: { serviceCategory: svc.serviceCategory, capacity: svc.capacity },
      };
    });
  }

  // 交通路线
  if (typeof data === "object" && "routes" in (data as Record<string, unknown>)) {
    const tr = data as TransportSearchResult;
    return tr.routes.map((r, i) => ({
      id: r.id,
      category: "hotel" as const, // fallback, transport handled separately
      title: `${r.carrierName ?? ""} ${r.routeNumber}`,
      subtitle: `${r.originCity}${r.originStation ? " " + r.originStation : ""} → ${r.destCity}${r.destStation ? " " + r.destStation : ""}`,
      rating: r.rating ?? 4.0,
      priceRangeMin: r.priceEconomy,
      priceRangeMax: r.priceBusiness,
      privacyLevel: "L1",
      sceneTags: [],
      description: `${r.departureTime}-${r.arrivalTime} (${r.durationMinutes}分钟)`,
      highlights: r.amenities ?? [],
      culturalStories: [],
      contactPhone: null,
      openingHours: null,
      extras: { transportType: r.transportType, routeNumber: r.routeNumber, vehicleType: r.vehicleType },
    }));
  }

  return [];
}

export { toContentCards, getIntentLabel };

// ============================================================
// 业务域路由器 — 核心分发
// ============================================================

const DOMAIN_HANDLERS: Record<Domain, DomainHandler | null> = {
  DINING: handleDining,
  ENTERTAINMENT: handleEntertainment,
  TRANSPORT: handleTransport,
  SHOPPING: handleShopping,
  SIMPLE: handleSimple,
  PLANNING: handleReception,
  UNKNOWN: null,
};

export async function routeToDomain(
  nluResult: NLUResult,
  sessionId: string
): Promise<DomainResponse> {
  const domain = INTENT_DOMAIN_MAP[nluResult.intent] ?? "UNKNOWN";
  const handler = DOMAIN_HANDLERS[domain];

  if (!handler) {
    return { reply: "抱歉，我暂时无法处理此类请求。请尝试描述您的餐饮、休闲或出行需求。" };
  }

  try {
    return await handler(nluResult, sessionId);
  } catch (err) {
    console.error(`[domain-router] ${domain} handler error:`, err);
    return { reply: "服务处理出现异常，请稍后重试。" };
  }
}

// ============================================================
// 多意图桥接: DomainResponse → SubResult
// ============================================================

export function domainResponseToSubResult(
  response: DomainResponse,
  intent: ExtendedIntent
): SubResult {
  if (response.data !== undefined && response.data !== null) {
    return { intent, status: "success", data: response.data };
  }
  return { intent, status: "failed", error: response.reply };
}

// ============================================================
// 类型守卫: 判断 DomainResponse.data 是否为餐饮推荐数据
// ============================================================

export function isDiningData(data: unknown): data is import("@/types").MatchedRestaurant[] {
  return Array.isArray(data) && data.length > 0 && "restaurant" in data[0];
}

export function isServiceData(data: unknown): data is import("@/types").ServiceRecommendation[] {
  return Array.isArray(data) && data.length > 0 && "service" in data[0];
}
