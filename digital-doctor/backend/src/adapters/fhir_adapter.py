"""FHIR R4 adapter — FHIR Patient / Observation conversion and Bundle building.

This module provides the primary FHIR integration surface for the digital-doctor
backend. It maintains backward compatibility with the minimal adapters while
re-exporting the complete FHIR resource model classes from fhir_resources.

For full FHIR R4 resource models (Condition, MedicationRequest, AllergyIntolerance,
DiagnosticReport, CarePlan, Procedure, Immunization, DocumentReference), import
from src.adapters.fhir_resources directly.
"""

from src.adapters.fhir_resources import (  # noqa: F401 — re-export for convenience
    FHIRAllergyIntolerance,
    FHIRCarePlan,
    FHIRCondition,
    FHIRDiagnosticReport,
    FHIRDocumentReference,
    FHIRImmunization,
    FHIRMedicationRequest,
    FHIRPatient,
    FHIRProcedure,
)


class FHIRPatientAdapter:
    """FHIR R4 Patient resource to internal Patient model fields.

    This adapter is the legacy interface; for new code prefer
    FHIRPatient.from_fhir_resource() / .to_fhir_json() from fhir_resources.
    """

    @staticmethod
    def from_fhir(fhir_resource: dict) -> dict:
        return {
            "fhir_id": fhir_resource.get("id"),
            "gender": _extract_gender(fhir_resource),
            "birth_year": _extract_birth_year(fhir_resource),
            "identifier": _extract_identifier(fhir_resource),
        }

    @staticmethod
    def to_fhir(patient: dict) -> dict:
        return {
            "resourceType": "Patient",
            "id": patient.get("fhir_id"),
            "gender": patient.get("gender", "unknown"),
            "birthDate": f"{patient.get('birth_year', '')}",
        }


class FHIRObservationAdapter:
    """FHIR Observation to lab test results.

    This adapter is the legacy interface; for full Observation handling
    use the resource model pattern from fhir_resources.
    """

    @staticmethod
    def from_fhir(fhir_resource: dict) -> dict:
        code = fhir_resource.get("code", {}).get("coding", [{}])[0].get("code", "unknown")
        value = fhir_resource.get("valueQuantity", {}).get("value")
        unit = fhir_resource.get("valueQuantity", {}).get("unit", "")
        effective = fhir_resource.get("effectiveDateTime", "")
        return {
            "code": code,
            "value": value,
            "unit": unit,
            "effective_date": effective,
        }


def _extract_gender(resource: dict) -> str:
    g = resource.get("gender", "unknown")
    mapping = {"male": "M", "female": "F"}
    return mapping.get(g, "U")


def _extract_birth_year(resource: dict) -> int:
    birth_date = resource.get("birthDate", "1970")
    try:
        return int(birth_date[:4])
    except (ValueError, TypeError):
        return 1970


def _extract_identifier(resource: dict) -> str:
    identifiers = resource.get("identifier", [])
    if identifiers:
        return identifiers[0].get("value", "")
    return ""


class FHIRBundleBuilder:
    """Build FHIR Bundle for batch import.

    For full Bundle parsing/building, see src.adapters.fhir_bundle.
    """

    @staticmethod
    def build_search_bundle(resources: list[dict], resource_type: str, total: int) -> dict:
        return {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": total,
            "entry": [
                {
                    "fullUrl": f"urn:uuid:{r.get('id', '')}",
                    "resource": {"resourceType": resource_type, **r},
                }
                for r in resources
            ],
        }
