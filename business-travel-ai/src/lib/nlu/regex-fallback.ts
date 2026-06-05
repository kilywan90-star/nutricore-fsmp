import type { ExtendedIntent, ExtendedNLUSlots, NLUResult, PrivacyLevel } from "@/types";

// ============================================================
// 意图正则 (优先级序)
// ============================================================

const INTENT_PATTERNS: { intent: ExtendedIntent; patterns: RegExp[]; confidence: number }[] = [
  {
    intent: "dining_recommend",
    patterns: [
      /(推荐|找|安排|订|选).{0,10}(餐厅|饭店|吃饭|请客|宴请|地方|馆子)/,
      /(请|约|招待|接待).{0,10}(吃|饭|客)/,
      /哪.{0,5}(吃|餐|饭)/,
      /(吃饭|用餐|宴请).{0,10}(推荐|安排|找)/,
    ],
    confidence: 0.70,
  },
  {
    intent: "booking",
    patterns: [
      /(预订|订位|预约|帮我订|定个|帮我约)/,
      /约.{0,5}(位子|座位|包间)/,
      /(刚才|之前|那家).{0,5}(订|约|预定)/,
    ],
    confidence: 0.70,
  },
  {
    intent: "query_restaurant",
    patterns: [
      /(查|看看|了解|介绍|详情).{0,10}(餐厅|饭店|这家|那家|店)/,
      /(这个|那家|这家).{0,5}(怎么样|如何|好不好)/,
    ],
    confidence: 0.65,
  },
  {
    intent: "modify_plan",
    patterns: [
      /(换一[个家]|换一个|改一[个下]|调整|不要这[个家])/,
      /(重新|再).{0,5}(推荐|找|选|安排)/,
      /(便宜|贵|远|近).{0,3}(点|些|一[点些])/,
      /取消/,
    ],
    confidence: 0.65,
  },
  {
    intent: "entertainment_recommend",
    patterns: [
      /(洗浴|按摩|KTV|ktv|舞厅|SPA|spa|放松|足浴|桑拿|汗蒸|休闲会所)/,
      /(找|推荐|安排|订).{0,10}(洗浴|按摩|KTV|spa|放松|休闲)/,
      /(洗完|按完|唱完).{0,5}(去哪|再|然后).{0,5}(放松|玩|娱乐)/,
      /(商务|请客户).{0,5}(放松|休闲|娱乐|洗浴)/,
    ],
    confidence: 0.70,
  },
  {
    intent: "flight_search",
    patterns: [
      /(机票|航班|飞机|航线)/,
      /(订|买|查|搜).{0,5}(机票|航班)/,
      /飞.{0,5}(上海|北京|深圳|广州|成都|重庆|昆明|长沙|武汉|西安|杭州|南京)/,
      /(去|到).{0,5}(上海|北京|深圳|广州|成都).{0,5}(飞|航班|机票)/,
    ],
    confidence: 0.70,
  },
  {
    intent: "train_search",
    patterns: [
      /(火车票|高铁|动车|列车|车次)/,
      /(订|买|查|搜).{0,5}(火车票|高铁|动车)/,
      /(高铁|动车).{0,5}(去|到|开往)/,
    ],
    confidence: 0.70,
  },
  {
    intent: "car_service",
    patterns: [
      /(专车|包车|租车|用车|打车|叫车)/,
      /(安排|帮我|叫).{0,5}(专车|车|包车)/,
      /(商务|豪华).{0,3}(用车|专车|包车)/,
    ],
    confidence: 0.65,
  },
  {
    intent: "pickup_service",
    patterns: [
      /(接机|接站|接人|到机场接|到车站接|接驾)/,
      /(安排|帮我).{0,5}(接机|接站|接人)/,
      /(机场|车站|火车站).{0,5}(接|有人接)/,
    ],
    confidence: 0.70,
  },
  {
    intent: "shopping_recommend",
    patterns: [
      /(购物|商场|逛街|奥特莱斯|免税店)/,
      /(买|带).{0,5}(特产|礼物|礼品|伴手礼|纪念品)/,
      /(商务|送人).{0,5}(礼品|礼物|购物)/,
      /(推荐|找|安排).{0,5}(购物|商场|买.*特产)/,
    ],
    confidence: 0.65,
  },
  {
    intent: "trip_plan",
    patterns: [
      /(安排行程|出差计划|行程安排|行程规划)/,
      /(帮我|给我).{0,3}安排.{5,}/,
      /规划.{0,3}(行程|出差|旅行|出行)/,
      /(出差|出行|旅行).{0,5}(计划|安排|攻略)/,
    ],
    confidence: 0.60,
  },
  {
    intent: "order_create",
    patterns: [
      /(下单|创建订单|确认预订|确认订单)/,
      /(帮我|给我).{0,3}(下单|创建.*订单|确认.*预订)/,
    ],
    confidence: 0.70,
  },
  {
    intent: "order_pay",
    patterns: [
      /(支付|付款|结账|买单|结算)/,
      /(帮我|给我).{0,3}(支付|付款|买单)/,
    ],
    confidence: 0.70,
  },
  {
    intent: "order_list",
    patterns: [
      /(我的订单|订单列表|查看订单|历史订单)/,
      /(查|看).{0,5}(订单|消费记录)/,
    ],
    confidence: 0.70,
  },
  {
    intent: "chitchat",
    patterns: [
      /(你好|嗨|hi|hello|你是谁|你能做什么|谢谢|再见)/i,
    ],
    confidence: 0.40,
  },
];

// ============================================================
// 城市列表
// ============================================================

const CITIES = [
  "北京", "上海", "深圳", "广州", "杭州", "成都",
  "南京", "武汉", "西安", "苏州", "重庆", "长沙",
  "天津", "郑州", "青岛", "大连", "沈阳", "哈尔滨",
  "昆明", "贵阳", "南宁", "海口", "三亚", "厦门",
  "福州", "济南", "合肥", "南昌", "石家庄", "太原",
  "兰州", "银川", "西宁", "乌鲁木齐", "呼和浩特",
  "拉萨", "珠海", "佛山", "东莞", "无锡", "宁波",
  "温州", "常州", "徐州", "扬州", "桂林", "丽江",
  "大理", "西双版纳", "德阳", "绵阳", "乐山", "宜宾",
  "泸州", "自贡", "攀枝花", "广元", "遂宁", "内江",
  "达州", "广安", "南充", "巴中", "雅安", "眉山",
  "资阳", "凉山", "阿坝", "甘孜",
  "曲靖", "玉溪", "保山", "昭通", "普洱", "临沧",
  "楚雄", "红河", "文山", "德宏", "怒江", "迪庆",
  "株洲", "湘潭", "邵阳", "常德", "益阳", "郴州",
  "永州", "怀化", "娄底", "湘西", "张家界", "衡阳",
  "岳阳",
];

// ============================================================
// 菜系列表
// ============================================================

const CUISINES = [
  "粤菜", "川菜", "鲁菜", "本帮菜", "江浙菜", "湘菜", "闽菜",
  "日料", "寿司", "韩餐", "西餐", "法餐", "意大利菜", "东南亚菜",
  "火锅", "烧烤", "海鲜", "素食", "清真", "京菜", "烤鸭",
  "潮汕菜", "涮肉", "茶餐厅", "融合菜",
];

// ============================================================
// 中文数字映射
// ============================================================

const CN_NUM: Record<string, number> = {
  "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
  "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
  "十一": 11, "十二": 12, "十三": 13, "十四": 14, "十五": 15,
  "二十": 20, "三十": 30,
};

function cnToNum(text: string): number | undefined {
  if (CN_NUM[text] !== undefined) return CN_NUM[text];
  const n = parseInt(text, 10);
  return isNaN(n) ? undefined : n;
}

// ============================================================
// 槽位提取函数
// ============================================================

function extractCity(text: string): string | undefined {
  for (const city of CITIES) {
    if (text.includes(city)) return city;
  }
  return undefined;
}

function extractDate(text: string): string | undefined {
  const today = new Date();

  if (/今天|今晚|今天晚上/.test(text)) {
    return today.toISOString().split("T")[0];
  }
  if (/明天|明晚/.test(text)) {
    const d = new Date(today);
    d.setDate(d.getDate() + 1);
    return d.toISOString().split("T")[0];
  }
  if (/后天/.test(text)) {
    const d = new Date(today);
    d.setDate(d.getDate() + 2);
    return d.toISOString().split("T")[0];
  }
  if (/大后天/.test(text)) {
    const d = new Date(today);
    d.setDate(d.getDate() + 3);
    return d.toISOString().split("T")[0];
  }

  // X月X日/号
  const dateMatch = text.match(/(\d{1,2})月(\d{1,2})[日号]/);
  if (dateMatch) {
    const month = parseInt(dateMatch[1], 10);
    const day = parseInt(dateMatch[2], 10);
    return `${today.getFullYear()}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  }

  // 下周X
  const weekMatch = text.match(/下周([一二三四五六日天])/);
  if (weekMatch) {
    const dayMap: Record<string, number> = {
      "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "日": 0, "天": 0,
    };
    const targetDay = dayMap[weekMatch[1]] ?? 0;
    const d = new Date(today);
    const currentDay = d.getDay();
    const daysUntilNext = ((targetDay - currentDay + 7) % 7) || 7;
    d.setDate(d.getDate() + daysUntilNext);
    return d.toISOString().split("T")[0];
  }

  return undefined;
}

function extractTime(text: string): string | undefined {
  // HH:MM 格式
  const hmMatch = text.match(/(\d{1,2}):(\d{2})/);
  if (hmMatch) {
    return `${hmMatch[1].padStart(2, "0")}:${hmMatch[2]}`;
  }

  // X点X分 / X点半
  const cnTimeMatch = text.match(/([一二两三四五六七八九十\d]+)点([一二三四五六七八九十\d]*)(分|半)?/);
  if (cnTimeMatch) {
    const hourStr = cnTimeMatch[1];
    let hour = cnToNum(hourStr);
    if (hour === undefined) return undefined;

    let minute = 0;
    if (cnTimeMatch[3] === "半") {
      minute = 30;
    } else if (cnTimeMatch[2]) {
      const minStr = cnTimeMatch[2];
      minute = cnToNum(minStr) ?? 0;
    }

    // 晚餐默认+12h (如果小时 < 10 且上下文暗示晚餐)
    if (hour < 10 && /(吃|饭|请|宴|约|晚|晚上)/.test(text)) {
      hour += 12;
    }

    return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
  }

  return undefined;
}

function extractGuestCount(text: string): number | undefined {
  // 数字+位/个/人
  const numMatch = text.match(/(\d+)\s*[位个人]/);
  if (numMatch) return parseInt(numMatch[1], 10);

  // 中文数字+位/个/人
  const cnMatch = text.match(/([一二两三四五六七八九十]+)\s*[位个人]/);
  if (cnMatch) return cnToNum(cnMatch[1]);

  return undefined;
}

function extractBudget(text: string): { perPerson?: number; max?: number } | undefined {
  // 人均/每人 X
  const ppMatch = text.match(/(?:人均|每人)\s*(\d+)/);
  if (ppMatch) return { perPerson: parseInt(ppMatch[1], 10) };

  // X块/元 每人/每人的变体
  const ppMatch2 = text.match(/(\d+)\s*[块元]\s*(?:每[人位])/);
  if (ppMatch2) return { perPerson: parseInt(ppMatch2[1], 10) };

  // 总共/预算 X
  const totalMatch = text.match(/(?:总共|预算)\s*(\d+)/);
  if (totalMatch) return { max: parseInt(totalMatch[1], 10) };

  // X以内/以下
  const underMatch = text.match(/(\d+)\s*(?:以[内下]|左右)/);
  if (underMatch) return { max: parseInt(underMatch[1], 10) };

  return undefined;
}

function extractCuisine(text: string): string | undefined {
  for (const cuisine of CUISINES) {
    if (text.includes(cuisine)) return cuisine;
  }
  return undefined;
}

function extractPrivacy(text: string): PrivacyLevel | undefined {
  if (/(顶级.{0,2}私密|最高.{0,2}私密|VIP|最高级)/.test(text)) return "L4";
  if (/(包间|包房|独立|私密|雅间)/.test(text)) return "L3";
  if (/(半包|隔断|安静|安静点|清静)/.test(text)) return "L2";
  if (/(大厅|开放|随便|不在意)/.test(text)) return "L1";
  return undefined;
}

function extractScene(text: string): string | undefined {
  if (/(高规格|高端|顶级|豪华|隆重)/.test(text)) return "高规格接待";
  if (/(签约|签合同|重要合作)/.test(text)) return "签约仪式";
  if (/(答谢|感谢|庆功)/.test(text)) return "客户答谢";
  if (/(商务|洽谈|会面|见面|谈事)/.test(text)) return "商务洽谈";
  if (/(团队|团建|同事|部门|聚餐)/.test(text)) return "团队聚餐";
  return undefined;
}

function extractGuestProfile(text: string): string | undefined {
  const match = text.match(/(客户|老板|领导|上司|合作方|投资人|CTO|CEO|CFO|VP|总裁|董事).{0,4}/);
  return match ? match[0] : undefined;
}

function extractDietaryRestrictions(text: string): string[] | undefined {
  const patterns = /(不吃辣|不要辣|素食|清真|不吃海鲜|过敏|忌口|不吃香菜|不吃葱|不吃蒜|不吃牛肉|低脂)/g;
  const matches = text.match(patterns);
  return matches && matches.length > 0 ? matches : undefined;
}

// ============================================================
// 扩展槽位提取函数 (多业态)
// ============================================================

function extractTransportType(text: string): ExtendedNLUSlots["transportType"] {
  if (/(飞机|航班|机票|航线)/.test(text)) return "flight";
  if (/(高铁|动车|城际)/.test(text)) return "train";
  if (/(火车|列车|车次)/.test(text)) return "train";
  if (/(专车|包车|租车|用车|商务车)/.test(text)) return "private_car";
  return undefined;
}

function extractEntertainmentType(text: string): ExtendedNLUSlots["entertainmentType"] {
  if (/(洗浴|桑拿|汗蒸|泡汤|温泉|汤泉)/.test(text)) return "bath";
  if (/(按摩|足浴|足疗|推拿|spa|SPA)/.test(text)) return "massage";
  if (/(KTV|ktv|唱歌|欢唱|歌厅)/.test(text)) return "ktv";
  if (/(舞厅|跳舞|夜总会|夜店)/.test(text)) return "dance_hall";
  return undefined;
}

function extractDepartureArrival(text: string): { departureCity?: string; arrivalCity?: string } {
  const result: { departureCity?: string; arrivalCity?: string } = {};

  // "从X出发/离开" -> departureCity
  const fromMatch = text.match(/从([\u4e00-\u9fa5]{2,4})(?:出发|离开|起飞|始发)/);
  if (fromMatch) {
    for (const city of CITIES) {
      if (fromMatch[1].includes(city) || city.includes(fromMatch[1])) {
        result.departureCity = city;
        break;
      }
    }
  }

  // "去/到X" -> arrivalCity
  const toMatch = text.match(/(?:去|到|抵达|飞往?)([\u4e00-\u9fa5]{2,4})/);
  if (toMatch) {
    for (const city of CITIES) {
      if (toMatch[1].includes(city) || city.includes(toMatch[1])) {
        result.arrivalCity = city;
        break;
      }
    }
  }

  // 如果只找到一个城市且没有明确的出发/到达标记，默认作为到达城市
  if (!result.departureCity && !result.arrivalCity) {
    const singleCity = extractCity(text);
    if (singleCity) {
      result.arrivalCity = singleCity;
    }
  }

  return result;
}

function extractPickupInfo(text: string): { pickupLocation?: ExtendedNLUSlots["pickupLocation"]; routeNumber?: string } {
  const result: { pickupLocation?: ExtendedNLUSlots["pickupLocation"]; routeNumber?: string } = {};

  if (/(机场|飞机场|航站楼)/.test(text)) result.pickupLocation = "airport";
  else if (/(火车站|高铁站|车站|站台)/.test(text)) result.pickupLocation = "station";
  else if (/(酒店|宾馆|饭店|旅馆)/.test(text)) result.pickupLocation = "hotel";

  // 提取航班号/车次号
  const routeMatch = text.match(/([A-Z]{2}\d{3,4}|[GDZKTC]\d{1,4})/i);
  if (routeMatch) result.routeNumber = routeMatch[1].toUpperCase();

  return result;
}

function extractShoppingType(text: string): string | undefined {
  if (/(特产|土特产|伴手礼|纪念品)/.test(text)) return "souvenir";
  if (/(奢侈品|名牌|大牌|名品)/.test(text)) return "luxury";
  if (/(商场|购物中心|百货|万达|华润)/.test(text)) return "mall";
  if (/(商务礼品|送人|送礼)/.test(text)) return "business_gift";
  return undefined;
}

function extractMeetingContext(text: string): { meetingTime?: string; meetingLocation?: string } {
  const result: { meetingTime?: string; meetingLocation?: string } = {};

  if (/(开会|会议|会面|洽谈|签约|面试)/.test(text)) {
    // 提取会议时间
    const timeMatch = text.match(/([一二两三四五六七八九十\d]+)点([一二三四五六七八九十\d]*)(分|半)?/);
    if (timeMatch) {
      const time = extractTime(text);
      if (time) result.meetingTime = time;
    }

    // 提取会议地点
    const locMatch = text.match(/(?:在|于)([\u4e00-\u9fa5]{2,8})(?:开会|开会|会面|洽谈|签约)/);
    if (locMatch) result.meetingLocation = locMatch[1];
  }

  return result;
}

// ============================================================
// 主函数
// ============================================================

export function regexParse(userInput: string): NLUResult {
  // 意图识别
  let intent: ExtendedIntent = "chitchat";
  let confidence = 0.30;

  for (const pattern of INTENT_PATTERNS) {
    if (pattern.patterns.some((re) => re.test(userInput))) {
      intent = pattern.intent;
      confidence = pattern.confidence;
      break;
    }
  }

  // 槽位提取 (基础 + 扩展)
  const slots: ExtendedNLUSlots = {};
  const city = extractCity(userInput);
  if (city) slots.city = city;

  const date = extractDate(userInput);
  if (date) slots.date = date;

  const time = extractTime(userInput);
  if (time) slots.time = time;

  const guestCount = extractGuestCount(userInput);
  if (guestCount) slots.guestCount = guestCount;

  const budget = extractBudget(userInput);
  if (budget?.perPerson) slots.budgetPerPerson = budget.perPerson;
  if (budget?.max) slots.budgetMax = budget.max;

  const cuisine = extractCuisine(userInput);
  if (cuisine) slots.cuisine = cuisine;

  const privacy = extractPrivacy(userInput);
  if (privacy) slots.privacy = privacy;

  const scene = extractScene(userInput);
  if (scene) slots.scene = scene;

  const guestProfile = extractGuestProfile(userInput);
  if (guestProfile) slots.guestProfile = guestProfile;

  const dietary = extractDietaryRestrictions(userInput);
  if (dietary) slots.dietaryRestrictions = dietary;

  // 扩展槽位 (多业态)
  const transportType = extractTransportType(userInput);
  if (transportType) slots.transportType = transportType;

  const entertainmentType = extractEntertainmentType(userInput);
  if (entertainmentType) slots.entertainmentType = entertainmentType;

  const depArr = extractDepartureArrival(userInput);
  if (depArr.departureCity) slots.departureCity = depArr.departureCity;
  if (depArr.arrivalCity) slots.arrivalCity = depArr.arrivalCity;

  const pickupInfo = extractPickupInfo(userInput);
  if (pickupInfo.pickupLocation) slots.pickupLocation = pickupInfo.pickupLocation;
  if (pickupInfo.routeNumber) slots.routeNumber = pickupInfo.routeNumber;

  const shoppingType = extractShoppingType(userInput);
  if (shoppingType) slots.shoppingType = shoppingType;

  const meetingCtx = extractMeetingContext(userInput);
  if (meetingCtx.meetingTime) slots.meetingTime = meetingCtx.meetingTime;
  if (meetingCtx.meetingLocation) slots.meetingLocation = meetingCtx.meetingLocation;

  // 计算缺失槽位
  const missingSlots: string[] = [];
  if (intent === "dining_recommend") {
    if (!slots.city) missingSlots.push("city");
    if (!slots.guestCount) missingSlots.push("guestCount");
  } else if (intent === "entertainment_recommend") {
    if (!slots.city) missingSlots.push("city");
  } else if (intent === "flight_search" || intent === "train_search") {
    if (!slots.departureCity) missingSlots.push("departureCity");
    if (!slots.arrivalCity) missingSlots.push("arrivalCity");
    if (!slots.date) missingSlots.push("date");
  } else if (intent === "pickup_service") {
    if (!slots.pickupLocation) missingSlots.push("pickupLocation");
    if (!slots.date) missingSlots.push("date");
  } else if (intent === "shopping_recommend") {
    if (!slots.city) missingSlots.push("city");
  } else if (intent === "trip_plan") {
    if (!slots.city && !slots.arrivalCity) missingSlots.push("city");
    if (!slots.date) missingSlots.push("date");
  }

  return {
    intent,
    confidence,
    slots,
    method: "regex",
    missingSlots,
  };
}
