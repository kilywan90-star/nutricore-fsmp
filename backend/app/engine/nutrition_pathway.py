from ..models.assessment import NutritionPathway, NutritionScreeningInput


def determine_pathway(screening: NutritionScreeningInput) -> NutritionPathway:
    """
    Determine nutrition support route based on GI function and swallowing ability.

    Decision tree:
    1. GI tract functional?
       YES → 2. Can swallow safely?
              YES → ONS (oral nutritional supplements)
              NO  → EN (enteral nutrition via tube)
       NO  → 3. GI tract partially functional?
              YES → EN (elemental/semi-elemental formula)
              NO  → PN (parenteral nutrition)

    4. If EN + unable to meet 60% needs orally → mixed (ONS + supplemental EN/PN)
    """
    gi = screening.gi_function
    swallow = screening.swallowing_function

    if gi == "non_functional":
        rationale = "GI tract non-functional — parenteral nutrition indicated"
        route = "PN"
    elif gi == "impaired":
        rationale = "GI function impaired — enteral nutrition with elemental/semi-elemental formula"
        route = "EN"
    elif swallow == "unsafe":
        rationale = "Safe swallow absent — enteral nutrition via nasogastric/nasojejunal tube"
        route = "EN"
    elif swallow == "impaired":
        if screening.food_intake_reduction_pct >= 50:
            rationale = "Impaired swallowing + significant oral intake reduction — mixed ONS + supplemental EN"
            route = "mixed"
        else:
            rationale = "Impaired swallowing with adequate oral intake — ONS with texture-modified supplements"
            route = "ONS"
    else:
        if screening.post_op_day > 0 and screening.food_intake_reduction_pct >= 50:
            rationale = "Post-operative with significant intake reduction — ONS to bridge gap"
            route = "ONS"
        else:
            rationale = "Functional GI tract + safe swallow — oral diet with ONS if needed"
            route = "ONS"

    # Calculate targets
    energy, protein = _calculate_targets(screening)
    fluid = _calculate_fluid_target(screening)

    return NutritionPathway(
        route=route,
        rationale=rationale,
        target_energy_kcal_per_day=energy,
        target_protein_g_per_day=protein,
        target_fluid_ml_per_day=fluid,
    )


def _calculate_targets(screening: NutritionScreeningInput) -> tuple[float, float]:
    """
    Calculate energy and protein targets.

    Energy:
    - Baseline: 25 kcal/kg/day (standard adult)
    - Mild stress (e.g. elective surgery): 25-30 kcal/kg/day
    - Moderate stress (major surgery, sepsis): 30-35 kcal/kg/day
    - Severe stress (major trauma, burns): 35-40 kcal/kg/day

    Protein:
    - Baseline: 0.8 g/kg/day (standard adult)
    - Mild stress: 1.0-1.2 g/kg/day
    - Moderate stress: 1.2-1.5 g/kg/day
    - Severe stress: 1.5-2.0 g/kg/day
    """
    wt = screening.patient.weight_kg
    if wt <= 0:
        return 1800.0, 60.0

    # Determine stress level from surgery or disease
    severe_surgeries = {
        "pancreaticoduodenectomy", "esophagectomy", "total_gastrectomy",
        "liver_resection_major", "cytoreductive_surgery",
    }
    moderate_surgeries = {
        "colorectal_resection", "gastrectomy_subtotal",
    }

    if screening.surgery_code and screening.surgery_code in severe_surgeries:
        stress = "severe"
    elif screening.surgery_code and screening.surgery_code in moderate_surgeries:
        stress = "moderate"
    elif screening.post_op_day > 0:
        stress = "mild"
    else:
        stress = "baseline"

    energy_map = {"baseline": 25, "mild": 28, "moderate": 32, "severe": 37}
    protein_map = {"baseline": 0.8, "mild": 1.1, "moderate": 1.4, "severe": 1.8}

    energy = round(wt * energy_map[stress])
    protein = round(wt * protein_map[stress], 1)

    return float(energy), protein


def _calculate_fluid_target(screening: NutritionScreeningInput) -> float:
    """Fluid target: 30-35 ml/kg/day, adjusted for renal function."""
    wt = screening.patient.weight_kg
    if wt <= 0:
        return 2000.0

    if screening.renal_function in ("impaired", "dialysis"):
        return round(min(wt * 25, 2000))
    return round(wt * 32)
