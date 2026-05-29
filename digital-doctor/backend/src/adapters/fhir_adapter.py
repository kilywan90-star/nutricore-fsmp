from datetime import date, datetime
from typing import Any
from uuid import UUID


class FHIRPatientAdapter:
    """将FHIR R4 Patient资源转换为内部Patient模型字段"""

    @staticmethod
    def from_fhir(fhir_resource: dict) -> dict[str, Any]:
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
    """FHIR Observation → 实验室检查结果"""

    @staticmethod
    def from_fhir(fhir_resource: dict) -> dict[str, Any]:
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


class FHIRBundleBuilder:
    """构建FHIR Bundle用于批量导入"""

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
