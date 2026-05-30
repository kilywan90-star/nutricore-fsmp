from __future__ import annotations

from pydantic import BaseModel, Field


class DiseaseBase(BaseModel):
    icd11_code: str
    name: str
    name_en: str = ""
    category: str  # surgical / medical / oncological / critical_care
    nutrition_impact_type: str  # hypercatabolic / malabsorption / dysphagia / metabolic_disorder / mixed
    energy_demand_change: str  # +20% / +50% / +100% / -10%
    protein_demand_g_per_kg: float  # 1.0 / 1.2 / 1.5 / 2.0
    restricted_nutrients: list[str] = Field(default_factory=list)
    micronutrient_deficiency_risk: list[str] = Field(default_factory=list)
    enteral_feeding_contraindication: bool = False
    parenteral_indication: bool = False
    refeeding_syndrome_risk: str = "low"  # low / medium / high
    description: str = ""


class Disease(DiseaseBase):
    pass


class SurgeryBase(BaseModel):
    code: str
    name: str
    category: str  # abdominal / thoracic / orthopedic / neuro / cardiac
    stress_level: str  # mild / moderate / severe
    metabolic_response: str  # ebb / flow / recovery
    expected_fasting_days: int = 0
    expected_oral_intake_delay_days: int = 0
    description: str = ""


class Surgery(SurgeryBase):
    pass
