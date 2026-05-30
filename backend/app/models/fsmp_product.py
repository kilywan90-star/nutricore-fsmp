from __future__ import annotations

from pydantic import BaseModel, Field


class FSMPProductBase(BaseModel):
    nmpa_registration_no: str  # 国食注字TY2025XXXXX
    brand_name: str
    manufacturer: str
    category: str  # complete / specific_complete / incomplete / modular
    target_population: str  # 1-10 / 10+/ adult / specific_disease
    energy_density_kcal_per_100ml: float
    protein_source: str  # whey / casein / soy / amino_acid / hydrolysate
    protein_content_g_per_100ml: float
    carb_source: str
    fat_source: str  # MCT / LCT / fish_oil / mixed
    fiber_content_g_per_100ml: float = 0
    osmolarity_mOsm_L: int = 300
    special_features: list[str] = Field(default_factory=list)
    contraindications: list[str] = Field(default_factory=list)
    price_per_unit_yuan: float = 0
    unit_size_ml: int = 500
    hospital_channel: str = ""  # tender / spot_purchase
    insurance_coverage: bool = False


class FSMPProduct(FSMPProductBase):
    pass


class FSMPProductMatch(BaseModel):
    product: FSMPProduct
    match_score: float  # 0-100
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    match_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
