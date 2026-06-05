import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { regexParse } from "@/lib/nlu/regex-fallback";

// ============================================================
// 意图识别测试 (5种意图, 20+条用例)
// ============================================================

describe("NLU regex - 意图识别", () => {
  // dining_recommend
  it("推荐餐厅 → dining_recommend", () => {
    const r = regexParse("帮我推荐一家餐厅");
    assert.equal(r.intent, "dining_recommend");
    assert.equal(r.confidence, 0.7);
  });

  it("找个地方请客 → dining_recommend", () => {
    const r = regexParse("帮我找个上海请客户吃饭的地方，4个人，要有包间");
    assert.equal(r.intent, "dining_recommend");
  });

  it("安排吃饭 → dining_recommend", () => {
    const r = regexParse("帮我安排一个吃饭的地方");
    assert.equal(r.intent, "dining_recommend");
  });

  it("请客户吃饭 → dining_recommend", () => {
    const r = regexParse("明天请客户吃饭，有推荐吗");
    assert.equal(r.intent, "dining_recommend");
  });

  it("选馆子 → dining_recommend", () => {
    const r = regexParse("帮我选个馆子");
    assert.equal(r.intent, "dining_recommend");
  });

  it("哪吃饭 → dining_recommend", () => {
    const r = regexParse("去哪吃饭好");
    assert.equal(r.intent, "dining_recommend");
  });

  // booking
  it("预订 → booking", () => {
    const r = regexParse("帮我预订");
    assert.equal(r.intent, "booking");
  });

  it("帮我订位 → booking", () => {
    const r = regexParse("帮我订位");
    assert.equal(r.intent, "booking");
  });

  it("预约包间 → booking", () => {
    const r = regexParse("帮我预约一个包间");
    assert.equal(r.intent, "booking");
  });

  // query_restaurant
  it("查看餐厅 → query_restaurant", () => {
    const r = regexParse("查一下这家餐厅");
    assert.equal(r.intent, "query_restaurant");
  });

  it("这家怎么样 → query_restaurant", () => {
    const r = regexParse("这家怎么样");
    assert.equal(r.intent, "query_restaurant");
  });

  // modify_plan
  it("换一个 → modify_plan", () => {
    const r = regexParse("换一个");
    assert.equal(r.intent, "modify_plan");
  });

  it("重新推荐 → modify_plan", () => {
    const r = regexParse("重新推荐");
    assert.equal(r.intent, "modify_plan");
  });

  it("便宜点 → modify_plan", () => {
    const r = regexParse("便宜点");
    assert.equal(r.intent, "modify_plan");
  });

  it("取消 → modify_plan", () => {
    const r = regexParse("取消");
    assert.equal(r.intent, "modify_plan");
  });

  // chitchat
  it("你好 → chitchat", () => {
    const r = regexParse("你好");
    assert.equal(r.intent, "chitchat");
  });

  it("谢谢 → chitchat", () => {
    const r = regexParse("谢谢");
    assert.equal(r.intent, "chitchat");
  });

  it("hi → chitchat", () => {
    const r = regexParse("hi");
    assert.equal(r.intent, "chitchat");
  });

  // 空输入
  it("空字符串 → chitchat (default)", () => {
    const r = regexParse("");
    assert.equal(r.intent, "chitchat");
    assert.equal(r.confidence, 0.3);
  });

  // method
  it("method始终为regex", () => {
    const r = regexParse("帮我找个餐厅");
    assert.equal(r.method, "regex");
  });
});

// ============================================================
// 槽位提取测试
// ============================================================

describe("NLU regex - 城市提取", () => {
  it("提取上海", () => {
    const r = regexParse("帮我找个上海的餐厅");
    assert.equal(r.slots.city, "上海");
  });

  it("提取北京", () => {
    const r = regexParse("北京有没有好的请客地方");
    assert.equal(r.slots.city, "北京");
  });

  it("提取深圳", () => {
    const r = regexParse("深圳粤菜推荐");
    assert.equal(r.slots.city, "深圳");
  });

  it("无城市时为undefined", () => {
    const r = regexParse("帮我找个餐厅");
    assert.equal(r.slots.city, undefined);
  });
});

describe("NLU regex - 人数提取", () => {
  it("阿拉伯数字: 4个人", () => {
    const r = regexParse("4个人吃饭");
    assert.equal(r.slots.guestCount, 4);
  });

  it("中文数字: 三位", () => {
    const r = regexParse("三位用餐");
    assert.equal(r.slots.guestCount, 3);
  });

  it("两位", () => {
    const r = regexParse("两位");
    assert.equal(r.slots.guestCount, 2);
  });
});

describe("NLU regex - 日期提取", () => {
  it("今天", () => {
    const r = regexParse("今天吃饭");
    assert.ok(r.slots.date);
    assert.match(r.slots.date!, /^\d{4}-\d{2}-\d{2}$/);
  });

  it("明天", () => {
    const r = regexParse("明天请客");
    assert.ok(r.slots.date);
  });

  it("X月X日", () => {
    const r = regexParse("6月15号吃饭");
    assert.ok(r.slots.date);
    assert.ok(r.slots.date!.includes("-06-15"));
  });
});

describe("NLU regex - 时间提取", () => {
  it("HH:MM格式", () => {
    const r = regexParse("晚上18:30吃饭");
    assert.equal(r.slots.time, "18:30");
  });

  it("中文时间: 七点半", () => {
    const r = regexParse("晚上七点半吃饭");
    assert.equal(r.slots.time, "19:30");
  });
});

describe("NLU regex - 预算提取", () => {
  it("人均500", () => {
    const r = regexParse("人均500");
    assert.equal(r.slots.budgetPerPerson, 500);
  });

  it("预算2000", () => {
    const r = regexParse("预算2000");
    assert.equal(r.slots.budgetMax, 2000);
  });

  it("500以内", () => {
    const r = regexParse("500以内");
    assert.equal(r.slots.budgetMax, 500);
  });
});

describe("NLU regex - 菜系提取", () => {
  it("粤菜", () => {
    const r = regexParse("想吃粤菜");
    assert.equal(r.slots.cuisine, "粤菜");
  });

  it("日料", () => {
    const r = regexParse("有日料推荐吗");
    assert.equal(r.slots.cuisine, "日料");
  });

  it("火锅", () => {
    const r = regexParse("吃火锅");
    assert.equal(r.slots.cuisine, "火锅");
  });
});

describe("NLU regex - 私密性提取", () => {
  it("包间 → L3", () => {
    const r = regexParse("要有包间");
    assert.equal(r.slots.privacy, "L3");
  });

  it("VIP → L4", () => {
    const r = regexParse("要VIP级别的");
    assert.equal(r.slots.privacy, "L4");
  });

  it("半包 → L2", () => {
    const r = regexParse("半包就行");
    assert.equal(r.slots.privacy, "L2");
  });

  it("大厅 → L1", () => {
    const r = regexParse("大厅就行");
    assert.equal(r.slots.privacy, "L1");
  });
});

describe("NLU regex - 场景提取", () => {
  it("高规格 → 高规格接待", () => {
    const r = regexParse("高规格接待");
    assert.equal(r.slots.scene, "高规格接待");
  });

  it("团建 → 团队聚餐", () => {
    const r = regexParse("团队聚餐");
    assert.equal(r.slots.scene, "团队聚餐");
  });

  it("商务 → 商务洽谈", () => {
    const r = regexParse("商务洽谈用的");
    assert.equal(r.slots.scene, "商务洽谈");
  });
});

describe("NLU regex - 饮食限制提取", () => {
  it("不吃辣", () => {
    const r = regexParse("不吃辣的");
    assert.ok(r.slots.dietaryRestrictions);
    assert.ok(r.slots.dietaryRestrictions!.includes("不吃辣"));
  });

  it("素食", () => {
    const r = regexParse("要素食的");
    assert.ok(r.slots.dietaryRestrictions);
    assert.ok(r.slots.dietaryRestrictions!.includes("素食"));
  });

  it("多项限制", () => {
    const r = regexParse("不吃辣不吃香菜");
    assert.ok(r.slots.dietaryRestrictions);
    assert.ok(r.slots.dietaryRestrictions!.length >= 2);
  });
});

// ============================================================
// 缺失槽位测试
// ============================================================

describe("NLU regex - 缺失槽位计算", () => {
  it("dining_recommend缺city和guestCount", () => {
    const r = regexParse("帮我推荐个餐厅");
    assert.ok(r.missingSlots.includes("city"));
    assert.ok(r.missingSlots.includes("guestCount"));
  });

  it("dining_recommend有city缺guestCount", () => {
    const r = regexParse("上海推荐个餐厅");
    assert.ok(!r.missingSlots.includes("city"));
    assert.ok(r.missingSlots.includes("guestCount"));
  });

  it("dining_recommend完整则无缺失", () => {
    const r = regexParse("上海2个人吃饭推荐");
    assert.equal(r.missingSlots.length, 0);
  });
});

// ============================================================
// 综合场景测试
// ============================================================

describe("NLU regex - 综合场景", () => {
  it("完整商务宴请请求", () => {
    const r = regexParse("帮我找个上海请客户吃饭的地方，4个人，要有包间，人均500，粤菜");
    assert.equal(r.intent, "dining_recommend");
    assert.equal(r.slots.city, "上海");
    assert.equal(r.slots.guestCount, 4);
    assert.equal(r.slots.privacy, "L3");
    assert.equal(r.slots.budgetPerPerson, 500);
    assert.equal(r.slots.cuisine, "粤菜");
  });

  it("简单推荐请求", () => {
    const r = regexParse("帮我推荐北京烤鸭餐厅，2人");
    assert.equal(r.intent, "dining_recommend");
    assert.equal(r.slots.city, "北京");
    assert.equal(r.slots.cuisine, "烤鸭");
    assert.equal(r.slots.guestCount, 2);
  });
});
