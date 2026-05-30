"""FHIR R4 Standard EMR Adapter — connects to any FHIR R4 compliant server.

Maps FHIR resources directly to internal models. Configurable base URL.
"""

import json
from datetime import date
from typing import Any

import httpx

from ..emr_base import (
    AllergyIntolerance,
    BaseEMRAdapter,
    Condition,
    Encounter,
    FHIRPatient,
    LiverFunction,
    MedicationRequest,
    Observation,
    PregnancyStatus,
    RenalFunction,
)
from ...config import settings


class FHIRStandardAdapter(BaseEMRAdapter):
    """Adapter for FHIR R4 compliant EMR servers."""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint.rstrip("/")
        self.client = httpx.AsyncClient(
            timeout=settings.EMR_TIMEOUT_SECONDS,
            headers={"Accept": "application/fhir+json"},
        )

    # ── helpers ─────────────────────────────────────────────────────────────────

    async def _get(self, resource: str, eid: str, params: dict | None = None) -> dict:
        url = f"{self.endpoint}/{resource}/{eid}" if eid else f"{self.endpoint}/{resource}"
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    async def _search(self, resource: str, params: dict) -> dict:
        url = f"{self.endpoint}/{resource}"
        resp = await self.client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _ext_identifier(resource: dict) -> str:
        ids = resource.get("identifier", [])
        return ids[0].get("value", "") if ids else ""

    @staticmethod
    def _ext_coding(resource: dict, path: str = "code") -> tuple[str, str]:
        c = resource.get(path, {}).get("coding", [{}])[0]
        return c.get("code", ""), c.get("display", "")

    @staticmethod
    def _ext_value(resource: dict) -> tuple[float | None, str]:
        vq = resource.get("valueQuantity", {})
        vs = resource.get("valueString")
        if vq:
            return vq.get("value"), vq.get("unit", "")
        if vs:
            try:
                return float(vs), ""
            except (ValueError, TypeError):
                return None, str(vs)
        return None, ""

    # ── adapter methods ─────────────────────────────────────────────────────────

    async def get_patient(self, patient_id: str) -> FHIRPatient:
        data = await self._get("Patient", patient_id)
        return FHIRPatient(
            id=data.get("id", patient_id),
            identifier=self._ext_identifier(data),
            name=_extract_patient_name(data),
            gender=data.get("gender", ""),
            birth_date=data.get("birthDate", ""),
            phone=_extract_telecom(data, "phone"),
            address=_extract_address(data),
        )

    async def get_allergies(self, patient_id: str) -> list[AllergyIntolerance]:
        bundle = await self._search("AllergyIntolerance", {"patient": patient_id})
        results: list[AllergyIntolerance] = []
        for entry in bundle.get("entry", []):
            r = entry.get("resource", {})
            code, display = self._ext_coding(r)
            results.append(AllergyIntolerance(
                id=r.get("id", ""),
                patient_id=r.get("patient", {}).get("reference", "").replace("Patient/", ""),
                substance=display or code,
                category=r.get("category", ["medication"])[0] if r.get("category") else "medication",
                severity=_extract_severity(r),
                status=r.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "active"),
                onset_date=r.get("onsetDateTime", ""),
                recorded_date=r.get("recordedDate", ""),
            ))
        return results

    async def get_lab_results(self, patient_id: str, since: date) -> list[Observation]:
        bundle = await self._search("Observation", {
            "patient": patient_id,
            "category": "laboratory",
            "date": f"ge{since.isoformat()}",
        })
        results: list[Observation] = []
        for entry in bundle.get("entry", []):
            r = entry.get("resource", {})
            code, display = self._ext_coding(r)
            value, unit = self._ext_value(r)
            ref = _extract_ref_range(r)
            results.append(Observation(
                id=r.get("id", ""),
                patient_id=patient_id,
                code=code,
                name=display,
                value=value,
                unit=unit,
                effective_date=r.get("effectiveDateTime", ""),
                reference_range=ref,
                interpretation=_extract_interpretation(r),
                status=r.get("status", "final"),
            ))
        return results

    async def get_medications(self, patient_id: str) -> list[MedicationRequest]:
        bundle = await self._search("MedicationRequest", {"patient": patient_id, "status": "active"})
        results: list[MedicationRequest] = []
        for entry in bundle.get("entry", []):
            r = entry.get("resource", {})
            med_ref = r.get("medicationReference", {}).get("display", "")
            med_cc = r.get("medicationCodeableConcept", {})
            med_name = med_ref or _extract_text(med_cc)
            dosage_instr = r.get("dosageInstruction", [{}])
            d = dosage_instr[0] if dosage_instr else {}
            timing = d.get("timing", {})
            freq = ""
            if timing.get("code"):
                freq = timing["code"].get("coding", [{}])[0].get("code", "")
            results.append(MedicationRequest(
                id=r.get("id", ""),
                patient_id=patient_id,
                medication_name=med_name,
                dosage=_format_dosage_qty(d),
                frequency=freq,
                route=_extract_route(d),
                start_date=r.get("authoredOn", ""),
                end_date="",
                status=r.get("status", "active"),
            ))
        return results

    async def get_diagnoses(self, patient_id: str) -> list[Condition]:
        bundle = await self._search("Condition", {"patient": patient_id, "clinical-status": "active"})
        results: list[Condition] = []
        for entry in bundle.get("entry", []):
            r = entry.get("resource", {})
            code, display = self._ext_coding(r)
            results.append(Condition(
                id=r.get("id", ""),
                patient_id=patient_id,
                code=code,
                name=display,
                category="diagnosis",
                severity=_extract_severity(r),
                onset_date=r.get("onsetDateTime", ""),
                status=r.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "active"),
            ))
        return results

    async def get_pregnancy_status(self, patient_id: str) -> PregnancyStatus | None:
        try:
            bundle = await self._search("Observation", {
                "patient": patient_id,
                "code": "82810-3",   # LOINC for pregnancy status
                "_sort": "-date",
                "_count": "1",
            })
            entries = bundle.get("entry", [])
            if not entries:
                return None
            r = entries[0].get("resource", {})
            vc = r.get("valueCodeableConcept", {})
            code = vc.get("coding", [{}])[0].get("code", "")
            is_pregnant = code == "LA15173-0"  # Pregnant
            # Try to get gestational age
            gw = None
            for comp in r.get("component", []):
                if "82810-3" not in json.dumps(comp):
                    continue
                vq = comp.get("valueQuantity", {})
                gw = int(vq.get("value", 0)) if vq.get("value") else None
            return PregnancyStatus(
                patient_id=patient_id,
                is_pregnant=is_pregnant,
                gestational_weeks=gw,
                last_confirmed_date=r.get("effectiveDateTime", ""),
            )
        except Exception:
            return None

    async def get_liver_function(self, patient_id: str) -> LiverFunction | None:
        try:
            params = {
                "patient": patient_id,
                "code": "ALT,AST",  # Common LOINC combos
                "_sort": "-date",
                "_count": "2",
            }
            bundle = await self._search("Observation", params)
            entries = bundle.get("entry", [])
            if not entries:
                return None
            lf = LiverFunction(patient_id=patient_id)
            for entry in entries:
                r = entry.get("resource", {})
                code, _ = self._ext_coding(r)
                value, _unit = self._ext_value(r)
                if "ALT" in code.upper() or "1742-6" in code:
                    lf.alt = value
                elif "AST" in code.upper() or "1920-8" in code:
                    lf.ast = value
                lf.lab_date = r.get("effectiveDateTime", lf.lab_date)
            return lf
        except Exception:
            return None

    async def get_renal_function(self, patient_id: str) -> RenalFunction | None:
        try:
            bundle = await self._search("Observation", {
                "patient": patient_id,
                "code": "creatinine,eGFR",
                "_sort": "-date",
                "_count": "2",
            })
            entries = bundle.get("entry", [])
            if not entries:
                return None
            rf = RenalFunction(patient_id=patient_id)
            for entry in entries:
                r = entry.get("resource", {})
                code, _ = self._ext_coding(r)
                value, _unit = self._ext_value(r)
                if "eGFR" in code.upper() or "98979-8" in code:
                    rf.egfr = value
                elif "creatinine" in code.lower() or "Creatinine" in code:
                    rf.creatinine = value
                rf.lab_date = r.get("effectiveDateTime", rf.lab_date)
            if rf.egfr is not None:
                rf.ckd_stage = _egfr_to_ckd_stage(rf.egfr)
            return rf
        except Exception:
            return None

    async def get_encounters(self, patient_id: str, since: date) -> list[Encounter]:
        bundle = await self._search("Encounter", {
            "patient": patient_id,
            "date": f"ge{since.isoformat()}",
        })
        results: list[Encounter] = []
        for entry in bundle.get("entry", []):
            r = entry.get("resource", {})
            period = r.get("period", {})
            results.append(Encounter(
                id=r.get("id", ""),
                patient_id=patient_id,
                encounter_type=_extract_encounter_class(r),
                date=period.get("start", ""),
                department=_extract_dept(r),
                provider=_extract_provider(r),
                reason=_extract_reason(r),
                discharge_disposition="",
            ))
        return results

    async def close(self) -> None:
        await self.client.aclose()


# ── shared extraction helpers ───────────────────────────────────────────────────

def _extract_patient_name(resource: dict) -> str:
    names = resource.get("name", [])
    if not names:
        return ""
    n = names[0]
    parts = [n.get("text", "")]
    if not parts[0]:
        given = " ".join(n.get("given", []))
        family = n.get("family", "")
        parts = [f"{family} {given}".strip()]
    return parts[0]


def _extract_telecom(resource: dict, system: str) -> str:
    for t in resource.get("telecom", []):
        if t.get("system") == system:
            return t.get("value", "")
    return ""


def _extract_address(resource: dict) -> str:
    addrs = resource.get("address", [])
    if not addrs:
        return ""
    a = addrs[0]
    line = a.get("line", [])
    city = a.get("city", "")
    state = a.get("state", "")
    return f"{' '.join(line)}, {city}, {state}".strip(", ")


def _extract_severity(resource: dict) -> str:
    sev = resource.get("severity")
    if isinstance(sev, dict):
        return sev.get("coding", [{}])[0].get("code", "")
    return str(sev) if sev else ""


def _extract_ref_range(resource: dict) -> str:
    rr = resource.get("referenceRange", [])
    if not rr:
        return ""
    lo = rr[0].get("low", {})
    hi = rr[0].get("high", {})
    lo_v = lo.get("value", "")
    hi_v = hi.get("value", "")
    if lo_v or hi_v:
        return f"{lo_v}-{hi_v}"
    text = rr[0].get("text", "")
    return text


def _extract_interpretation(resource: dict) -> str:
    interp = resource.get("interpretation", [])
    if not interp:
        return ""
    return interp[0].get("coding", [{}])[0].get("code", "")


def _extract_text(concept: dict) -> str:
    return concept.get("text", "") or concept.get("coding", [{}])[0].get("display", "")


def _format_dosage_qty(dosage: dict) -> str:
    dq = dosage.get("doseQuantity", dosage.get("doseAndRate", [{}]))
    if isinstance(dq, list):
        dq = dq[0].get("doseQuantity", {}) if dq else {}
    val = dq.get("value", "")
    unit = dq.get("unit", "")
    if val:
        return f"{val} {unit}".strip()
    text = dosage.get("text", "")
    return text


def _extract_route(dosage: dict) -> str:
    route = dosage.get("route", {})
    return route.get("coding", [{}])[0].get("code", "")


def _extract_encounter_class(resource: dict) -> str:
    cls = resource.get("class", {})
    if isinstance(cls, dict):
        return cls.get("code", "")
    return str(cls) if cls else ""


def _extract_dept(resource: dict) -> str:
    for st in resource.get("serviceType", []):
        return st.get("coding", [{}])[0].get("display", "")
    return ""


def _extract_provider(resource: dict) -> str:
    for p in resource.get("participant", []):
        ind = p.get("individual", {}).get("display", "")
        if ind:
            return ind
    return ""


def _extract_reason(resource: dict) -> str:
    for r in resource.get("reasonCode", []):
        return r.get("text", "") or r.get("coding", [{}])[0].get("display", "")
    return ""


def _egfr_to_ckd_stage(egfr: float) -> int:
    if egfr >= 90:
        return 1
    if egfr >= 60:
        return 2
    if egfr >= 45:
        return 3
    if egfr >= 30:
        return 3
    if egfr >= 15:
        return 4
    return 5
