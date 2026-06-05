// ============================================================
// 餐厅相关类型
// ============================================================

export type PrivacyLevel = "L1" | "L2" | "L3" | "L4";

export interface Restaurant {
  id: number;
  name: string;
  city: string;
  district: string | null;
  address: string;
  latitude: number | null;
  longitude: number | null;
  cuisineType: string;
  cuisineTags: string[];
  priceRangeMin: number | null;
  priceRangeMax: number | null;
  privacyLevel: PrivacyLevel;
  privateRoomMin: number | null;
  privateRoomMax: number | null;
  privateRoomCount: number | null;
  rating: number;
  sceneTags: string[];
  businessTopics: string[];
  photoTips: string | null;
  signatureDishes: string[];
  contactPhone: string | null;
  openingHours: string | null;
  reservationNote: string | null;
}

export interface CulturalStory {
  id: number;
  restaurantId: number;
  storyType: "历史" | "文化" | "菜品" | "建筑";
  title: string;
  content: string;
  talkingPoints: string[];
  relatedTopics: string[];
}

// ============================================================
// NLU 类型
// ============================================================

export type Intent =
  | "dining_recommend"   // 宴请推荐
  | "booking"            // 预订
  | "query_restaurant"   // 查询餐厅
  | "modify_plan"        // 修改计划
  | "chitchat";          // 闲聊/其他

export interface NLUSlots {
  city?: string;
  date?: string;           // ISO日期
  time?: string;           // "18:30"
  guestCount?: number;
  budgetPerPerson?: number;
  budgetMax?: number;
  cuisine?: string;
  privacy?: PrivacyLevel;
  scene?: string;          // '高规格接待' | '团队聚餐' ...
  guestProfile?: string;   // '客户CTO' 等
  dietaryRestrictions?: string[];
}

export interface NLUResult {
  intent: Intent | ExtendedIntent;
  confidence: number;      // 0-1
  slots: NLUSlots | ExtendedNLUSlots;
  method: "llm" | "regex";
  missingSlots: string[];  // 缺失的必须槽位
}

// ============================================================
// 推荐系统类型
// ============================================================

export interface SearchConstraints {
  city: string;
  date?: string;
  time?: string;
  guestCount: number;
  budgetPerPerson?: number;
  budgetMax?: number;
  cuisine?: string;
  privacyMin?: PrivacyLevel;
  scene?: string;
  dietaryRestrictions?: string[];
}

export interface MatchedRestaurant {
  restaurant: Restaurant;
  culturalStories: CulturalStory[];
  llmReason?: string;       // LLM生成的推荐理由
  verified: boolean;        // P0-2: 是否通过交叉验证
  source: "database" | "llm_verified" | "llm_unverified" | "memory";
  score: number;            // 综合评分
}

export interface RecommendResponse {
  reply: string;                          // 自然语言回复
  recommendations: MatchedRestaurant[];   // Top 3 推荐 (向后兼容)
  cards?: ContentCard[];                  // 差序v2: 统一内容卡片
  followupQuestion: string | null;        // 追问问题
  nluDebug: {
    intent: string;
    slots: NLUSlots;
    method: string;
    confidence: number;
  };
}

// ============================================================
// 对话类型
// ============================================================

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  recommendations?: MatchedRestaurant[];
  cards?: ContentCard[];
  timestamp: string;
}

export interface ConversationContext {
  sessionId: string;
  currentIntent?: Intent;
  currentSlots: NLUSlots;
  history: ChatMessage[];
}

// ============================================================
// 预订相关类型
// ============================================================

export type BookingStatus = "recommended" | "confirmed" | "completed" | "reviewed";

export interface Booking {
  id: number;
  sessionId: string;
  restaurantId: number | null;
  restaurantName: string | null;
  bookingDate: string;
  bookingTime: string | null;
  guestCount: number;
  purpose: string | null;
  budgetPerPerson: number | null;
  totalSpent: number | null;
  status: BookingStatus;
  notes: string | null;
}

export interface UserPreferences {
  id: number;
  sessionId: string;
  preferredCuisines: string[] | null;
  budgetRange: { min: number; max: number } | null;
  preferredPrivacy: PrivacyLevel | null;
  dietaryRestrictions: string[] | null;
  frequentCities: string[] | null;
  notes: string | null;
}

export interface ConversationHistoryEntry {
  id: number;
  sessionId: string;
  role: "user" | "assistant" | "system";
  content: string;
  nluResult: NLUResult | null;
  metadata: Record<string, unknown> | null;
}

// ============================================================
// 多业态服务类型 (Phase 1: 类型基础)
// ============================================================

export type ServiceCategory = "bath" | "massage" | "ktv" | "dance_hall" | "business_shopping";

export type TransportType = "flight" | "train" | "private_car";

export type SeatClass = "economy" | "business" | "first" | "second" | "vip";

// ============================================================
// 扩展意图 (保留原 Intent 不变)
// ============================================================

export type ExtendedIntent =
  | Intent                                    // 原有5个意图
  | "entertainment_recommend"                 // 休闲娱乐推荐
  | "flight_search"                          // 机票搜索
  | "train_search"                           // 火车票搜索
  | "car_service"                            // 专车接送
  | "pickup_service"                         // 接机/接站
  | "shopping_recommend"                     // 商务购物
  | "trip_plan"                              // 行程规划(元意图)
  | "order_create"                           // 创建订单
  | "order_pay"                              // 支付订单
  | "order_list";                            // 查询订单

// ============================================================
// 扩展槽位
// ============================================================

export interface ExtendedNLUSlots extends NLUSlots {
  // 交通槽位
  departureCity?: string;
  arrivalCity?: string;
  transportType?: TransportType;
  seatClass?: SeatClass;
  departureDate?: string;
  returnDate?: string;
  passengerCount?: number;
  routeNumber?: string;

  // 娱乐槽位
  entertainmentType?: ServiceCategory;
  entertainmentScene?: string;              // '商务放松' | '团建' | '客户招待'

  // 购物槽位
  shoppingType?: string;                    // '商务礼品' | '特产' | '电子产品'
  shoppingBudget?: number;

  // 接驳槽位
  pickupLocation?: "airport" | "station" | "hotel" | "custom";
  pickupAddress?: string;

  // 会议/行程上下文
  meetingTime?: string;
  meetingLocation?: string;
  purpose?: string;
  tripDays?: number;
  orderNumber?: string;
}

// ============================================================
// 多意图分解类型
// ============================================================

export interface SharedContext {
  city?: string;
  arrivalCity?: string;
  date?: string;
  dateRange?: { start: string; end: string };
  purpose?: string;
  guestProfile?: string;
  meetingTime?: string;
  meetingLocation?: string;
  extractedFromOriginalInput: string;
}

export type SubIntentStatus = "pending" | "matched" | "failed" | "skipped";

export interface SubIntent {
  id: string;                               // 'si-1', 'si-2' ...
  intent: ExtendedIntent;
  confidence: number;
  slots: ExtendedNLUSlots;
  sourceSegment: string;                    // 产生该意图的原文片段
  missingSlots: string[];
  status: SubIntentStatus;
}

export interface MultiNLUResult {
  isMultiIntent: true;
  subIntents: SubIntent[];
  sharedContext: SharedContext;
  method: "llm" | "regex" | "hybrid";
  rawInput: string;
}

// 类型守卫
export function isMultiIntent(result: NLUResult | MultiNLUResult): result is MultiNLUResult {
  return "isMultiIntent" in result && result.isMultiIntent === true;
}

// ============================================================
// 服务 POI 类型 (entertainment + shopping)
// ============================================================

export interface Service {
  id: number;
  name: string;
  city: string;
  district: string | null;
  address: string;
  latitude: number | null;
  longitude: number | null;
  serviceCategory: ServiceCategory;
  serviceTags: string[];
  priceRangeMin: number | null;
  priceRangeMax: number | null;
  rating: number;
  privacyLevel: PrivacyLevel;
  capacity: number | null;
  sceneTags: string[];
  description: string | null;
  highlights: string[];
  contactPhone: string | null;
  openingHours: string | null;
  reservationNote: string | null;
}

export interface ServiceCulturalStory {
  id: number;
  serviceId: number;
  storyType: "品牌" | "特色" | "文化" | "工艺";
  title: string;
  content: string;
  talkingPoints: string[];
  relatedTopics: string[];
}

// ============================================================
// 交通类型
// ============================================================

export interface TransportRoute {
  id: number;
  transportType: TransportType;
  originCity: string;
  destCity: string;
  originStation: string | null;
  destStation: string | null;
  carrierName: string | null;
  routeNumber: string;
  departureTime: string;
  arrivalTime: string;
  durationMinutes: number | null;
  priceEconomy: number | null;
  priceBusiness: number | null;
  vehicleType: string | null;
  scheduleDays: string[];
  amenities: string[];
  rating: number;
}

export type TransportBookingStatus = "pending" | "confirmed" | "in_progress" | "completed" | "cancelled";

export interface TransportBooking {
  id: number;
  sessionId: string;
  routeId: number | null;
  transportType: TransportType;
  routeNumber: string | null;
  originCity: string;
  destCity: string;
  travelDate: string;
  departureTime: string | null;
  seatClass: SeatClass | null;
  passengerCount: number;
  passengerNames: string[];
  unitPrice: number | null;
  totalPrice: number | null;
  contactName: string | null;
  contactPhone: string | null;
  specialRequests: string | null;
  status: TransportBookingStatus;
}

// ============================================================
// 行程规划类型
// ============================================================

export type ItineraryStatus = "draft" | "confirmed" | "in_progress" | "completed" | "cancelled";

export type ItineraryItemType =
  | "transport" | "dining" | "entertainment"
  | "shopping" | "pickup" | "free_time" | "hotel";

export type ItineraryItemStatus = "planned" | "confirmed" | "in_progress" | "completed" | "cancelled";

export interface Itinerary {
  id: number;
  sessionId: string;
  title: string;
  purpose: string | null;
  originCity: string | null;
  destCity: string | null;
  startDate: string | null;
  endDate: string | null;
  travelerCount: number | null;
  totalBudget: number | null;
  totalCost: number;
  status: ItineraryStatus;
  metadata: Record<string, unknown> | null;
}

export interface ItineraryItem {
  id: number;
  itineraryId: number;
  sortOrder: number;
  itemType: ItineraryItemType;
  title: string;
  description: string | null;
  date: string | null;
  startTime: string | null;
  endTime: string | null;
  location: string | null;
  address: string | null;
  city: string | null;
  latitude: number | null;
  longitude: number | null;
  estimatedCost: number | null;
  actualCost: number | null;
  status: ItineraryItemStatus;
  refId: number | null;
  refType: "restaurant" | "service" | "transport_route" | null;
  metadata: Record<string, unknown> | null;
}

// ============================================================
// 聚合订单类型
// ============================================================

export type OrderStatus = "pending" | "paid" | "refunded" | "cancelled";

export type OrderItemCategory = "dining" | "transport" | "entertainment" | "shopping" | "service_fee";

export type PaymentMethod = "mock_alipay" | "mock_wechat" | "mock_corporate" | "manual";

export interface OrderItem {
  id: number;
  orderId: number;
  itemCategory: OrderItemCategory;
  itemTitle: string;
  itemDescription: string | null;
  quantity: number;
  unitPrice: number;
  subtotal: number;
  refId: number | null;
  refType: "restaurant" | "service" | "transport_route" | "transport_booking" | null;
  metadata: Record<string, unknown> | null;
}

export interface AggregatedOrder {
  id: number;
  sessionId: string;
  itineraryId: number | null;
  orderNumber: string;
  totalAmount: number;
  discountAmount: number;
  finalAmount: number;
  status: OrderStatus;
  paymentMethod: PaymentMethod | null;
  contactName: string | null;
  contactPhone: string | null;
  notes: string | null;
  metadata: Record<string, unknown> | null;
  items: OrderItem[];
}

// ============================================================
// 扩展响应类型
// ============================================================

export interface ServiceRecommendation {
  service: Service;
  culturalStories: ServiceCulturalStory[];
  reason?: string;
  score: number;
}

export interface TransportSearchResult {
  routes: TransportRoute[];
  originCity: string;
  destCity: string;
  date: string | null;
}

// ============================================================
// 统一内容卡片类型 (差序 v2)
// ============================================================

export type ContentCardCategory =
  | "restaurant" | "dance_hall" | "ktv" | "bath" | "massage"
  | "hotel" | "attraction" | "shopping";

export interface ContentCard {
  id: number;
  category: ContentCardCategory;
  title: string;
  subtitle: string;
  rating: number;
  priceRangeMin: number | null;
  priceRangeMax: number | null;
  privacyLevel: string;
  sceneTags: string[];
  description: string | null;
  highlights: string[];
  culturalStories: CulturalStory[] | ServiceCulturalStory[];
  contactPhone: string | null;
  openingHours: string | null;
  extras: Record<string, unknown>;
}

export interface SubResult {
  intent: ExtendedIntent;
  status: "success" | "failed";
  data?: unknown;                            // 类型取决于 intent
  error?: string;
}

export interface MultiIntentResponse {
  reply: string;
  isMultiIntent: true;
  subResults: SubResult[];
  itinerary?: { itineraryId: number; items: Array<Record<string, unknown>> } | null;
  followupQuestion: string | null;
  nluDebug: {
    sharedContext: SharedContext;
    subIntents: Array<{ intent: string; confidence: number; sourceSegment: string }>;
    method: string;
  };
}

// ============================================================
// 扩展用户偏好
// ============================================================

export interface UserExtendedPreferences {
  id: number;
  sessionId: string;
  preferredEntertainment: string[] | null;
  preferredTransport: string[] | null;
  preferredSeatClass: string | null;
  preferredShopping: string[] | null;
  frequentRoutes: Array<{ origin: string; dest: string }> | null;
  notes: string | null;
}
