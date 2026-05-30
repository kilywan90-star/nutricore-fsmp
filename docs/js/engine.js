/**
 * NutriCore FSMP — Clinical Nutrition Engine (v2.1)
 * ESPEN 2025 / CSPEN 2025 / ERAS 2025 based
 * Pass 1-3 fixes applied
 */

const SEVERE_SURGERIES = new Set(["pancreaticoduodenectomy","esophagectomy","total_gastrectomy","liver_resection_major","cytoreductive_surgery"]);
const MODERATE_SURGERIES = new Set(["colorectal_resection","gastrectomy_subtotal"]);

// Disease → compatible surgeries mapping
const DISEASE_SURGERY_MAP = {
  "2B92.0": ["colorectal_resection","cytoreductive_surgery"],
  "2B72.0": ["gastrectomy_subtotal","total_gastrectomy"],
  "2C13.0": ["pancreaticoduodenectomy","cytoreductive_surgery"],
  "2C22.0": ["esophagectomy"],
  "2C17.0": ["liver_resection_major"],
  "5A11": [],
  "CB01": [],
  "1C00": [],
  "8B20": [],
  "5C50": [],
};

// Disease severity scores when no surgery (NRS2002 component B)
const DISEASE_SEVERITY_NONSURGICAL = {
  "1C00": 3,  // sepsis = severe
  "2C13.0": 2, // pancreatic cancer = moderate (major illness)
  "2C22.0": 2, // esophageal cancer = moderate
  "2B72.0": 2, // gastric cancer = moderate
  "2B92.0": 1, // colorectal cancer = mild (chronic)
  "2C17.0": 1, // liver cancer = mild (chronic)
  "5A11": 1,  // T2DM = mild (chronic)
  "CB01": 1,  // COPD = mild (chronic)
  "8B20": 2,  // stroke = moderate
  "5C50": 1,  // cirrhosis = mild (chronic)
};

function calcBMI(w, h) { const hm = h/100; return Math.round(w/(hm*hm)*10)/10; }

/** Get adjusted body weight for obese patients (BMI > 30) */
function adjustedWeight(actualWt, heightCm) {
  const bmi = calcBMI(actualWt, heightCm);
  if (bmi <= 30) return actualWt;
  const idealWt = 22 * (heightCm/100) ** 2;
  return Math.round((idealWt + 0.25 * (actualWt - idealWt)) * 10) / 10;
}

/** NRS 2002 Nutrition Risk Screening — FIXED: nutrientScore starts at 0 */
function scoreNRS2002(data) {
  const bmi = calcBMI(data.weight, data.height);
  let nutrientScore = 0;

  // Impaired nutritional status (0-3)
  const lossPct = data.weight > 0 ? (data.weightLoss / data.weight) * 100 : 0;

  if (lossPct > 15) {
    nutrientScore = 3;
  } else if (lossPct > 5) {
    nutrientScore = 2;
  } else if (bmi < 18.5) {
    nutrientScore = 3;
  } else if (bmi < 20.5) {
    nutrientScore = 2;
  } else if (lossPct > 0 || bmi < 25) {
    nutrientScore = 1;
  }

  // Food intake reduction can override
  if (data.foodIntake >= 75) nutrientScore = Math.max(nutrientScore, 3);
  else if (data.foodIntake >= 50) nutrientScore = Math.max(nutrientScore, 2);
  else if (data.foodIntake >= 25) nutrientScore = Math.max(nutrientScore, 1);

  // Disease severity (0-3)
  let diseaseScore = 0;
  if (data.surgery && SEVERE_SURGERIES.has(data.surgery)) {
    diseaseScore = 3;
  } else if (data.surgery && MODERATE_SURGERIES.has(data.surgery)) {
    diseaseScore = 2;
  } else if (data.surgery) {
    diseaseScore = 1;
  } else {
    diseaseScore = DISEASE_SEVERITY_NONSURGICAL[data.disease] || 1;
  }

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

  if (gi === "non_functional") {
    route="PN"; rationale="消化道无功能，需肠外营养(PN)支持";
  } else if (gi === "impaired") {
    route="EN"; rationale="消化道功能受损→要素型/半要素型肠内营养(EN)";
  } else if (swallow === "unsafe") {
    route="EN"; rationale="吞咽不安全→管饲肠内营养(鼻胃管/鼻肠管)";
  } else if (swallow === "impaired") {
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

  // Use adjusted weight for obese patients (BMI > 30)
  const bmi = calcBMI(data.weight, data.height);
  const useWeight = bmi > 30 ? adjustedWeight(data.weight, data.height) : data.weight;

  const energyMap = {baseline:25, mild:28, moderate:32, severe:37};
  const proteinMap = {baseline:0.8, mild:1.1, moderate:1.4, severe:1.8};
  const energy = Math.round(useWeight * energyMap[stress]);
  const protein = Math.round(useWeight * proteinMap[stress]*10)/10;

  // Fluid: 30-35 ml/kg, restricted for renal
  let fluid;
  if (data.renal === "dialysis") {
    fluid = Math.min(Math.round(useWeight * 20), 1500);
  } else if (data.renal === "impaired") {
    fluid = Math.min(Math.round(useWeight * 25), 2000);
  } else {
    fluid = Math.round(useWeight * 32);
  }

  return { route, rationale, energy, protein, fluid, stress, adjustedWeight: bmi > 30 };
}

/** Filter FSMP candidates — FIXED: exclude 非全营养 from complete formula matching */
function getFSMPCandidates(pathway) {
  if (pathway.route === "PN") return [];

  return FSMP_PRODUCTS.filter(p => {
    const cat = p.cat;
    // Only match complete nutrition formulas (not components)
    if (cat === "全营养" || cat === "特定全营养") return true;
    // For EN, also include incomplete (starter) formulas
    if (pathway.route === "EN" && cat === "非全营养") return true;
    return false;
  });
}

/** Match FSMP products against patient needs (5-dimension weighted scoring) */
function matchProducts(data, pathway) {
  const candidates = getFSMPCandidates(pathway);
  if (candidates.length === 0) return [];

  return candidates.map(p => {
    const scores = {};
    const reasons = [];
    const warnings = [];

    // 1. Category match (30%)
    if (pathway.route === "ONS") {
      scores.cat = p.cat === "全营养" ? 100 : p.cat === "特定全营养" ? 85 : 50;
    } else if (pathway.route === "EN") {
      scores.cat = p.cat === "全营养" ? 100 : p.cat === "特定全营养" ? 90 : p.cat === "非全营养" ? 60 : 50;
    } else {
      scores.cat = 70;
    }

    // 2. Energy density (20%)
    const volNeeded = pathway.energy / p.energy * 100;
    if (volNeeded >= 900 && volNeeded <= 2000) scores.energy = 100;
    else if (volNeeded >= 700 && volNeeded <= 2500) scores.energy = 80;
    else if (volNeeded < 500) scores.energy = 60;  // too concentrated
    else scores.energy = 45;
    reasons.push(`日需约${Math.round(volNeeded)}ml`);

    // 3. Protein quality (20%)
    const protScores = {whey:100, casein:85, hydrolysate:80, soy:65, amino_acid:55, "casein+whey":95};
    scores.protein = protScores[p.protSrc] || 70;

    // 4. Disease-specific features (20%)
    scores.feat = 50;
    const feat = p.feat || [];
    const hasSurgery = data.surgery && data.surgery.length > 0;
    const isSevereSurgery = hasSurgery && SEVERE_SURGERIES.has(data.surgery);

    if (feat.includes("immune_modulation") && isSevereSurgery) {
      scores.feat += 30; reasons.push("免疫调节配方适应大手术(ESPEN 2025 Rec.28)");
    }
    if (feat.includes("diabetes") && (data.disease === "5A11" || (data.comorbidities||[]).includes("diabetes"))) {
      scores.feat += 25; reasons.push("糖尿病专用低GI配方");
    }
    if (feat.includes("renal") && data.renal !== "normal") {
      scores.feat += 25; reasons.push("肾病适用低电解质配方");
    }
    if (feat.includes("hepatic") && data.liver !== "normal") {
      scores.feat += 25; reasons.push("肝病适用高BCAA配方");
    }
    if (feat.includes("high_mct") && data.giFunction === "impaired") {
      scores.feat += 20; reasons.push("高MCT适配脂肪吸收障碍");
    }
    if (feat.includes("low_residue") && data.giFunction === "impaired") {
      scores.feat += 15; reasons.push("低渣配方适配肠道功能受损");
    }
    if (feat.includes("fiber") && data.giFunction === "normal" && pathway.route !== "EN") {
      scores.feat += 10; reasons.push("膳食纤维助肠道功能");
    }
    if (feat.includes("high_protein") && pathway.stress === "severe") {
      scores.feat += 10; reasons.push("高蛋白适配高分解代谢");
    }
    scores.feat = Math.min(scores.feat, 100);

    // 5. Contraindications / Safety (10%)
    scores.contra = 100;
    if (p.osm > 500 && data.giFunction === "impaired") {
      scores.contra -= 20; warnings.push(`渗透压${p.osm}mOsm/L偏高→肠功能受损时需稀释缓输`);
    }
    if (p.osm > 400 && data.giFunction === "impaired") {
      scores.contra -= 10;
    }
    if (data.renal === "impaired" && p.protein > 6.0) {
      scores.contra -= 15; warnings.push("高蛋白配方→肾功能不全需监测BUN/Cr");
    }
    if (data.renal === "dialysis" && p.protein < 5.0 && pathway.stress === "severe") {
      scores.contra -= 5; warnings.push("透析患者需更高蛋白(HD丢失氨基酸)→考虑高蛋白配方");
    }
    if (data.liver === "failure" && !["hydrolysate","amino_acid"].includes(p.protSrc)) {
      scores.contra -= 15; warnings.push("肝衰竭对整蛋白耐受差→考虑要素型/氨基酸型");
    }
    scores.contra = Math.max(scores.contra, 0);

    const total = scores.cat*0.30 + scores.energy*0.20 + scores.protein*0.20 + scores.feat*0.20 + scores.contra*0.10;
    return { product: p, score: Math.round(total*10)/10, scores, reasons, warnings };
  }).sort((a,b) => b.score - a.score).slice(0, 5);
}

/** Check drug-nutrient interactions — FIXED: dedup by drug+nutrient */
function checkInteractions(atcCodes) {
  const seen = new Set();
  const results = [];
  for (const code of atcCodes) {
    const data = DRUG_INTERACTIONS[code];
    if (!data) continue;
    for (const ix of data.interactions) {
      const key = `${data.drug}|${ix.nutrient}`;
      if (seen.has(key)) continue;
      seen.add(key);
      results.push({ drug: data.drug, class: data.class, ...ix });
    }
  }
  return results;
}

/** Get compatible surgeries for a disease code */
function getSurgeriesForDisease(diseaseCode) {
  return DISEASE_SURGERY_MAP[diseaseCode] || [];
}

/** Update surgery dropdown based on selected disease */
function updateSurgeryOptions(diseaseCode, surgerySelectId) {
  const sel = document.getElementById(surgerySelectId);
  if (!sel) return;
  const compatible = getSurgeriesForDisease(diseaseCode);
  const currentVal = sel.value;

  // Surgery name lookup
  const nameMap = {
    "colorectal_resection":"结直肠癌根治术","gastrectomy_subtotal":"胃大部切除术",
    "total_gastrectomy":"全胃切除术","pancreaticoduodenectomy":"胰十二指肠切除术",
    "esophagectomy":"食管癌根治术","liver_resection_major":"大范围肝切除术",
    "cholecystectomy":"腹腔镜胆囊切除术","cytoreductive_surgery":"肿瘤细胞减灭术",
  };

  sel.innerHTML = '<option value="">— 无手术 —</option>';
  for (const code of compatible) {
    const name = nameMap[code] || code;
    const selected = code === currentVal ? ' selected' : '';
    sel.innerHTML += `<option value="${code}"${selected}>${name}</option>`;
  }
  if (compatible.length === 0 || currentVal === '') {
    sel.value = '';
  } else if (!compatible.includes(currentVal)) {
    sel.value = compatible[0];
  }
}

/** Validate form before submission */
function validateForm(data) {
  const errors = [];
  if (!data.age || data.age <= 0 || data.age > 120) errors.push("请输入有效年龄");
  if (!data.height || data.height < 50 || data.height > 250) errors.push("请输入有效身高");
  if (!data.weight || data.weight < 20 || data.weight > 300) errors.push("请输入有效体重");
  return errors;
}
