/**
 * NutriCore FSMP — Clinical Nutrition Engine
 * ESPEN 2025 / CSPEN 2025 / ERAS 2025 based
 */

const SEVERE_SURGERIES = new Set(["pancreaticoduodenectomy","esophagectomy","total_gastrectomy","liver_resection_major","cytoreductive_surgery"]);
const MODERATE_SURGERIES = new Set(["colorectal_resection","gastrectomy_subtotal"]);

function calcBMI(w, h) { const hm = h/100; return Math.round(w/(hm*hm)*10)/10; }

/** NRS 2002 Nutrition Risk Screening */
function scoreNRS2002(data) {
  const bmi = calcBMI(data.weight, data.height);
  let nutrientScore = 1;
  if (data.weight > 0) {
    const lossPct = data.weightLoss / data.weight * 100;
    if (lossPct > 15) nutrientScore = 3;
    else if (lossPct > 5) nutrientScore = 2;
    else if (bmi < 18.5) nutrientScore = 3;
    else if (bmi < 20.5) nutrientScore = 2;
  }
  if (data.foodIntake >= 75) nutrientScore = Math.max(nutrientScore, 3);
  else if (data.foodIntake >= 50) nutrientScore = Math.max(nutrientScore, 2);
  else if (data.foodIntake >= 25) nutrientScore = Math.max(nutrientScore, 1);

  let diseaseScore = 0;
  if (data.surgery && SEVERE_SURGERIES.has(data.surgery)) diseaseScore = 3;
  else if (data.surgery && MODERATE_SURGERIES.has(data.surgery)) diseaseScore = 2;
  else if (data.surgery) diseaseScore = 1;
  else if (["1C00"].includes(data.disease)) diseaseScore = 3;
  else if (["2C25","8B20"].includes(data.disease)) diseaseScore = 2;
  else diseaseScore = 1;

  const ageScore = data.age >= 70 ? 1 : 0;
  const total = nutrientScore + diseaseScore + ageScore;

  let riskLevel, triggers;
  if (total >= 5) { riskLevel = "high"; triggers = true; }
  else if (total >= 3) { riskLevel = "medium"; triggers = true; }
  else { riskLevel = "low"; triggers = false; }

  return { score: total, riskLevel, triggers, breakdown: { nutrientScore, diseaseScore, ageScore }, bmi };
}

/** Determine nutrition pathway (ONS / EN / PN / mixed) */
function determinePathway(data) {
  const gi = data.giFunction, swallow = data.swallow;
  let route, rationale;

  if (gi === "non_functional") { route="PN"; rationale="消化道无功能，需肠外营养(PN)支持"; }
  else if (gi === "impaired") { route="EN"; rationale="消化道功能受损→要素型/半要素型肠内营养(EN)"; }
  else if (swallow === "unsafe") { route="EN"; rationale="吞咽不安全→管饲肠内营养(鼻胃管/鼻肠管)"; }
  else if (swallow === "impaired") {
    if (data.foodIntake >= 50) { route="mixed"; rationale="吞咽功能受损+经口摄入显著不足→ONS+管饲EN联合"; }
    else { route="ONS"; rationale="吞咽功能轻度受损→口服营养补充剂(调整质地)"; }
  } else {
    if (data.postOpDay > 0 && data.foodIntake >= 50) { route="ONS"; rationale="术后经口摄入不足→ONS补充营养缺口"; }
    else if (data.postOpDay > 0) { route="ONS"; rationale="ERAS路径→术后早期经口进食+ONS"; }
    else { route="ONS"; rationale="消化道功能正常+吞咽安全→口服营养补充/常规饮食"; }
  }

  let stress = "baseline";
  if (data.surgery && SEVERE_SURGERIES.has(data.surgery)) stress = "severe";
  else if (data.surgery && MODERATE_SURGERIES.has(data.surgery)) stress = "moderate";
  else if (data.postOpDay > 0) stress = "mild";

  const energyMap = {baseline:25, mild:28, moderate:32, severe:37};
  const proteinMap = {baseline:0.8, mild:1.1, moderate:1.4, severe:1.8};
  const energy = Math.round(data.weight * energyMap[stress]);
  const protein = Math.round(data.weight * proteinMap[stress]*10)/10;
  let fluid = Math.round(data.weight * 32);
  if (data.renal === "impaired" || data.renal === "dialysis") fluid = Math.min(Math.round(data.weight*25), 2000);

  return { route, rationale, energy, protein, fluid, stress };
}

/** Match FSMP products against patient needs (5-dimension weighted scoring) */
function matchProducts(data, pathway) {
  if (pathway.route === "PN") return [];

  const candidates = FSMP_PRODUCTS.filter(p => p.cat.includes("全营养") || p.cat.includes("特定全营养"));
  return candidates.map(p => {
    const scores = {};
    const reasons = [];
    const warnings = [];

    // 1. Category (30%)
    scores.cat = pathway.route==="ONS" ? (p.cat.includes("全营养")?100:p.cat.includes("特定")?85:50) :
                 pathway.route==="EN" ? (p.cat.includes("全营养")?100:60) : 70;

    // 2. Energy density (20%)
    const volNeeded = pathway.energy / p.energy * 100;
    if (volNeeded >= 900 && volNeeded <= 2000) scores.energy = 100;
    else if (volNeeded >= 700 && volNeeded <= 2500) scores.energy = 80;
    else scores.energy = 50;
    reasons.push(`日需约${Math.round(volNeeded)}ml`);

    // 3. Protein (20%)
    const protScores = {whey:100, casein:85, hydrolysate:80, soy:65, amino_acid:55};
    scores.protein = protScores[p.protSrc] || 70;

    // 4. Disease-specific features (20%)
    scores.feat = 50;
    const feat = p.feat || [];
    if (feat.includes("immune_modulation") && data.surgery && SEVERE_SURGERIES.has(data.surgery)) {
      scores.feat += 30; reasons.push("免疫调节配方适应大手术(ESPEN 2025)");
    }
    if (feat.includes("diabetes") && (data.disease==="5A11" || data.comorbidities.includes("diabetes"))) {
      scores.feat += 25; reasons.push("糖尿病专用低GI配方");
    }
    if (feat.includes("renal") && data.renal !== "normal") { scores.feat += 25; reasons.push("肾病适用低电解质配方"); }
    if (feat.includes("hepatic") && data.liver !== "normal") { scores.feat += 25; reasons.push("肝病适用高BCAA配方"); }
    if (feat.includes("high_mct") && data.giFunction === "impaired") { scores.feat += 20; reasons.push("高MCT适配脂肪吸收障碍"); }
    if (feat.includes("low_residue") && data.giFunction === "impaired") { scores.feat += 15; reasons.push("低渣配方适配肠道功能受损"); }
    if (feat.includes("fiber") && data.giFunction === "normal") { scores.feat += 10; reasons.push("膳食纤维助肠道功能"); }
    if (feat.includes("high_protein") && pathway.stress === "severe") { scores.feat += 10; reasons.push("高蛋白适配高分解代谢"); }
    scores.feat = Math.min(scores.feat, 100);

    // 5. Contraindications / Safety (10%)
    scores.contra = 100;
    if (p.osm > 500 && data.giFunction === "impaired") { scores.contra -= 15; warnings.push(`渗透压${p.osm}mOsm/L偏高→肠功能受损时需稀释缓输`); }
    if (p.osm > 400 && data.giFunction === "impaired") { scores.contra -= 8; warnings.push(`渗透压${p.osm}mOsm/L→注意输注速率`); }
    if (data.renal === "impaired" && p.protein > 6.0) { scores.contra -= 10; warnings.push("高蛋白配方→肾功能不全需监测"); }
    if (data.liver === "failure" && !["hydrolysate","amino_acid"].includes(p.protSrc)) { scores.contra -= 10; warnings.push("肝衰竭对整蛋白耐受差→考虑要素型"); }

    const total = scores.cat*0.30 + scores.energy*0.20 + scores.protein*0.20 + scores.feat*0.20 + scores.contra*0.10;
    return { product: p, score: Math.round(total*10)/10, scores, reasons, warnings };
  }).sort((a,b) => b.score - a.score).slice(0, 5);
}

/** Check drug-nutrient interactions */
function checkInteractions(atcCodes) {
  const results = [];
  for (const code of atcCodes) {
    const data = DRUG_INTERACTIONS[code];
    if (data) {
      for (const ix of data.interactions) {
        results.push({ drug: data.drug, class: data.class, ...ix });
      }
    }
  }
  return results;
}
