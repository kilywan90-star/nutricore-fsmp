import { createClient } from "@libsql/client";
import { drizzle } from "drizzle-orm/libsql";
import * as schema from "./schema";
import path from "path";
import fs from "fs";
import { pathToFileURL } from "url";

const DB_DIR = path.join(process.cwd(), "data");
const DB_PATH = path.join(DB_DIR, "travel.db");

if (!fs.existsSync(DB_DIR)) {
  fs.mkdirSync(DB_DIR, { recursive: true });
}

const client = createClient({
  url: pathToFileURL(DB_PATH).href,
});

export const db = drizzle({ client, schema });

// PRAGMA设置
client.execute({ sql: "PRAGMA journal_mode = WAL", args: [] });
client.execute({ sql: "PRAGMA foreign_keys = ON", args: [] });

// 建表(幂等) — libSQL每次只能执行一条SQL
const DDL_STATEMENTS = [
  `CREATE TABLE IF NOT EXISTS restaurants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    district TEXT,
    address TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    cuisine_type TEXT NOT NULL,
    cuisine_tags TEXT DEFAULT '[]',
    price_range_min INTEGER,
    price_range_max INTEGER,
    privacy_level TEXT NOT NULL DEFAULT 'L2',
    private_room_min INTEGER,
    private_room_max INTEGER,
    private_room_count INTEGER,
    rating REAL NOT NULL DEFAULT 4.0,
    scene_tags TEXT DEFAULT '[]',
    business_topics TEXT DEFAULT '[]',
    photo_tips TEXT,
    signature_dishes TEXT DEFAULT '[]',
    contact_phone TEXT,
    opening_hours TEXT,
    reservation_note TEXT,
    data_source TEXT DEFAULT 'ai_seed',
    last_verified TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
  )`,
  `CREATE TABLE IF NOT EXISTS cultural_stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER NOT NULL REFERENCES restaurants(id) ON DELETE CASCADE,
    story_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    talking_points TEXT DEFAULT '[]',
    related_topics TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now','localtime'))
  )`,
  `CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    restaurant_id INTEGER REFERENCES restaurants(id) ON DELETE SET NULL,
    restaurant_name TEXT,
    booking_date TEXT NOT NULL,
    booking_time TEXT,
    guest_count INTEGER NOT NULL,
    purpose TEXT,
    budget_per_person INTEGER,
    total_spent INTEGER,
    status TEXT NOT NULL DEFAULT 'recommended',
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
  )`,
  `CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,
    preferred_cuisines TEXT,
    budget_range TEXT,
    preferred_privacy TEXT,
    dietary_restrictions TEXT,
    frequent_cities TEXT,
    notes TEXT,
    updated_at TEXT DEFAULT (datetime('now','localtime'))
  )`,
  `CREATE TABLE IF NOT EXISTS conversation_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    nlu_result TEXT,
    metadata TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
  )`,
  `CREATE INDEX IF NOT EXISTS idx_restaurants_city ON restaurants(city)`,
  `CREATE INDEX IF NOT EXISTS idx_restaurants_city_cuisine ON restaurants(city, cuisine_type)`,
  `CREATE INDEX IF NOT EXISTS idx_cultural_stories_restaurant ON cultural_stories(restaurant_id)`,
  `CREATE INDEX IF NOT EXISTS idx_bookings_session ON bookings(session_id)`,
  `CREATE INDEX IF NOT EXISTS idx_conversation_session ON conversation_history(session_id)`,

  // === 多业态扩展表 ===
  `CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    district TEXT,
    address TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    service_category TEXT NOT NULL,
    service_tags TEXT DEFAULT '[]',
    price_range_min INTEGER,
    price_range_max INTEGER,
    rating REAL NOT NULL DEFAULT 4.0,
    privacy_level TEXT NOT NULL DEFAULT 'L2',
    capacity INTEGER,
    scene_tags TEXT DEFAULT '[]',
    description TEXT,
    highlights TEXT DEFAULT '[]',
    contact_phone TEXT,
    opening_hours TEXT,
    reservation_note TEXT,
    data_source TEXT DEFAULT 'ai_seed',
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
  )`,
  `CREATE TABLE IF NOT EXISTS service_cultural_stories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id INTEGER NOT NULL REFERENCES services(id) ON DELETE CASCADE,
    story_type TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    talking_points TEXT DEFAULT '[]',
    related_topics TEXT DEFAULT '[]',
    created_at TEXT DEFAULT (datetime('now','localtime'))
  )`,
  `CREATE TABLE IF NOT EXISTS transport_routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transport_type TEXT NOT NULL,
    origin_city TEXT NOT NULL,
    dest_city TEXT NOT NULL,
    origin_station TEXT,
    dest_station TEXT,
    carrier_name TEXT,
    route_number TEXT NOT NULL,
    departure_time TEXT NOT NULL,
    arrival_time TEXT NOT NULL,
    duration_minutes INTEGER,
    price_economy INTEGER,
    price_business INTEGER,
    vehicle_type TEXT,
    schedule_days TEXT DEFAULT '[]',
    amenities TEXT DEFAULT '[]',
    rating REAL DEFAULT 4.0,
    data_source TEXT DEFAULT 'seed',
    created_at TEXT DEFAULT (datetime('now','localtime'))
  )`,
  `CREATE TABLE IF NOT EXISTS transport_bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    route_id INTEGER REFERENCES transport_routes(id) ON DELETE SET NULL,
    transport_type TEXT NOT NULL,
    route_number TEXT,
    origin_city TEXT NOT NULL,
    dest_city TEXT NOT NULL,
    travel_date TEXT NOT NULL,
    departure_time TEXT,
    seat_class TEXT,
    passenger_count INTEGER NOT NULL DEFAULT 1,
    passenger_names TEXT DEFAULT '[]',
    unit_price INTEGER,
    total_price INTEGER,
    contact_name TEXT,
    contact_phone TEXT,
    special_requests TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
  )`,
  `CREATE TABLE IF NOT EXISTS itineraries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    title TEXT NOT NULL,
    purpose TEXT,
    origin_city TEXT,
    dest_city TEXT,
    start_date TEXT,
    end_date TEXT,
    traveler_count INTEGER,
    total_budget INTEGER,
    total_cost INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'draft',
    metadata TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
  )`,
  `CREATE TABLE IF NOT EXISTS itinerary_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    itinerary_id INTEGER NOT NULL REFERENCES itineraries(id) ON DELETE CASCADE,
    sort_order INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    date TEXT,
    start_time TEXT,
    end_time TEXT,
    location TEXT,
    address TEXT,
    city TEXT,
    latitude REAL,
    longitude REAL,
    estimated_cost INTEGER,
    actual_cost INTEGER,
    status TEXT NOT NULL DEFAULT 'planned',
    ref_id INTEGER,
    ref_type TEXT,
    metadata TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
  )`,
  `CREATE TABLE IF NOT EXISTS aggregated_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    itinerary_id INTEGER REFERENCES itineraries(id) ON DELETE SET NULL,
    order_number TEXT NOT NULL,
    total_amount INTEGER NOT NULL,
    discount_amount INTEGER DEFAULT 0,
    final_amount INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    payment_method TEXT,
    contact_name TEXT,
    contact_phone TEXT,
    notes TEXT,
    metadata TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
  )`,
  `CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES aggregated_orders(id) ON DELETE CASCADE,
    item_category TEXT NOT NULL,
    item_title TEXT NOT NULL,
    item_description TEXT,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price INTEGER NOT NULL,
    subtotal INTEGER NOT NULL,
    ref_id INTEGER,
    ref_type TEXT,
    metadata TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
  )`,
  `CREATE TABLE IF NOT EXISTS user_extended_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,
    preferred_entertainment TEXT,
    preferred_transport TEXT,
    preferred_seat_class TEXT,
    preferred_shopping TEXT,
    frequent_routes TEXT,
    notes TEXT,
    updated_at TEXT DEFAULT (datetime('now','localtime'))
  )`,

  // === 扩展索引 ===
  `CREATE INDEX IF NOT EXISTS idx_services_city ON services(city)`,
  `CREATE INDEX IF NOT EXISTS idx_services_city_category ON services(city, service_category)`,
  `CREATE INDEX IF NOT EXISTS idx_services_category ON services(service_category)`,
  `CREATE INDEX IF NOT EXISTS idx_service_stories_service ON service_cultural_stories(service_id)`,
  `CREATE INDEX IF NOT EXISTS idx_routes_origin_dest ON transport_routes(origin_city, dest_city)`,
  `CREATE INDEX IF NOT EXISTS idx_routes_type ON transport_routes(transport_type)`,
  `CREATE INDEX IF NOT EXISTS idx_routes_number ON transport_routes(route_number)`,
  `CREATE INDEX IF NOT EXISTS idx_transport_bookings_session ON transport_bookings(session_id)`,
  `CREATE INDEX IF NOT EXISTS idx_transport_bookings_status ON transport_bookings(status)`,
  `CREATE INDEX IF NOT EXISTS idx_transport_bookings_date ON transport_bookings(travel_date)`,
  `CREATE INDEX IF NOT EXISTS idx_itineraries_session ON itineraries(session_id)`,
  `CREATE INDEX IF NOT EXISTS idx_itineraries_status ON itineraries(status)`,
  `CREATE INDEX IF NOT EXISTS idx_itinerary_items_parent ON itinerary_items(itinerary_id)`,
  `CREATE INDEX IF NOT EXISTS idx_itinerary_items_sort ON itinerary_items(itinerary_id, sort_order)`,
  `CREATE INDEX IF NOT EXISTS idx_orders_session ON aggregated_orders(session_id)`,
  `CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_number ON aggregated_orders(order_number)`,
  `CREATE INDEX IF NOT EXISTS idx_orders_status ON aggregated_orders(status)`,
  `CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)`,
  `CREATE UNIQUE INDEX IF NOT EXISTS idx_user_ext_prefs_session ON user_extended_preferences(session_id)`,
];

for (const sql of DDL_STATEMENTS) {
  client.execute({ sql, args: [] });
}

export type DB = typeof db;
