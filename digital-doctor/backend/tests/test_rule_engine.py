import pytest
from src.engine.rule_loader import RuleLoader
from src.engine.rule_engine import RuleEngine


@pytest.fixture
def rule_loader():
    return RuleLoader()


@pytest.fixture
def rule_engine(rule_loader):
    rules = rule_loader.load("t2dm_guidelines_v1")
    return RuleEngine(rules)


def test_load_rules(rule_loader):
    rules = rule_loader.load("t2dm_guidelines_v1")
    assert rules is not None
    assert "classification" in rules["rules"]
    assert "treatment_target" in rules["rules"]
    assert "medication_pathway" in rules["rules"]


def test_evaluate_diagnosis_fpg_high(rule_engine):
    patient_data = {"fpg": 7.8, "fpg_count": 2}
    matches = rule_engine.evaluate(patient_data, category="classification")
    assert len(matches) >= 1
    found = any(m["id"] == "class-001" for m in matches)
    assert found, f"Expected class-001 in {matches}"


def test_evaluate_prediabetes(rule_engine):
    patient_data = {"fpg": 6.5}
    matches = rule_engine.evaluate(patient_data, category="classification")
    prediabetes = [m for m in matches if m["id"] == "class-003"]
    assert len(prediabetes) == 1


def test_evaluate_treatment_target_young(rule_engine):
    patient_data = {"age": 45, "has_complication": False}
    matches = rule_engine.evaluate(patient_data, category="treatment_target")
    target = [m for m in matches if m["id"] == "target-001"]
    assert len(target) == 1


def test_evaluate_treatment_target_elderly(rule_engine):
    patient_data = {"age": 70, "has_complication": True}
    matches = rule_engine.evaluate(patient_data, category="treatment_target")
    target = [m for m in matches if m["id"] == "target-002"]
    assert len(target) == 1


def test_evaluate_metformin_safe(rule_engine):
    patient_data = {"egfr": 80, "has_contraindication_metformin": False}
    matches = rule_engine.evaluate(patient_data, category="medication_pathway")
    med = [m for m in matches if m["id"] == "med-001"]
    assert len(med) == 1


def test_evaluate_metformin_contraindicated(rule_engine):
    patient_data = {"egfr": 30, "has_contraindication_metformin": False}
    matches = rule_engine.evaluate(patient_data, category="medication_pathway")
    contra = [m for m in matches if m["id"] == "med-002"]
    assert len(contra) == 1


def test_evaluate_severe_hyperglycemia_alert(rule_engine):
    patient_data = {"fpg": 18.0}
    matches = rule_engine.evaluate(patient_data, category="alert_thresholds")
    alert = [m for m in matches if m["id"] == "alert-001"]
    assert len(alert) == 1
    assert alert[0]["severity"] == "critical"


def test_evaluate_hypoglycemia_alert(rule_engine):
    patient_data = {"glucose": 3.2}
    matches = rule_engine.evaluate(patient_data, category="alert_thresholds")
    alert = [m for m in matches if m["id"] == "alert-002"]
    assert len(alert) == 1


def test_evaluate_consecutive_high_alert(rule_engine):
    patient_data = {"consecutive_high_fpg_days": 5}
    matches = rule_engine.evaluate(patient_data, category="alert_thresholds")
    alert = [m for m in matches if m["id"] == "alert-003"]
    assert len(alert) == 1


def test_evaluate_no_match(rule_engine):
    patient_data = {"fpg": 5.0, "fpg_count": 0}
    matches = rule_engine.evaluate(patient_data, category="classification")
    assert len(matches) == 0
