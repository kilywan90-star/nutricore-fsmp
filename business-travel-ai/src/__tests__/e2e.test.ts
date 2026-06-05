import { describe, it } from "node:test";
import assert from "node:assert/strict";

const BASE_URL = "http://localhost:3000";

async function chat(message: string, sessionId = "e2e-test") {
  const res = await fetch(`${BASE_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, sessionId }),
  });
  assert.equal(res.status, 200, `Expected 200, got ${res.status}`);
  return res.json();
}

// ============================================================
// 端到端黄金场景测试
// ============================================================

describe("E2E - 健康检查", () => {
  it("GET /api/health 返回 ok", async () => {
    const res = await fetch(`${BASE_URL}/api/health`);
    assert.equal(res.status, 200);
    const data = await res.json();
    assert.equal(data.status, "ok");
    assert.equal(data.db, "ok");
  });
});

describe("E2E - 餐厅列表", () => {
  it("GET /api/restaurants 返回种子数据", async () => {
    const res = await fetch(`${BASE_URL}/api/restaurants?city=上海&pageSize=5`);
    assert.equal(res.status, 200);
    const data = await res.json();
    assert.ok(data.data.length > 0, "Should return restaurants");
    assert.ok(data.total > 0, "Total should be > 0");
    assert.equal(data.data[0].city, "上海");
  });

  it("按菜系筛选", async () => {
    const res = await fetch(`${BASE_URL}/api/restaurants?city=上海&cuisine=粤菜&pageSize=10`);
    assert.equal(res.status, 200);
    const data = await res.json();
    for (const item of data.data) {
      assert.equal(item.cuisineType, "粤菜");
    }
  });
});

describe("E2E - 场景1: 闲聊问候", () => {
  it("你好 → 返回欢迎语", async () => {
    const data = await chat("你好");
    assert.equal(data.nluDebug.intent, "chitchat");
    assert.ok(data.reply.length > 0, "Should have reply");
    assert.equal(data.recommendations.length, 0);
  });
});

describe("E2E - 场景2: 完整推荐请求 (上海)", () => {
  it("上海4人包间宴请 → 返回3家推荐", async () => {
    const data = await chat("帮我找个上海请客户吃饭的地方，4个人，要有包间");
    assert.equal(data.nluDebug.intent, "dining_recommend");
    assert.equal(data.nluDebug.slots.city, "上海");
    assert.equal(data.nluDebug.slots.guestCount, 4);
    assert.ok(data.recommendations.length > 0, "Should have recommendations");
    assert.ok(data.recommendations.length <= 3, "Max 3 recommendations");

    for (const rec of data.recommendations) {
      assert.ok(rec.restaurant.name, "Restaurant should have name");
      assert.ok(rec.verified, "Restaurant should be verified");
      assert.equal(rec.restaurant.city, "上海");
      assert.ok(Array.isArray(rec.culturalStories), "Should have stories array");
    }
  });
});

describe("E2E - 场景3: 北京烤鸭推荐", () => {
  it("北京烤鸭2人 → 返回推荐", async () => {
    const data = await chat("帮我找个北京吃烤鸭的地方，2个人");
    assert.equal(data.nluDebug.intent, "dining_recommend");
    assert.equal(data.nluDebug.slots.city, "北京");
    assert.equal(data.nluDebug.slots.cuisine, "烤鸭");
    assert.ok(data.recommendations.length > 0);
  });
});

describe("E2E - 场景4: 预订意图", () => {
  it("预订 → 追问城市人数", async () => {
    const data = await chat("帮我订个位子");
    assert.equal(data.nluDebug.intent, "booking");
    assert.ok(data.reply.includes("城市") || data.reply.includes("几位"),
      "Should ask for missing info");
  });
});

describe("E2E - 场景5: 修改计划", () => {
  it("换一个 → 返回修改提示", async () => {
    const data = await chat("换一个");
    assert.equal(data.nluDebug.intent, "modify_plan");
    assert.ok(data.reply.length > 0);
  });
});

describe("E2E - 场景6: 空消息拒绝", () => {
  it("空消息 → 400", async () => {
    const res = await fetch(`${BASE_URL}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: "", sessionId: "e2e-test" }),
    });
    assert.equal(res.status, 400);
  });
});

describe("E2E - 回复结构验证", () => {
  it("推荐回复包含所有必要字段", async () => {
    const data = await chat("帮我找个深圳粤菜推荐，4个人");
    assert.ok("reply" in data, "Should have reply");
    assert.ok("recommendations" in data, "Should have recommendations");
    assert.ok("followupQuestion" in data, "Should have followupQuestion");
    assert.ok("nluDebug" in data, "Should have nluDebug");
    assert.ok("intent" in data.nluDebug, "nluDebug should have intent");
    assert.ok("slots" in data.nluDebug, "nluDebug should have slots");
    assert.ok("method" in data.nluDebug, "nluDebug should have method");
    assert.ok("confidence" in data.nluDebug, "nluDebug should have confidence");
  });
});
