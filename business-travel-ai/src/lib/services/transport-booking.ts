import { db } from "@/db";
import { transportBookings } from "@/db/schema";
import { eq, and } from "drizzle-orm";
import type {
  TransportType,
  SeatClass,
  TransportBookingStatus,
} from "@/types";

// ============================================================
// 交通预订管理 (模拟)
// ============================================================

export interface CreateBookingParams {
  sessionId: string;
  routeId?: number;
  transportType: TransportType;
  routeNumber?: string;
  originCity: string;
  destCity: string;
  travelDate: string;
  departureTime?: string;
  seatClass?: SeatClass;
  passengerCount: number;
  passengerNames?: string[];
  unitPrice?: number;
  contactName?: string;
  contactPhone?: string;
  specialRequests?: string;
}

export async function createTransportBooking(params: CreateBookingParams) {
  const totalPrice = params.unitPrice
    ? params.unitPrice * params.passengerCount
    : undefined;

  const result = await db.insert(transportBookings).values({
    sessionId: params.sessionId,
    routeId: params.routeId ?? null,
    transportType: params.transportType,
    routeNumber: params.routeNumber ?? null,
    originCity: params.originCity,
    destCity: params.destCity,
    travelDate: params.travelDate,
    departureTime: params.departureTime ?? null,
    seatClass: params.seatClass ?? null,
    passengerCount: params.passengerCount,
    passengerNames: params.passengerNames ?? [],
    unitPrice: params.unitPrice ?? null,
    totalPrice: totalPrice ?? null,
    contactName: params.contactName ?? null,
    contactPhone: params.contactPhone ?? null,
    specialRequests: params.specialRequests ?? null,
    status: "pending",
  }).returning();

  return result[0];
}

export async function updateBookingStatus(
  bookingId: number,
  status: TransportBookingStatus
) {
  await db.update(transportBookings)
    .set({ status, updatedAt: new Date().toISOString() })
    .where(eq(transportBookings.id, bookingId));
}

export async function getBookingsBySession(sessionId: string) {
  return db.select().from(transportBookings)
    .where(eq(transportBookings.sessionId, sessionId))
    .limit(20);
}

export async function getBookingsByDate(sessionId: string, date: string) {
  return db.select().from(transportBookings)
    .where(and(
      eq(transportBookings.sessionId, sessionId),
      eq(transportBookings.travelDate, date),
    ));
}
