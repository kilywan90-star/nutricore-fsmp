from fastapi import APIRouter, Query

from ..models.drug import DrugNutrientInteraction
from ..engine.drug_interaction import check_interactions

router = APIRouter()


@router.post("/check", response_model=list[DrugNutrientInteraction])
async def check_drug_nutrient_interactions(
    atc_codes: list[str] = Query(default_factory=list),
):
    """Check drug-nutrient interactions for a list of ATC codes."""
    return check_interactions(atc_codes)


@router.get("/drugs")
async def list_monitored_drugs():
    """List drugs with known significant nutrient interactions."""
    return {
        "drugs": [
            {
                "atc": "A02BC01",
                "name": "奥美拉唑 (PPI类)",
                "depletes": ["镁", "维生素B12", "钙"],
                "advice": "长期使用者每年监测B12+Mg; 钙改用柠檬酸钙",
            },
            {
                "atc": "A10BA02",
                "name": "二甲双胍",
                "depletes": ["维生素B12"],
                "advice": "每年监测B12; 缺乏者补充口服B12",
            },
            {
                "atc": "B01AA03",
                "name": "华法林",
                "interacts": ["维生素K"],
                "advice": "保持维生素K摄入稳定; 避免大量绿叶蔬菜突变",
            },
            {
                "atc": "C03CA01",
                "name": "呋塞米 (袢利尿剂)",
                "depletes": ["钾", "镁", "硫胺素"],
                "advice": "监测K+/Mg2+; 长期大剂量补充硫胺素",
            },
            {
                "atc": "H02AB06",
                "name": "泼尼松龙 (糖皮质激素)",
                "depletes": ["钙", "钾"],
                "advice": "疗程>3月者补充钙+维生素D",
            },
            {
                "atc": "C09AA02",
                "name": "依那普利 (ACEI)",
                "depletes": ["锌"],
                "advice": "锌缺乏症状出现时补充",
            },
            {
                "atc": "J01GB03",
                "name": "庆大霉素 (氨基糖苷类)",
                "depletes": ["镁"],
                "advice": "疗程中监测Mg2+水平",
            },
            {
                "atc": "J04AC01",
                "name": "异烟肼",
                "depletes": ["维生素B6"],
                "advice": "常规补充B6 10-50mg/日",
            },
            {
                "atc": "C10AA01",
                "name": "辛伐他汀 (他汀类)",
                "depletes": ["辅酶Q10"],
                "advice": "肌痛症状出现时考虑补充CoQ10",
            },
        ]
    }
