import { handleDining } from "../router/dining-handler";
import { handleEntertainment, handleShopping, handleTransport } from "../router/service-adapter";
import { searchServices } from "@/lib/services/service-search";
import type { DomainResponse, DomainHandler } from "../router/types";
import type { NLUResult, ExtendedNLUSlots, ContentCard, ServiceRecommendation } from "@/types";
import { toContentCards } from "../router/domain-router";

const RECEPTION_PATTERNS = [
  /(接待|招待|宴请|请客|找个地方|安排一下).{0,20}(客户|老板|领导|合作方|投资人|CEO|CTO|董事长|总裁|重要|VIP)/,
  /(客户|老板|领导|合作方).{0,20}(来了|要来|过来|考察|到访|拜访)/,
  /(帮我|给我).{0,5}(安排|规划|设计).{0,10}(接待|行程|招待)/,
  /(出差|商务).{0,10}(接待|安排|规划)/,
];

export function isReceptionIntent(input: string): boolean {
  return RECEPTION_PATTERNS.some((p) => p.test(input));
}

interface ReceptionPlan {
  city: string;
  guestProfile: string;
  guestLevel: "VIP" | "important" | "normal";
  guestCount: number;
  budget?: number;
  date?: string;
  purpose: string;
  meetingTime?: string;
  meetingLocation?: string;
}

export function parseReceptionInput(input: string, slots: ExtendedNLUSlots): ReceptionPlan {
  const guestLevel =
    /(VIP|重要|大客户|CTO|CEO|CFO|董事长|总裁)/.test(input) ? "VIP" :
    /(经理|主管|合作方|客户)/.test(input) ? "important" :
    "normal";

  return {
    city: slots.city || slots.arrivalCity || "成都",
    guestProfile: slots.guestProfile || "客户",
    guestLevel,
    guestCount: slots.guestCount || 2,
    budget: slots.budgetPerPerson || slots.budgetMax,
    date: slots.date || slots.departureDate,
    purpose: slots.purpose || "商务接待",
    meetingTime: slots.meetingTime,
    meetingLocation: slots.meetingLocation,
  };
}

interface TimelineItem {
  time: string;
  title: string;
  description: string;
  category: string;
  icon: string;
  cards: ContentCard[];
}

export async function planReception(
  plan: ReceptionPlan,
  sessionId: string
): Promise<{ reply: string; timeline: TimelineItem[] }> {
  const timeline: TimelineItem[] = [];
  const nluBase: NLUResult = {
    intent: "dining_recommend",
    confidence: 0.9,
    slots: {
      city: plan.city,
      guestCount: plan.guestCount,
      budgetPerPerson: plan.budget,
      scene: plan.guestLevel === "VIP" ? "高规格接待" : "商务洽谈",
      guestProfile: plan.guestProfile,
      date: plan.date,
    },
    method: "llm" as const,
    missingSlots: [],
  };

  // Step 1: Dining recommendation
  try {
    const diningResult = await handleDining(nluBase, sessionId);
    const diningCards = toContentCards(diningResult.data, "dining_recommend");
    timeline.push({
      time: plan.meetingTime ? adjustTime(plan.meetingTime, -2) : "18:00",
      title: "商务晚宴",
      description: diningResult.reply.substring(0, 120),
      category: "dining",
      icon: "restaurant",
      cards: diningCards.slice(0, 3),
    });
  } catch {
    timeline.push({
      time: "18:00",
      title: "商务晚宴",
      description: "暂无可用的餐厅推荐",
      category: "dining",
      icon: "restaurant",
      cards: [],
    });
  }

  // Step 2: Entertainment recommendation
  try {
    const entNLU: NLUResult = {
      ...nluBase,
      intent: "entertainment_recommend",
      slots: {
        ...nluBase.slots,
        entertainmentType: plan.guestLevel === "VIP" ? "ktv" : "bath",
        entertainmentScene: plan.guestLevel === "VIP" ? "商务招待" : "商务放松",
      },
    };
    const entResult = await handleEntertainment(entNLU, sessionId);
    const entCards = toContentCards(entResult.data, "entertainment_recommend");
    timeline.push({
      time: "20:30",
      title: getEntertainmentLabel(plan.guestLevel),
      description: entResult.reply.substring(0, 120),
      category: "entertainment",
      icon: "music",
      cards: entCards.slice(0, 3),
    });
  } catch {
    timeline.push({
      time: "20:30",
      title: "商务娱乐",
      description: "暂无可用的娱乐推荐",
      category: "entertainment",
      icon: "music",
      cards: [],
    });
  }

  // Step 3: Gift/shopping recommendation
  try {
    const shopNLU: NLUResult = {
      ...nluBase,
      intent: "shopping_recommend",
    };
    const shopResult = await handleShopping(shopNLU, sessionId);
    const shopCards = toContentCards(shopResult.data, "shopping_recommend");
    timeline.push({
      time: "次日09:00",
      title: "商务礼品",
      description: shopResult.reply.substring(0, 120),
      category: "shopping",
      icon: "gift",
      cards: shopCards.slice(0, 3),
    });
  } catch {
    timeline.push({
      time: "次日09:00",
      title: "商务礼品",
      description: "建议准备当地特产",
      category: "shopping",
      icon: "gift",
      cards: [],
    });
  }

  const reply = `为您规划了${plan.city}商务接待方案（${plan.guestProfile}，${plan.guestLevel === "VIP" ? "VIP级接待" : "标准接待"}）：

1. **商务晚宴**（18:00）：根据客户级别推荐合适餐厅
2. **商务娱乐**（20:30）：${getEntertainmentLabel(plan.guestLevel)}
3. **商务礼品**（次日）：当地特色商务礼品

点击下方时间线查看每个环节的详细推荐。`;

  return { reply, timeline };
}

function adjustTime(time: string, hoursOffset: number): string {
  const match = time.match(/(\d+):(\d+)/);
  if (!match) return time;
  const h = (parseInt(match[1]) + hoursOffset + 24) % 24;
  return `${String(h).padStart(2, "0")}:${match[2]}`;
}

function getEntertainmentLabel(level: string): string {
  switch (level) {
    case "VIP": return "高端KTV接待";
    case "important": return "商务KTV/洗浴";
    default: return "休闲放松";
  }
}
