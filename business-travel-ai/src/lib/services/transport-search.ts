import { db } from "@/db";
import { transportRoutes } from "@/db/schema";
import { eq, and, asc } from "drizzle-orm";
import type {
  TransportType,
  TransportRoute,
  TransportSearchResult,
} from "@/types";

// ============================================================
// 交通线路搜索 (预设种子数据)
// ============================================================

function rowToRoute(row: typeof transportRoutes.$inferSelect): TransportRoute {
  return {
    id: row.id,
    transportType: row.transportType as TransportType,
    originCity: row.originCity,
    destCity: row.destCity,
    originStation: row.originStation,
    destStation: row.destStation,
    carrierName: row.carrierName,
    routeNumber: row.routeNumber,
    departureTime: row.departureTime,
    arrivalTime: row.arrivalTime,
    durationMinutes: row.durationMinutes,
    priceEconomy: row.priceEconomy,
    priceBusiness: row.priceBusiness,
    vehicleType: row.vehicleType,
    scheduleDays: row.scheduleDays ?? [],
    amenities: row.amenities ?? [],
    rating: row.rating ?? 4.0,
  };
}

export async function searchTransport(
  originCity: string,
  destCity: string,
  transportType?: TransportType
): Promise<TransportSearchResult> {
  let rows: (typeof transportRoutes.$inferSelect)[];

  if (transportType) {
    rows = await db.select().from(transportRoutes)
      .where(and(
        eq(transportRoutes.originCity, originCity),
        eq(transportRoutes.destCity, destCity),
        eq(transportRoutes.transportType, transportType),
      ))
      .orderBy(asc(transportRoutes.departureTime))
      .limit(10);
  } else {
    rows = await db.select().from(transportRoutes)
      .where(and(
        eq(transportRoutes.originCity, originCity),
        eq(transportRoutes.destCity, destCity),
      ))
      .orderBy(asc(transportRoutes.departureTime))
      .limit(10);
  }

  return {
    routes: rows.map(rowToRoute),
    originCity,
    destCity,
    date: null,
  };
}
