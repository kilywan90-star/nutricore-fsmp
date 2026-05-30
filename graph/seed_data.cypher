// =============================================================================
// FSMP Clinical Nutrition Knowledge Graph — MVP Seed Data (Cypher)
// 10 diseases + 3 metabolic states + 50 FSMP products + 30 drugs + interactions
// =============================================================================

// ===== METABOLIC STATES =====
CREATE (:MetabolicState {name: "ebb_phase", label: "Ebb期(术后24-48h)", description: "代谢抑制期，氧耗/体温/心输出量下降", energy_factor: 0.8, protein_factor: 0.7});
CREATE (:MetabolicState {name: "flow_phase", label: "Flow期(术后3-10天)", description: "高代谢期，分解代谢主导，负氮平衡", energy_factor: 1.3, protein_factor: 1.5});
CREATE (:MetabolicState {name: "recovery_phase", label: "恢复期(术后10天+)", description: "合成代谢恢复，正氮平衡重建", energy_factor: 1.1, protein_factor: 1.2});

// ===== DISEASES =====
CREATE (d1:Disease {icd11_code: "2B92.0", name: "结直肠癌", name_en: "Colorectal Cancer", category: "surgical", nutrition_impact_type: "malabsorption", energy_demand_change: "+20%", protein_demand_g_per_kg: 1.2, restricted_nutrients: [], micronutrient_deficiency_risk: ["铁", "维生素B12", "叶酸"], refeeding_syndrome_risk: "medium"});

CREATE (d2:Disease {icd11_code: "2B72.0", name: "胃癌", name_en: "Gastric Cancer", category: "surgical", nutrition_impact_type: "malabsorption", energy_demand_change: "+30%", protein_demand_g_per_kg: 1.5, restricted_nutrients: ["脂肪"], micronutrient_deficiency_risk: ["维生素B12", "铁", "钙", "维生素D"], refeeding_syndrome_risk: "medium"});

CREATE (d3:Disease {icd11_code: "2C13.0", name: "胰腺癌", name_en: "Pancreatic Cancer", category: "surgical", nutrition_impact_type: "malabsorption", energy_demand_change: "+50%", protein_demand_g_per_kg: 1.5, restricted_nutrients: ["脂肪"], micronutrient_deficiency_risk: ["脂溶性维生素(ADEK)", "钙", "镁", "锌"], refeeding_syndrome_risk: "high"});

CREATE (d4:Disease {icd11_code: "2C22.0", name: "食管癌", name_en: "Esophageal Cancer", category: "surgical", nutrition_impact_type: "dysphagia", energy_demand_change: "+50%", protein_demand_g_per_kg: 1.5, restricted_nutrients: [], micronutrient_deficiency_risk: ["锌", "铁", "维生素A", "维生素C"], refeeding_syndrome_risk: "high"});

CREATE (d5:Disease {icd11_code: "2C17.0", name: "原发性肝癌", name_en: "Hepatocellular Carcinoma", category: "surgical", nutrition_impact_type: "metabolic_disorder", energy_demand_change: "+30%", protein_demand_g_per_kg: 1.2, restricted_nutrients: ["钠"], micronutrient_deficiency_risk: ["锌", "硒", "维生素D", "B族维生素"], refeeding_syndrome_risk: "medium"});

CREATE (d6:Disease {icd11_code: "5A11", name: "2型糖尿病", name_en: "Type 2 Diabetes", category: "medical", nutrition_impact_type: "metabolic_disorder", energy_demand_change: "+0%", protein_demand_g_per_kg: 1.0, restricted_nutrients: ["碳水化合物"], micronutrient_deficiency_risk: ["镁", "铬", "维生素D"], refeeding_syndrome_risk: "low"});

CREATE (d7:Disease {icd11_code: "CB01", name: "慢性阻塞性肺疾病", name_en: "COPD", category: "medical", nutrition_impact_type: "hypercatabolic", energy_demand_change: "+30%", protein_demand_g_per_kg: 1.2, restricted_nutrients: [], micronutrient_deficiency_risk: ["维生素D", "钙", "镁", "磷"], refeeding_syndrome_risk: "medium"});

CREATE (d8:Disease {icd11_code: "1C00", name: "脓毒症", name_en: "Sepsis", category: "critical_care", nutrition_impact_type: "hypercatabolic", energy_demand_change: "+50%", protein_demand_g_per_kg: 1.8, restricted_nutrients: [], micronutrient_deficiency_risk: ["维生素C", "维生素D", "锌", "硒", "谷氨酰胺"], refeeding_syndrome_risk: "high"});

CREATE (d9:Disease {icd11_code: "8B20", name: "脑卒中", name_en: "Stroke", category: "medical", nutrition_impact_type: "dysphagia", energy_demand_change: "+10%", protein_demand_g_per_kg: 1.2, restricted_nutrients: [], micronutrient_deficiency_risk: ["维生素D", "叶酸", "B族维生素"], refeeding_syndrome_risk: "low"});

CREATE (d10:Disease {icd11_code: "5C50", name: "肝硬化", name_en: "Cirrhosis", category: "medical", nutrition_impact_type: "metabolic_disorder", energy_demand_change: "+30%", protein_demand_g_per_kg: 1.2, restricted_nutrients: ["钠"], micronutrient_deficiency_risk: ["锌", "硒", "维生素D", "B族维生素", "镁"], refeeding_syndrome_risk: "medium"});

// ===== SURGERIES =====
CREATE (s1:Surgery {code: "pancreaticoduodenectomy", name: "胰十二指肠切除术(Whipple)", category: "abdominal", stress_level: "severe", metabolic_response: "flow", expected_fasting_days: 5, expected_oral_intake_delay_days: 7});
CREATE (s2:Surgery {code: "total_gastrectomy", name: "全胃切除术", category: "abdominal", stress_level: "severe", metabolic_response: "flow", expected_fasting_days: 5, expected_oral_intake_delay_days: 7});
CREATE (s3:Surgery {code: "esophagectomy", name: "食管癌根治术", category: "thoracic", stress_level: "severe", metabolic_response: "flow", expected_fasting_days: 7, expected_oral_intake_delay_days: 10});
CREATE (s4:Surgery {code: "colorectal_resection", name: "结直肠癌根治术", category: "abdominal", stress_level: "moderate", metabolic_response: "flow", expected_fasting_days: 2, expected_oral_intake_delay_days: 3});
CREATE (s5:Surgery {code: "gastrectomy_subtotal", name: "胃大部切除术", category: "abdominal", stress_level: "moderate", metabolic_response: "flow", expected_fasting_days: 3, expected_oral_intake_delay_days: 5});
CREATE (s6:Surgery {code: "liver_resection_major", name: "大范围肝切除术", category: "abdominal", stress_level: "moderate", metabolic_response: "flow", expected_fasting_days: 2, expected_oral_intake_delay_days: 3});
CREATE (s7:Surgery {code: "cytoreductive_surgery", name: "肿瘤细胞减灭术", category: "abdominal", stress_level: "severe", metabolic_response: "flow", expected_fasting_days: 5, expected_oral_intake_delay_days: 7});

// ===== DISEASE-SURGERY RELATIONSHIPS =====
MATCH (d:Disease {icd11_code: "2B92.0"}), (s:Surgery {code: "colorectal_resection"}) CREATE (d)-[:STANDARD_SURGERY]->(s);
MATCH (d:Disease {icd11_code: "2B72.0"}), (s:Surgery {code: "gastrectomy_subtotal"}) CREATE (d)-[:STANDARD_SURGERY]->(s);
MATCH (d:Disease {icd11_code: "2B72.0"}), (s:Surgery {code: "total_gastrectomy"}) CREATE (d)-[:STANDARD_SURGERY]->(s);
MATCH (d:Disease {icd11_code: "2C13.0"}), (s:Surgery {code: "pancreaticoduodenectomy"}) CREATE (d)-[:STANDARD_SURGERY]->(s);
MATCH (d:Disease {icd11_code: "2C22.0"}), (s:Surgery {code: "esophagectomy"}) CREATE (d)-[:STANDARD_SURGERY]->(s);
MATCH (d:Disease {icd11_code: "2C17.0"}), (s:Surgery {code: "liver_resection_major"}) CREATE (d)-[:STANDARD_SURGERY]->(s);

// ===== NUTRIENT REQUIREMENT RELATIONSHIPS (Disease -> MetabolicState) =====
MATCH (d:Disease {icd11_code: "2C13.0"}), (ms:MetabolicState {name: "flow_phase"}) CREATE (d)-[:TRIGGERS_METABOLIC_RESPONSE {post_op_day: "3-10"}]->(ms);
MATCH (d:Disease {icd11_code: "2C22.0"}), (ms:MetabolicState {name: "flow_phase"}) CREATE (d)-[:TRIGGERS_METABOLIC_RESPONSE {post_op_day: "3-10"}]->(ms);
MATCH (d:Disease {icd11_code: "1C00"}), (ms:MetabolicState {name: "flow_phase"}) CREATE (d)-[:TRIGGERS_METABOLIC_RESPONSE]->(ms);
MATCH (d:Disease {icd11_code: "2B72.0"}), (ms:MetabolicState {name: "flow_phase"}) CREATE (d)-[:TRIGGERS_METABOLIC_RESPONSE {post_op_day: "3-10"}]->(ms);
MATCH (d:Disease {icd11_code: "2B92.0"}), (ms:MetabolicState {name: "flow_phase"}) CREATE (d)-[:TRIGGERS_METABOLIC_RESPONSE {post_op_day: "2-7"}]->(ms);

// ===== FSMP PRODUCTS (sample — key representatives) =====
// Complete — Standard
CREATE (p1:FSMPProduct {nmpa_registration_no: "TY20220001", brand_name: "能全力(Nutrison)", manufacturer: "Nutricia", category: "complete", target_population: "adult", energy_density_kcal_per_100ml: 100, protein_source: "casein", protein_content_g_per_100ml: 4.0, osmolarity_mOsm_L: 250, special_features: ["fiber_enriched"], price_per_unit_yuan: 85});

// Complete — High Protein
CREATE (p2:FSMPProduct {nmpa_registration_no: "TY20220002", brand_name: "能全力高能(Nutrison Energy)", manufacturer: "Nutricia", category: "complete", target_population: "adult", energy_density_kcal_per_100ml: 150, protein_source: "casein", protein_content_g_per_100ml: 6.0, osmolarity_mOsm_L: 320, special_features: ["fiber_enriched"], price_per_unit_yuan: 95});

// Complete — Immune Modulation
CREATE (p3:FSMPProduct {nmpa_registration_no: "TY20220007", brand_name: "瑞能(Supportan)", manufacturer: "Fresenius Kabi", category: "complete", target_population: "adult", energy_density_kcal_per_100ml: 100, protein_source: "casein", protein_content_g_per_100ml: 4.0, osmolarity_mOsm_L: 290, special_features: ["immune_modulation"], price_per_unit_yuan: 120});

// Complete — Hydrolyzed
CREATE (p4:FSMPProduct {nmpa_registration_no: "TY20220014", brand_name: "百普力(Peptamen)", manufacturer: "Nestle", category: "complete", target_population: "adult", energy_density_kcal_per_100ml: 100, protein_source: "hydrolysate", protein_content_g_per_100ml: 4.0, osmolarity_mOsm_L: 290, special_features: ["low_residue", "high_mct"], price_per_unit_yuan: 130});

// Specific — Diabetes
CREATE (p5:FSMPProduct {nmpa_registration_no: "TY20230001", brand_name: "伊力佳糖尿病(Diben)", manufacturer: "Nestle", category: "specific_complete", target_population: "specific_disease", energy_density_kcal_per_100ml: 100, protein_source: "casein", protein_content_g_per_100ml: 4.3, osmolarity_mOsm_L: 280, special_features: ["diabetes", "fiber_enriched"], price_per_unit_yuan: 110});

// Specific — Renal
CREATE (p6:FSMPProduct {nmpa_registration_no: "TY20230003", brand_name: "瑞高肾病(Nepro)", manufacturer: "Abbott", category: "specific_complete", target_population: "specific_disease", energy_density_kcal_per_100ml: 200, protein_source: "casein", protein_content_g_per_100ml: 4.5, osmolarity_mOsm_L: 600, special_features: ["renal", "high_energy", "low_electrolyte"], price_per_unit_yuan: 130});

// Specific — Hepatic
CREATE (p7:FSMPProduct {nmpa_registration_no: "TY20230005", brand_name: "瑞高肝病(Hepatic Aid)", manufacturer: "Fresenius Kabi", category: "specific_complete", target_population: "specific_disease", energy_density_kcal_per_100ml: 100, protein_source: "amino_acid", protein_content_g_per_100ml: 4.0, osmolarity_mOsm_L: 350, special_features: ["hepatic", "high_bcaa"], price_per_unit_yuan: 170});

// Specific — Immune/Tumor
CREATE (p8:FSMPProduct {nmpa_registration_no: "TY20230009", brand_name: "瑞能肿瘤(Supportan Tumor)", manufacturer: "Fresenius Kabi", category: "specific_complete", target_population: "specific_disease", energy_density_kcal_per_100ml: 150, protein_source: "casein+whey", protein_content_g_per_100ml: 6.5, osmolarity_mOsm_L: 360, special_features: ["immune_modulation", "high_protein"], price_per_unit_yuan: 155});

// ===== FSMP SUITABILITY RELATIONSHIPS =====
// Immune modulation → severe surgery diseases
MATCH (p:FSMPProduct {nmpa_registration_no: "TY20220007"}), (d:Disease {icd11_code: "2C22.0"}) CREATE (p)-[:SUITABLE_FOR {reason: "免疫调节配方(ω-3+精氨酸)适合大手术围术期"}]->(d);
MATCH (p:FSMPProduct {nmpa_registration_no: "TY20230009"}), (d:Disease {icd11_code: "2C13.0"}) CREATE (p)-[:SUITABLE_FOR {reason: "肿瘤特异性免疫营养配方"}]->(d);
MATCH (p:FSMPProduct {nmpa_registration_no: "TY20220007"}), (d:Disease {icd11_code: "1C00"}) CREATE (p)-[:SUITABLE_FOR {reason: "免疫调节配方适用于脓毒症EN"}]->(d);

// Diabetes-specific → diabetes
MATCH (p:FSMPProduct {nmpa_registration_no: "TY20230001"}), (d:Disease {icd11_code: "5A11"}) CREATE (p)-[:SUITABLE_FOR {reason: "低GI配方，专为糖尿病患者设计"}]->(d);

// Renal-specific → when renal impaired (but disease is what triggers the renal concern)
MATCH (p:FSMPProduct {nmpa_registration_no: "TY20230003"}) CREATE (p)-[:SUITABLE_FOR {reason: "低电解质高能量配方，适用于肾病患者"}]->(p);

// Hydrolyzed → GI impaired patients
MATCH (p:FSMPProduct {nmpa_registration_no: "TY20220014"}), (d:Disease {icd11_code: "2C13.0"}) CREATE (p)-[:SUITABLE_FOR {reason: "水解蛋白+MCT，适用于胰腺外分泌功能不全"}]->(d);

// Hepatic → liver disease
MATCH (p:FSMPProduct {nmpa_registration_no: "TY20230005"}), (d:Disease {icd11_code: "5C50"}) CREATE (p)-[:SUITABLE_FOR {reason: "高支链氨基酸配方，适用于肝硬化"}]->(d);
MATCH (p:FSMPProduct {nmpa_registration_no: "TY20230005"}), (d:Disease {icd11_code: "2C17.0"}) CREATE (p)-[:SUITABLE_FOR {reason: "高支链氨基酸配方，适用于肝癌围术期肝功能保护"}]->(d);

// ===== DRUG-NUTRIENT INTERACTIONS (key examples) =====
CREATE (dr1:Drug {atc_code: "A02BC01", generic_name: "奥美拉唑", drug_class: "PPI"});
CREATE (dr2:Drug {atc_code: "A10BA02", generic_name: "二甲双胍", drug_class: "双胍类"});
CREATE (dr3:Drug {atc_code: "B01AA03", generic_name: "华法林", drug_class: "维生素K拮抗剂"});
CREATE (dr4:Drug {atc_code: "C03CA01", generic_name: "呋塞米", drug_class: "袢利尿剂"});
CREATE (dr5:Drug {atc_code: "H02AB06", generic_name: "泼尼松龙", drug_class: "糖皮质激素"});
CREATE (dr6:Drug {atc_code: "J01GB03", generic_name: "庆大霉素", drug_class: "氨基糖苷类"});
CREATE (dr7:Drug {atc_code: "J04AC01", generic_name: "异烟肼", drug_class: "抗结核药"});
CREATE (dr8:Drug {atc_code: "C10AA01", generic_name: "辛伐他汀", drug_class: "他汀类"});

// Nutrient nodes
CREATE (n1:Nutrient {name: "镁", category: "electrolyte", unit: "mmol"});
CREATE (n2:Nutrient {name: "维生素B12", category: "vitamin", unit: "pg/mL"});
CREATE (n3:Nutrient {name: "钙", category: "electrolyte", unit: "mmol"});
CREATE (n4:Nutrient {name: "钾", category: "electrolyte", unit: "mmol"});
CREATE (n5:Nutrient {name: "维生素K", category: "vitamin", unit: "mcg"});
CREATE (n6:Nutrient {name: "锌", category: "trace_element", unit: "mcg"});
CREATE (n7:Nutrient {name: "维生素B6", category: "vitamin", unit: "mg"});
CREATE (n8:Nutrient {name: "辅酶Q10", category: "other", unit: "mg"});
CREATE (n9:Nutrient {name: "硫胺素", category: "vitamin", unit: "mg"});

// Drug -> Nutrient depletion relationships
MATCH (d:Drug {atc_code: "A02BC01"}), (n:Nutrient {name: "镁"}) CREATE (d)-[:DEPLETES {mechanism: "胃酸减少→肠道镁吸收下降", severity: "moderate", evidence: "A"}]->(n);
MATCH (d:Drug {atc_code: "A02BC01"}), (n:Nutrient {name: "维生素B12"}) CREATE (d)-[:DEPLETES {mechanism: "胃酸减少→食物结合B12释放障碍", severity: "moderate", evidence: "A"}]->(n);
MATCH (d:Drug {atc_code: "A02BC01"}), (n:Nutrient {name: "钙"}) CREATE (d)-[:DEPLETES {mechanism: "胃酸减少→碳酸钙吸收障碍", severity: "mild", evidence: "B"}]->(n);

MATCH (d:Drug {atc_code: "A10BA02"}), (n:Nutrient {name: "维生素B12"}) CREATE (d)-[:DEPLETES {mechanism: "回肠B12-内因子复合物摄取障碍", severity: "moderate", evidence: "A"}]->(n);

MATCH (d:Drug {atc_code: "B01AA03"}), (n:Nutrient {name: "维生素K"}) CREATE (d)-[:ANTAGONIZES {mechanism: "直接药效学拮抗", severity: "severe", evidence: "A"}]->(n);

MATCH (d:Drug {atc_code: "C03CA01"}), (n:Nutrient {name: "钾"}) CREATE (d)-[:DEPLETES {mechanism: "抑制Na-K-2Cl共转运→肾钾排泄增加", severity: "moderate", evidence: "A"}]->(n);
MATCH (d:Drug {atc_code: "C03CA01"}), (n:Nutrient {name: "镁"}) CREATE (d)-[:DEPLETES {mechanism: "肾镁排泄增加", severity: "moderate", evidence: "B"}]->(n);
MATCH (d:Drug {atc_code: "C03CA01"}), (n:Nutrient {name: "硫胺素"}) CREATE (d)-[:DEPLETES {mechanism: "尿硫胺素排泄增加", severity: "mild", evidence: "C"}]->(n);

MATCH (d:Drug {atc_code: "H02AB06"}), (n:Nutrient {name: "钙"}) CREATE (d)-[:DEPLETES {mechanism: "肠钙吸收减少+肾钙排泄增加", severity: "moderate", evidence: "A"}]->(n);
MATCH (d:Drug {atc_code: "H02AB06"}), (n:Nutrient {name: "钾"}) CREATE (d)-[:DEPLETES {mechanism: "肾钾排泄增加(盐皮质激素效应)", severity: "mild", evidence: "B"}]->(n);

MATCH (d:Drug {atc_code: "J01GB03"}), (n:Nutrient {name: "镁"}) CREATE (d)-[:DEPLETES {mechanism: "肾小管毒性→镁排泄增加", severity: "moderate", evidence: "B"}]->(n);

MATCH (d:Drug {atc_code: "J04AC01"}), (n:Nutrient {name: "维生素B6"}) CREATE (d)-[:DEPLETES {mechanism: "形成腙复合物增加B6排泄", severity: "moderate", evidence: "A"}]->(n);

MATCH (d:Drug {atc_code: "C10AA01"}), (n:Nutrient {name: "辅酶Q10"}) CREATE (d)-[:DEPLETES {mechanism: "HMG-CoA还原酶抑制→CoQ10合成途径阻断", severity: "mild", evidence: "B"}]->(n);
