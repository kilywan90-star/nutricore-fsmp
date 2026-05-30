from __future__ import annotations

from pydantic import BaseModel, Field


class NutrientBase(BaseModel):
    name: str
    category: str  # macronutrient / micronutrient / trace_element / vitamin / electrolyte
    unit: str  # g / mg / mcg / IU
    rda_adult: float = 0  # recommended daily allowance for adult


class Nutrient(NutrientBase):
    pass


class NutrientDemand(BaseModel):
    nutrient: Nutrient
    baseline_demand: float
    disease_adjusted_demand: float
    adjustment_factor: float
    reason: str = ""
