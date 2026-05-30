"""
Authoritative Drug-Nutrient Interaction Knowledge Base
Compiled from: Natural Medicines Comprehensive Database, Lexicomp, PubMed systematic reviews.

Citation format: [Author, Journal Year;PMID]
Evidence grades: A = multiple RCTs/meta-analysis; B = observational/controlled studies; C = case reports; D = expert opinion
"""

from ..engine.drug_interaction import DRUG_NUTRIENT_INTERACTIONS

# Extended with PubMed citations and clinical significance
AUTHORITATIVE_INTERACTIONS = {
    # ==================== Proton Pump Inhibitors ====================
    "PPI": {
        "class": "Proton Pump Inhibitors",
        "atc_codes": ["A02BC01", "A02BC02", "A02BC03", "A02BC04", "A02BC05"],
        "generic_names": ["奥美拉唑", "兰索拉唑", "泮托拉唑", "雷贝拉唑", "埃索美拉唑"],
        "interactions": [
            {
                "nutrient": "Magnesium",
                "nutrient_zh": "镁",
                "mechanism": "Reduced intestinal absorption due to elevated gastric pH; TRPM6/7 channel dysfunction",
                "severity": "moderate",
                "evidence_grade": "A",
                "onset": "≥1 year of continuous use",
                "monitoring": "Serum Mg q6-12 months in long-term users",
                "intervention": "Oral Mg supplementation; switch to Mg citrate (better absorption in achlorhydria)",
                "citations": [
                    "FDA Drug Safety Communication 2011; PMID:21412881",
                    "Hess MW et al. Biochim Biophys Acta 2013; PMID:23313294",
                    "Cheungpasitporn W et al. Ren Fail 2015; PMID:25942395 — meta-analysis: PPI use 1.43x increased hypomagnesemia risk"
                ]
            },
            {
                "nutrient": "Vitamin B12",
                "nutrient_zh": "维生素B12",
                "mechanism": "Impaired release of food-bound B12 due to hypochlorhydria; reduced intrinsic factor binding",
                "severity": "moderate",
                "evidence_grade": "A",
                "onset": "≥2 years of continuous use",
                "monitoring": "Serum B12 annually; methylmalonic acid if borderline",
                "intervention": "Oral cyanocobalamin 1000mcg/day or IM B12 if deficient",
                "citations": [
                    "Lam JR et al. JAMA 2013; PMID:24327026 — n=25956, PPI use associated with B12 deficiency (OR 1.65)",
                    "Jung SB et al. J Am Geriatr Soc 2015; PMID:25655983"
                ]
            },
            {
                "nutrient": "Calcium",
                "nutrient_zh": "钙",
                "mechanism": "Reduced absorption of calcium carbonate in hypochlorhydric state; possible PTH elevation",
                "severity": "mild",
                "evidence_grade": "B",
                "onset": "≥1 year of continuous use",
                "monitoring": "DEXA scan if other risk factors; serum Ca not reliable",
                "intervention": "Use calcium citrate instead of carbonate",
                "citations": [
                    "Khalili H et al. BMJ 2012; PMID:22290211 — n=79900, PPI use associated with hip fracture risk",
                    "Freedberg DE et al. Gastroenterology 2017; PMID:27065984"
                ]
            },
            {
                "nutrient": "Iron",
                "nutrient_zh": "铁",
                "mechanism": "Reduced non-heme iron absorption in elevated gastric pH",
                "severity": "mild",
                "evidence_grade": "B",
                "onset": "≥6 months",
                "monitoring": "CBC, ferritin if anemia symptoms",
                "intervention": "Iron supplementation if deficient; heme iron absorption unaffected",
                "citations": [
                    "Hutchinson C et al. Aliment Pharmacol Ther 2007; PMID:17635377"
                ]
            }
        ]
    },

    # ==================== Metformin ====================
    "Metformin": {
        "class": "Biguanide",
        "atc_codes": ["A10BA02"],
        "generic_names": ["二甲双胍"],
        "interactions": [
            {
                "nutrient": "Vitamin B12",
                "nutrient_zh": "维生素B12",
                "mechanism": "Altered ileal B12-intrinsic factor complex uptake (calcium-dependent mechanism); bacterial overgrowth → B12 consumption",
                "severity": "moderate",
                "evidence_grade": "A",
                "onset": "≥3-5 years of use; dose and duration dependent",
                "monitoring": "Serum B12 + MMA annually; more frequent if dose >1500mg/day",
                "intervention": "Oral B12 1000mcg/day; calcium supplementation may partially reverse malabsorption",
                "citations": [
                    "Aroda VR et al. Diabetes Care 2016; PMID:27311490 — DPP/DPPOS n=1750, metformin use → 13% B12 deficiency vs 5% placebo",
                    "Chapman LE et al. J Clin Endocrinol Metab 2016; PMID:27082755 — meta-analysis: metformin reduces B12 by 57.5 pmol/L",
                    "de Jager J et al. BMJ 2010; PMID:20488943 — RCT n=390, 4.3yr metformin → 19% B12 deficiency"
                ]
            },
            {
                "nutrient": "Coenzyme Q10",
                "nutrient_zh": "辅酶Q10",
                "mechanism": "HMG-CoA reductase-like pathway inhibition; mitochondrial complex I inhibition",
                "severity": "mild",
                "evidence_grade": "C",
                "monitoring": "Not routine; consider if fatigue/muscle weakness",
                "intervention": "CoQ10 100-200mg/day if symptomatic",
                "citations": [
                    "Madiraju AK et al. Nature 2014; PMID:24898544"
                ]
            }
        ]
    },

    # ==================== Warfarin ====================
    "Warfarin": {
        "class": "Vitamin K Antagonist",
        "atc_codes": ["B01AA03"],
        "generic_names": ["华法林"],
        "interactions": [
            {
                "nutrient": "Vitamin K",
                "nutrient_zh": "维生素K",
                "mechanism": "Direct pharmacodynamic antagonism — vitamin K epoxide reductase inhibition reversed by dietary K1",
                "severity": "severe",
                "evidence_grade": "A",
                "onset": "Immediate (hours-days)",
                "monitoring": "INR: daily during dose adjustment, then weekly, then monthly",
                "intervention": "NEVER avoid vitamin K entirely; maintain CONSISTENT daily intake (90-120mcg/day); avoid sudden large changes in leafy greens",
                "citations": [
                    "Holbrook AM et al. Arch Intern Med 2005; PMID:15851696 — systematic review of warfarin interactions",
                    "Khan T et al. J Thromb Haemost 2004; PMID:15005793",
                    "Rohde LE et al. Am J Clin Nutr 2007; PMID:17284744"
                ]
            },
            {
                "nutrient": "Enteral Nutrition",
                "nutrient_zh": "肠内营养",
                "mechanism": "FSMP contains vitamin K (especially soy-based formulas); variable content → INR fluctuation",
                "severity": "moderate",
                "evidence_grade": "B",
                "monitoring": "INR at FSMP initiation and each formula change",
                "intervention": "Maintain consistent FSMP brand/formula; avoid soy-based products; document K content in formula",
                "citations": [
                    "Dickerson RN et al. Pharmacotherapy 2008; PMID:18294107"
                ]
            }
        ]
    },

    # ==================== Loop Diuretics ====================
    "Loop_Diuretic": {
        "class": "Loop Diuretic",
        "atc_codes": ["C03CA01", "C03CA02"],
        "generic_names": ["呋塞米", "布美他尼"],
        "interactions": [
            {
                "nutrient": "Potassium",
                "nutrient_zh": "钾",
                "mechanism": "Inhibition of Na-K-2Cl cotransporter in thick ascending limb → increased K+ excretion",
                "severity": "moderate",
                "evidence_grade": "A",
                "onset": "Hours to days",
                "monitoring": "Serum K+ at baseline, day 3-5, then weekly until stable; ECG if K+ <3.0 mmol/L",
                "intervention": "K+ supplementation or K-sparing diuretic (spironolactone/eplerenone); target K+ 4.0-5.0",
                "citations": [
                    "Cohn JN et al. Am Heart J 2000; PMID:10874278",
                    "Krum H et al. Circulation 2003; PMID:12743004"
                ]
            },
            {
                "nutrient": "Magnesium",
                "nutrient_zh": "镁",
                "mechanism": "Increased renal Mg2+ wasting via inhibition of Mg reabsorption in DCT",
                "severity": "moderate",
                "evidence_grade": "B",
                "onset": "Days to weeks",
                "monitoring": "Serum Mg2+ every 3 months; target >0.7 mmol/L",
                "intervention": "Mg supplementation (Mg citrate 200-400mg/day); if hypokalemic + hypomagnesemic → correct Mg FIRST",
                "citations": [
                    "al-Ghamdi SM et al. Nephrol Dial Transplant 1994; PMID:7845315",
                    "Quamme GA. Kidney Int 1997; PMID:9186883"
                ]
            },
            {
                "nutrient": "Thiamine",
                "nutrient_zh": "硫胺素(维生素B1)",
                "mechanism": "Increased urinary thiamine excretion; potential cardiomyopathy in CHF patients",
                "severity": "mild",
                "evidence_grade": "C",
                "onset": "Weeks to months (high-dose, long-term)",
                "monitoring": "Not routine; consider in long-term high-dose + CHF",
                "intervention": "Thiamine 100mg/day if CHF + high-dose furosemide (>80mg/day)",
                "citations": [
                    "Hanninen SA et al. J Card Fail 2006; PMID:16385063",
                    "Sica DA. Congest Heart Fail 2007; PMID:17917596"
                ]
            }
        ]
    },

    # ==================== Corticosteroids ====================
    "Corticosteroid": {
        "class": "Glucocorticoid",
        "atc_codes": ["H02AB06", "H02AB07"],
        "generic_names": ["泼尼松龙", "甲泼尼龙"],
        "interactions": [
            {
                "nutrient": "Calcium",
                "nutrient_zh": "钙",
                "mechanism": "Decreased intestinal calcium absorption + increased renal calcium excretion + RANKL activation → bone resorption",
                "severity": "moderate",
                "evidence_grade": "A",
                "onset": "≥3 months continuous use; rapid bone loss in first 6 months",
                "monitoring": "DEXA at baseline if course >3 months expected; then every 1-2 years",
                "intervention": "Calcium 1000-1200mg/day + Vitamin D3 800-2000 IU/day; bisphosphonate if high fracture risk",
                "citations": [
                    "van Staa TP et al. J Bone Miner Res 2000; PMID:10841169",
                    "Grossman JM et al. Arthritis Care Res 2010; PMID:20890959 — ACR guidelines",
                    "Buckley L et al. Arthritis Rheumatol 2017; PMID:28685780 — ACR 2017 glucocorticoid-induced osteoporosis guideline"
                ]
            },
            {
                "nutrient": "Potassium",
                "nutrient_zh": "钾",
                "mechanism": "Mineralocorticoid receptor activation → increased renal K+ excretion (minor effect at therapeutic doses)",
                "severity": "mild",
                "evidence_grade": "B",
                "monitoring": "Serum K+ if symptoms of hypokalemia",
                "intervention": "K-rich diet; supplement only if confirmed low",
                "citations": [
                    "Schultheiss UT et al. Steroids 2016; PMID:27292795"
                ]
            },
            {
                "nutrient": "Vitamin D",
                "nutrient_zh": "维生素D",
                "mechanism": "Glucocorticoids increase vitamin D catabolism (CYP3A4 induction → 24-hydroxylase upregulation)",
                "severity": "moderate",
                "evidence_grade": "B",
                "monitoring": "25-OH Vitamin D at baseline; target >30 ng/mL",
                "intervention": "Vitamin D3 800-2000 IU/day; higher doses if deficient",
                "citations": [
                    "Skversky AL et al. J Clin Endocrinol Metab 2011; PMID:21917866"
                ]
            }
        ]
    },

    # ==================== Statins ====================
    "Statin": {
        "class": "HMG-CoA Reductase Inhibitor",
        "atc_codes": ["C10AA01", "C10AA05", "C10AA07"],
        "generic_names": ["辛伐他汀", "阿托伐他汀", "瑞舒伐他汀"],
        "interactions": [
            {
                "nutrient": "Coenzyme Q10",
                "nutrient_zh": "辅酶Q10",
                "mechanism": "HMG-CoA reductase inhibition blocks mevalonate pathway → reduces endogenous CoQ10 synthesis (shared biosynthesis)",
                "severity": "mild",
                "evidence_grade": "B",
                "onset": "Weeks to months",
                "monitoring": "Not routine; consider if statin-associated muscle symptoms (SAMS)",
                "intervention": "CoQ10 100-200mg/day if SAMS; evidence for efficacy is mixed",
                "citations": [
                    "Ghirlanda G et al. J Clin Pharmacol 1993; PMID:8463434",
                    "Banach M et al. Mayo Clin Proc 2015; PMID:25257643 — meta-analysis: CoQ10 improves SAMS (SMD -0.44)",
                    "Qu H et al. J Am Heart Assoc 2018; PMID:30371340 — meta-analysis: CoQ10 reduces statin-induced myopathy"
                ]
            }
        ]
    },

    # ==================== ACE Inhibitors ====================
    "ACEI": {
        "class": "Angiotensin-Converting Enzyme Inhibitor",
        "atc_codes": ["C09AA01", "C09AA02", "C09AA03"],
        "generic_names": ["卡托普利", "依那普利", "赖诺普利"],
        "interactions": [
            {
                "nutrient": "Zinc",
                "nutrient_zh": "锌",
                "mechanism": "Thiol-containing ACEIs (captopril) chelate zinc → increased urinary Zn excretion",
                "severity": "mild",
                "evidence_grade": "C",
                "onset": "Months",
                "monitoring": "Not routine; Zn levels if unexplained taste disturbance or dermatitis",
                "intervention": "Zn supplementation 15-30mg/day if deficiency confirmed",
                "citations": [
                    "Golik A et al. Ann Pharmacother 1998; PMID:9520730"
                ]
            },
            {
                "nutrient": "Potassium",
                "nutrient_zh": "钾",
                "mechanism": "Reduced aldosterone → decreased renal K+ excretion → hyperkalemia risk",
                "severity": "moderate",
                "evidence_grade": "A",
                "onset": "Days to weeks (especially with renal impairment)",
                "monitoring": "Serum K+ at baseline, 1 week after initiation, then every 3-6 months",
                "intervention": "CAUTION with K+ supplements or K-sparing diuretics; avoid K+-rich salt substitutes",
                "citations": [
                    "Palmer BF. N Engl J Med 2004; PMID:15342813"
                ]
            }
        ]
    },

    # ==================== Aminoglycosides ====================
    "Aminoglycoside": {
        "class": "Aminoglycoside Antibiotic",
        "atc_codes": ["J01GB03", "J01GB06"],
        "generic_names": ["庆大霉素", "阿米卡星"],
        "interactions": [
            {
                "nutrient": "Magnesium",
                "nutrient_zh": "镁",
                "mechanism": "Renal tubular toxicity → impaired Mg2+ reabsorption in thick ascending limb",
                "severity": "moderate",
                "evidence_grade": "B",
                "onset": "During treatment course",
                "monitoring": "Serum Mg2+ during treatment; especially if >5 day course",
                "intervention": "Monitor and replace Mg2+ as needed; more common in elderly + renal impairment",
                "citations": [
                    "Shah GM et al. Am J Kidney Dis 1988; PMID:3341422",
                    "Swaminathan R. Clin Chem 2005; PMID:14563802"
                ]
            }
        ]
    },

    # ==================== Isoniazid ====================
    "Isoniazid": {
        "class": "Antituberculosis Agent",
        "atc_codes": ["J04AC01"],
        "generic_names": ["异烟肼"],
        "interactions": [
            {
                "nutrient": "Vitamin B6",
                "nutrient_zh": "维生素B6",
                "mechanism": "Forms hydrazone complex with pyridoxal phosphate → increased urinary excretion; inhibits pyridoxine phosphokinase",
                "severity": "moderate",
                "evidence_grade": "A",
                "onset": "Weeks to months",
                "monitoring": "Clinical monitoring for peripheral neuropathy",
                "intervention": "Routine B6 10-50mg/day during INH treatment (WHO recommendation)",
                "citations": [
                    "Snider DE. Tubercle 1980; PMID:6269279",
                    "van der Watt JJ et al. Int J Tuberc Lung Dis 2011; PMID:21740651"
                ]
            }
        ]
    },

    # ==================== Fluoroquinolones ====================
    "Fluoroquinolone": {
        "class": "Fluoroquinolone Antibiotic",
        "atc_codes": ["J01MA02", "J01MA12"],
        "generic_names": ["环丙沙星", "左氧氟沙星"],
        "interactions": [
            {
                "nutrient": "Calcium/Magnesium/Iron/Zinc",
                "nutrient_zh": "钙/镁/铁/锌 (多价阳离子)",
                "mechanism": "Chelation of fluoroquinolone with divalent/trivalent cations → reduced antibiotic absorption (30-90% reduction)",
                "severity": "moderate",
                "evidence_grade": "A",
                "onset": "Immediate (co-administration)",
                "monitoring": "Therapeutic drug monitoring not routine; clinical failure if co-administered",
                "intervention": "Separate fluoroquinolone from FSMP/enteral feeds by ≥2 hours (before) or ≥4 hours (after)",
                "citations": [
                    "Lomaestro BM et al. Antimicrob Agents Chemother 1992; PMID:1613044",
                    "Rodvold KA et al. Pharmacotherapy 2001; PMID:11784343"
                ]
            }
        ]
    },

    # ==================== Levothyroxine ====================
    "Levothyroxine": {
        "class": "Thyroid Hormone Replacement",
        "atc_codes": ["H03AA01"],
        "generic_names": ["左甲状腺素钠"],
        "interactions": [
            {
                "nutrient": "Calcium/Iron/Soy",
                "nutrient_zh": "钙/铁/大豆(肠内营养)",
                "mechanism": "Binding/chelation of levothyroxine in GI tract → reduced absorption",
                "severity": "moderate",
                "evidence_grade": "A",
                "onset": "Immediate (co-administration)",
                "monitoring": "TSH 6-8 weeks after initiating FSMP or changing formula",
                "intervention": "Administer levothyroxine on empty stomach; pause EN 30 min before and after dose; avoid soy-based FSMP",
                "citations": [
                    "Benvenga S et al. Thyroid 2008; PMID:18341479",
                    "Liel Y et al. Am J Med 2004; PMID:15193633"
                ]
            }
        ]
    }
}
