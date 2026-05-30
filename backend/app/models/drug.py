from __future__ import annotations

from pydantic import BaseModel, Field


class DrugBase(BaseModel):
    atc_code: str
    generic_name: str
    brand_names: list[str] = Field(default_factory=list)
    drug_class: str
    indication: str = ""
    administration_route: str = "oral"  # oral / iv / im / sc / topical
    food_interaction: str = ""  # take_with_food / take_on_empty / no_restriction
    depletes_nutrients: list[dict[str, str]] = Field(default_factory=list)
    # [{"nutrient": "Zinc", "mechanism": "increased_renal_excretion"}]
    requires_nutrient_monitoring: list[str] = Field(default_factory=list)
    interacts_with_enteral_formula: bool = False
    interaction_notes: str = ""


class Drug(DrugBase):
    pass


class DrugNutrientInteraction(BaseModel):
    drug: Drug
    nutrient: str
    interaction_type: str  # depletion / malabsorption / synergism / antagonism
    mechanism: str
    severity: str  # mild / moderate / severe
    recommendation: str
    evidence_level: str  # A / B / C / D
