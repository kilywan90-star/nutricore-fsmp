from ..models.drug import Drug, DrugNutrientInteraction
from ..models.assessment import NutritionScreeningInput

# Drug-nutrient interaction knowledge base (curated from literature)
DRUG_NUTRIENT_INTERACTIONS: list[dict] = [
    # PPIs
    {
        "atc_code": "A02BC01", "drug": "Omeprazole",
        "nutrient": "Magnesium", "type": "depletion",
        "mechanism": "Reduced intestinal absorption due to elevated gastric pH",
        "severity": "moderate", "evidence": "A",
        "recommendation": "Monitor serum Mg; consider supplementation if long-term use (>1 year)",
    },
    {
        "atc_code": "A02BC01", "drug": "Omeprazole",
        "nutrient": "Vitamin B12", "type": "depletion",
        "mechanism": "Impaired release of food-bound B12 due to hypochlorhydria",
        "severity": "moderate", "evidence": "A",
        "recommendation": "Monitor B12 levels annually with long-term PPI use",
    },
    {
        "atc_code": "A02BC01", "drug": "Omeprazole",
        "nutrient": "Calcium", "type": "depletion",
        "mechanism": "Reduced absorption of calcium carbonate in hypochlorhydric state",
        "severity": "mild", "evidence": "B",
        "recommendation": "Use calcium citrate instead of carbonate; monitor bone density",
    },

    # Metformin
    {
        "atc_code": "A10BA02", "drug": "Metformin",
        "nutrient": "Vitamin B12", "type": "depletion",
        "mechanism": "Altered ileal B12-intrinsic factor complex uptake; calcium-dependent mechanism",
        "severity": "moderate", "evidence": "A",
        "recommendation": "Annual B12 monitoring; supplementation if deficient",
    },

    # Warfarin
    {
        "atc_code": "B01AA03", "drug": "Warfarin",
        "nutrient": "Vitamin K", "type": "antagonism",
        "mechanism": "Pharmacodynamic antagonism — vitamin K reverses warfarin effect",
        "severity": "severe", "evidence": "A",
        "recommendation": "Maintain consistent vitamin K intake; avoid sudden changes in leafy greens consumption",
    },

    # Corticosteroids
    {
        "atc_code": "H02AB06", "drug": "Prednisolone",
        "nutrient": "Calcium", "type": "depletion",
        "mechanism": "Decreased intestinal absorption + increased renal excretion",
        "severity": "moderate", "evidence": "A",
        "recommendation": "Calcium + Vitamin D supplementation for courses > 3 months",
    },
    {
        "atc_code": "H02AB06", "drug": "Prednisolone",
        "nutrient": "Potassium", "type": "depletion",
        "mechanism": "Increased renal potassium wasting (mineralocorticoid effect)",
        "severity": "mild", "evidence": "B",
        "recommendation": "Monitor potassium; supplement if needed",
    },

    # Loop diuretics
    {
        "atc_code": "C03CA01", "drug": "Furosemide",
        "nutrient": "Potassium", "type": "depletion",
        "mechanism": "Increased renal potassium excretion via Na-K-2Cl cotransporter inhibition",
        "severity": "moderate", "evidence": "A",
        "recommendation": "Monitor K+; supplement or co-prescribe K-sparing diuretic",
    },
    {
        "atc_code": "C03CA01", "drug": "Furosemide",
        "nutrient": "Magnesium", "type": "depletion",
        "mechanism": "Increased renal magnesium wasting",
        "severity": "moderate", "evidence": "B",
        "recommendation": "Monitor Mg; supplement if < 0.7 mmol/L",
    },
    {
        "atc_code": "C03CA01", "drug": "Furosemide",
        "nutrient": "Thiamine", "type": "depletion",
        "mechanism": "Increased urinary thiamine excretion",
        "severity": "mild", "evidence": "C",
        "recommendation": "Consider thiamine in long-term high-dose diuretic therapy",
    },

    # ACE inhibitors
    {
        "atc_code": "C09AA02", "drug": "Enalapril",
        "nutrient": "Zinc", "type": "depletion",
        "mechanism": "Increased urinary zinc excretion (ACE inhibitors contain thiol groups that chelate zinc)",
        "severity": "mild", "evidence": "C",
        "recommendation": "Zinc-rich diet; supplement if deficiency symptoms present",
    },

    # Statins
    {
        "atc_code": "C10AA01", "drug": "Simvastatin",
        "nutrient": "Coenzyme Q10", "type": "depletion",
        "mechanism": "HMG-CoA reductase inhibition blocks CoQ10 synthesis pathway",
        "severity": "mild", "evidence": "B",
        "recommendation": "Consider CoQ10 supplementation if myopathy symptoms present",
    },

    # Gentamicin / aminoglycosides
    {
        "atc_code": "J01GB03", "drug": "Gentamicin",
        "nutrient": "Magnesium", "type": "depletion",
        "mechanism": "Renal tubular toxicity → increased Mg wasting",
        "severity": "moderate", "evidence": "B",
        "recommendation": "Monitor Mg during treatment course",
    },

    # Isoniazid
    {
        "atc_code": "J04AC01", "drug": "Isoniazid",
        "nutrient": "Vitamin B6", "type": "depletion",
        "mechanism": "Forms hydrazone complex with pyridoxal, increasing excretion",
        "severity": "moderate", "evidence": "A",
        "recommendation": "Routine B6 supplementation (10-50mg/day) during treatment",
    },
]


def check_interactions(medication_atc_codes: list[str]) -> list[DrugNutrientInteraction]:
    """Check drug-nutrient interactions for a list of medications."""
    results = []
    for code in medication_atc_codes:
        for entry in DRUG_NUTRIENT_INTERACTIONS:
            if entry["atc_code"] == code:
                results.append(DrugNutrientInteraction(
                    drug=Drug(
                        atc_code=entry["atc_code"],
                        generic_name=entry["drug"],
                        drug_class="",
                    ),
                    nutrient=entry["nutrient"],
                    interaction_type=entry["type"],
                    mechanism=entry["mechanism"],
                    severity=entry["severity"],
                    recommendation=entry["recommendation"],
                    evidence_level=entry["evidence"],
                ))
    return results


def get_interactions_relevant_to_nutrition(medication_atc_codes: list[str]) -> list[DrugNutrientInteraction]:
    """Filter interactions specifically relevant for nutrition support planning."""
    all_interactions = check_interactions(medication_atc_codes)
    # Only return moderate/severe interactions that affect nutrition-relevant nutrients
    nutrition_nutrients = {
        "Potassium", "Magnesium", "Calcium", "Zinc", "Vitamin B12",
        "Vitamin K", "Vitamin B6", "Thiamine", "Coenzyme Q10",
    }
    return [
        i for i in all_interactions
        if i.nutrient in nutrition_nutrients or i.severity == "severe"
    ]
