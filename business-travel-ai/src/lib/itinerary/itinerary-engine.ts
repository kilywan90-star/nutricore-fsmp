import { db } from "@/db";
import { itineraries, itineraryItems } from "@/db/schema";
import type {
  MultiNLUResult,
  SubResult,
  SharedContext,
  ItineraryItemType,
  ExtendedIntent,
} from "@/types";

// ============================================================
// 行程规划引擎
// 将多意图结果编排为时间轴行程
// ============================================================

interface TimelineEntry {
  intent: ExtendedIntent;
  itemType: ItineraryItemType;
  title: string;
  startTime: string | null;
  endTime: string | null;
  location: string | null;
  address: string | null;
  city: string | null;
  latitude: number | null;
  longitude: number | null;
  estimatedCost: number | null;
  refId: number | null;
  refType: "restaurant" | "service" | "transport_route" | null;
  flexibility: "fixed" | "semi-fixed" | "flexible";
  data: unknown;
}

/**
 * 从子意图结果中提取时间锚点
 */
function extractTimeAnchor(subResult: SubResult, ctx: SharedContext): { startTime: string | null; flexibility: "fixed" | "semi-fixed" | "flexible" } {
  const slots = subResult.data as Record<string, unknown> | null;
  // 检查是否有明确时间
  const intent = subResult.intent;

  // 固定时间: 交通出发、会议
  if (intent === "flight_search" || intent === "train_search") {
    const routes = (slots as { routes?: Array<{ departureTime: string }> })?.routes;
    if (routes && routes.length > 0) {
      return { startTime: routes[0].departureTime, flexibility: "fixed" };
    }
  }

  if (intent === "pickup_service") {
    // 接机时间取决于航班时间
    return { startTime: null, flexibility: "fixed" };
  }

  // 半固定: 餐饮 (用餐时段)
  if (intent === "dining_recommend") {
    const time = (slots as Record<string, unknown>)?.time as string | undefined;
    if (time) return { startTime: time, flexibility: "semi-fixed" };
    // 根据上下文推断
    if (ctx.meetingTime) {
      // 会议后用餐: 会议时间 + 1.5h
      const [h, m] = ctx.meetingTime.split(":").map(Number);
      const dinnerHour = Math.min(h + 1 + Math.floor((m + 30) / 60), 21);
      return { startTime: `${String(dinnerHour).padStart(2, "0")}:00`, flexibility: "semi-fixed" };
    }
    return { startTime: "18:00", flexibility: "semi-fixed" }; // 默认晚餐
  }

  // 灵活: 娱乐、购物
  if (intent === "entertainment_recommend" || intent === "shopping_recommend") {
    return { startTime: null, flexibility: "flexible" };
  }

  return { startTime: null, flexibility: "flexible" };
}

/**
 * 从子结果中提取位置信息
 */
function extractLocation(subResult: SubResult, ctx: SharedContext): {
  title: string; location: string | null; address: string | null;
  city: string | null; lat: number | null; lng: number | null;
  cost: number | null; refId: number | null; refType: TimelineEntry["refType"];
} {
  const data = subResult.data as Record<string, unknown> | null;
  const intent = subResult.intent;

  if (intent === "dining_recommend" && Array.isArray(data) && data.length > 0) {
    const first = data[0] as { restaurant?: { name: string; address: string; city: string; latitude: number | null; longitude: number | null; priceRangeMin: number | null } };
    return {
      title: first.restaurant?.name || "餐厅",
      location: first.restaurant?.name || null,
      address: first.restaurant?.address || null,
      city: first.restaurant?.city || ctx.city || null,
      lat: first.restaurant?.latitude ?? null,
      lng: first.restaurant?.longitude ?? null,
      cost: first.restaurant?.priceRangeMin ?? null,
      refId: (first as { restaurant?: { id: number } }).restaurant?.id ?? null,
      refType: "restaurant",
    };
  }

  if ((intent === "entertainment_recommend" || intent === "shopping_recommend") && Array.isArray(data) && data.length > 0) {
    const first = data[0] as { service?: { name: string; address: string; city: string; latitude: number | null; longitude: number | null; priceRangeMin: number | null; id: number } };
    return {
      title: first.service?.name || "服务场所",
      location: first.service?.name || null,
      address: first.service?.address || null,
      city: first.service?.city || ctx.city || null,
      lat: first.service?.latitude ?? null,
      lng: first.service?.longitude ?? null,
      cost: first.service?.priceRangeMin ?? null,
      refId: first.service?.id ?? null,
      refType: "service",
    };
  }

  if ((intent === "flight_search" || intent === "train_search") && data) {
    const result = data as { routes?: Array<{ routeNumber: string; originStation: string | null; destStation: string | null; originCity: string; destCity: string; priceEconomy: number | null; id: number }> };
    const route = result.routes?.[0];
    if (route) {
      return {
        title: `${intent === "flight_search" ? "航班" : "列车"} ${route.routeNumber}`,
        location: route.originStation || route.originCity,
        address: route.originStation || null,
        city: route.originCity,
        lat: null, lng: null,
        cost: route.priceEconomy,
        refId: route.id,
        refType: "transport_route",
      };
    }
  }

  if (intent === "pickup_service" && data) {
    const d = data as { pickupLocation?: string; city?: string };
    const locName = d.pickupLocation === "airport" ? "机场" : d.pickupLocation === "station" ? "车站" : "酒店";
    return {
      title: `接驳 - ${locName}`,
      location: locName,
      address: null,
      city: d.city || ctx.city || null,
      lat: null, lng: null, cost: null, refId: null, refType: null,
    };
  }

  return {
    title: subResult.intent,
    location: null, address: null,
    city: ctx.city || null,
    lat: null, lng: null, cost: null, refId: null, refType: null,
  };
}

/**
 * 估算两点之间的交通时间(分钟)
 */
function estimateTransitTime(a: TimelineEntry, b: TimelineEntry): number {
  if (a.latitude && a.longitude && b.latitude && b.longitude) {
    // Haversine 粗略距离 → 城市驾车速度 30km/h
    const R = 6371;
    const dLat = (b.latitude - a.latitude) * Math.PI / 180;
    const dLng = (b.longitude - a.longitude) * Math.PI / 180;
    const x = Math.sin(dLat / 2) ** 2 +
      Math.cos(a.latitude * Math.PI / 180) * Math.cos(b.latitude * Math.PI / 180) *
      Math.sin(dLng / 2) ** 2;
    const distKm = R * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
    return Math.max(10, Math.round(distKm / 30 * 60));
  }
  // 无坐标: 同区域10-15分钟，跨区域30分钟
  return a.city === b.city ? 15 : 30;
}

function addMinutes(time: string, minutes: number): string {
  const [h, m] = time.split(":").map(Number);
  const total = h * 60 + m + minutes;
  return `${String(Math.floor(total / 60) % 24).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

/**
 * 主入口: 生成行程
 */
export async function generateItinerary(
  sessionId: string,
  multiResult: MultiNLUResult,
  subResults: SubResult[]
): Promise<{ itineraryId: number; items: Array<Record<string, unknown>> }> {
  const ctx = multiResult.sharedContext;

  // Step 1: 构建时间轴条目
  const entries: TimelineEntry[] = [];
  for (const sr of subResults) {
    if (sr.status !== "success") continue;

    const { startTime, flexibility } = extractTimeAnchor(sr, ctx);
    const loc = extractLocation(sr, ctx);

    // 推断itemType
    let itemType: ItineraryItemType = "free_time";
    if (sr.intent === "dining_recommend") itemType = "dining";
    else if (sr.intent === "entertainment_recommend") itemType = "entertainment";
    else if (sr.intent === "shopping_recommend") itemType = "shopping";
    else if (sr.intent === "flight_search" || sr.intent === "train_search" || sr.intent === "car_service") itemType = "transport";
    else if (sr.intent === "pickup_service") itemType = "pickup";

    entries.push({
      intent: sr.intent,
      itemType,
      title: loc.title,
      startTime,
      endTime: null,
      location: loc.location,
      address: loc.address,
      city: loc.city,
      latitude: loc.lat,
      longitude: loc.lng,
      estimatedCost: loc.cost,
      refId: loc.refId,
      refType: loc.refType,
      flexibility,
      data: sr.data,
    });
  }

  // Step 2: 排序 — 固定 > 半固定 > 灵活
  entries.sort((a, b) => {
    const flexOrder = { fixed: 0, "semi-fixed": 1, flexible: 2 };
    if (flexOrder[a.flexibility] !== flexOrder[b.flexibility]) {
      return flexOrder[a.flexibility] - flexOrder[b.flexibility];
    }
    if (a.startTime && b.startTime) return a.startTime.localeCompare(b.startTime);
    if (a.startTime) return -1;
    if (b.startTime) return 1;
    return 0;
  });

  // Step 3: 分配时间 (灵活项目按顺序排在前面项目之后)
  let lastEndTime: string | null = null;
  for (let i = 0; i < entries.length; i++) {
    const entry = entries[i];

    if (!entry.startTime) {
      // 灵活项目: 排在前一项结束后 + 交通时间
      if (lastEndTime && i > 0) {
        const transit = estimateTransitTime(entries[i - 1], entry);
        entry.startTime = addMinutes(lastEndTime, transit);
      } else {
        // 第一个灵活项目: 默认 10:00
        entry.startTime = "10:00";
      }
    }

    // 估算结束时间
    const durationMap: Record<ItineraryItemType, number> = {
      transport: 120,
      dining: 90,
      entertainment: 120,
      shopping: 90,
      pickup: 30,
      free_time: 60,
      hotel: 0,
    };
    entry.endTime = addMinutes(entry.startTime, durationMap[entry.itemType] || 60);
    lastEndTime = entry.endTime;
  }

  // Step 4: 持久化到数据库
  const city = ctx.city || ctx.arrivalCity || "";
  const title = `${city || ""}商务出行行程`.trim();

  const [itinerary] = await db.insert(itineraries).values({
    sessionId,
    title,
    purpose: ctx.purpose || null,
    originCity: null,
    destCity: city || null,
    startDate: ctx.date || null,
    endDate: ctx.date || null,
    travelerCount: null,
    totalBudget: null,
    totalCost: entries.reduce((sum, e) => sum + (e.estimatedCost || 0), 0),
    status: "draft",
  }).returning();

  // 插入行程项目
  const items: Array<Record<string, unknown>> = [];
  for (let i = 0; i < entries.length; i++) {
    const entry = entries[i];
    const [item] = await db.insert(itineraryItems).values({
      itineraryId: itinerary.id,
      sortOrder: i + 1,
      itemType: entry.itemType,
      title: entry.title,
      description: null,
      date: ctx.date || null,
      startTime: entry.startTime,
      endTime: entry.endTime,
      location: entry.location,
      address: entry.address,
      city: entry.city,
      latitude: entry.latitude,
      longitude: entry.longitude,
      estimatedCost: entry.estimatedCost,
      status: "planned",
      refId: entry.refId,
      refType: entry.refType,
    }).returning();
    items.push(item);
  }

  return { itineraryId: itinerary.id, items };
}
