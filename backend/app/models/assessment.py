from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class PatientInfo(BaseModel):
    age: int
    gender: str  # male / female
    height_cm: float
    weight_kg: float
    bmi: float = 0


class NutritionScreeningInput(BaseModel):
    patient: PatientInfo
    disease_icd11_code: str = ""
    surgery_code: Optional[str] = None
    post_op_day: int = 0
    weight_loss_3m_kg: float = 0  # weight loss in last 3 months
    food_intake_reduction_pct: float = 0  # % reduction in food intake last week
    alb_g_L: Optional[float] = None  # albumin g/L
    prealb_mg_L: Optional[float] = None  # prealbumin mg/L
    comorbidities: list[str] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)  # ATC codes
    gi_function: str = "normal"  # normal / impaired / non_functional
    swallowing_function: str = "normal"  # normal / impaired / unsafe
    renal_function: str = "normal"  # normal / impaired / dialysis
    liver_function: str = "normal"  # normal / impaired / failure


class NRS2002Result(BaseModel):
    score: int  # 0-7
    risk_level: str  # low / medium / high
    breakdown: dict[str, int] = Field(default_factory=dict)
    triggers_intervention: bool  # score >= 3


class NutritionPathway(BaseModel):
    route: str  # ONS / EN / PN / mixed
    rationale: str
    target_energy_kcal_per_day: float
    target_protein_g_per_day: float
    target_fluid_ml_per_day: float = 2000
    feeding_schedule: str = ""


class NutritionPlanOutput(BaseModel):
    screening: NRS2002Result
    pathway: NutritionPathway
    energy_breakdown: dict[str, float] = Field(default_factory=dict)
    protein_target_rationale: str = ""
    micronutrient_concerns: list[str] = Field(default_factory=list)
    refeeding_risk_warning: Optional[str] = None
    monitoring_plan: list[str] = Field(default_factory=list)
    product_matches: list = Field(default_factory=list)  # list[FSMPProductMatch]
    drug_interactions: list = Field(default_factory=list)  # list[DrugNutrientInteraction]
