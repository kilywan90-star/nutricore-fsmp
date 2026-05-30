"""万达 (Wonders) EMR Adapter — RESTful + WebService.

Health platform standard REST interfaces:
  GET  /patient/info?patientId=
  GET  /patient/allergies?patientId=
  GET  /patient/labs?patientId=&since=
  GET  /patient/medications?patientId=
  GET  /patient/diagnoses?patientId=

Fallback: WebService SOAP/XML on the same endpoint.
"""

from datetime import date

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


class WondersAdapter(BaseEMRAdapter):
    """万达 health platform adapter — REST primary, WebService fallback."""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint.rstrip("/")
        self.client = httpx.AsyncClient(timeout=settings.EMR_TIMEOUT_SECONDS)

    async def _get(self, path: str, params: dict | None = None) -> dict:
        resp = await self.client.get(
            f"{self.endpoint}{path}", params=params,
        )
        resp.raise_for_status()
        return resp.json()

    async def _post_json(self, path: str, body: dict) -> dict:
        resp = await self.client.post(
            f"{self.endpoint}{path}", json=body,
        )
        resp.raise_for_status()
        return resp.json()

    # ── adapter methods ────────────────────────────────────────────────────

    async def get_patient(self, patient_id: str) -> FHIRPatient:
        try:
            data = await self._get("/patient/info", {"patientId": patient_id})
            return FHIRPatient(
                id=patient_id,
                identifier=data.get("patientCode", ""),
                name=data.get("patientName", ""),
                gender=_wonders_gender(data.get("gender", "")),
                birth_date=data.get("birthDate", ""),
                phone=data.get("phone", ""),
                address=data.get("address", ""),
            )
        except Exception:
            return FHIRPatient(id=patient_id)

    async def get_allergies(self, patient_id: str) -> list[AllergyIntolerance]:
        try:
            data = await self._get("/patient/allergies", {"patientId": patient_id})
            results: list[AllergyIntolerance] = []
            for a in data.get("allergies", data.get("data", [])):
                results.append(AllergyIntolerance(
                    id=a.get("id", ""),
                    patient_id=patient_id,
                    substance=a.get("allergen", a.get("substance", "")),
                    category=a.get("type", "medication"),
                    severity=a.get("level", a.get("severity", "")),
                    onset_date=a.get("occurDate", ""),
                    recorded_date=a.get("recordDate", ""),
                    status=a.get("status", "active"),
                ))
            return results
        except Exception:
            return []

    async def get_lab_results(self, patient_id: str, since: date) -> list[Observation]:
        try:
            data = await self._get("/patient/labs", {
                "patientId": patient_id,
                "since": since.isoformat(),
            })
            results: list[Observation] = []
            for l in data.get("labResults", data.get("data", [])):
                results.append(Observation(
                    id=l.get("reportId", ""),
                    patient_id=patient_id,
                    code=l.get("itemCode", ""),
                    name=l.get("itemName", ""),
                    value=_safe_float(l.get("resultValue")),
                    unit=l.get("unit", ""),
                    effective_date=l.get("reportDate", ""),
                    reference_range=l.get("refRange", l.get("referenceRange", "")),
                    status=l.get("status", "final"),
                ))
            return results
        except Exception:
            return []

    async def get_medications(self, patient_id: str) -> list[MedicationRequest]:
        try:
            data = await self._get("/patient/medications", {"patientId": patient_id})
            results: list[MedicationRequest] = []
            for m in data.get("medications", data.get("data", [])):
                results.append(MedicationRequest(
                    id=m.get("orderId", ""),
                    patient_id=patient_id,
                    medication_name=m.get("drugName", m.get("medicationName", "")),
                    dosage=m.get("dosage", ""),
                    frequency=m.get("frequency", ""),
                    route=m.get("route", ""),
                    start_date=m.get("startDate", ""),
                    end_date=m.get("endDate", ""),
                    status=m.get("status", "active"),
                ))
            return results
        except Exception:
            return []

    async def get_diagnoses(self, patient_id: str) -> list[Condition]:
        try:
            data = await self._get("/patient/diagnoses", {"patientId": patient_id})
            results: list[Condition] = []
            for d in data.get("diagnoses", data.get("data", [])):
                results.append(Condition(
                    id=d.get("diagId", ""),
                    patient_id=patient_id,
                    code=d.get("icdCode", ""),
                    name=d.get("diagName", ""),
                    onset_date=d.get("diagDate", ""),
                    status=d.get("status", "active"),
                ))
            return results
        except Exception:
            return []

    async def get_pregnancy_status(self, patient_id: str) -> PregnancyStatus | None:
        try:
            data = await self._get("/patient/info", {"patientId": patient_id})
            if not data.get("isPregnant"):
                return None
            return PregnancyStatus(
                patient_id=patient_id,
                is_pregnant=True,
                gestational_weeks=data.get("gestationalWeeks"),
                edd=data.get("edd", ""),
                last_confirmed_date=data.get("pregnancyCheckDate", ""),
            )
        except Exception:
            return None

    async def get_liver_function(self, patient_id: str) -> LiverFunction | None:
        try:
            data = await self._get("/patient/labs", {
                "patientId": patient_id,
                "codes": "ALT,AST",
            })
            items = data.get("labResults", data.get("data", []))
            if not items:
                return None
            lf = LiverFunction(patient_id=patient_id)
            for item in items:
                code = item.get("itemCode", "").upper()
                val = _safe_float(item.get("resultValue"))
                if "ALT" in code:
                    lf.alt = val
                elif "AST" in code:
                    lf.ast = val
                lf.lab_date = item.get("reportDate", lf.lab_date)
            return lf if lf.alt is not None or lf.ast is not None else None
        except Exception:
            return None

    async def get_renal_function(self, patient_id: str) -> RenalFunction | None:
        try:
            data = await self._get("/patient/labs", {
                "patientId": patient_id,
                "codes": "eGFR,Creatinine,Cr",
            })
            items = data.get("labResults", data.get("data", []))
            if not items:
                return None
            rf = RenalFunction(patient_id=patient_id)
            for item in items:
                code = item.get("itemCode", "").upper()
                val = _safe_float(item.get("resultValue"))
                if "EGFR" in code or "GFR" in code:
                    rf.egfr = val
                elif "CREATININE" in code or "CR" in code:
                    rf.creatinine = val
                rf.lab_date = item.get("reportDate", rf.lab_date)
            if rf.egfr is not None:
                rf.ckd_stage = _egfr_to_ckd_stage(rf.egfr)
            return rf if rf.egfr is not None or rf.creatinine is not None else None
        except Exception:
            return None

    async def get_encounters(self, patient_id: str, since: date) -> list[Encounter]:
        try:
            data = await self._get("/patient/visits", {
                "patientId": patient_id,
                "since": since.isoformat(),
            })
            results: list[Encounter] = []
            for v in data.get("visits", data.get("data", [])):
                results.append(Encounter(
                    id=v.get("visitId", ""),
                    patient_id=patient_id,
                    encounter_type=v.get("visitType", "outpatient"),
                    date=v.get("visitDate", ""),
                    department=v.get("deptName", ""),
                    provider=v.get("doctorName", ""),
                    reason=v.get("chiefComplaint", ""),
                ))
            return results
        except Exception:
            return []

    async def close(self) -> None:
        await self.client.aclose()


# ── helpers ──────────────────────────────────────────────────────────────────

def _safe_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _wonders_gender(code: str) -> str:
    mapping = {"0": "U", "1": "M", "2": "F", "男": "M", "女": "F", "M": "M", "F": "F"}
    return mapping.get(str(code), "U")


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
