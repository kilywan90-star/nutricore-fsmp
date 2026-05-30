from ..models.fsmp_product import FSMPProduct, FSMPProductMatch
from ..models.assessment import NutritionPathway, NutritionScreeningInput


def match_products(
    screening: NutritionScreeningInput,
    pathway: NutritionPathway,
    products: list[FSMPProduct],
) -> list[FSMPProductMatch]:
    """
    Match and score FSMP products against patient needs.

    Scoring dimensions (weighted):
    1. Category match (30%): does product category align with route?
    2. Energy density match (20%): does kcal/ml meet needs?
    3. Protein match (20%): does protein source/content meet needs?
    4. Disease-specific features (20%): special features relevant?
    5. Contraindication check (10%): any contraindications triggered?
    """
    results = []

    for product in products:
        scores = {}
        reasons = []
        warnings = []

        # 1. Category match
        route = pathway.route
        category_score, cat_reason = _score_category(product, route)
        scores["category_match"] = category_score
        if cat_reason:
            reasons.append(cat_reason)

        # 2. Energy density match
        energy_score, energy_reason = _score_energy(product, pathway)
        scores["energy_match"] = energy_score
        if energy_reason:
            reasons.append(energy_reason)

        # 3. Protein match
        protein_score, protein_reason = _score_protein(product, screening)
        scores["protein_match"] = protein_score
        if protein_reason:
            reasons.append(protein_reason)

        # 4. Disease-specific features
        feature_score, feature_reasons = _score_features(product, screening)
        scores["feature_match"] = feature_score
        reasons.extend(feature_reasons)

        # 5. Contraindication check
        contra_score, contra_warnings = _check_contraindications(product, screening)
        scores["contraindication_check"] = contra_score
        warnings.extend(contra_warnings)

        # Weighted total
        weights = {
            "category_match": 0.30,
            "energy_match": 0.20,
            "protein_match": 0.20,
            "feature_match": 0.20,
            "contraindication_check": 0.10,
        }
        total = sum(scores[k] * weights[k] for k in weights)

        results.append(FSMPProductMatch(
            product=product,
            match_score=round(total, 1),
            score_breakdown=scores,
            match_reasons=reasons,
            warnings=warnings,
        ))

    results.sort(key=lambda x: x.match_score, reverse=True)
    return results[:5]  # top 5


def _score_category(product: FSMPProduct, route: str) -> tuple[float, str]:
    """Score product category against nutrition route."""
    if route == "ONS":
        if product.category == "complete":
            return 100.0, "全营养配方，适合口服补充"
        if product.category == "specific_complete":
            return 85.0, "特定全营养配方，需确认适应症"
        return 40.0, "非全营养配方不适合作为主要ONS来源"
    elif route == "EN":
        if product.category in ("complete", "specific_complete"):
            return 100.0, "全营养配方，适合管饲"
        if product.category == "incomplete":
            return 30.0, "非全营养配方需搭配使用"
        return 50.0, ""
    elif route == "PN":
        return 0.0, "肠外营养不适用肠内FSMP产品"
    else:  # mixed
        if product.category == "complete":
            return 90.0, "全营养配方可作为混合营养的肠内部分"
        return 60.0, ""
    return 50.0, ""


def _score_energy(product: FSMPProduct, pathway: NutritionPathway) -> tuple[float, str]:
    """Score energy density against target."""
    target = pathway.target_energy_kcal_per_day
    if target <= 0:
        return 50.0, ""

    volume_needed = target / product.energy_density_kcal_per_100ml * 100

    if 1000 <= volume_needed <= 2000:
        return 100.0, f"能量密度适配，每日约需{volume_needed:.0f}ml"
    if volume_needed < 800:
        return 75.0, f"能量密度偏高，每日仅需{volume_needed:.0f}ml"
    if volume_needed <= 2500:
        return 70.0, f"能量密度偏低，每日需{volume_needed:.0f}ml"
    return 40.0, f"需大量补液({volume_needed:.0f}ml/日)，考虑更高能量密度产品"


def _score_protein(product: FSMPProduct, screening: NutritionScreeningInput) -> tuple[float, str]:
    """Score protein source and content."""
    score = 70.0
    reasons = []

    # Protein source quality
    source_scores = {
        "whey": 100, "casein": 85, "hydrolysate": 80,
        "soy": 65, "amino_acid": 55,
    }
    if product.protein_source in source_scores:
        score = source_scores[product.protein_source]
        reasons.append(f"蛋白来源：{product.protein_source}")

    # Renal function adjustment
    if screening.renal_function == "impaired":
        if product.protein_content_g_per_100ml < 4.0:
            score += 10
            reasons.append("低蛋白配方适合肾功能受损")
        else:
            score -= 20
    if screening.renal_function == "dialysis":
        if product.protein_content_g_per_100ml >= 5.0:
            score += 10
            reasons.append("高蛋白配方适合透析患者")

    if reasons:
        return min(score, 100.0), "; ".join(reasons)
    return score, ""


def _score_features(product: FSMPProduct, screening: NutritionScreeningInput) -> tuple[float, list[str]]:
    """Score disease-specific features."""
    reasons = []
    score = 50.0

    features = set(product.special_features)

    # Diabetes
    if "diabetes" in features and (
        "diabetes" in screening.comorbidities
        or screening.disease_icd11_code.startswith("5A")
    ):
        score += 30
        reasons.append("糖尿病适用配方")

    # Renal
    if "renal" in features and screening.renal_function != "normal":
        score += 30
        reasons.append("肾病适用配方")

    # Hepatic
    if "hepatic" in features and screening.liver_function != "normal":
        score += 30
        reasons.append("肝病适用配方（支链氨基酸）")

    # Immune modulation
    if "immune_modulation" in features and screening.surgery_code in {
        "pancreaticoduodenectomy", "esophagectomy", "total_gastrectomy",
    }:
        score += 25
        reasons.append("免疫调节配方（精氨酸/ω-3/核苷酸）适合大手术")

    # High MCT
    if "high_mct" in features and screening.gi_function == "impaired":
        score += 20
        reasons.append("高MCT配方适合脂肪吸收障碍")

    # Low residue / elemental
    if "low_residue" in features and screening.gi_function == "impaired":
        score += 15
        reasons.append("低渣/要素型配方适合肠道功能受损")

    # Fiber
    if "fiber_enriched" in features and screening.gi_function == "normal":
        score += 10
        reasons.append("含膳食纤维，有助于维持肠道功能")

    return min(score, 100.0), reasons


def _check_contraindications(product: FSMPProduct, screening: NutritionScreeningInput) -> tuple[float, list[str]]:
    """Check for contraindications."""
    warnings = []
    score = 100.0

    # Osmolarity check for EN
    if product.osmolarity_mOsm_L > 500 and screening.gi_function == "impaired":
        warnings.append(f"产品渗透压较高({product.osmolarity_mOsm_L}mOsm/L)，肠功能受损时需稀释/缓慢输注")
        score -= 15

    # Renal contraindications
    if screening.renal_function == "impaired":
        if product.protein_content_g_per_100ml > 6.0:
            warnings.append("蛋白质含量较高，肾功能不全患者需监测")
            score -= 10
        # Check for potassium/phosphorus restrictions (would need product composition data)

    # Liver failure contraindications
    if screening.liver_function == "failure":
        if product.protein_source not in ("hydrolysate", "amino_acid"):
            warnings.append("肝功能衰竭时对整蛋白耐受差，考虑要素型配方")
            score -= 10

    return max(score, 0.0), warnings
