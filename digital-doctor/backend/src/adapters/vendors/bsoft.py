"""创业 (B-Soft) Hi-HIS EMR Adapter — HL7 v2 + FHIR hybrid.

Primary path: FHIR REST endpoints at http://his/fhir/Patient/{id}
Fallback: HL7 v2 ADT^A08 (patient), ORU^R01 (lab results)
"""

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


class BsoftAdapter(BaseEMRAdapter):
    """创业 Hi-HIS adapter — FHIR primary, HL7 v2 fallback."""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint.rstrip("/")
        self.fhir_base = f"{self.endpoint}/fhir"
        self.client = httpx.AsyncClient(timeout=settings.EMR_TIMEOUT_SECONDS)

    # ── FHIR helpers ──────────────────────────────────────────────────────────

    async def _fhir_get(self, resource: str, eid: str) -> dict:
        url = f"{self.fhir_base}/{resource}/{eid}"
        resp = await self.client.get(
            url, headers={"Accept": "application/fhir+json"},
        )
        resp.raise_for_status()
        return resp.json()

    async def _fhir_search(self, resource: str, params: dict) -> dict:
        url = f"{self.fhir_base}/{resource}"
        resp = await self.client.get(
            url, params=params,
            headers={"Accept": "application/fhir+json"},
        )
        resp.raise_for_status()
        return resp.json()

    # ── HL7 v2 helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_hl7_field(segment: str, index: int, sub: int = 0) -> str:
        parts = segment.split("|")
        if index >= len(parts):
            return ""
        field = parts[index]
        if sub > 0:
            subparts = field.split("^")
            return subparts[sub] if sub < len(subparts) else ""
        return field

    # ── adapter methods ───────────────────────────────────────────────────────

    async def get_patient(self, patient_id: str) -> FHIRPatient:
        try:
            data = await self._fhir_get("Patient", patient_id)
            return FHIRPatient(
                id=data.get("id", patient_id),
                identifier=_ext_identifier(data),
                name=_ext_patient_name(data),
                gender=data.get("gender", ""),
                birth_date=data.get("birthDate", ""),
                phone=_ext_telecom(data, "phone"),
                address=_ext_address(data),
            )
        except Exception:
            # Fallback to HL7 v2 ADT^A08
            return await self._get_patient_hl7(patient_id)

    async def _get_patient_hl7(self, patient_id: str) -> FHIRPatient:
        hl7_msg = (
            f"MSH|^~\&|DDD|HIS|HIS|DDD|{_hl7_ts()}||ADT^A08|{patient_id}|P|2.5\r"
            f"EVN|A08|{_hl7_ts()}\r"
            f"PID|1||{patient_id}^^^HIS||^^^^||{_hl7_ts()}|U\r"
        )
        resp = await self.client.post(
            f"{self.endpoint}/hl7",
            content=hl7_msg,
            headers={"Content-Type": "text/plain"},
        )
        resp.raise_for_status()
        body = resp.text
        pid = _get_segment(body, "PID")
        if not pid:
            return FHIRPatient(id=patient_id)
        return FHIRPatient(
            id=patient_id,
            identifier=self._parse_hl7_field(pid, 2),
            name=_hl7_extract_name(pid),
            gender=_hl7_gender(self._parse_hl7_field(pid, 8)),
            birth_date=self._parse_hl7_field(pid, 7),
        )

    async def get_allergies(self, patient_id: str) -> list[AllergyIntolerance]:
        try:
            bundle = await self._fhir_search("AllergyIntolerance", {"patient": patient_id})
            results: list[AllergyIntolerance] = []
            for entry in bundle.get("entry", []):
                r = entry.get("resource", {})
                code, display = _ext_coding(r)
                results.append(AllergyIntolerance(
                    id=r.get("id", ""),
                    patient_id=patient_id,
                    substance=display or code,
                    category=r.get("category", ["medication"])[0] if r.get("category") else "medication",
                    onset_date=r.get("onsetDateTime", ""),
                    recorded_date=r.get("recordedDate", ""),
                    status=r.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "active"),
                ))
            return results
        except Exception:
            return []

    async def get_lab_results(self, patient_id: str, since: date) -> list[Observation]:
        try:
            bundle = await self._fhir_search("Observation", {
                "patient": patient_id,
                "category": "laboratory",
                "date": f"ge{since.isoformat()}",
            })
            return _parse_fhir_observations(bundle, patient_id)
        except Exception:
            # Fallback to HL7 v2 ORU^R01
            return await self._get_lab_results_hl7(patient_id, since)

    async def _get_lab_results_hl7(self, patient_id: str, since: date) -> list[Observation]:
        hl7_msg = (
            f"MSH|^~\&|DDD|HIS|HIS|DDD|{_hl7_ts()}||ORU^R01|{patient_id}|P|2.5\r"
            f"PID|1||{patient_id}\r"
            f"OBR|1|||ALL^FULL PANEL|||{since.isoformat()}\r"
        )
        resp = await self.client.post(
            f"{self.endpoint}/hl7",
            content=hl7_msg,
            headers={"Content-Type": "text/plain"},
        )
        resp.raise_for_status()
        results: list[Observation] = []
        for line in resp.text.strip().split("\r"):
            if line.startswith("OBX"):
                results.append(Observation(
                    id=self._parse_hl7_field(line, 1),
                    patient_id=patient_id,
                    code=self._parse_hl7_field(line, 3, 0),
                    name=self._parse_hl7_field(line, 3, 1),
                    value=_safe_float(self._parse_hl7_field(line, 5)),
                    unit=self._parse_hl7_field(line, 6),
                    effective_date=self._parse_hl7_field(line, 14),
                    reference_range=self._parse_hl7_field(line, 7),
                    status="final",
                ))
        return results

    async def get_medications(self, patient_id: str) -> list[MedicationRequest]:
        try:
            bundle = await self._fhir_search("MedicationRequest", {"patient": patient_id, "status": "active"})
            results: list[MedicationRequest] = []
            for entry in bundle.get("entry", []):
                r = entry.get("resource", {})
                med_ref = r.get("medicationReference", {}).get("display", "")
                med_cc = r.get("medicationCodeableConcept", {})
                med_name = med_ref or med_cc.get("text", "") or med_cc.get("coding", [{}])[0].get("display", "")
                results.append(MedicationRequest(
                    id=r.get("id", ""),
                    patient_id=patient_id,
                    medication_name=med_name,
                    dosage="",
                    frequency="",
                    start_date=r.get("authoredOn", ""),
                    status=r.get("status", "active"),
                ))
            return results
        except Exception:
            return []

    async def get_diagnoses(self, patient_id: str) -> list[Condition]:
        try:
            bundle = await self._fhir_search("Condition", {"patient": patient_id, "clinical-status": "active"})
            results: list[Condition] = []
            for entry in bundle.get("entry", []):
                r = entry.get("resource", {})
                code, display = _ext_coding(r)
                results.append(Condition(
                    id=r.get("id", ""),
                    patient_id=patient_id,
                    code=code,
                    name=display,
                    onset_date=r.get("onsetDateTime", ""),
                    status=r.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "active"),
                ))
            return results
        except Exception:
            return []

    async def get_pregnancy_status(self, patient_id: str) -> PregnancyStatus | None:
        return None

    async def get_liver_function(self, patient_id: str) -> LiverFunction | None:
        try:
            bundle = await self._fhir_search("Observation", {
                "patient": patient_id,
                "code": "ALT,AST",
                "_sort": "-date",
                "_count": "2",
            })
            entries = bundle.get("entry", [])
            if not entries:
                return None
            lf = LiverFunction(patient_id=patient_id)
            for entry in entries:
                r = entry.get("resource", {})
                code, _ = _ext_coding(r)
                vq = r.get("valueQuantity", {})
                val = vq.get("value") if vq else None
                if "ALT" in code.upper():
                    lf.alt = val
                elif "AST" in code.upper():
                    lf.ast = val
                lf.lab_date = r.get("effectiveDateTime", lf.lab_date)
            return lf if lf.alt is not None or lf.ast is not None else None
        except Exception:
            return None

    async def get_renal_function(self, patient_id: str) -> RenalFunction | None:
        try:
            bundle = await self._fhir_search("Observation", {
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
                code, _ = _ext_coding(r)
                vq = r.get("valueQuantity", {})
                val = vq.get("value") if vq else None
                if "eGFR" in code.upper():
                    rf.egfr = val
                elif "creatinine" in code.lower():
                    rf.creatinine = val
                rf.lab_date = r.get("effectiveDateTime", rf.lab_date)
            if rf.egfr is not None:
                rf.ckd_stage = _egfr_to_ckd_stage(rf.egfr)
            return rf if rf.egfr is not None or rf.creatinine is not None else None
        except Exception:
            return None

    async def get_encounters(self, patient_id: str, since: date) -> list[Encounter]:
        try:
            bundle = await self._fhir_search("Encounter", {
                "patient": patient_id,
                "date": f"ge{since.isoformat()}",
            })
            results: list[Encounter] = []
            for entry in bundle.get("entry", []):
                r = entry.get("resource", {})
                period = r.get("period", {})
                cls_info = r.get("class", {})
                if isinstance(cls_info, dict):
                    cls_code = cls_info.get("code", "")
                else:
                    cls_code = str(cls_info) if cls_info else ""
                results.append(Encounter(
                    id=r.get("id", ""),
                    patient_id=patient_id,
                    encounter_type=cls_code,
                    date=period.get("start", ""),
                    department=_ext_enc_dept(r),
                    provider=_ext_enc_provider(r),
                    reason=_ext_enc_reason(r),
                ))
            return results
        except Exception:
            return []

    async def close(self) -> None:
        await self.client.aclose()


# ── shared helpers ────────────────────────────────────────────────────────────

def _ext_identifier(resource: dict) -> str:
    ids = resource.get("identifier", [])
    return ids[0].get("value", "") if ids else ""


def _ext_patient_name(resource: dict) -> str:
    names = resource.get("name", [])
    if not names:
        return ""
    n = names[0]
    text = n.get("text", "")
    if text:
        return text
    given = " ".join(n.get("given", []))
    family = n.get("family", "")
    return f"{family} {given}".strip()


def _ext_telecom(resource: dict, system: str) -> str:
    for t in resource.get("telecom", []):
        if t.get("system") == system:
            return t.get("value", "")
    return ""


def _ext_address(resource: dict) -> str:
    addrs = resource.get("address", [])
    if not addrs:
        return ""
    a = addrs[0]
    return f"{' '.join(a.get('line', []))}, {a.get('city', '')}".strip(", ")


def _ext_coding(resource: dict, path: str = "code") -> tuple[str, str]:
    c = resource.get(path, {}).get("coding", [{}])[0]
    return c.get("code", ""), c.get("display", "")


def _parse_fhir_observations(bundle: dict, patient_id: str) -> list[Observation]:
    results: list[Observation] = []
    for entry in bundle.get("entry", []):
        r = entry.get("resource", {})
        code, display = _ext_coding(r)
        vq = r.get("valueQuantity", {})
        value = vq.get("value") if vq else None
        unit = vq.get("unit", "")
        rr = r.get("referenceRange", [])
        ref_str = ""
        if rr:
            lo = rr[0].get("low", {})
            hi = rr[0].get("high", {})
            lo_v = lo.get("value", "")
            hi_v = hi.get("value", "")
            ref_str = f"{lo_v}-{hi_v}" if lo_v or hi_v else rr[0].get("text", "")
        results.append(Observation(
            id=r.get("id", ""),
            patient_id=patient_id,
            code=code,
            name=display,
            value=value,
            unit=unit,
            effective_date=r.get("effectiveDateTime", ""),
            reference_range=ref_str,
            status=r.get("status", "final"),
        ))
    return results


def _hl7_ts() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d%H%M%S")


def _hl7_gender(code: str) -> str:
    mapping = {"M": "M", "F": "F", "O": "U"}
    return mapping.get(code.upper(), "U")


def _hl7_extract_name(pid_segment: str) -> str:
    """Extract display name from PID-5 (family^given^middle^suffix^prefix)."""
    parts = pid_segment.split("|")
    if len(parts) < 6:
        return ""
    field = parts[5]
    subparts = field.split("^")
    family = subparts[0] if len(subparts) > 0 else ""
    given = subparts[1] if len(subparts) > 1 else ""
    name = f"{family}{given}".strip()
    return name


def _get_segment(text: str, seg_name: str) -> str:
    for line in text.strip().split("\r"):
        if line.startswith(seg_name + "|"):
            return line
    return ""


def _safe_float(s: str) -> float | None:
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _ext_enc_dept(resource: dict) -> str:
    for st in resource.get("serviceType", []):
        return st.get("coding", [{}])[0].get("display", "")
    return ""


def _ext_enc_provider(resource: dict) -> str:
    for p in resource.get("participant", []):
        return p.get("individual", {}).get("display", "")
    return ""


def _ext_enc_reason(resource: dict) -> str:
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
