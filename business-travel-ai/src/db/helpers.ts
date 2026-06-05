import { db } from "./index";
import {
  restaurants,
  culturalStories,
  bookings,
  userPreferences,
  conversationHistory,
  services,
  serviceCulturalStories,
  transportRoutes,
  transportBookings,
  itineraries,
  itineraryItems,
  aggregatedOrders,
  orderItems,
  userExtendedPreferences,
} from "./schema";

// Drizzle 推断类型 — 原有表
export type RestaurantRow = typeof restaurants.$inferSelect;
export type NewRestaurant = typeof restaurants.$inferInsert;
export type CulturalStoryRow = typeof culturalStories.$inferSelect;
export type NewCulturalStory = typeof culturalStories.$inferInsert;
export type BookingRow = typeof bookings.$inferSelect;
export type NewBooking = typeof bookings.$inferInsert;
export type UserPreferencesRow = typeof userPreferences.$inferSelect;
export type ConversationHistoryRow = typeof conversationHistory.$inferSelect;

// Drizzle 推断类型 — 扩展表
export type ServiceRow = typeof services.$inferSelect;
export type NewService = typeof services.$inferInsert;
export type ServiceCulturalStoryRow = typeof serviceCulturalStories.$inferSelect;
export type NewServiceCulturalStory = typeof serviceCulturalStories.$inferInsert;
export type TransportRouteRow = typeof transportRoutes.$inferSelect;
export type NewTransportRoute = typeof transportRoutes.$inferInsert;
export type TransportBookingRow = typeof transportBookings.$inferSelect;
export type NewTransportBooking = typeof transportBookings.$inferInsert;
export type ItineraryRow = typeof itineraries.$inferSelect;
export type NewItinerary = typeof itineraries.$inferInsert;
export type ItineraryItemRow = typeof itineraryItems.$inferSelect;
export type NewItineraryItem = typeof itineraryItems.$inferInsert;
export type AggregatedOrderRow = typeof aggregatedOrders.$inferSelect;
export type NewAggregatedOrder = typeof aggregatedOrders.$inferInsert;
export type OrderItemRow = typeof orderItems.$inferSelect;
export type NewOrderItem = typeof orderItems.$inferInsert;
export type UserExtendedPreferencesRow = typeof userExtendedPreferences.$inferSelect;

export async function dbReset(): Promise<void> {
  // 按FK逆序删除，避免外键约束冲突
  // 先删最底层子表，再删父表
  await db.delete(orderItems);
  await db.delete(aggregatedOrders);
  await db.delete(itineraryItems);
  await db.delete(itineraries);
  await db.delete(transportBookings);
  await db.delete(serviceCulturalStories);
  await db.delete(conversationHistory);
  await db.delete(bookings);
  await db.delete(userPreferences);
  await db.delete(userExtendedPreferences);
  await db.delete(culturalStories);
  await db.delete(services);
  await db.delete(transportRoutes);
  await db.delete(restaurants);
}
