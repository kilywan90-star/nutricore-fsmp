import { executeServiceHandler } from "@/lib/services/service-handler";
import { getIntentLabel } from "./domain-map";
import { chatCompletion } from "@/lib/llm/client";
import type { DomainResponse, DomainHandler } from "./types";
import type { ExtendedIntent, ExtendedNLUSlots, ServiceRecommendation } from "@/types";

// ============================================================
// 服务适配器
// 将现有 ServiceHandler (SubResult) 桥接为 DomainHandler (DomainResponse)
// ============================================================

function emptyFallback(intent: ExtendedIntent, label: string, slots: ExtendedNLUSlots): string {
  const city = slots.city ?? "当地";
  switch (intent) {
    case "entertainment_recommend": {
      const type = slots.entertainmentType;
      const typeLabel = type === "dance_hall" ? "舞厅" : type === "ktv" ? "KTV" : type === "bath" ? "洗浴" : type === "massage" ? "按摩" : "休闲场所";
      return `抱歉，${city}暂无${typeLabel}数据。您可以试试其他品类（KTV、洗浴、按摩），或者换个城市看看。`;
    }
    case "flight_search":
      return `抱歉，未找到从${slots.departureCity ?? "出发地"}到${slots.arrivalCity ?? "目的地"}的航班。请检查城市名称或尝试其他出行方式。`;
    case "train_search":
      return `抱歉，未找到从${slots.departureCity ?? "出发地"}到${slots.arrivalCity ?? "目的地"}的火车票。请尝试其他出行方式。`;
    case "shopping_recommend":
      return `抱歉，${city}暂无商务购物推荐数据。正在扩展中，敬请期待。`;
    default:
      return `抱歉，${city}暂无${label}相关数据。功能正在完善中。`;
  }
}

function createServiceDomainHandler(intent: ExtendedIntent): DomainHandler {
  return async (nluResult, sessionId): Promise<DomainResponse> => {
    const slots = nluResult.slots as ExtendedNLUSlots;
    const result = await executeServiceHandler(intent, slots, sessionId);
    const label = getIntentLabel(intent);

    if (result.status === "success") {
      const data = result.data;

      if (!data || (Array.isArray(data) && data.length === 0)) {
        return { reply: emptyFallback(intent, label, slots) };
      }

      // 有结果时，调用 LLM 生成自然语言回复（和餐厅推荐一样的体验）
      if (Array.isArray(data) && data.length > 0) {
        const reply = await generateServiceReply(intent, label, slots, data);
        return { reply, data };
      }

      if (data && typeof data === "object" && "routes" in data) {
        const routes = (data as { routes: unknown[] }).routes;
        const origin = (data as { originCity?: string }).originCity || slots.departureCity || "";
        const dest = (data as { destCity?: string }).destCity || slots.arrivalCity || "";
        const reply = await generateTransportReply(intent, origin, dest, routes);
        return { reply, data };
      }

      if (data && typeof data === "object" && "message" in data) {
        return { reply: (data as { message: string }).message, data };
      }

      return { reply: `${label}已处理`, data };
    }

    return { reply: result.error || `${label}处理失败` };
  };
}

// 预构建的域处理器
export const handleEntertainment = createServiceDomainHandler("entertainment_recommend");
export const handleShopping = createServiceDomainHandler("shopping_recommend");

// 交通域：一个域覆盖 4 个意图，按 nluResult.intent 分发
export const handleTransport: DomainHandler = async (nluResult, sessionId): Promise<DomainResponse> => {
  const intent = nluResult.intent as ExtendedIntent;
  const handler = createServiceDomainHandler(intent);
  return handler(nluResult, sessionId);
};

/**
 * 为娱乐/服务结果生成自然语言回复（仿餐厅推荐的 LLM 风格）
 */
async function generateServiceReply(
  intent: ExtendedIntent,
  label: string,
  slots: ExtendedNLUSlots,
  items: ServiceRecommendation[]
): Promise<string> {
  const city = slots.city || "当地";
  const categoryLabel =
    slots.entertainmentType === "dance_hall" ? "舞厅" :
    slots.entertainmentType === "ktv" ? "KTV" :
    slots.entertainmentType === "bath" ? "洗浴中心" :
    slots.entertainmentType === "massage" ? "按摩会所" :
    label;

  try {
    const { chatCompletion } = await import("@/lib/llm/client");
    const summary = items.slice(0, 5).map((item, i) => {
      const s = (item as ServiceRecommendation).service;
      if (!s) return `${i + 1}. 未知`;
      const parts = [`${i + 1}. ${s.name}`];
      if (s.district) parts.push(`（${s.district}）`);
      if (s.priceRangeMin) {
        parts.push(`，人均 ¥${s.priceRangeMin}-${s.priceRangeMax}`);
      }
      if (s.rating) parts.push(`，评分 ${s.rating}`);
      if (s.sceneTags?.length) parts.push(`，适合${s.sceneTags.join("、")}`);
      if (s.description) parts.push(`，「${s.description}」`);
      return parts.join("");
    }).join("\n");

    const system = `你是"差序"商务出行助手，风格专业、简洁、有温度。根据用户需求和搜索结果生成自然语言回复。
规则：
1. 先一句话概括搜索结果（城市+品类+数量）
2. 逐条介绍推荐，每家 1-2 句话，包含位置、特色、评分
3. 如果用户指定了人数，提及适合度
4. 结尾追问是否需要预订或查看更多
5. 不要编造不存在的数据
6. 语气像一个贴心商旅管家`;

    const user = `用户需求：${city}，${categoryLabel}${slots.guestCount ? `，${slots.guestCount}人` : ""}${slots.scene ? `，${slots.scene}` : ""}

搜索结果：
${summary}

请生成回复。`;

    const resp = await chatCompletion([
      { role: "system", content: system },
      { role: "user", content: user },
    ], { temperature: 0.7, maxTokens: 512, timeout: 8000 });

    return resp;
  } catch {
    // LLM 不可用时优雅降级
    const names = items.slice(0, 3).map(d =>
      d.service?.name ?? "未知"
    );
    const detail = items.slice(0, 3).map((item, i) => {
      const s = item.service;
      if (!s) return "";
      const parts = [];
      if (s.district) parts.push(s.district);
      if (s.rating) parts.push(`${s.rating}分`);
      return parts.length ? `（${parts.join("，")}）` : "";
    });
    const lines = items.slice(0, 5).map((item, i) =>
      `${i + 1}. ${item.service?.name ?? "未知"}${detail[i] || ""}`
    );
    return `为您在${city}找到 ${items.length} 家${categoryLabel}推荐：\n${lines.join("\n")}${items.length > 3 ? `\n共 ${items.length} 家，建议您根据位置和评分进一步筛选。` : ""}`;
  }
}

async function generateTransportReply(
  intent: ExtendedIntent,
  origin: string,
  dest: string,
  routes: unknown[]
): Promise<string> {
  const typeLabel = intent === "flight_search" ? "航班" : intent === "train_search" ? "车次" : "线路";
  if (routes.length === 0) {
    return `未找到从 ${origin} 到 ${dest} 的${typeLabel}。`;
  }

  try {
    const { chatCompletion } = await import("@/lib/llm/client");
    const summary = routes.slice(0, 6).map((r, i) => {
      const rt = r as Record<string, unknown>;
      return `${i + 1}. ${rt.carrierName || ""}${rt.routeNumber || ""} | ${rt.departureTime}-${rt.arrivalTime} | ¥${rt.priceEconomy || "?"}/${rt.priceBusiness || "?"}`;
    }).join("\n");

    const resp = await chatCompletion([
      { role: "system", content: "你是差序商务出行助手，专业简洁。根据搜索结果生成自然回复，像一位贴心的商旅秘书。" },
      { role: "user", content: `从${origin}到${dest}的${typeLabel}搜索结果：\n${summary}\n请生成回复，介绍几条最优选择（考虑时间和价格），建议客户如何选择，结尾问是否需要预订。` },
    ], { temperature: 0.7, maxTokens: 400, timeout: 8000 });

    return resp;
  } catch {
    return `已为您找到 ${routes.length} 条从 ${origin} 到 ${dest} 的${typeLabel}，请查看详情。`;
  }
}
