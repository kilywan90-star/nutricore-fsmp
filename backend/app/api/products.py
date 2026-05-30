from fastapi import APIRouter, Query

from ..seed.fsmp_products import get_mvp_products
from ..models.fsmp_product import FSMPProduct

router = APIRouter()


@router.get("/", response_model=list[FSMPProduct])
async def list_products(
    category: str | None = Query(None, description="complete/specific_complete/incomplete/modular"),
    target_population: str | None = Query(None, description="1-10/10+/adult/specific_disease"),
    feature: str | None = Query(None, description="diabetes/renal/hepatic/immune_modulation/high_mct"),
):
    """List available FSMP products with optional filtering."""
    products = get_mvp_products()

    if category:
        products = [p for p in products if p.category == category]
    if target_population:
        products = [p for p in products if p.target_population == target_population]
    if feature:
        products = [p for p in products if feature in p.special_features]

    return products


@router.get("/categories")
async def list_categories():
    """List FSMP product categories with descriptions."""
    return [
        {
            "category": "complete",
            "label": "全营养配方",
            "description": "可作为单一营养来源的全营养配方食品",
        },
        {
            "category": "specific_complete",
            "label": "特定全营养配方",
            "description": "针对特定疾病或医学状态人群的全营养配方食品",
        },
        {
            "category": "incomplete",
            "label": "非全营养配方",
            "description": "需与其他食品配合使用的营养组件或配方食品",
        },
        {
            "category": "modular",
            "label": "组件制剂",
            "description": "蛋白质组件、脂肪组件、碳水化合物组件等模块化产品",
        },
    ]
