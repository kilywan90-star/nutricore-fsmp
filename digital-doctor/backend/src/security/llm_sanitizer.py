"""LLM input sanitizer — whitelist approach to strip PHI before sending to LLM."""
from __future__ import annotations

import logging
from copy import deepcopy
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Fields safe for LLM consumption — everything else is blocked.
# Each entry is a field name that may appear in clinical data dicts.
SAFE_CLINICAL_FIELDS: frozenset[str] = frozenset({
    # Glucose / metabolic
    "glucose", "value_mmol_l", "fpg", "ppg", "fasting_glucose",
    "post_prandial", "hba1c", "tc", "ldl", "hdl", "tg",
    "blood_pressure", "bmi", "waist_circumference",

    # Medications
    "medications", "drug_name", "dosage", "frequency", "time_of_day",
    "start_date", "end_date", "is_active",

    # Demographics (de-identified only — never names/phones/addresses)
    "age", "gender", "birth_year", "diabetes_type",

    # Lab / reports
    "lab_results", "results", "report_type", "report_date",
    "items", "status", "status_label", "interpretation",

    # Lifestyle / adherence
    "diet_adherence", "exercise_adherence", "physical_activity",

    # Clinical context
    "diagnosis_date", "hba1c_target", "has_hypertension",
    "family_history",

    # Risk assessment
    "risk_level", "score", "max_score", "factor_scores",
    "recommendations", "age_score", "bmi_score", "waist_score",
    "family_score", "activity_score", "glucose_score",
    "hypertension_score",

    # Alerts
    "alerts", "alert_type", "severity", "title", "detail",
    "reference_guideline", "acknowledged",

    # Record metadata (non-PHI)
    "measure_type", "recorded_at", "created_at", "notes",
    "interpreted_at", "count", "avg", "max", "min", "std",
    "direction", "change_rate", "recent_values",
    "in_range_pct", "above_range_pct", "below_range_pct",

    # Safe identifiers (UUIDs / internal IDs)
    "patient_id", "id",
})

# Fields that are ALWAYS stripped — even if they somehow appear in safe lists.
PHI_FIELDS: frozenset[str] = frozenset({
    "name", "patient_name", "full_name", "given_name", "family_name",
    "name_hash",
    "phone", "phone_number", "mobile", "tel", "telephone",
    "id_card", "id_number", "ssn", "national_id", "passport",
    "address", "home_address", "work_address", "mailing_address",
    "email", "email_address",
    "wechat", "qq",
})


def sanitize_for_llm(clinical_data: dict) -> dict:
    """Remove/mask PHI fields from clinical data before sending to an LLM.

    Uses a whitelist approach: only fields in ``SAFE_CLINICAL_FIELDS`` are
    kept.  PHI fields (name, phone, ID card, address, etc.) are always
    stripped regardless of whitelist membership.

    Returns a new dict with an added ``_sanitization_metadata`` key for
    audit purposes.
    """
    if not clinical_data:
        return _empty_sanitized()

    sanitized = _sanitize_dict(clinical_data, path="root")
    sanitized["_sanitization_metadata"] = {
        "sanitized_at": datetime.now(timezone.utc).isoformat(),
        "fields_removed": sorted(_collect_removed(clinical_data, sanitized)),
        "fields_kept": sorted(_collect_kept(sanitized)),
        "sanitizer_version": "1.0.0",
    }
    return sanitized


def desanitize_llm_output(sanitized_output: str, original_context: dict) -> str:
    """Restore clinical identifiers in LLM output if needed.

    Currently a passthrough: the sanitized input contains only safe clinical
    fields, so the LLM output should not reference any masked identifiers.
    This function exists as an extension point for future identifier
    restoration (e.g., mapping de-identified study IDs back to real IDs).
    """
    if not sanitized_output:
        return ""
    return sanitized_output


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sanitize_dict(data: dict, path: str) -> dict:
    """Recursively sanitize a dict, returning a new dict with PHI removed."""
    result: dict = {}
    for key, value in data.items():
        if key in PHI_FIELDS:
            logger.debug("Stripping PHI field %s at %s", key, path)
            continue
        if key not in SAFE_CLINICAL_FIELDS:
            logger.debug("Stripping non-whitelisted field %s at %s", key, path)
            continue

        if isinstance(value, dict):
            result[key] = _sanitize_dict(value, f"{path}.{key}")
        elif isinstance(value, list):
            result[key] = [
                _sanitize_dict(item, f"{path}.{key}[{i}]")
                if isinstance(item, dict)
                else item
                for i, item in enumerate(value)
            ]
        else:
            result[key] = value
    return result


def _collect_removed(original: dict, sanitized: dict) -> list[str]:
    """Return field names present in original but absent from sanitized."""
    original_keys: set[str] = set()
    sanitized_keys: set[str] = set()
    _collect_keys(original, original_keys)
    _collect_keys(sanitized, sanitized_keys)
    # Include PHI fields that were in the original
    removed = (original_keys - sanitized_keys) | (PHI_FIELDS & original_keys)
    return sorted(removed)


def _collect_keys(data: dict, keys: set[str], prefix: str = "") -> None:
    """Recursively collect all flattened key paths."""
    for k, v in data.items():
        full = f"{prefix}.{k}" if prefix else k
        keys.add(full)
        if isinstance(v, dict):
            _collect_keys(v, keys, full)
        elif isinstance(v, list):
            for i, item in enumerate(v):
                if isinstance(item, dict):
                    _collect_keys(item, keys, f"{full}[{i}]")


def _collect_kept(sanitized: dict) -> list[str]:
    """Return sorted list of top-level keys kept (excludes metadata)."""
    return [k for k in sanitized if k != "_sanitization_metadata"]


def _empty_sanitized() -> dict:
    return {
        "_sanitization_metadata": {
            "sanitized_at": datetime.now(timezone.utc).isoformat(),
            "fields_removed": [],
            "fields_kept": [],
            "sanitizer_version": "1.0.0",
        },
    }
