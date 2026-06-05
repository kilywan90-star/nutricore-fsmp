import { describe, it, before } from "node:test";
import assert from "node:assert/strict";

// ============================================================
// 名称归一化逻辑测试 (从cross-validator提取)
// ============================================================

function normalizeName(name: string): string {
  return name
    .trim()
    .replace(/\s+/g, "")
    .replace(/(餐厅|饭店|饭馆|馆子|酒楼|酒家|食府|餐厅|小馆)$/g, "");
}

describe("交叉验证 - 名称归一化", () => {
  it("去除尾部'餐厅'", () => {
    assert.equal(normalizeName("老吉士餐厅"), "老吉士");
  });

  it("去除尾部'酒家'", () => {
    assert.equal(normalizeName("老吉士酒家"), "老吉士");
  });

  it("去除尾部'酒楼'", () => {
    assert.equal(normalizeName("陶陶居酒楼"), "陶陶居");
  });

  it("去除尾部'饭店'", () => {
    assert.equal(normalizeName("和平饭店"), "和平");
  });

  it("去除尾部'食府'", () => {
    assert.equal(normalizeName("南京食府"), "南京");
  });

  it("无后缀则保持原样", () => {
    assert.equal(normalizeName("大董烤鸭店"), "大董烤鸭店");
  });

  it("去除空白字符", () => {
    assert.equal(normalizeName("老 吉士 餐厅"), "老吉士");
  });

  it("去除前后空格", () => {
    assert.equal(normalizeName("  逸龙阁  "), "逸龙阁");
  });

  it("相同餐厅不同写法归一化后一致", () => {
    assert.equal(
      normalizeName("老吉士酒家"),
      normalizeName("老吉士餐厅")
    );
  });
});

// ============================================================
// 评分公式验证
// ============================================================

describe("排序评分公式验证", () => {
  function calcScore(opts: {
    rating: number;
    verified: boolean;
    cuisineMatch: boolean;
    privacyMatch: boolean;
    sceneMatch: boolean;
    dbScore: number;
    memoryBonus: number;
  }): number {
    const base = opts.rating * 20;
    const verifiedMul = opts.verified ? 1.5 : 0.3;
    let fieldMatch = 1.0;
    if (opts.cuisineMatch) fieldMatch *= 1.1;
    if (opts.privacyMatch) fieldMatch *= 1.1;
    if (opts.sceneMatch) fieldMatch *= 1.15;
    const dbBonus = 1.0 + opts.dbScore / 100;
    return Math.round(base * verifiedMul * opts.memoryBonus * fieldMatch * dbBonus * 100) / 100;
  }

  it("已验证餐厅分数高于未验证", () => {
    const verified = calcScore({
      rating: 4.5, verified: true, cuisineMatch: false,
      privacyMatch: false, sceneMatch: false, dbScore: 0, memoryBonus: 1.0,
    });
    const unverified = calcScore({
      rating: 4.5, verified: false, cuisineMatch: false,
      privacyMatch: false, sceneMatch: false, dbScore: 0, memoryBonus: 1.0,
    });
    assert.ok(verified > unverified, `verified(${verified}) should > unverified(${unverified})`);
    assert.ok(verified / unverified > 4, "verified should be ~5x unverified (1.5/0.3)");
  });

  it("菜系匹配增加10%分数", () => {
    const match = calcScore({
      rating: 4.0, verified: true, cuisineMatch: true,
      privacyMatch: false, sceneMatch: false, dbScore: 0, memoryBonus: 1.0,
    });
    const noMatch = calcScore({
      rating: 4.0, verified: true, cuisineMatch: false,
      privacyMatch: false, sceneMatch: false, dbScore: 0, memoryBonus: 1.0,
    });
    const ratio = match / noMatch;
    assert.ok(Math.abs(ratio - 1.1) < 0.01, `cuisine match ratio should be 1.1, got ${ratio}`);
  });

  it("场景匹配增加15%分数", () => {
    const match = calcScore({
      rating: 4.0, verified: true, cuisineMatch: false,
      privacyMatch: false, sceneMatch: true, dbScore: 0, memoryBonus: 1.0,
    });
    const noMatch = calcScore({
      rating: 4.0, verified: true, cuisineMatch: false,
      privacyMatch: false, sceneMatch: false, dbScore: 0, memoryBonus: 1.0,
    });
    const ratio = match / noMatch;
    assert.ok(Math.abs(ratio - 1.15) < 0.01, `scene match ratio should be 1.15, got ${ratio}`);
  });

  it("记忆乘数正确叠加", () => {
    const withMemory = calcScore({
      rating: 4.0, verified: true, cuisineMatch: false,
      privacyMatch: false, sceneMatch: false, dbScore: 0, memoryBonus: 1.2,
    });
    const without = calcScore({
      rating: 4.0, verified: true, cuisineMatch: false,
      privacyMatch: false, sceneMatch: false, dbScore: 0, memoryBonus: 1.0,
    });
    const ratio = withMemory / without;
    assert.ok(Math.abs(ratio - 1.2) < 0.01, `memory ratio should be 1.2, got ${ratio}`);
  });

  it("未验证餐厅分数被大幅压低", () => {
    const score = calcScore({
      rating: 5.0, verified: false, cuisineMatch: true,
      privacyMatch: true, sceneMatch: true, dbScore: 50, memoryBonus: 1.0,
    });
    const baseline = calcScore({
      rating: 3.0, verified: true, cuisineMatch: false,
      privacyMatch: false, sceneMatch: false, dbScore: 0, memoryBonus: 1.0,
    });
    // 即使5星未验证 vs 3星已验证，未验证分数应更低
    assert.ok(score < baseline, `unverified 5-star(${score}) should < verified 3-star(${baseline})`);
  });
});

// ============================================================
// DB集成测试 (使用实际种子数据库)
// ============================================================

describe("交叉验证 - DB集成", () => {
  let crossValidate: typeof import("@/lib/matching/cross-validator").crossValidate;

  before(async () => {
    const mod = await import("@/lib/matching/cross-validator");
    crossValidate = mod.crossValidate;
  });

  it("精确名称匹配 → verified", async () => {
    const results = await crossValidate(
      [{ name: "老吉士酒家", reason: "经典本帮菜", fromDBList: false }],
      [],
      "上海"
    );
    assert.equal(results.length, 1);
    assert.equal(results[0].verified, true);
    assert.equal(results[0].source, "llm_verified");
  });

  it("归一化匹配: '老吉士' 匹配 '老吉士酒家'", async () => {
    const results = await crossValidate(
      [{ name: "老吉士", reason: "推荐", fromDBList: false }],
      [],
      "上海"
    );
    assert.equal(results.length, 1);
    assert.equal(results[0].verified, true);
  });

  it("不存在的餐厅 → unverified", async () => {
    const results = await crossValidate(
      [{ name: "完全不存在的餐厅ABC123", reason: "LLM幻觉", fromDBList: false }],
      [],
      "上海"
    );
    assert.equal(results.length, 1);
    assert.equal(results[0].verified, false);
    assert.equal(results[0].source, "llm_unverified");
    assert.equal(results[0].restaurant.rating, 3.0);
  });

  it("与DB候选精确匹配 → verified + llm_verified", async () => {
    const dbCandidates = [{
      restaurant: {
        id: 999, name: "测试餐厅", city: "上海", district: "浦东",
        address: "测试路1号", latitude: 31.2, longitude: 121.5,
        cuisineType: "粤菜", cuisineTags: [], priceRangeMin: 100,
        priceRangeMax: 200, privacyLevel: "L3" as const,
        privateRoomMin: 4, privateRoomMax: 10, privateRoomCount: 2,
        rating: 4.5, sceneTags: [], businessTopics: [],
        photoTips: null, signatureDishes: [], contactPhone: null,
        openingHours: null, reservationNote: null,
      },
      matchScore: 80,
      matchedFields: ["cuisine"],
    }];
    const results = await crossValidate(
      [{ name: "测试餐厅", reason: "粤菜推荐", fromDBList: true }],
      dbCandidates,
      "上海"
    );
    assert.equal(results[0].verified, true);
    assert.equal(results[0].restaurant.id, 999);
  });
});
