import fs from "fs";
import path from "path";

const SEED_DIR = path.join(__dirname);
const CITIES = [
  // 原有一线
  "shanghai", "beijing", "shenzhen",
  // 四川 21市州
  "chengdu", "deyang", "mianyang", "guangyuan", "bazhong", "dazhou", "guangan",
  "nanchong", "suining", "neijiang", "zigong", "luzhou", "yibin", "leshan",
  "meishan", "yaan", "ziyang", "panzhihua", "aba", "ganzi", "liangshan",
  // 重庆
  "chongqing",
  // 云南 16市州
  "kunming", "qujing", "yuxi", "baoshan", "zhaotong", "lijiang", "puer",
  "lincang", "chuxiong", "honghe", "wenshan", "xishuangbanna", "dali",
  "dehong", "nujiang", "diqing",
  // 湖南 14市州
  "changsha", "zhuzhou", "xiangtan", "hengyang", "shaoyang", "yueyang",
  "changde", "zhangjiajie", "yiyang", "chenzhou", "yongzhou", "huaihua",
  "loudi", "xiangxi",
] as const;

const CITY_NAMES: Record<string, string> = {
  shanghai: "上海", beijing: "北京", shenzhen: "深圳",
  // 四川
  chengdu: "成都", deyang: "德阳", mianyang: "绵阳", guangyuan: "广元",
  bazhong: "巴中", dazhou: "达州", guangan: "广安", nanchong: "南充",
  suining: "遂宁", neijiang: "内江", zigong: "自贡", luzhou: "泸州",
  yibin: "宜宾", leshan: "乐山", meishan: "眉山", yaan: "雅安",
  ziyang: "资阳", panzhihua: "攀枝花", aba: "阿坝", ganzi: "甘孜", liangshan: "凉山",
  // 重庆
  chongqing: "重庆",
  // 云南
  kunming: "昆明", qujing: "曲靖", yuxi: "玉溪", baoshan: "保山",
  zhaotong: "昭通", lijiang: "丽江", puer: "普洱", lincang: "临沧",
  chuxiong: "楚雄", honghe: "红河", wenshan: "文山",
  xishuangbanna: "西双版纳", dali: "大理",
  dehong: "德宏", nujiang: "怒江", diqing: "迪庆",
  // 湖南
  changsha: "长沙", zhuzhou: "株洲", xiangtan: "湘潭", hengyang: "衡阳",
  shaoyang: "邵阳", yueyang: "岳阳", changde: "常德", zhangjiajie: "张家界",
  yiyang: "益阳", chenzhou: "郴州", yongzhou: "永州", huaihua: "怀化",
  loudi: "娄底", xiangxi: "湘西",
};

const COORD_BOUNDS: Record<string, { latMin: number; latMax: number; lonMin: number; lonMax: number }> = {
  shanghai: { latMin: 30.7, latMax: 31.6, lonMin: 120.9, lonMax: 122.0 },
  beijing: { latMin: 39.4, latMax: 40.4, lonMin: 115.7, lonMax: 117.2 },
  shenzhen: { latMin: 22.4, latMax: 22.7, lonMin: 113.7, lonMax: 114.5 },
  // 四川
  chengdu: { latMin: 30.2, latMax: 31.0, lonMin: 103.0, lonMax: 104.9 },
  deyang: { latMin: 30.5, latMax: 31.5, lonMin: 103.8, lonMax: 105.2 },
  mianyang: { latMin: 30.7, latMax: 33.0, lonMin: 103.7, lonMax: 106.0 },
  guangyuan: { latMin: 31.5, latMax: 33.0, lonMin: 104.6, lonMax: 106.8 },
  bazhong: { latMin: 31.2, latMax: 32.8, lonMin: 106.2, lonMax: 107.8 },
  dazhou: { latMin: 30.5, latMax: 32.2, lonMin: 106.3, lonMax: 108.5 },
  guangan: { latMin: 30.0, latMax: 30.8, lonMin: 105.9, lonMax: 107.0 },
  nanchong: { latMin: 30.5, latMax: 31.8, lonMin: 105.4, lonMax: 106.8 },
  suining: { latMin: 30.1, latMax: 31.0, lonMin: 105.0, lonMax: 106.0 },
  neijiang: { latMin: 29.2, latMax: 30.0, lonMin: 104.1, lonMax: 105.5 },
  zigong: { latMin: 28.9, latMax: 29.6, lonMin: 104.0, lonMax: 105.3 },
  luzhou: { latMin: 27.6, latMax: 29.3, lonMin: 105.0, lonMax: 106.6 },
  yibin: { latMin: 27.8, latMax: 29.2, lonMin: 103.6, lonMax: 105.3 },
  leshan: { latMin: 28.4, latMax: 29.7, lonMin: 102.9, lonMax: 104.2 },
  meishan: { latMin: 29.5, latMax: 30.3, lonMin: 102.8, lonMax: 104.3 },
  yaan: { latMin: 28.9, latMax: 30.7, lonMin: 101.9, lonMax: 103.2 },
  ziyang: { latMin: 29.7, latMax: 30.5, lonMin: 104.2, lonMax: 105.6 },
  panzhihua: { latMin: 26.0, latMax: 27.5, lonMin: 101.0, lonMax: 102.3 },
  aba: { latMin: 30.5, latMax: 34.2, lonMin: 100.5, lonMax: 104.5 },
  ganzi: { latMin: 27.5, latMax: 34.0, lonMin: 97.5, lonMax: 102.5 },
  liangshan: { latMin: 26.0, latMax: 29.5, lonMin: 100.2, lonMax: 103.8 },
  // 重庆
  chongqing: { latMin: 28.1, latMax: 31.5, lonMin: 105.3, lonMax: 109.5 },
  // 云南
  kunming: { latMin: 24.2, latMax: 26.0, lonMin: 102.0, lonMax: 103.5 },
  qujing: { latMin: 24.3, latMax: 27.5, lonMin: 103.0, lonMax: 105.0 },
  yuxi: { latMin: 23.2, latMax: 24.8, lonMin: 101.2, lonMax: 103.2 },
  baoshan: { latMin: 24.0, latMax: 25.7, lonMin: 98.0, lonMax: 100.0 },
  zhaotong: { latMin: 26.5, latMax: 28.5, lonMin: 103.0, lonMax: 105.5 },
  lijiang: { latMin: 26.3, latMax: 27.8, lonMin: 99.5, lonMax: 101.5 },
  puer: { latMin: 22.0, latMax: 24.5, lonMin: 99.5, lonMax: 102.0 },
  lincang: { latMin: 23.0, latMax: 25.0, lonMin: 98.5, lonMax: 100.5 },
  chuxiong: { latMin: 24.5, latMax: 26.5, lonMin: 100.5, lonMax: 102.5 },
  honghe: { latMin: 22.5, latMax: 24.6, lonMin: 101.5, lonMax: 104.5 },
  wenshan: { latMin: 22.5, latMax: 24.5, lonMin: 103.5, lonMax: 106.2 },
  xishuangbanna: { latMin: 21.1, latMax: 22.7, lonMin: 99.9, lonMax: 101.7 },
  dali: { latMin: 24.5, latMax: 26.7, lonMin: 99.0, lonMax: 101.0 },
  dehong: { latMin: 23.8, latMax: 25.3, lonMin: 97.5, lonMax: 98.8 },
  nujiang: { latMin: 25.5, latMax: 28.3, lonMin: 98.0, lonMax: 99.5 },
  diqing: { latMin: 26.8, latMax: 29.2, lonMin: 98.5, lonMax: 100.5 },
  // 湖南
  changsha: { latMin: 27.8, latMax: 28.7, lonMin: 112.5, lonMax: 114.3 },
  zhuzhou: { latMin: 26.0, latMax: 28.0, lonMin: 112.8, lonMax: 114.2 },
  xiangtan: { latMin: 27.2, latMax: 28.1, lonMin: 111.9, lonMax: 113.3 },
  hengyang: { latMin: 26.3, latMax: 27.5, lonMin: 111.5, lonMax: 113.0 },
  shaoyang: { latMin: 25.9, latMax: 27.6, lonMin: 109.8, lonMax: 112.0 },
  yueyang: { latMin: 28.4, latMax: 29.8, lonMin: 112.3, lonMax: 114.1 },
  changde: { latMin: 28.4, latMax: 30.1, lonMin: 110.5, lonMax: 112.5 },
  zhangjiajie: { latMin: 28.8, latMax: 29.9, lonMin: 109.6, lonMax: 111.3 },
  yiyang: { latMin: 27.9, latMax: 29.5, lonMin: 110.7, lonMax: 112.8 },
  chenzhou: { latMin: 25.0, latMax: 26.5, lonMin: 112.0, lonMax: 114.0 },
  yongzhou: { latMin: 24.8, latMax: 26.6, lonMin: 111.0, lonMax: 112.5 },
  huaihua: { latMin: 26.0, latMax: 29.0, lonMin: 109.0, lonMax: 111.5 },
  loudi: { latMin: 27.2, latMax: 28.2, lonMin: 110.7, lonMax: 112.5 },
  xiangxi: { latMin: 27.8, latMax: 29.5, lonMin: 109.1, lonMax: 110.5 },
};

const PRIVACY_LEVELS = ["L1", "L2", "L3", "L4"];

// 根据城市规模调整餐厅数量要求
const CITY_SIZE_RULES: Record<string, { min: number; max: number }> = {
  // 省会/直辖市: 规模大
  shanghai: { min: 20, max: 300 },
  beijing: { min: 20, max: 300 },
  shenzhen: { min: 20, max: 300 },
  chengdu: { min: 20, max: 300 },
  chongqing: { min: 20, max: 300 },
  kunming: { min: 25, max: 300 },
  changsha: { min: 25, max: 300 },
  // 普通地级市: 中等规模
  deyang: { min: 10, max: 200 },
  mianyang: { min: 20, max: 200 },
  guangyuan: { min: 10, max: 200 },
  bazhong: { min: 10, max: 200 },
  dazhou: { min: 10, max: 200 },
  guangan: { min: 10, max: 200 },
  nanchong: { min: 10, max: 200 },
  suining: { min: 10, max: 200 },
  neijiang: { min: 10, max: 200 },
  zigong: { min: 10, max: 200 },
  luzhou: { min: 10, max: 200 },
  yibin: { min: 10, max: 200 },
  leshan: { min: 10, max: 200 },
  meishan: { min: 10, max: 200 },
  yaan: { min: 10, max: 200 },
  ziyang: { min: 10, max: 200 },
  panzhihua: { min: 10, max: 200 },
  aba: { min: 10, max: 300 },
  ganzi: { min: 10, max: 300 },
  liangshan: { min: 10, max: 300 },
  qujing: { min: 10, max: 200 },
  yuxi: { min: 10, max: 200 },
  baoshan: { min: 10, max: 200 },
  zhaotong: { min: 10, max: 200 },
  lijiang: { min: 10, max: 200 },
  puer: { min: 10, max: 200 },
  lincang: { min: 10, max: 200 },
  chuxiong: { min: 10, max: 200 },
  honghe: { min: 10, max: 200 },
  wenshan: { min: 10, max: 200 },
  xishuangbanna: { min: 10, max: 200 },
  dali: { min: 10, max: 200 },
  dehong: { min: 10, max: 200 },
  nujiang: { min: 10, max: 200 },
  diqing: { min: 10, max: 200 },
  zhuzhou: { min: 10, max: 200 },
  xiangtan: { min: 10, max: 200 },
  hengyang: { min: 10, max: 200 },
  shaoyang: { min: 10, max: 200 },
  yueyang: { min: 10, max: 200 },
  changde: { min: 10, max: 200 },
  zhangjiajie: { min: 10, max: 200 },
  yiyang: { min: 10, max: 200 },
  chenzhou: { min: 10, max: 200 },
  yongzhou: { min: 10, max: 200 },
  huaihua: { min: 10, max: 200 },
  loudi: { min: 10, max: 200 },
  xiangxi: { min: 10, max: 200 },
};

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

interface SeedStory {
  storyType: string;
  title: string;
  content: string;
  talkingPoints: string[];
  relatedTopics: string[];
}

interface SeedFile {
  city: string;
  restaurants: SeedRestaurant[];
}

let errors = 0;
let warnings = 0;

function error(msg: string) {
  console.error(`  [ERROR] ${msg}`);
  errors++;
}

function warn(msg: string) {
  console.warn(`  [WARN]  ${msg}`);
  warnings++;
}

function ok(msg: string) {
  console.log(`  [OK]    ${msg}`);
}

function validateCityFile(cityKey: string): SeedFile | null {
  const filePath = path.join(SEED_DIR, `${cityKey}.json`);
  const cityName = CITY_NAMES[cityKey];
  console.log(`\n--- ${cityName} (${cityKey}.json) ---`);

  if (!fs.existsSync(filePath)) {
    error(`文件不存在: ${filePath}`);
    return null;
  }

  let data: SeedFile;
  try {
    data = JSON.parse(fs.readFileSync(filePath, "utf-8"));
  } catch {
    error("JSON解析失败");
    return null;
  }

  if (data.city !== cityName) {
    error(`city字段 "${data.city}" 不匹配预期 "${cityName}"`);
  } else {
    ok(`城市名正确: ${cityName}`);
  }

  const count = data.restaurants.length;
  const sizeRule = CITY_SIZE_RULES[cityKey] || { min: 10, max: 300 };
  if (count < sizeRule.min || count > sizeRule.max) {
    error(`餐厅数量 ${count} 不在范围 [${sizeRule.min}, ${sizeRule.max}]`);
  } else {
    ok(`餐厅数量: ${count}`);
  }

  const cuisines = new Set(data.restaurants.map((r) => r.cuisineType));
  if (cuisines.size < 4) {
    error(`菜系种类 ${cuisines.size} < 4`);
  } else {
    ok(`菜系种类: ${cuisines.size} (${[...cuisines].join(", ")})`);
  }

  const privacyCounts: Record<string, number> = { L1: 0, L2: 0, L3: 0, L4: 0 };
  for (const r of data.restaurants) {
    if (PRIVACY_LEVELS.includes(r.privacyLevel)) {
      privacyCounts[r.privacyLevel]++;
    } else {
      error(`餐厅 "${r.name}" 的privacyLevel无效: ${r.privacyLevel}`);
    }
  }
  for (const level of PRIVACY_LEVELS) {
    const pct = (privacyCounts[level] / count) * 100;
    if (privacyCounts[level] === 0) {
      error(`私密性 ${level} 数量为0`);
    } else if (pct < 5 || pct > 55) {
      warn(`私密性 ${level} 占比 ${pct.toFixed(0)}% 偏极端`);
    }
  }
  ok(`私密性分布: L1=${privacyCounts.L1} L2=${privacyCounts.L2} L3=${privacyCounts.L3} L4=${privacyCounts.L4}`);

  const bounds = COORD_BOUNDS[cityKey];

  let coordErrors = 0;
  for (const r of data.restaurants) {
    if (r.latitude < bounds.latMin || r.latitude > bounds.latMax) {
      if (coordErrors < 5) error(`"${r.name}" 纬度 ${r.latitude} 超出范围`);
      coordErrors++;
    }
    if (r.longitude < bounds.lonMin || r.longitude > bounds.lonMax) {
      if (coordErrors < 5) error(`"${r.name}" 经度 ${r.longitude} 超出范围`);
      coordErrors++;
    }
    if (r.priceRangeMin >= r.priceRangeMax) {
      error(`"${r.name}" 价格范围无效: ${r.priceRangeMin} >= ${r.priceRangeMax}`);
    }
    if (r.rating < 3.0 || r.rating > 5.0) {
      error(`"${r.name}" 评分 ${r.rating} 超出范围`);
    }
    if (r.privacyLevel === "L1") {
      if (r.privateRoomMin != null || r.privateRoomMax != null || r.privateRoomCount != null) {
        warn(`"${r.name}" 是L1但设置了包间信息`);
      }
    }
    if (r.stories.length < 1 || r.stories.length > 3) {
      error(`"${r.name}" 故事数量 ${r.stories.length} 不在 [1, 3]`);
    }
    for (const s of r.stories) {
      if (!["菜品", "文化", "历史", "建筑"].includes(s.storyType)) {
        error(`"${r.name}" 故事类型无效: ${s.storyType}`);
      }
      const contentLen = s.content.length;
      if (contentLen < 200 || contentLen > 600) {
        warn(`"${r.name}" 故事 "${s.title}" 长度 ${contentLen} 偏离范围`);
      }
      if (s.talkingPoints.length < 2) {
        warn(`"${r.name}" 故事 "${s.title}" talkingPoints < 2`);
      }
    }
  }
  if (coordErrors > 5) {
    warn(`还有 ${coordErrors - 5} 个坐标错误未显示`);
  }

  return data;
}

console.log("=== 种子数据校验 ===");

let totalRestaurants = 0;
let totalStories = 0;

for (const cityKey of CITIES) {
  const data = validateCityFile(cityKey);
  if (data) {
    totalRestaurants += data.restaurants.length;
    totalStories += data.restaurants.reduce((sum, r) => sum + r.stories.length, 0);
  }
}

console.log(`\n=== 汇总 ===`);
console.log(`餐厅总数: ${totalRestaurants}`);
console.log(`故事总数: ${totalStories}`);
console.log(`错误: ${errors}`);
console.log(`警告: ${warnings}`);

if (errors > 0) {
  console.error(`\n校验失败: ${errors} 个错误`);
  process.exit(1);
} else {
  console.log(`\n校验通过!`);
}
