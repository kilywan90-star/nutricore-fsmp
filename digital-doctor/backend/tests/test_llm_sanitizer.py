"""Tests for LLM input sanitizer — whitelist-based PHI removal."""
import pytest
from src.security.llm_sanitizer import (
    sanitize_for_llm,
    desanitize_llm_output,
    SAFE_CLINICAL_FIELDS,
    PHI_FIELDS,
)


class TestSanitizeRemovesPhi:
    """Verify that PHI fields are stripped from clinical data."""

    def test_strips_phi_fields(self):
        data = {
            "name": "张三",
            "phone": "13812345678",
            "id_card": "110101199001011234",
            "address": "北京市海淀区中关村大街1号",
            "email": "zhangsan@example.com",
        }
        result = sanitize_for_llm(data)
        assert "name" not in result
        assert "phone" not in result
        assert "id_card" not in result
        assert "address" not in result
        assert "email" not in result

    def test_keeps_safe_clinical_fields(self):
        data = {
            "glucose": 6.5,
            "hba1c": 7.2,
            "medications": ["二甲双胍 500mg"],
            "age": 55,
            "gender": "男",
            "bmi": 26.0,
            "risk_level": "中危",
            "score": 12,
        }
        result = sanitize_for_llm(data)
        assert result["glucose"] == 6.5
        assert result["hba1c"] == 7.2
        assert result["medications"] == ["二甲双胍 500mg"]
        assert result["age"] == 55
        assert result["gender"] == "男"
        assert result["bmi"] == 26.0
        assert result["risk_level"] == "中危"
        assert result["score"] == 12

    def test_handles_empty_input(self):
        result = sanitize_for_llm({})
        assert "_sanitization_metadata" in result
        assert result["_sanitization_metadata"]["fields_removed"] == []

        result_none = sanitize_for_llm({})
        assert "_sanitization_metadata" in result_none

    def test_handles_nested_dicts(self):
        data = {
            "patient_info": {
                "name": "李四",
                "phone": "13900001111",
                "age": 45,
                "glucose": 7.0,
            },
            "lab_results": {
                "hba1c": 8.0,
                "report_type": "blood_glucose_panel",
            },
            "address": "上海市浦东新区",
        }
        result = sanitize_for_llm(data)
        # Top-level PHI removed
        assert "address" not in result
        # patient_info is not whitelisted at top level, so stripped entirely
        # lab_results is safe and should be kept
        assert "lab_results" in result
        assert result["lab_results"]["hba1c"] == 8.0

    def test_enforces_whitelist(self):
        """Fields not in the whitelist must be removed."""
        data = {
            "glucose": 5.5,
            "custom_field_xyz": "should be removed",
            "another_random_field": 42,
            "hba1c": 6.8,
            "internal_notes": "patient complains of dizziness",  # not in whitelist
        }
        result = sanitize_for_llm(data)
        assert "glucose" in result
        assert "hba1c" in result
        assert "custom_field_xyz" not in result
        assert "another_random_field" not in result
        assert "internal_notes" not in result
        # Metadata should track what was removed
        meta = result["_sanitization_metadata"]
        assert len(meta["fields_kept"]) == 2  # glucose, hba1c

    def test_metadata_tracks_sanitization(self):
        data = {
            "glucose": 6.0,
            "name": "王五",
            "phone": "13700001111",
        }
        result = sanitize_for_llm(data)
        meta = result["_sanitization_metadata"]
        assert "sanitized_at" in meta
        assert "sanitizer_version" in meta
        assert "fields_kept" in meta
        assert "fields_removed" in meta
        assert "name" in meta["fields_removed"]
        assert "phone" in meta["fields_removed"]


class TestDesanitize:
    """Verify desanitize_llm_output is a safe passthrough."""

    def test_passthrough(self):
        output = "您的空腹血糖6.5mmol/L，属于正常范围。"
        result = desanitize_llm_output(output, {})
        assert result == output

    def test_empty_input(self):
        assert desanitize_llm_output("", {}) == ""


class TestWhitelistIntegrity:
    """Verify whitelist does not contain PHI fields."""

    def test_no_phi_in_safe_list(self):
        overlap = SAFE_CLINICAL_FIELDS & PHI_FIELDS
        assert overlap == set(), f"PHI fields in safe list: {overlap}"

    def test_common_clinical_fields_whitelisted(self):
        """Smoke test: critical clinical fields must be present."""
        required = {
            "glucose", "hba1c", "medications", "age", "gender",
            "bmi", "risk_level", "score", "status",
        }
        missing = required - SAFE_CLINICAL_FIELDS
        assert missing == set(), f"Required fields missing from whitelist: {missing}"
