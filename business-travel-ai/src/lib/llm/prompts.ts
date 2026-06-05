import type { ChatCompletionMessageParam } from "openai/resources/chat/completions";
import type { ExtendedIntent, NLUSlots, SearchConstraints, MatchedRestaurant } from "@/types";

export function buildIntentPrompt(
  userInput: string,
  historyContext?: string
): ChatCompletionMessageParam[] {
  const systemMsg = `你是"差序"商务出行助手的意图分类器。将用户输入分类为以下意图之一：

【餐饮】
- dining_recommend: 推荐餐厅、安排宴请、请客吃饭
- booking: 预订某家餐厅
- query_restaurant: 了解某家餐厅详情

【休闲娱乐】
- entertainment_recommend: 洗浴、按摩、KTV、舞厅、SPA等休闲娱乐推荐

【交通出行】
- flight_search: 查询/预订机票
- train_search: 查询/预订火车票、高铁
- car_service: 专车接送、包车、租车
- pickup_service: 接机、接站

【购物】
- shopping_recommend: 商务购物、特产、礼品、商场

【行程/订单】
- trip_plan: 综合行程规划（涉及多个服务品类）
- order_create: 创建/确认订单
- order_pay: 支付/付款
- order_list: 查看订单列表

【其他】
- modify_plan: 修改之前的推荐方案
- chitchat: 闲聊、打招呼

以JSON格式回复: {"intent": "意图名", "confidence": 0.0-1.0}

示例：
- "帮我找个上海请客户吃饭的地方" → {"intent": "dining_recommend", "confidence": 0.95}
- "安排个洗浴放松" → {"intent": "entertainment_recommend", "confidence": 0.90}
- "明天飞上海的机票" → {"intent": "flight_search", "confidence": 0.90}
- "帮我安排接机" → {"intent": "pickup_service", "confidence": 0.90}
- "买些特产送人" → {"intent": "shopping_recommend", "confidence": 0.85}
- "帮我预订刚才推荐的那家" → {"intent": "booking", "confidence": 0.90}
- "换一家便宜点的" → {"intent": "modify_plan", "confidence": 0.85}
- "你好" → {"intent": "chitchat", "confidence": 0.95}`;

  const messages: ChatCompletionMessageParam[] = [{ role: "system", content: systemMsg }];
  if (historyContext) {
    messages.push({ role: "system", content: `最近对话上下文: ${historyContext}` });
  }
  messages.push({ role: "user", content: `${userInput}\n\nReply with valid JSON.` });
  return messages;
}

export function buildSlotExtractionPrompt(
  userInput: string,
  intent: ExtendedIntent
): ChatCompletionMessageParam[] {
  const today = new Date().toISOString().split("T")[0];
  const systemMsg = `你是商务出行助手的信息提取器。从用户输入中提取结构化信息，以JSON格式返回。今天日期: ${today}

可提取的字段（只返回你能确认的字段）：
【基础】
- city: 城市名
- date: ISO日期
- time: 24小时制时间 (如 "六点半"→"18:30")
- guestCount: 人数 (整数)
- budgetPerPerson: 人均预算(元)
- budgetMax: 总预算上限(元)
- cuisine: 菜系
- privacy: 私密性等级 ("L1"|"L2"|"L3"|"L4")
- scene: 场景
- guestProfile: 客人描述
- dietaryRestrictions: 饮食限制数组

【交通】
- departureCity: 出发城市
- arrivalCity: 到达城市
- transportType: "flight"|"train"|"private_car"
- seatClass: "economy"|"business"|"first"|"second"|"vip"
- departureDate: 出发日期
- passengerCount: 乘客数
- routeNumber: 航班号/车次

【娱乐】
- entertainmentType: "bath"|"massage"|"ktv"|"dance_hall"|"business_shopping"
- entertainmentScene: 娱乐场景

【购物】
- shoppingType: "souvenir"|"luxury"|"mall"|"business_gift"

【接驳】
- pickupLocation: "airport"|"station"|"hotel"|"custom"

【会议/行程】
- meetingTime: 会议时间
- meetingLocation: 会议地点
- purpose: 出行目的
- tripDays: 出差天数

只返回你能从文本中确认的字段，不确定的不要包含。`;

  return [
    { role: "system", content: systemMsg },
    { role: "user", content: `[意图: ${intent}] ${userInput}\n\nReply with valid JSON.` },
  ];
}

export function buildRestaurantRecommendPrompt(
  constraints: SearchConstraints,
  restaurantNames: string[]
): ChatCompletionMessageParam[] {
  const systemMsg = `你是资深商务餐饮顾问。根据用户需求从候选餐厅列表中推荐最合适的，并说明推荐理由。

重要规则：
1. 你不得编造任何文化故事、历史典故或菜品传说。你只负责基于约束条件推荐餐厅并给出理由。
2. 所有文化故事由独立数据库提供，你不需要也不应该生成任何文化相关内容。
3. 推荐理由应聚焦于商务场景的适合度（私密性、氛围、菜系匹配度等）。

以JSON格式回复: {"recommendations": [{"name": "餐厅名", "reason": "推荐理由"}]}`;

  const userMsg = `用户需求:
- 城市: ${constraints.city}
- 人数: ${constraints.guestCount}人
${constraints.cuisine ? `- 菜系: ${constraints.cuisine}` : ""}
${constraints.budgetPerPerson ? `- 人均预算: ${constraints.budgetPerPerson}元` : ""}
${constraints.privacyMin ? `- 私密性要求: ${constraints.privacyMin}及以上` : ""}
${constraints.scene ? `- 场景: ${constraints.scene}` : ""}

候选餐厅: ${restaurantNames.join("、")}

Reply with valid JSON.`;

  return [
    { role: "system", content: systemMsg },
    { role: "user", content: userMsg },
  ];
}

export function buildResponsePrompt(
  recommendations: MatchedRestaurant[],
  slots: NLUSlots,
  followUp: string | null
): ChatCompletionMessageParam[] {
  const systemMsg = `你是"差序"商务出行助手，专业、简洁、温和。根据推荐结果生成自然语言回复。

规则：
1. 回复要简洁专业，像一位资深行政助理
2. 如果餐厅有文化故事，可以自然地提及一个谈资要点（但不要编造）
3. 如果有追问，放在回复末尾
4. 不要使用过多修饰语，直接给出有价值的信息`;

  const recSummary = recommendations
    .map(
      (r, i) =>
        `${i + 1}. ${r.restaurant.name} (${r.restaurant.cuisineType}, ${r.restaurant.privacyLevel}, 人均¥${r.restaurant.priceRangeMin}-${r.restaurant.priceRangeMax}, ${r.verified ? "已验证" : "待验证"})${r.llmReason ? `\n   推荐理由: ${r.llmReason}` : ""}`
    )
    .join("\n");

  const userMsg = `用户条件: ${slots.city || "未知"}${slots.guestCount ? `, ${slots.guestCount}人` : ""}${slots.cuisine ? `, ${slots.cuisine}` : ""}${slots.budgetPerPerson ? `, 人均${slots.budgetPerPerson}元` : ""}

推荐结果:
${recSummary}

${followUp ? `追问: ${followUp}` : ""}

请生成回复。`;

  return [
    { role: "system", content: systemMsg },
    { role: "user", content: userMsg },
  ];
}
