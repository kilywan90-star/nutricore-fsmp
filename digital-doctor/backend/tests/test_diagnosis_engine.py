"""Tests for diagnosis engine, HOMA calculator, and diagnosis prompts."""
import pytest
from unittest.mock import AsyncMock, patch

from src.engine.rule_loader import RuleLoader
from src.engine.rule_engine import RuleEngine
from src.services.diagnosis_engine import (
    differential_diagnosis,
    calculate_confidence,
    _is_complex_case,
    _build_result_from_rules,
    _derive_from_rules,
)
from src.services.homa_calculator import calculate_homa_ir, calculate_homa_beta
from src.services.diagnosis_prompts import (
    DIFFERENTIAL_DIAGNOSIS_SYSTEM,
    DIAGNOSIS_USER_TEMPLATE,
)


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def rule_loader():
    return RuleLoader()


@pytest.fixture
def rule_engine(rule_loader):
    rules = rule_loader.load("t2dm_guidelines_v1")
    return RuleEngine(rules)


# ── Test: Type 2 diabetes diagnosis ──────────────────────────────────────

@pytest.mark.asyncio
async def test_type2_diagnosis_fpg_high():
    """Patient with FPG >= 7.0 on two measurements should get T2DM diagnosis."""
    patient_data = {
        "fpg": 7.8,
        "fpg_count": 2,
        "hba1c": 7.5,
        "age": 45,
        "bmi": 27.0,
        "egfr": 80,
    }
    result = await differential_diagnosis(patient_data)
    assert result["primary_diagnosis"]["type"] == "2型糖尿病"
    assert result["primary_diagnosis"]["confidence"] == "high"
    assert result["overall_confidence"] > 0.5
    assert len(result["differentials"]) >= 0
    assert len(result["recommended_tests"]) >= 2

    # Should include OGTT and HbA1c in recommended tests
    test_names = [t["test"] for t in result["recommended_tests"]]
    assert any("OGTT" in name or "葡萄糖耐量" in name for name in test_names)
    assert any("HbA1c" in name or "糖化" in name for name in test_names)


# ── Test: Prediabetes diagnosis ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_prediabetes_diagnosis():
    """Patient with FPG 6.1-7.0 should get prediabetes (IFG) diagnosis."""
    patient_data = {
        "fpg": 6.5,
        "hba1c": 5.8,
        "age": 55,
        "bmi": 26.0,
    }
    result = await differential_diagnosis(patient_data)
    assert result["primary_diagnosis"]["type"] == "糖尿病前期"
    assert result["primary_diagnosis"]["subtype"] == "空腹血糖受损(IFG)"
    assert result["primary_diagnosis"]["confidence"] == "high"

    # Should recommend lifestyle and OGTT
    test_names = [t["test"] for t in result["recommended_tests"]]
    assert any("OGTT" in name or "葡萄糖耐量" in name for name in test_names)


# ── Test: Combination case (FPG + HbA1c both diabetic) ──────────────────

@pytest.mark.asyncio
async def test_combination_case():
    """Patient with both FPG >= 7.0 and HbA1c >= 6.5 confirms T2DM."""
    patient_data = {
        "fpg": 8.2,
        "fpg_count": 3,
        "hba1c": 8.1,
        "age": 60,
        "bmi": 30.0,
        "egfr": 65,
        "tc": 5.8,
        "tg": 2.3,
        "ldl": 3.5,
        "hdl": 0.9,
        "has_hypertension": True,
    }
    result = await differential_diagnosis(patient_data)
    # Should detect T2DM (HbA1c >= 6.5 overrides prediabetes from FPG alone)
    assert result["primary_diagnosis"]["type"] == "2型糖尿病"
    assert result["primary_diagnosis"]["confidence"] == "high"

    # Should have UACR screening for T2DM
    test_names = [t["test"] for t in result["recommended_tests"]]
    assert any("UACR" in name or "尿微量" in name for name in test_names)


# ── Test: Low confidence case ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_low_confidence_case():
    """Patient with marginal values and no clear diagnosis gets low confidence."""
    patient_data = {
        "fpg": 5.0,
        "age": 30,
        "bmi": 22.0,
    }
    result = await differential_diagnosis(patient_data)
    # FPG 5.0 is normal, but without more data confidence should be reasonable
    assert result["primary_diagnosis"]["type"] in ("血糖正常", "未明确诊断")
    # With FPG 5.0, this is a normal case — should not be high confidence without more tests
    assert result["overall_confidence"] < 0.8


# ── Test: HOMA-IR normal ─────────────────────────────────────────────────

def test_homa_ir_normal():
    """Normal insulin sensitivity should return HOMA-IR < 1.0."""
    result = calculate_homa_ir(fasting_insulin=3.0, fasting_glucose=4.5)
    assert result["homa_ir"] is not None
    assert result["homa_ir"] < 1.0
    assert "正常" in result["interpretation"]


# ── Test: HOMA-IR insulin resistant ──────────────────────────────────────

def test_homa_ir_insulin_resistant():
    """High fasting insulin + glucose should indicate insulin resistance."""
    result = calculate_homa_ir(fasting_insulin=15.0, fasting_glucose=6.5)
    assert result["homa_ir"] is not None
    assert result["homa_ir"] >= 2.5
    assert "抵抗" in result["interpretation"]


# ── Test: Empty input ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_empty_input():
    """Empty patient data should not crash — returns '未明确诊断'."""
    result = await differential_diagnosis({})
    assert "primary_diagnosis" in result
    assert "differentials" in result
    assert "recommended_tests" in result
    assert result["overall_confidence"] is not None
    # With no data, should get "未明确诊断"
    assert result["primary_diagnosis"]["type"] in ("未明确诊断", "血糖正常")


# ── Test: calculate_confidence ───────────────────────────────────────────

def test_calculate_confidence_rule_only():
    """Confidence from rule engine matches only (no LLM)."""
    rule_matches = [
        {
            "id": "class-001",
            "category": "diagnosis",
            "confidence": "high",
            "conclusion": "T2DM confirmed",
        }
    ]
    score = calculate_confidence(rule_matches, None)
    # Rule-only: 0.6 * 1.0 = 0.6
    assert score == 0.6


def test_calculate_confidence_rule_plus_llm_high():
    """Confidence with high-confidence rule and LLM."""
    rule_matches = [
        {
            "id": "class-001",
            "category": "diagnosis",
            "confidence": "high",
        }
    ]
    llm_analysis = {
        "primary_diagnosis": {"confidence": "high", "type": "2型糖尿病"}
    }
    score = calculate_confidence(rule_matches, llm_analysis)
    # 0.6 * 1.0 + 0.4 * 1.0 = 1.0
    assert score == 1.0


def test_calculate_confidence_no_matches():
    """Confidence with no rule matches and no LLM."""
    score = calculate_confidence([], None)
    assert score == 0.0


# ── Test: HOMA-beta ──────────────────────────────────────────────────────

def test_homa_beta_normal():
    """Normal beta-cell function."""
    result = calculate_homa_beta(fasting_insulin=8.0, fasting_glucose=4.5)
    assert result["homa_beta"] is not None
    # HOMA-beta = 20 * 8.0 / (4.5 - 3.5) = 160 / 1.0 = 160.0
    # 160 is in the 120-200 range = normal
    assert "正常" in result["interpretation"]


def test_homa_beta_invalid_glucose():
    """Glucose <= 3.5 results in invalid calculation."""
    result = calculate_homa_beta(fasting_insulin=8.0, fasting_glucose=3.0)
    assert result["homa_beta"] is None
    assert "无法计算" in result["interpretation"]


def test_homa_ir_invalid_input():
    """Zero insulin should return invalid result."""
    result = calculate_homa_ir(fasting_insulin=0, fasting_glucose=5.0)
    assert result["homa_ir"] is None
    assert "无法计算" in result["interpretation"]


# ── Test: Prompt templates ───────────────────────────────────────────────

def test_diagnosis_system_prompt_exists():
    """System prompt should contain key clinical elements."""
    assert "中国2型糖尿病防治指南(2024版)" in DIFFERENTIAL_DIAGNOSIS_SYSTEM
    assert "primary_diagnosis" in DIFFERENTIAL_DIAGNOSIS_SYSTEM
    assert "differentials" in DIFFERENTIAL_DIAGNOSIS_SYSTEM
    assert "recommended_tests" in DIFFERENTIAL_DIAGNOSIS_SYSTEM


def test_diagnosis_user_template_fills_correctly():
    """User template should fill patient data without crashing."""
    result = DIAGNOSIS_USER_TEMPLATE.format(
        gender="M",
        birth_year="1980",
        diabetes_type="type2",
        bmi="28.0",
        waist_circumference="92",
        blood_pressure="130/85",
        family_history="是",
        has_hypertension="是",
        physical_activity="low",
        fpg="7.5",
        ppg="11.0",
        hba1c="7.2",
        tc="5.5",
        tg="2.1",
        ldl="3.2",
        hdl="1.0",
        egfr="80",
        pre_consult_summary="患者主诉多饮多尿3个月",
        lab_results="- OGTT 2h: 13.5 mmol/L",
        rule_matches="- [class-001] 2型糖尿病诊断标准: FPG >= 7.0 (置信度: high)",
    )
    assert "M" in result
    assert "7.5" in result
    assert "多饮多尿" in result
    assert "class-001" in result


# ── Test: is_complex_case helper ─────────────────────────────────────────

def test_is_complex_no_matches():
    """No rule matches => complex case."""
    assert _is_complex_case([], {}) is True


def test_is_complex_low_confidence():
    """Low-confidence match => complex case."""
    matches = [
        {"id": "x", "category": "diagnosis", "confidence": "low", "conclusion": "uncertain"}
    ]
    assert _is_complex_case(matches, {}) is True


def test_is_not_complex_high_confidence():
    """Single high-confidence match => not complex."""
    matches = [
        {"id": "class-001", "category": "diagnosis", "confidence": "high", "conclusion": "T2DM"}
    ]
    assert _is_complex_case(matches, {}) is False
