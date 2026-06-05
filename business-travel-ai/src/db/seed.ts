import fs from "fs";
import path from "path";
import { db } from "./index";
import { restaurants, culturalStories } from "./schema";

const SEED_DIR = path.join(__dirname, "../data/seed");
const CITIES = [
  "shanghai", "beijing", "shenzhen",
  "chengdu", "deyang", "mianyang", "guangyuan", "bazhong", "dazhou", "guangan",
  "nanchong", "suining", "neijiang", "zigong", "luzhou", "yibin", "leshan",
  "meishan", "yaan", "ziyang", "panzhihua", "aba", "ganzi", "liangshan",
  "chongqing",
  "kunming", "qujing", "yuxi", "baoshan", "zhaotong", "lijiang", "puer",
  "lincang", "chuxiong", "honghe", "wenshan", "xishuangbanna", "dali",
  "dehong", "nujiang", "diqing",
  "changsha", "zhuzhou", "xiangtan", "hengyang", "shaoyang", "yueyang",
  "changde", "zhangjiajie", "yiyang", "chenzhou", "yongzhou", "huaihua",
  "loudi", "xiangxi",
] as const;

interface SeedStory {
  storyType: string;
  title: string;
  content: string;
  talkingPoints: string[];
  relatedTopics: string[];
}

interface SeedRestaurant {
  name: string;
  district: string;
  address: string;
  latitude: number;
  longitude: number;
  cuisineType: string;
  cuisineTags: string[];
  priceRangeMin: number;
  priceRangeMax: number;
  privacyLevel: string;
  privateRoomMin: number | null;
  privateRoomMax: number | null;
  privateRoomCount: number | null;
  rating: number;
  sceneTags: string[];
  businessTopics: string[];
  signatureDishes: string[];
  openingHours: string;
  contactPhone: string;
  reservationNote: string;
  stories: SeedStory[];
}

interface SeedFile {
  city: string;
  restaurants: SeedRestaurant[];
}

function loadCityData(cityKey: string): SeedFile {
  const filePath = path.join(SEED_DIR, `${cityKey}.json`);
  const raw = fs.readFileSync(filePath, "utf-8");
  return JSON.parse(raw);
}

async function clearDatabase(): Promise<void> {
  // 按FK逆序清空
  await db.delete(culturalStories);
  await db.delete(restaurants);
  console.log("数据库已清空");
}

async function seedCity(data: SeedFile): Promise<{ restaurantCount: number; storyCount: number }> {
  let restaurantCount = 0;
  let storyCount = 0;

  for (const r of data.restaurants) {
    // 插入餐厅
    const [inserted] = await db
      .insert(restaurants)
      .values({
        name: r.name,
        city: data.city,
        district: r.district,
        address: r.address,
        latitude: r.latitude,
        longitude: r.longitude,
        cuisineType: r.cuisineType,
        cuisineTags: r.cuisineTags,
        priceRangeMin: r.priceRangeMin,
        priceRangeMax: r.priceRangeMax,
        privacyLevel: r.privacyLevel,
        privateRoomMin: r.privateRoomMin,
        privateRoomMax: r.privateRoomMax,
        privateRoomCount: r.privateRoomCount,
        rating: r.rating,
        sceneTags: r.sceneTags,
        businessTopics: r.businessTopics,
        signatureDishes: r.signatureDishes,
        contactPhone: r.contactPhone,
        openingHours: r.openingHours,
        reservationNote: r.reservationNote,
        dataSource: "ai_seed",
      })
      .returning({ id: restaurants.id });

    restaurantCount++;

    // 插入文化故事
    for (const story of r.stories) {
      await db.insert(culturalStories).values({
        restaurantId: inserted.id,
        storyType: story.storyType,
        title: story.title,
        content: story.content,
        talkingPoints: story.talkingPoints,
        relatedTopics: story.relatedTopics,
      });
      storyCount++;
    }

    if (restaurantCount % 5 === 0) {
      console.log(`  ${data.city}: ${restaurantCount}/${data.restaurants.length} 家餐厅已导入`);
    }
  }

  return { restaurantCount, storyCount };
}

async function main() {
  console.log("=== 种子数据导入 ===\n");

  // 加载所有城市数据
  const allCities: SeedFile[] = [];
  for (const cityKey of CITIES) {
    console.log(`加载 ${cityKey}.json...`);
    allCities.push(loadCityData(cityKey));
  }

  // 清空数据库
  await clearDatabase();

  // 逐城市导入
  let totalRestaurants = 0;
  let totalStories = 0;

  for (const data of allCities) {
    console.log(`\n导入 ${data.city} (${data.restaurants.length} 家餐厅)...`);
    const result = await seedCity(data);
    totalRestaurants += result.restaurantCount;
    totalStories += result.storyCount;
  }

  console.log(`\n=== 导入完成 ===`);
  console.log(`餐厅总数: ${totalRestaurants}`);
  console.log(`故事总数: ${totalStories}`);
}

main().catch((err) => {
  console.error("种子数据导入失败:", err);
  process.exit(1);
});
