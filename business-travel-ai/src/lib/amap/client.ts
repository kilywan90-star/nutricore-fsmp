import { env } from "@/lib/env";
import crypto from "crypto";

const BASE = "https://restapi.amap.com/v3";

function buildSig(params: Record<string, string>): string {
  const sorted = Object.keys(params).sort().map(k => `${k}=${params[k]}`).join("&");
  return crypto.createHash("md5").update(sorted + (env.AMAP_SECRET || "")).digest("hex");
}

async function amapGet(path: string, params: Record<string, string>): Promise<Record<string, unknown>> {
  const all: Record<string, string> = { key: env.AMAP_API_KEY || "", ...params };
  // USERKEY_PLAT_NOMATCH = key类型不匹配。Web端key只能浏览器JS API用
  // 服务端需要创建"Web服务"类型的key: https://console.amap.com/dev/key/app
  // 当前降级：返回空数据，由DB兜底

  const query = Object.entries(all)
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
    .join("&");

  const url = `${BASE}${path}?${query}`;

  try {
    const resp = await fetch(url, {
      headers: { "Accept": "application/json" },
      signal: AbortSignal.timeout(6000),
    });
    if (!resp.ok) return {};
    const data = await resp.json() as Record<string, unknown>;
    if (data.status !== "1") {
      // USERKEY_PLAT_NOMATCH, DAILY_QUERY_OVER_LIMIT 等均降级
      if (String(data.infocode || "") !== "10000") {
        console.warn(`[amap] key issue: ${data.info} (code=${data.infocode}). Need Web服务 key. Falling back to DB.`);
      }
      return {};
    }
    return data;
  } catch (err) {
    console.warn("[amap] network error, falling back to DB");
    return {};
  }
}

interface AmapPOI {
  id: string; name: string; type: string; address: string; location: string;
  pname: string; cityname: string; adname: string;
  biz_ext?: { rating?: string; cost?: string };
  photos?: Array<{ url: string }>; distance?: string; tel?: string;
}

export interface AmapRestaurant {
  name: string; city: string; district: string; address: string;
  longitude: number | null; latitude: number | null;
  category: string; subCategory: string;
  rating: number; avgCost: number | null; tel: string | null; photos: string[];
}

function mapPOI(p: AmapPOI): AmapRestaurant {
  const [lng, lat] = (p.location || "0,0").split(",").map(Number);
  return {
    name: p.name, city: p.cityname, district: p.adname, address: p.address,
    longitude: lng || null, latitude: lat || null,
    category: p.type?.split(";")[0] || "", subCategory: p.type || "",
    rating: p.biz_ext?.rating ? parseFloat(p.biz_ext.rating) / 20 : 3.5,
    avgCost: p.biz_ext?.cost ? parseFloat(p.biz_ext.cost) : null,
    tel: p.tel || null, photos: (p.photos || []).map(x => x.url),
  };
}

export async function searchAmapRestaurants(city: string, keywords?: string, cuisine?: string): Promise<AmapRestaurant[]> {
  if (!env.AMAP_API_KEY) return [];
  try {
    const params: Record<string, string> = { city, types: "050000", citylimit: "true", extensions: "all", offset: "20" };
    if (keywords || cuisine) params.keywords = cuisine || keywords || "";
    const data = await amapGet("/place/text", params);
    const pois = (data.pois || []) as AmapPOI[];
    return pois.map(mapPOI);
  } catch (err) { console.error("[amap] restaurant search failed:", err); return []; }
}

export async function searchAmapEntertainment(city: string, category: string): Promise<AmapRestaurant[]> {
  if (!env.AMAP_API_KEY) return [];
  const typeMap: Record<string, string> = { ktv: "080303", dance_hall: "080304", bath: "080400", massage: "080304" };
  try {
    const params: Record<string, string> = { city, types: typeMap[category] || "080000", citylimit: "true", extensions: "all", offset: "20" };
    const data = await amapGet("/place/text", params);
    return ((data.pois || []) as AmapPOI[]).map(mapPOI);
  } catch (err) { console.error("[amap] entertainment search failed:", err); return []; }
}

export async function searchAmapHotels(city: string): Promise<AmapRestaurant[]> {
  if (!env.AMAP_API_KEY) return [];
  try {
    const params: Record<string, string> = { city, types: "100000", citylimit: "true", extensions: "all", offset: "20" };
    const data = await amapGet("/place/text", params);
    return ((data.pois || []) as AmapPOI[]).map(mapPOI);
  } catch (err) { console.error("[amap] hotel search failed:", err); return []; }
}
