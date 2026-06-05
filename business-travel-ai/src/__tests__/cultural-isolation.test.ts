import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

// ============================================================
// P0-3 文化故事隔离验证
// 仅 cultural-repository.ts 可访问 culturalStories 表
// ============================================================

const SRC_DIR = resolve("src");

function getAllTsFiles(dir: string, files: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    const stat = statSync(full);
    if (stat.isDirectory()) {
      // 跳过测试目录和node_modules
      if (entry === "__tests__" || entry === "node_modules") continue;
      getAllTsFiles(full, files);
    } else if (/\.(ts|tsx)$/.test(entry)) {
      files.push(full);
    }
  }
  return files;
}

describe("文化故事隔离 - 静态分析", () => {
  const allFiles = getAllTsFiles(SRC_DIR);
  // 允许访问 culturalStories 的文件 (基础设施+隔离层)
  const ALLOWED_SUFFIXES = [
    join("cultural", "cultural-repository.ts"),  // P0-3 隔离层入口
    join("db", "helpers.ts"),                      // dbReset 清空所有表
    join("db", "seed.ts"),                         // 种子数据导入
  ];

  // 禁止直接导入 culturalStories schema
  const FORBIDDEN_IMPORTS = [
    /import\s+.*culturalStories.*from\s+["'].*schema["']/,
    /import\s+.*\{[^}]*culturalStories[^}]*\}.*from/,
  ];

  // 禁止直接查询 culturalStories 表 (drizzle操作)
  const FORBIDDEN_QUERIES = [
    /\.from\(culturalStories\)/,
    /culturalStories\.\$inferSelect/,
    /culturalStories\.\$inferInsert/,
  ];

  it("源码中存在.ts/.tsx文件", () => {
    assert.ok(allFiles.length > 0, "Should find source files");
  });

  it("cultural-repository.ts 存在", () => {
    const exists = allFiles.some((f) =>
      f.endsWith(join("cultural", "cultural-repository.ts"))
    );
    assert.ok(exists, "cultural-repository.ts should exist");
  });

  for (const filePath of allFiles) {
    const relativePath = filePath.replace(SRC_DIR + "\\", "src/").replace(/\\/g, "/");
    const isAllowed = ALLOWED_SUFFIXES.some((suffix) => filePath.endsWith(suffix));

    if (isAllowed) continue;

    const content = readFileSync(filePath, "utf-8");

    for (const pattern of FORBIDDEN_IMPORTS) {
      it(`${relativePath} 不导入 culturalStories schema`, () => {
        assert.ok(
          !pattern.test(content),
          `${relativePath} must not import culturalStories from schema. ` +
            `Only cultural-repository.ts is allowed to access culturalStories.`
        );
      });
    }

    for (const pattern of FORBIDDEN_QUERIES) {
      it(`${relativePath} 不直接查询 culturalStories 表`, () => {
        assert.ok(
          !pattern.test(content),
          `${relativePath} must not query culturalStories table directly. ` +
            `Use attachCulturalStories() from cultural-repository.ts instead.`
        );
      });
    }
  }
});

// ============================================================
// 文化故事功能测试 (使用实际DB)
// ============================================================

describe("文化故事 - 功能测试", () => {
  let attachCulturalStories: typeof import("@/lib/cultural/cultural-repository").attachCulturalStories;
  let getStoriesByRestaurantId: typeof import("@/lib/cultural/cultural-repository").getStoriesByRestaurantId;

  it("动态导入cultural-repository", async () => {
    const mod = await import("@/lib/cultural/cultural-repository");
    attachCulturalStories = mod.attachCulturalStories;
    getStoriesByRestaurantId = mod.getStoriesByRestaurantId;
    assert.ok(typeof attachCulturalStories === "function");
    assert.ok(typeof getStoriesByRestaurantId === "function");
  });

  it("已验证餐厅附加文化故事", async () => {
    const mod = await import("@/lib/cultural/cultural-repository");
    const input = [{
      restaurant: {
        id: 1, name: "老吉士酒家", city: "上海", district: "徐汇区",
        address: "天平路41号", latitude: 31.1955, longitude: 121.4385,
        cuisineType: "本帮菜", cuisineTags: ["浓油赤酱"], priceRangeMin: 800,
        priceRangeMax: 1500, privacyLevel: "L4" as const,
        privateRoomMin: 6, privateRoomMax: 12, privateRoomCount: 5,
        rating: 4.8, sceneTags: ["高规格接待"], businessTopics: [],
        photoTips: null, signatureDishes: ["红烧肉"],
        contactPhone: null, openingHours: null, reservationNote: null,
      },
      culturalStories: [],
      verified: true,
      source: "database" as const,
      score: 100,
    }];

    const result = await mod.attachCulturalStories(input);
    assert.equal(result.length, 1);
    assert.ok(result[0].culturalStories.length > 0, "Should have cultural stories");
    assert.ok(result[0].culturalStories.length <= 2, "Max 2 stories per restaurant");
  });

  it("未验证餐厅不附加文化故事", async () => {
    const mod = await import("@/lib/cultural/cultural-repository");
    const input = [{
      restaurant: {
        id: -1, name: "虚构餐厅", city: "上海", district: null,
        address: "未知", latitude: null, longitude: null,
        cuisineType: "未知", cuisineTags: [], priceRangeMin: null,
        priceRangeMax: null, privacyLevel: "L2" as const,
        privateRoomMin: null, privateRoomMax: null, privateRoomCount: null,
        rating: 3.0, sceneTags: [], businessTopics: [],
        photoTips: null, signatureDishes: [],
        contactPhone: null, openingHours: null, reservationNote: null,
      },
      culturalStories: [],
      verified: false,
      source: "llm_unverified" as const,
      score: 50,
    }];

    const result = await mod.attachCulturalStories(input);
    assert.equal(result.length, 1);
    assert.equal(result[0].culturalStories.length, 0, "Unverified should have no stories");
  });

  it("故事类型在允许范围内", async () => {
    const mod = await import("@/lib/cultural/cultural-repository");
    const stories = await mod.getStoriesByRestaurantId(1);
    const validTypes = ["历史", "文化", "菜品", "建筑"];
    for (const story of stories) {
      assert.ok(
        validTypes.includes(story.storyType),
        `Story type "${story.storyType}" should be one of: ${validTypes.join(", ")}`
      );
    }
  });

  it("每条故事包含必要字段", async () => {
    const mod = await import("@/lib/cultural/cultural-repository");
    const stories = await mod.getStoriesByRestaurantId(1);
    for (const story of stories) {
      assert.ok(story.id > 0, "Story should have valid id");
      assert.ok(story.restaurantId > 0, "Story should have restaurantId");
      assert.ok(story.title.length > 0, "Story should have title");
      assert.ok(story.content.length > 0, "Story should have content");
      assert.ok(Array.isArray(story.talkingPoints), "talkingPoints should be array");
      assert.ok(Array.isArray(story.relatedTopics), "relatedTopics should be array");
    }
  });
});
