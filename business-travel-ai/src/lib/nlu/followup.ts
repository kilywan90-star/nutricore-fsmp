import type { ExtendedIntent, ExtendedNLUSlots } from "@/types";

const REQUIRED_SLOTS: Record<string, string[]> = {
  dining_recommend: ["guestCount"],
  booking: ["city", "guestCount"],
  query_restaurant: [],
  modify_plan: [],
  chitchat: [],
  // 新增意图
  entertainment_recommend: ["city"],
  flight_search: ["departureCity", "arrivalCity", "date"],
  train_search: ["departureCity", "arrivalCity", "date"],
  car_service: [],
  pickup_service: ["pickupLocation", "date"],
  shopping_recommend: ["city"],
  trip_plan: ["city", "date"],
  order_create: [],
  order_pay: [],
  order_list: [],
};

const SLOT_QUESTIONS: Record<string, (slots: ExtendedNLUSlots) => string> = {
  city: (slots) =>
    slots.guestProfile
      ? `您要宴请${slots.guestProfile}在哪个城市呢？`
      : "请问在哪个城市？",
  guestCount: (slots) =>
    slots.scene ? `${slots.scene}大概多少人参加？` : "请问一共几位？",
  date: () => "请问安排在哪天？",
  time: () => "大概几点开始呢？",
  cuisine: () => "想吃什么菜系呢？比如粤菜、川菜、日料？",
  budgetPerPerson: () => "人均预算大概多少？",
  departureCity: () => "从哪个城市出发？",
  arrivalCity: () => "要到哪个城市？",
  pickupLocation: () => "在哪里接？机场、车站还是酒店？",
};

// 组合追问模板 (按优先级)
const COMBO_QUESTIONS: Array<{
  slots: string[];
  template: (s: ExtendedNLUSlots) => string;
}> = [
  {
    slots: ["city", "guestCount"],
    template: () => "请问在哪个城市，一共几位？",
  },
  {
    slots: ["departureCity", "arrivalCity"],
    template: () => "请问从哪到哪？",
  },
];

export function generateFollowUp(
  intent: ExtendedIntent | string,
  slots: ExtendedNLUSlots
): { missingSlots: string[]; question: string | null } {
  const required = REQUIRED_SLOTS[intent] || [];
  const missingSlots = required.filter((key) => {
    const value = (slots as Record<string, unknown>)[key];
    return value === undefined || value === null;
  });

  if (missingSlots.length === 0) {
    return { missingSlots: [], question: null };
  }

  // 尝试组合追问
  for (const combo of COMBO_QUESTIONS) {
    if (combo.slots.every((s) => missingSlots.includes(s))) {
      return { missingSlots, question: combo.template(slots) };
    }
  }

  // 单个追问 (最多2个)
  const toAsk = missingSlots.slice(0, 2);
  const questions = toAsk
    .map((key) => SLOT_QUESTIONS[key]?.(slots))
    .filter(Boolean);

  return {
    missingSlots,
    question: questions.length > 0 ? questions.join(" ") : null,
  };
}
