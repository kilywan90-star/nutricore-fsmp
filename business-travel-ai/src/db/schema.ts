import { sqliteTable, text, integer, real } from "drizzle-orm/sqlite-core";
import { sql } from "drizzle-orm";
import type { NLUResult } from "@/types";
// ============================================================
// restaurants — 餐厅主表
// ============================================================
export const restaurants = sqliteTable("restaurants", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  name: text("name").notNull(),
  city: text("city").notNull(),            // '上海' | '北京' | '深圳'
  district: text("district"),              // '徐汇区' | '朝阳区' ...
  address: text("address").notNull(),
  latitude: real("latitude"),
  longitude: real("longitude"),

  // 菜系
  cuisineType: text("cuisine_type").notNull(), // '本帮菜' | '粤菜' | '川菜' ...
  cuisineTags: text("cuisine_tags", { mode: "json" }).$type<string[]>().default([]),

  // 价格
  priceRangeMin: integer("price_range_min"),   // 人均最低(元)
  priceRangeMax: integer("price_range_max"),   // 人均最高(元)

  // 私密性: L1(开放) L2(半隔断) L3(独立包间) L4(顶级私密)
  privacyLevel: text("privacy_level").notNull().default("L2"),
  privateRoomMin: integer("private_room_min"), // 最小包间容量(人)
  privateRoomMax: integer("private_room_max"), // 最大包间容量(人)
  privateRoomCount: integer("private_room_count"), // 包间数量

  // 评分
  rating: real("rating").notNull().default(4.0),

  // 标签
  sceneTags: text("scene_tags", { mode: "json" }).$type<string[]>().default([]),
  businessTopics: text("business_topics", { mode: "json" }).$type<string[]>().default([]),
  photoTips: text("photo_tips"),           // 拍照推荐文本
  signatureDishes: text("signature_dishes", { mode: "json" }).$type<string[]>().default([]),

  // 联系
  contactPhone: text("contact_phone"),
  openingHours: text("opening_hours"),
  reservationNote: text("reservation_note"),

  // 元数据
  dataSource: text("data_source").default("ai_seed"), // 'ai_seed' | 'manual' | 'api'
  lastVerified: text("last_verified"),
  createdAt: text("created_at").default(sql`(datetime('now','localtime'))`),
  updatedAt: text("updated_at").default(sql`(datetime('now','localtime'))`),
});

// ============================================================
// cultural_stories — 文化故事表 (P0-3: 独立于LLM, 只从DB读取)
// ============================================================
export const culturalStories = sqliteTable("cultural_stories", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  restaurantId: integer("restaurant_id")
    .notNull()
    .references(() => restaurants.id, { onDelete: "cascade" }),
  storyType: text("story_type").notNull(),   // '历史' | '文化' | '菜品' | '建筑'
  title: text("title").notNull(),
  content: text("content").notNull(),        // 故事正文 (300-500字)
  talkingPoints: text("talking_points", { mode: "json" }).$type<string[]>().default([]),
  relatedTopics: text("related_topics", { mode: "json" }).$type<string[]>().default([]),
  createdAt: text("created_at").default(sql`(datetime('now','localtime'))`),
});

// ============================================================
// bookings — 宴请预订记录
// ============================================================
export const bookings = sqliteTable("bookings", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  sessionId: text("session_id").notNull(),
  restaurantId: integer("restaurant_id")
    .references(() => restaurants.id, { onDelete: "set null" }),
  restaurantName: text("restaurant_name"),   // 冗余存储(餐厅可能删除)
  bookingDate: text("booking_date").notNull(),
  bookingTime: text("booking_time"),
  guestCount: integer("guest_count").notNull(),
  purpose: text("purpose"),                  // '宴请客户' | '团队聚餐' ...
  budgetPerPerson: integer("budget_per_person"),
  totalSpent: integer("total_spent"),        // 实际消费(宴请后补填)
  status: text("status").notNull().default("recommended"),
  // 'recommended' → 'confirmed' → 'completed' → 'reviewed'
  notes: text("notes"),
  createdAt: text("created_at").default(sql`(datetime('now','localtime'))`),
});

// ============================================================
// user_preferences — 用户偏好 (C路记忆数据源)
// ============================================================
export const userPreferences = sqliteTable("user_preferences", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  sessionId: text("session_id").notNull().unique(),
  preferredCuisines: text("preferred_cuisines", { mode: "json" }).$type<string[]>(),
  budgetRange: text("budget_range", { mode: "json" }).$type<{ min: number; max: number }>(),
  preferredPrivacy: text("preferred_privacy"),    // 'L3' | 'L4'
  dietaryRestrictions: text("dietary_restrictions", { mode: "json" }).$type<string[]>(),
  frequentCities: text("frequent_cities", { mode: "json" }).$type<string[]>(),
  notes: text("notes"),
  updatedAt: text("updated_at").default(sql`(datetime('now','localtime'))`),
});

// ============================================================
// conversation_history — 对话历史
// ============================================================
export const conversationHistory = sqliteTable("conversation_history", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  sessionId: text("session_id").notNull(),
  role: text("role").notNull(),           // 'user' | 'assistant' | 'system'
  content: text("content").notNull(),
  nluResult: text("nlu_result", { mode: "json" }).$type<NLUResult>(),
  metadata: text("metadata", { mode: "json" }).$type<Record<string, unknown>>(),
  createdAt: text("created_at").default(sql`(datetime('now','localtime'))`),
});

// ============================================================
// services — 休闲娱乐 + 商务购物 POI
// ============================================================
export const services = sqliteTable("services", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  name: text("name").notNull(),
  city: text("city").notNull(),
  district: text("district"),
  address: text("address").notNull(),
  latitude: real("latitude"),
  longitude: real("longitude"),

  serviceCategory: text("service_category").notNull(),
  serviceTags: text("service_tags", { mode: "json" }).$type<string[]>().default([]),

  priceRangeMin: integer("price_range_min"),
  priceRangeMax: integer("price_range_max"),
  rating: real("rating").notNull().default(4.0),
  privacyLevel: text("privacy_level").notNull().default("L2"),
  capacity: integer("capacity"),

  sceneTags: text("scene_tags", { mode: "json" }).$type<string[]>().default([]),
  description: text("description"),
  highlights: text("highlights", { mode: "json" }).$type<string[]>().default([]),

  contactPhone: text("contact_phone"),
  openingHours: text("opening_hours"),
  reservationNote: text("reservation_note"),

  dataSource: text("data_source").default("ai_seed"),
  createdAt: text("created_at").default(sql`(datetime('now','localtime'))`),
  updatedAt: text("updated_at").default(sql`(datetime('now','localtime'))`),
});

// ============================================================
// serviceCulturalStories — 非餐饮服务的文化故事
// ============================================================
export const serviceCulturalStories = sqliteTable("service_cultural_stories", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  serviceId: integer("service_id")
    .notNull()
    .references(() => services.id, { onDelete: "cascade" }),
  storyType: text("story_type").notNull(),
  title: text("title").notNull(),
  content: text("content").notNull(),
  talkingPoints: text("talking_points", { mode: "json" }).$type<string[]>().default([]),
  relatedTopics: text("related_topics", { mode: "json" }).$type<string[]>().default([]),
  createdAt: text("created_at").default(sql`(datetime('now','localtime'))`),
});

// ============================================================
// transportRoutes — 预设航线/火车线路
// ============================================================
export const transportRoutes = sqliteTable("transport_routes", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  transportType: text("transport_type").notNull(),
  originCity: text("origin_city").notNull(),
  destCity: text("dest_city").notNull(),
  originStation: text("origin_station"),
  destStation: text("dest_station"),
  carrierName: text("carrier_name"),
  routeNumber: text("route_number").notNull(),
  departureTime: text("departure_time").notNull(),
  arrivalTime: text("arrival_time").notNull(),
  durationMinutes: integer("duration_minutes"),
  priceEconomy: integer("price_economy"),
  priceBusiness: integer("price_business"),
  vehicleType: text("vehicle_type"),
  scheduleDays: text("schedule_days", { mode: "json" }).$type<string[]>().default([]),
  amenities: text("amenities", { mode: "json" }).$type<string[]>().default([]),
  rating: real("rating").default(4.0),
  dataSource: text("data_source").default("seed"),
  createdAt: text("created_at").default(sql`(datetime('now','localtime'))`),
});

// ============================================================
// transportBookings — 交通预订记录
// ============================================================
export const transportBookings = sqliteTable("transport_bookings", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  sessionId: text("session_id").notNull(),
  routeId: integer("route_id")
    .references(() => transportRoutes.id, { onDelete: "set null" }),
  transportType: text("transport_type").notNull(),
  routeNumber: text("route_number"),
  originCity: text("origin_city").notNull(),
  destCity: text("dest_city").notNull(),
  travelDate: text("travel_date").notNull(),
  departureTime: text("departure_time"),
  seatClass: text("seat_class"),
  passengerCount: integer("passenger_count").notNull().default(1),
  passengerNames: text("passenger_names", { mode: "json" }).$type<string[]>().default([]),
  unitPrice: integer("unit_price"),
  totalPrice: integer("total_price"),
  contactName: text("contact_name"),
  contactPhone: text("contact_phone"),
  specialRequests: text("special_requests"),
  status: text("status").notNull().default("pending"),
  createdAt: text("created_at").default(sql`(datetime('now','localtime'))`),
  updatedAt: text("updated_at").default(sql`(datetime('now','localtime'))`),
});

// ============================================================
// itineraries — 行程计划
// ============================================================
export const itineraries = sqliteTable("itineraries", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  sessionId: text("session_id").notNull(),
  title: text("title").notNull(),
  purpose: text("purpose"),
  originCity: text("origin_city"),
  destCity: text("dest_city"),
  startDate: text("start_date"),
  endDate: text("end_date"),
  travelerCount: integer("traveler_count"),
  totalBudget: integer("total_budget"),
  totalCost: integer("total_cost").default(0),
  status: text("status").notNull().default("draft"),
  metadata: text("metadata", { mode: "json" }).$type<Record<string, unknown>>(),
  createdAt: text("created_at").default(sql`(datetime('now','localtime'))`),
  updatedAt: text("updated_at").default(sql`(datetime('now','localtime'))`),
});

// ============================================================
// itineraryItems — 行程中的有序项目
// ============================================================
export const itineraryItems = sqliteTable("itinerary_items", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  itineraryId: integer("itinerary_id")
    .notNull()
    .references(() => itineraries.id, { onDelete: "cascade" }),
  sortOrder: integer("sort_order").notNull(),
  itemType: text("item_type").notNull(),
  title: text("title").notNull(),
  description: text("description"),
  date: text("date"),
  startTime: text("start_time"),
  endTime: text("end_time"),
  location: text("location"),
  address: text("address"),
  city: text("city"),
  latitude: real("latitude"),
  longitude: real("longitude"),
  estimatedCost: integer("estimated_cost"),
  actualCost: integer("actual_cost"),
  status: text("status").notNull().default("planned"),
  refId: integer("ref_id"),
  refType: text("ref_type"),
  metadata: text("metadata", { mode: "json" }).$type<Record<string, unknown>>(),
  createdAt: text("created_at").default(sql`(datetime('now','localtime'))`),
});

// ============================================================
// aggregatedOrders — 聚合支付订单
// ============================================================
export const aggregatedOrders = sqliteTable("aggregated_orders", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  sessionId: text("session_id").notNull(),
  itineraryId: integer("itinerary_id")
    .references(() => itineraries.id, { onDelete: "set null" }),
  orderNumber: text("order_number").notNull(),
  totalAmount: integer("total_amount").notNull(),
  discountAmount: integer("discount_amount").default(0),
  finalAmount: integer("final_amount").notNull(),
  status: text("status").notNull().default("pending"),
  paymentMethod: text("payment_method"),
  contactName: text("contact_name"),
  contactPhone: text("contact_phone"),
  notes: text("notes"),
  metadata: text("metadata", { mode: "json" }).$type<Record<string, unknown>>(),
  createdAt: text("created_at").default(sql`(datetime('now','localtime'))`),
  updatedAt: text("updated_at").default(sql`(datetime('now','localtime'))`),
});

// ============================================================
// orderItems — 订单明细行
// ============================================================
export const orderItems = sqliteTable("order_items", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  orderId: integer("order_id")
    .notNull()
    .references(() => aggregatedOrders.id, { onDelete: "cascade" }),
  itemCategory: text("item_category").notNull(),
  itemTitle: text("item_title").notNull(),
  itemDescription: text("item_description"),
  quantity: integer("quantity").notNull().default(1),
  unitPrice: integer("unit_price").notNull(),
  subtotal: integer("subtotal").notNull(),
  refId: integer("ref_id"),
  refType: text("ref_type"),
  metadata: text("metadata", { mode: "json" }).$type<Record<string, unknown>>(),
  createdAt: text("created_at").default(sql`(datetime('now','localtime'))`),
});

// ============================================================
// userExtendedPreferences — 多业态用户偏好
// ============================================================
export const userExtendedPreferences = sqliteTable("user_extended_preferences", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  sessionId: text("session_id").notNull().unique(),
  preferredEntertainment: text("preferred_entertainment", { mode: "json" }).$type<string[]>(),
  preferredTransport: text("preferred_transport", { mode: "json" }).$type<string[]>(),
  preferredSeatClass: text("preferred_seat_class"),
  preferredShopping: text("preferred_shopping", { mode: "json" }).$type<string[]>(),
  frequentRoutes: text("frequent_routes", { mode: "json" }).$type<Array<{ origin: string; dest: string }>>(),
  notes: text("notes"),
  updatedAt: text("updated_at").default(sql`(datetime('now','localtime'))`),
});
