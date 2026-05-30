from fastapi import APIRouter

from ..models.assessment import NutritionScreeningInput, NutritionPlanOutput
from ..models.fsmp_product import FSMPProductMatch
from ..engine import score_nrs2002, determine_pathway, match_products, check_interactions
from ..engine import calculate_bmi
from ..seed.fsmp_products import get_mvp_products
from ..seed.drugs import get_mvp_drugs

router = APIRouter()


@router.post("/generate", response_model=NutritionPlanOutput)
async def generate_nutrition_plan(screening: NutritionScreeningInput):
    """
    Generate a complete nutrition plan for a patient.

    Steps:
    1. NRS 2002 nutrition risk screening
    2. Determine nutrition route (ONS/EN/PN/mixed)
    3. Calculate energy and protein targets
    4. Match best-fit FSMP products
    5. Check drug-nutrient interactions
    """
    if screening.patient.bmi == 0:
        screening.patient.bmi = calculate_bmi(
            screening.patient.weight_kg, screening.patient.height_cm,
        )

    # Step 1: Screening
    nrs_result = score_nrs2002(screening)

    # Step 2-3: Pathway + targets
    pathway = determine_pathway(screening)

    # Step 4: FSMP product matching
    products = get_mvp_products()
    product_matches = match_products(screening, pathway, products)

    # Step 5: Drug-nutrient interactions
    interactions = check_interactions(screening.current_medications)

    # Compile micronutrient concerns
    micronutrient_concerns = []
    if screening.liver_function != "normal":
        micronutrient_concerns.append("肝功能异常：关注锌、硒、脂溶性维生素(ADEK)水平")
    if screening.renal_function != "normal":
        micronutrient_concerns.append("肾功能异常：关注钾、磷、镁、维生素D水平")
    if screening.gi_function == "impaired":
        micronutrient_concerns.append("肠道功能受损：关注维生素B12、铁、钙吸收障碍")
    if screening.patient.age >= 65:
        micronutrient_concerns.append("老年患者：关注维生素D、钙、B12、蛋白质摄入")

    # Check refeeding risk
    refeeding_warning = None
    if screening.weight_loss_3m_kg > 5 and screening.patient.weight_kg > 0:
        loss_pct = screening.weight_loss_3m_kg / screening.patient.weight_kg * 100
        if loss_pct > 10:
            refeeding_warning = (
                f"再喂养综合征高风险（3个月体重下降{loss_pct:.0f}%）。"
                "建议起始能量10-15kcal/kg/d，缓慢递增，监测钾/磷/镁，补充硫胺素。"
            )

    # Monitoring plan
    monitoring = [
        "每日：体重、出入量",
        "第1-3天：K+, PO4, Mg2+, 血糖 (每日)",
        "第4-7天：K+, PO4, Mg2+, 血糖 (隔日)，肝功能、前白蛋白",
        "第7天：NRS2002复筛，前白蛋白，氮平衡评估",
    ]
    if screening.renal_function != "normal":
        monitoring.append("每日：肾功能(BUN, Cr), 尿量")
    if screening.liver_function != "normal":
        monitoring.append("每周：肝功能全套, 凝血功能, 血氨")

    return NutritionPlanOutput(
        screening=nrs_result,
        pathway=pathway,
        energy_breakdown={
            "carbohydrate_pct": 50,
            "protein_pct": round(pathway.target_protein_g_per_day * 4 / pathway.target_energy_kcal_per_day * 100),
            "fat_pct": 30,
        },
        protein_target_rationale=f"基于患者体重{screening.patient.weight_kg}kg，按应激状态计算目标蛋白需求",
        micronutrient_concerns=micronutrient_concerns,
        refeeding_risk_warning=refeeding_warning,
        monitoring_plan=monitoring,
        product_matches=[m.model_dump() for m in product_matches],
        drug_interactions=[i.model_dump() for i in interactions],
    )


@router.get("/protocols")
async def list_protocols():
    """List available nutrition protocols by surgery type."""
    return {
        "protocols": [
            {
                "surgery": "colorectal_resection",
                "name": "结直肠癌术后加速康复(ERAS)营养方案",
                "route": "ONS",
                "timeline": {
                    "pod0": "清流质，500-1000ml",
                    "pod1": "ONS 200ml bid + 半流质",
                    "pod2": "ONS 400ml bid + 软食",
                    "pod3": "ONS 200ml bid + 普通饮食",
                },
                "target_energy": "25-30 kcal/kg/d",
                "target_protein": "1.2-1.5 g/kg/d",
            },
            {
                "surgery": "pancreaticoduodenectomy",
                "name": "胰十二指肠切除术后营养方案",
                "route": "EN (鼻肠管)",
                "timeline": {
                    "pod0-1": "EN 10ml/h 起始，逐日递增20ml/h",
                    "pod2-3": "EN 30-50ml/h 目标量，监测腹胀/腹泻",
                    "pod4+": "经口尝试清流质，EN递减，ONS递增",
                },
                "target_energy": "25-30 kcal/kg/d (术后早期15-20)",
                "target_protein": "1.5 g/kg/d",
            },
            {
                "surgery": "total_gastrectomy",
                "name": "全胃切除术后营养方案",
                "route": "EN (空肠造口管)",
                "timeline": {
                    "pod1": "EN 10ml/h 等渗配方",
                    "pod2-3": "EN 20-30ml/h 递增",
                    "pod4-7": "EN 50-70ml/h 目标量",
                    "pod7+": "经口小量多次进食 + 夜间EN补充",
                },
                "target_energy": "25-30 kcal/kg/d",
                "target_protein": "1.5 g/kg/d",
                "special_notes": "监测倾倒综合征，少食多餐，补充B12+铁+钙",
            },
        ]
    }
