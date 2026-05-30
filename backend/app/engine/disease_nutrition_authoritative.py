"""
Authoritative Disease-Nutrition Mapping
Based on: ESPEN Surgery 2025, ERAS Colorectal 2025, CSPEN 2025 Guidelines

Each entry includes:
- Energy and protein targets per guideline recommendations
- Specific nutrient concerns based on disease pathophysiology
- Refeeding syndrome risk stratification
- Guideline citation references
"""

AUTHORITATIVE_DISEASE_NUTRITION = {
    # ==================== SURGICAL ONCOLOGY ====================
    "colorectal_cancer": {
        icd11_code: "2B92.0",
        name_zh: "结直肠癌",
        name_en: "Colorectal Cancer",
        category: "surgical",

        # From ESPEN 2025 + ERAS Colorectal 2025
        preop_nutrition: {
            screening: "NRS2002 mandatory for ALL patients (ERAS CR 2025)",
            immunonutrition: "Recommended for MALNOURISHED patients only (ERAS CR 2025 — NEW 2025 recommendation)",
            carbohydrate_loading: "Evidence WEAKENED vs prior guidelines (ERAS CR 2025)",
            severe_malnutrition: "10-14 days preop nutrition even if surgery delayed (ESPEN 2025 Rec.20 Grade A)",
        },
        postop_nutrition: {
            oral_feeding: "Early oral feeding within hours post-op (ESPEN 2025 Rec.4 Grade A, ERAS CR 2025)",
            ons: "ONS to supplement if oral intake <50% needs (ESPEN 2025 Rec.28)",
            en_tube: "NOT routinely required for colorectal (ESPEN 2025 Rec.30 — reserved for upper GI)",
            immunonutrition: "Supported postoperatively (ERAS CR 2025)",
            mobilisation: "≥3 hours/day from POD1 (ERAS CR 2025)",
        },

        energy_target_kcal_kg: {
            baseline: 25,
            mild_stress: 28,
            moderate_stress: 30,  # post-op moderate stress
            severe_stress: 35,
        },
        protein_target_g_kg: {
            baseline: 0.8,
            mild_stress: 1.0,
            moderate_stress: 1.2,  # post-op
            severe_stress: 1.5,
        },

        nutrient_deficiency_risk: [
            {"nutrient": "铁", "mechanism": "慢性失血 + 肿瘤相关性炎症 → 铁调素升高 → 功能性缺铁"},
            {"nutrient": "维生素B12", "mechanism": "右半结肠切除 → 回肠B12吸收位点受影响"},
            {"nutrient": "叶酸", "mechanism": "肿瘤消耗 + 化疗(5-FU抗叶酸效应)"},
        ],
        refeeding_risk: "medium" if weight_loss > 5 else "low",

        citations: [
            "Gustafsson UO et al. Surgery 2025;184:109397 — ERAS CR Guidelines 2025",
            "Weimann A et al. Clin Nutr 2025;53:222-261 — ESPEN Surgery 2025 Rec.4,20,28",
        ]
    },

    "gastric_cancer": {
        icd11_code: "2B72.0",
        name_zh: "胃癌",
        name_en: "Gastric Cancer",
        category: "surgical",

        preop_nutrition: {
            screening: "NRS2002 at admission (all patients)",
            severe_malnutrition: "10-14 days preop nutrition (ESPEN 2025 Rec.20)",
            immunonutrition: "Consider for malnourished patients undergoing major resection",
        },
        postop_nutrition: {
            oral_feeding: "Early oral feeding; adjust to surgery type and tolerance (ESPEN 2025 Rec.5)",
            en: "Start EN within 24h if oral <50% for 7d, ESPECIALLY after upper GI resection for tumor (ESPEN 2025 Rec.28 Grade A/B)",
            tube: "Consider nasojejunal/jejunostomy for total gastrectomy in malnourished patients (ESPEN 2025 Rec.30 Grade B, 89% agreement)",
            supplements: "Lifetime B12 (IM) post total gastrectomy; Fe, Ca, Vitamin D monitoring",
        },

        energy_target_kcal_kg: {
            baseline: 25,
            mild_stress: 28,
            moderate_stress: 32,
            severe_stress: 37,  # total gastrectomy = severe stress
        },
        protein_target_g_kg: {
            baseline: 0.8,
            mild_stress: 1.0,
            moderate_stress: 1.4,
            severe_stress: 1.5,  # ESPEN 2025: 1.5 g/kg for major upper GI surgery
        },

        nutrient_deficiency_risk: [
            {"nutrient": "维生素B12", "mechanism": "全胃切除 → 内因子完全缺失 → 终身IM B12必需"},
            {"nutrient": "铁", "mechanism": "胃酸缺乏 → 非血红素铁吸收障碍；慢性失血"},
            {"nutrient": "钙", "mechanism": "十二指肠旁路 → 钙吸收减少；长期PPI使用"},
            {"nutrient": "维生素D", "mechanism": "脂肪吸收不良 → 脂溶性维生素缺乏"},
            {"nutrient": "锌", "mechanism": "胃切除 → 锌吸收减少 + 肠液丢失"},
        ],
        refeeding_risk: "high" if bmi < 18.5 else "medium",

        citations: [
            "Weimann A et al. Clin Nutr 2025;53:222-261 — ESPEN Surgery 2025 Rec.28,30,31",
            "Mariette C et al. Ann Surg 2019: French national guidelines for gastric cancer",
        ]
    },

    "pancreatic_cancer": {
        icd11_code: "2C13.0",
        name_zh: "胰腺癌",
        name_en: "Pancreatic Cancer",
        category: "surgical",

        preop_nutrition: {
            screening: "NRS2002 入院24h内 (CSPEN胰腺2025)",
            assessment: "有风险者行营养评估：病史+膳食+体格+实验室 (CSPEN胰腺2025)",
            strategy: "术前7天营养打底 + 术后早期EN + 出院后30天延续管理 (CSPEN胰腺2025)",
            severe_malnutrition: "10-14 days preop nutrition (ESPEN 2025 Rec.20)",
            exocrine_insufficiency: "PERT (pancreatic enzyme replacement therapy) screening preop",
        },
        postop_nutrition: {
            en_route: "首选肠内营养 (CSPEN胰腺2025)",
            tube: "Consider intraoperative jejunostomy for Whipple in malnourished patients (ESPEN 2025 Rec.30 Grade B)",
            en_start: "EN within 24h if oral route insufficient (ESPEN 2025 Rec.28)",
            pert: "Pancreatic enzyme replacement if steatorrhea or weight loss post-op",
            home_en: "Jejunostomy may be maintained at discharge depending on weight gain and chemotherapy compliance (ESPEN 2025 Rec.34)",
        },

        energy_target_kcal_kg: {
            baseline: 25,
            mild_stress: 30,
            moderate_stress: 32,
            severe_stress: 37,  # Whipple = severe catabolic stress
        },
        protein_target_g_kg: {"baseline": 0.8, "mild": 1.2, "moderate": 1.5, "severe": 1.8},

        nutrient_deficiency_risk: [
            {"nutrient": "脂溶性维生素(ADEK)", "mechanism": "胰腺外分泌功能不全 → 脂肪吸收障碍"},
            {"nutrient": "钙", "mechanism": "脂肪泻 → 钙皂形成 → 钙吸收减少"},
            {"nutrient": "镁", "mechanism": "脂肪泻 + 化疗(顺铂)肾毒性"},
            {"nutrient": "锌", "mechanism": "胰酶分泌减少 → 锌结合配体减少"},
            {"nutrient": "蛋白质-能量", "mechanism": "胰蛋白酶/脂肪酶不足 → 整体营养不良 → 癌性恶液质高风险"},
        ],
        refeeding_risk: "high",  # Whipple = highest risk for refeeding

        citations: [
            "CSPEN 胰腺外科围手术期全程化营养管理指南 2025版 — 18问题 23推荐",
            "Weimann A et al. Clin Nutr 2025;53:222-261 — ESPEN Surgery 2025 Rec.20,28,30,31,34",
        ]
    },

    "esophageal_cancer": {
        icd11_code: "2C22.0",
        name_zh: "食管癌",
        name_en: "Esophageal Cancer",
        category: "surgical",

        preop_nutrition: {
            screening: "NRS2002; almost all patients are malnourished at presentation (dysphagia → progressive intake reduction)",
            severe_malnutrition: "10-14 days preop nutrition (ESPEN 2025 Rec.20) — critical for esophagectomy outcomes",
            route: "If oral intake impossible → EN via nasogastric/PEG preop",
        },
        postop_nutrition: {
            tube: "Intraoperative jejunostomy STRONGLY recommended (ESPEN 2025 Rec.30 Grade B)",
            en_start: "EN 10-20 mL/h POD1, advance to target over 4-5 days (refeeding precaution — ESPEN 2025 Rec.31)",
            oral: "Oral intake begins POD7-10 after swallow assessment; EN continues until oral meets 75% needs",
        },

        energy_target_kcal_kg: {"baseline": 25, "severe": 35},
        protein_target_g_kg: {"baseline": 0.8, "severe": 1.5},

        nutrient_deficiency_risk: [
            {"nutrient": "蛋白质-能量", "mechanism": "长期吞咽困难 → 严重蛋白质-能量营养不良"},
            {"nutrient": "锌", "mechanism": "食管黏膜修复需要；摄入不足"},
            {"nutrient": "维生素A/C", "mechanism": "抗氧化防御减弱 + 伤口愈合需求增加"},
            {"nutrient": "铁", "mechanism": "慢性失血(肿瘤溃疡) + 进食减少"},
        ],
        refeeding_risk: "high",  # esophagectomy patients = highest refeeding risk — often NPO >7 days

        citations: [
            "Weimann A et al. Clin Nutr 2025;53:222-261 — ESPEN Surgery 2025 Rec.30,31",
            "Low DE et al. Ann Surg 2019: Esophagectomy complications consensus",
        ]
    },

    "liver_cancer": {
        icd11_code: "2C17.0",
        name_zh: "原发性肝癌",
        name_en: "Hepatocellular Carcinoma",
        category: "surgical",

        preop_nutrition: {
            screening: "NRS2002 + liver-specific assessment (Child-Pugh, sarcopenia CT assessment)",
            prehabilitation: "Frailty and sarcopenia assessment formally included (ESPEN 2025 — NEW)",
            bcaa: "Consider branched-chain amino acid supplementation in cirrhotic patients",
            late_evening_snack: "Prevent nocturnal fasting catabolism — LES 50g CHO before bed",
        },
        postop_nutrition: {
            en_start: "Early EN within 24h if oral inadequate",
            protein_restriction: "DO NOT restrict protein (outdated practice); target 1.2 g/kg even in cirrhosis",
            sodium: "Restrict to <2g/day if ascites present",
        },

        energy_target_kcal_kg: {"baseline": 25, "cirrhotic": 30},  # 30 kcal/kg for cirrhotic patients
        protein_target_g_kg: {"baseline": 0.8, "cirrhotic": 1.2},  # ESPEN: 1.2 g/kg in cirrhosis

        nutrient_deficiency_risk: [
            {"nutrient": "锌", "mechanism": "肝病→锌代谢异常+尿排泄增加；锌缺乏→氨解毒障碍"},
            {"nutrient": "硒", "mechanism": "肝功能不全→GPX合成减少→抗氧化防御降低"},
            {"nutrient": "维生素D", "mechanism": "肝25-羟化酶活性降低→25-OH D3合成障碍"},
            {"nutrient": "B族维生素", "mechanism": "肝脏储存减少+酒精性肝病吸收障碍"},
            {"nutrient": "支链氨基酸(BCAA)", "mechanism": "肝硬化→BCAA/AAA比值降低→肝性脑病风险"},
        ],
        refeeding_risk: "medium",
        special_notes: "夜间加餐(late evening snack)可逆转肝硬化患者的夜间饥饿代谢",

        citations: [
            "Weimann A et al. Clin Nutr 2025;53:222-261 — ESPEN Surgery 2025",
            "Plauth M et al. Clin Nutr 2019;38:485-521 — ESPEN guideline on liver disease",
        ]
    },

    # ==================== MEDICAL ====================
    "diabetes_t2": {
        icd11_code: "5A11",
        name_zh: "2型糖尿病",
        name_en: "Type 2 Diabetes Mellitus",
        category: "medical",

        nutrition: {
            screening: "NRS2002 + MUST at diagnosis and annually",
            carbohydrate: "Individualize CHO intake; low-GI preferred; fiber ≥25-35 g/day",
            protein: "1.0-1.2 g/kg/day; up to 1.5 g/kg if catabolic or wound healing",
            fat: "MUFA/PUFA preferred; limit SFA <10%; avoid trans fat",
            fsmp: "Diabetes-specific formulas (low GI, high MUFA, fiber-enriched) improve postprandial glycemia vs standard formulas",
        },

        energy_target_kcal_kg: {"baseline": 25, "overweight": 20},  # energy restriction for overweight
        protein_target_g_kg: {"baseline": 0.8, "catabolic": 1.2, "wound": 1.5},

        nutrient_deficiency_risk: [
            {"nutrient": "镁", "mechanism": "高血糖→渗透性利尿→尿镁排泄增加；低镁→胰岛素抵抗加重"},
            {"nutrient": "铬", "mechanism": "铬增强胰岛素信号；糖尿病→铬需求增加(证据有限)"},
            {"nutrient": "维生素D", "mechanism": "胰岛素抵抗与低维生素D状态相关"},
            {"nutrient": "维生素B12", "mechanism": "二甲双胍使用→B12缺乏(≥3年使用者19%缺乏率)"},
        ],
        refeeding_risk: "low",

        citations: [
            "Aroda VR et al. Diabetes Care 2016; PMID:27311490 — metformin B12",
            "Elia M et al. Clin Nutr 2005 — diabetes-specific ONS meta-analysis",
        ]
    },

    "copd": {
        icd11_code: "CB01",
        name_zh: "慢性阻塞性肺疾病",
        name_en: "COPD",
        category: "medical",

        nutrition: {
            screening: "NRS2002 + MNA-SF (significant proportion of elderly)",
            energy: "REE elevated ~15-30% due to increased work of breathing",
            carbohydrate_restriction: "Excessive CHO → increased RQ → increased CO2 production → may worsen respiratory failure",
            fat_ratio: "Higher fat (40-55% kcal) to reduce CO2 load in ventilated patients",
            protein: "1.2-1.5 g/kg to preserve respiratory muscle mass",
        },

        energy_target_kcal_kg: {"baseline": 30, "ventilated": 25},  # avoid overfeeding in ventilated
        protein_target_g_kg: {"baseline": 1.2, "severe": 1.5},

        nutrient_deficiency_risk: [
            {"nutrient": "维生素D", "mechanism": "活动受限→日照不足；COPD严重度与25-OH D负相关"},
            {"nutrient": "钙", "mechanism": "长期激素使用者→骨质疏松风险(ACR 2017 guideline)"},
            {"nutrient": "镁", "mechanism": "支气管扩张剂(β2激动剂)→细胞内镁转移？；利尿剂丢失"},
            {"nutrient": "磷", "mechanism": "呼吸肌ATP需求增加；低磷→膈肌无力→脱机困难"},
        ],
        refeeding_risk: "medium",

        citations: [
            "Schols AM et al. Am J Respir Crit Care Med 2014; PMID:25133397",
            "Collins PF et al. Thorax 2019; PMID:31266899 — ONS in COPD meta-analysis",
        ]
    },

    "sepsis": {
        icd11_code: "1C00",
        name_zh: "脓毒症",
        name_en: "Sepsis",
        category: "critical_care",

        nutrition: {
            screening: "NUTRIC score (preferred for ICU); NRS2002 valid but less specific in ICU",
            timing: "Early EN within 24-48h of ICU admission IF hemodynamically stable (not on escalating vasopressors)",
            trophic_feeding: "Start trophic EN (10-20 mL/h) in septic shock; advance when vasopressors stable/decreasing",
            pn: "Supplemental PN if EN <60% target by day 7-10; do NOT start early PN (<48h)",
            protein: "1.2-2.0 g/kg/day (ASPEN 2024); higher targets for sepsis/septic shock",
            immunonutrition: "AVOID arginine-enriched formulas in septic shock (potential harm — increased NO→vasodilation)",
            glutamine: "NOT recommended in septic shock (SIGNET trial harm signal)",
            selenium: "Selenium RCTs mixed; NOT routinely recommended (REDOXS trial negative)",
        },

        energy_target_kcal_kg: {"acute_phase": 20, "recovery": 25},  # avoid overfeeding in acute phase
        protein_target_g_kg: {"baseline": 1.5, "severe": 2.0},  # ASPEN 2024: up to 2.0 g/kg in sepsis

        nutrient_deficiency_risk: [
            {"nutrient": "维生素C", "mechanism": "氧化应激消耗→维生素C快速消耗；CITRIS-ALI/HYPRESS等RCT结果不一"},
            {"nutrient": "维生素D", "mechanism": "危重病→维生素D结合蛋白减少→25-OH D急剧下降"},
            {"nutrient": "锌", "mechanism": "急性期反应→锌重分布(细胞内) + 尿排泄增加"},
            {"nutrient": "硒", "mechanism": "GPX抗氧化消耗→硒水平降低；REDOXS trial: 高剂量硒无益"},
            {"nutrient": "谷氨酰胺", "mechanism": "肌肉谷氨酰胺储备急剧消耗；SIGNET trial: 高剂量可能有害"},
        ],
        refeeding_risk: "high",  # ICU patients = high refeeding risk

        citations: [
            "Singer P et al. Clin Nutr 2023; PMID:37084772 — ESPEN ICU guideline",
            "Compher C et al. JPEN 2022; PMID:34784036 — ASPEN critical care guideline",
            "Heyland D et al. N Engl J Med 2013; PMID:23635090 — REDOXS trial (glutamine/selenium)",
        ]
    },

    "cirrhosis": {
        icd11_code: "5C50",
        name_zh: "肝硬化",
        name_en: "Cirrhosis",
        category: "medical",

        nutrition: {
            screening: "NRS2002 + liver-specific (SGA + mid-arm muscle circumference + handgrip)",
            energy: "30-35 kcal/kg/day (ESPEN liver guideline 2019)",
            protein: "1.2-1.5 g/kg/day; DO NOT restrict protein — ESPEN emphasizes this STRONGLY",
            bcaa: "BCAA-enriched formulas in patients with hepatic encephalopathy refractory to lactulose/rifaximin",
            late_evening_snack: "50g CHO at bedtime prevents nocturnal catabolism",
            sodium: "<2g/day if ascites; avoid excessive restriction causing hyponatremia",
            zinc: "Zinc deficiency common → supplement if low (zinc acetate preferred)",
            thiamine: "Supplement 100mg/day for all cirrhotic patients (alcoholic or not)",
        },

        energy_target_kcal_kg: {"baseline": 30, "malnourished": 35},
        protein_target_g_kg: {"baseline": 1.2, "severe": 1.5},

        nutrient_deficiency_risk: [
            {"nutrient": "锌", "mechanism": "门体分流→锌尿排泄增加；低锌→氨解毒障碍→脑病加重"},
            {"nutrient": "硒", "mechanism": "肝功能下降→硒蛋白合成减少→抗氧化减弱"},
            {"nutrient": "维生素D", "mechanism": "25-羟化酶活性降低；胆盐分泌减少→脂溶性维生素吸收障碍"},
            {"nutrient": "硫胺素(B1)", "mechanism": "酒精→B1吸收抑制+肝储存减少→Wernicke脑病风险"},
            {"nutrient": "镁", "mechanism": "利尿剂(螺内酯/呋塞米)→肾排泄增加；酒精摄入"},
        ],
        refeeding_risk: "medium",

        citations: [
            "Plauth M et al. Clin Nutr 2019;38:485-521 — ESPEN liver disease guideline",
            "Amodio P et al. Hepatology 2013; PMID:23707592 — hepatic encephalopathy nutrition",
        ]
    },

    "stroke": {
        icd11_code: "8B20",
        name_zh: "脑卒中",
        name_en: "Stroke",
        category: "medical",

        nutrition: {
            screening: "NRS2002 + dysphagia screening (water swallow test → FEES/VFSS if failed)",
            en: "Early EN (within 24-72h) if dysphagic; nasogastric tube standard",
            peg: "PEG if EN needed >4 weeks (ASPEN guideline)",
            protein: 1.2,
            energy: 25,
        },

        energy_target_kcal_kg: {"baseline": 25, "acute": 20},
        protein_target_g_kg: {"baseline": 1.2},

        nutrient_deficiency_risk: [
            {"nutrient": "维生素D", "mechanism": "卒中前→低D与卒中风险正相关；卒中后→制动→日照不足"},
            {"nutrient": "叶酸/B12/B6", "mechanism": "高同型半胱氨酸是卒中独立风险因子→B族补充可能降低复发"}
        ],
        refeeding_risk: "low",

        citations: [
            "Dennis M et al. Lancet 2005; PMID:15766937 — FOOD trial (EN timing in stroke)",
        ]
    },
}
