import pytest
from src.adapters.ocr_adapter import (
    extract_lab_values_from_text,
    parse_chinese_lab_report,
)


def test_extract_fasting_glucose():
    """Extract fasting glucose from structured Chinese lab report text."""
    text = """
    检验报告单
    姓名：张三  性别：男  年龄：58
    ----------------------------------------
    项目           结果     单位     参考范围
    空腹血糖(GLU)  6.5      mmol/L   3.9-6.1
    """
    results = extract_lab_values_from_text(text)
    assert "fpg" in results
    assert results["fpg"]["value"] == 6.5
    assert results["fpg"]["unit"] == "mmol/L"
    assert results["fpg"]["reference_range"] == "3.9-6.1"


def test_extract_hba1c():
    """Extract HbA1c from Chinese lab report."""
    text = """
    糖化血红蛋白(HbA1c)  8.2  %  4.0-6.0
    """
    results = extract_lab_values_from_text(text)
    assert "hba1c" in results
    assert results["hba1c"]["value"] == 8.2
    assert results["hba1c"]["unit"] == "%"


def test_extract_lipid_panel():
    """Extract full lipid panel from Chinese text."""
    text = """
    血脂四项检测结果：
    总胆固醇(TC)  5.8  mmol/L  3.1-5.7
    甘油三酯(TG)  2.3  mmol/L  0.56-1.70
    高密度脂蛋白(HDL-C)  1.0  mmol/L  1.0-2.0
    低密度脂蛋白(LDL-C)  3.8  mmol/L  0-3.4
    """
    results = extract_lab_values_from_text(text)
    assert "tc" in results
    assert "tg" in results
    assert "hdl" in results
    assert "ldl" in results
    assert results["tc"]["value"] == 5.8
    assert results["hdl"]["value"] == 1.0


def test_handle_ocr_errors():
    """Handle common OCR errors in extracted text."""
    # OCR reads 皿 instead of 糖, mmo1/L instead of mmol/L
    text = "空肢血皿(GLU)  6.5  mmo1/L  3.9-6.1"
    results = extract_lab_values_from_text(text)
    assert "fpg" in results
    assert results["fpg"]["value"] == 6.5
    assert results["fpg"]["status"] == "high"


def test_empty_text():
    """Handle empty or None input gracefully."""
    assert extract_lab_values_from_text("") == {}
    assert extract_lab_values_from_text(None) == {}
    assert extract_lab_values_from_text("   ") == {}


def test_parse_chinese_lab_report_format():
    """parse_chinese_lab_report extracts structured entries from report lines."""
    text = """
    空腹血糖  6.5  mmol/L  3.9-6.1
    糖化血红蛋白  8.2  %  4.0-6.0
    肌酐  95  umol/L  44-133
    """
    entries = parse_chinese_lab_report(text)
    assert len(entries) >= 2
    items = [e["item"] for e in entries]
    assert any("血糖" in i or "GLU" in i.upper() for i in items)
    assert any("肌酐" in i for i in items)


def test_traditional_chinese_characters():
    """Handle traditional Chinese characters in lab reports."""
    text = "空腹血糖(空腹血糖)  6.5  mmol/L  3.9-6.1"
    results = extract_lab_values_from_text(text)
    assert len(results) > 0
