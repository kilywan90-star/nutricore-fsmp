# digital-doctor/backend/tests/test_report_interpreter.py
import pytest
from datetime import date
from src.services.report_interpreter import interpret_lab_report


def test_interpret_fpg_normal():
    result = interpret_lab_report("blood_glucose_panel", {"fpg": 5.2})
    assert result["status"] == "normal"
    assert "正常" in result["interpretation"]


def test_interpret_fpg_impaired():
    result = interpret_lab_report("blood_glucose_panel", {"fpg": 6.5})
    assert result["status"] == "impaired"


def test_interpret_fpg_diabetic():
    result = interpret_lab_report("blood_glucose_panel", {"fpg": 8.0})
    assert result["status"] == "abnormal"


def test_interpret_hba1c_target():
    result = interpret_lab_report("hba1c_only", {"hba1c": 6.8})
    assert result["status"] in ("normal", "impaired")


def test_interpret_hba1c_high():
    result = interpret_lab_report("hba1c_only", {"hba1c": 9.0})
    assert result["status"] == "abnormal"


def test_interpret_lipid_panel():
    result = interpret_lab_report("lipid_panel", {
        "tc": 5.5, "ldl": 3.5, "hdl": 1.0, "tg": 2.0
    })
    assert "interpretation" in result
    assert "items" in result


def test_interpret_unknown_report_type():
    result = interpret_lab_report("unknown", {"x": 1})
    assert result["status"] == "normal"
