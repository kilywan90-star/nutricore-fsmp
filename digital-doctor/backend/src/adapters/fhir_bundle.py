"""FHIR Bundle handler — parse and build FHIR Bundle resources.

Supports searchset and transaction bundle types as per FHIR R4 spec.
"""

from __future__ import annotations


def parse_fhir_bundle(bundle_json: dict) -> dict[str, list]:
    """Split a FHIR Bundle into categorized resource lists keyed by resourceType.

    Returns a dict like:
        {"Patient": [...], "Observation": [...], "Condition": [...]}
    """
    categorized: dict[str, list] = {}
    entries = bundle_json.get("entry", {} if isinstance(bundle_json.get("entry"), list) else [])
    if isinstance(entries, list):
        for entry in entries:
            resource = entry.get("resource", {})
            rt = resource.get("resourceType", "Unknown")
            if rt not in categorized:
                categorized[rt] = []
            categorized[rt].append(resource)
    return categorized


def build_fhir_bundle(resources: list[dict], resource_type: str, total: int) -> dict:
    """Build a FHIR searchset Bundle from a list of resources.

    Args:
        resources: List of FHIR resource dicts (must include "id" and "resourceType").
        resource_type: The resourceType for the bundle entries.
        total: Total number of results (may differ from len(resources) for pagination).

    Returns:
        A FHIR Bundle dict with type "searchset".
    """
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
