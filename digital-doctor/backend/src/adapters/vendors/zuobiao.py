"""深圳坐标 (Zuobiao) HealthOne EMR Adapter — WebService V6.0.1 + stored procedures.

Known WebService methods: getPatientInfo
Known views: patient_exam_order
Known SPs: Pacs_VBI1_Update, PACS_PAP1_Edit
"""

import xml.etree.ElementTree as ET
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


ZUOBIAO_NS = "http://www.zuobiao.com.cn/HealthOne"


class ZuobiaoAdapter(BaseEMRAdapter):
    """深圳坐标 HealthOne V6.0.1 adapter via WebService."""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.client = httpx.AsyncClient(timeout=settings.EMR_TIMEOUT_SECONDS)

    async def _call(self, method: str, **kwargs: str) -> ET.Element:
        params = "".join(f"<{k}>{v}</{k}>" for k, v in kwargs.items())
        soap_body = (
            f'<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
            f'<soap:Body><{method} xmlns="{ZUOBIAO_NS}">{params}</{method}></soap:Body>'
            f"</soap:Envelope>"
        )
        resp = await self.client.post(
            self.endpoint,
            content=soap_body,
            headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": method},
        )
        resp.raise_for_status()
        return ET.fromstring(resp.text)

    @staticmethod
    def _find_text(elem: ET.Element, tag: str) -> str:
        found = elem.find(tag)
        return found.text.strip() if found is not None and found.text else ""

    # ── adapter methods ────────────────────────────────────────────────────

    async def get_patient(self, patient_id: str) -> FHIRPatient:
        try:
            root = await self._call("getPatientInfo", patientId=patient_id)
            body = _soap_body(root)
            pe = body.find(".//{*}patientInfo")
            if pe is None:
                return FHIRPatient(id=patient_id)
            return FHIRPatient(
                id=patient_id,
                identifier=self._find_text(pe, "{*}patientId"),
                name=self._find_text(pe, "{*}patientName"),
                gender=_zuobiao_gender(self._find_text(pe, "{*}gender")),
                birth_date=self._find_text(pe, "{*}birthday"),
                phone=self._find_text(pe, "{*}tel"),
                address=self._find_text(pe, "{*}homeAddr"),
            )
        except Exception:
            return FHIRPatient(id=patient_id)

    async def get_allergies(self, patient_id: str) -> list[AllergyIntolerance]:
        try:
            root = await self._call("getPatientInfo", patientId=patient_id)
            body = _soap_body(root)
            pe = body.find(".//{*}patientInfo")
            if pe is None:
                return []
            results: list[AllergyIntolerance] = []
            for ae in pe.iter("{*}allergyInfo"):
                results.append(AllergyIntolerance(
                    id=self._find_text(ae, "{*}allergyId"),
                    patient_id=patient_id,
                    substance=self._find_text(ae, "{*}allergen"),
                    category="medication",
                    severity=self._find_text(ae, "{*}allergyLevel"),
                    recorded_date=self._find_text(ae, "{*}recordDate"),
                ))
            return results
        except Exception:
            return []

    async def get_lab_results(self, patient_id: str, since: date) -> list[Observation]:
        try:
            root = await self._call(
                "getPatientInfo", patientId=patient_id,
            )
            body = _soap_body(root)
            results: list[Observation] = []
            for le in body.iter("{*}examResult"):
                result_date = self._find_text(le, "{*}examDate")
                if result_date < since.isoformat():
                    continue
                results.append(Observation(
                    id=self._find_text(le, "{*}examId"),
                    patient_id=patient_id,
                    code=self._find_text(le, "{*}itemCode"),
                    name=self._find_text(le, "{*}itemName"),
                    value=_safe_float(self._find_text(le, "{*}resultValue")),
                    unit=self._find_text(le, "{*}resultUnit"),
                    effective_date=result_date,
                    reference_range=self._find_text(le, "{*}normalRange"),
                    status="final",
                ))
            return results
        except Exception:
            return []

    async def get_medications(self, patient_id: str) -> list[MedicationRequest]:
        try:
            root = await self._call("getPatientInfo", patientId=patient_id)
            body = _soap_body(root)
            pe = body.find(".//{*}patientInfo")
            if pe is None:
                return []
            results: list[MedicationRequest] = []
            for me in pe.iter("{*}drugOrder"):
                results.append(MedicationRequest(
                    id=self._find_text(me, "{*}orderId"),
                    patient_id=patient_id,
                    medication_name=self._find_text(me, "{*}drugName"),
                    dosage=self._find_text(me, "{*}dosage"),
                    frequency=self._find_text(me, "{*}freq}"),
                    route=self._find_text(me, "{*}route}"),
                    start_date=self._find_text(me, "{*}startDate"),
                    end_date=self._find_text(me, "{*}endDate"),
                    status=_zuobiao_order_status(self._find_text(me, "{*}orderStatus")),
                ))
            return results
        except Exception:
            return []

    async def get_diagnoses(self, patient_id: str) -> list[Condition]:
        try:
            root = await self._call("getPatientInfo", patientId=patient_id)
            body = _soap_body(root)
            pe = body.find(".//{*}patientInfo")
            if pe is None:
                return []
            results: list[Condition] = []
            for de in pe.iter("{*}diagInfo"):
                results.append(Condition(
                    id=self._find_text(de, "{*}diagId"),
                    patient_id=patient_id,
                    code=self._find_text(de, "{*}icdCode"),
                    name=self._find_text(de, "{*}diagName"),
                    onset_date=self._find_text(de, "{*}diagDate"),
                    status=_zuobiao_diag_status(self._find_text(de, "{*}diagType")),
                ))
            return results
        except Exception:
            return []

    async def get_pregnancy_status(self, patient_id: str) -> PregnancyStatus | None:
        return None

    async def get_liver_function(self, patient_id: str) -> LiverFunction | None:
        try:
            root = await self._call("getPatientInfo", patientId=patient_id)
            body = _soap_body(root)
            lf = LiverFunction(patient_id=patient_id)
            for le in body.iter("{*}examResult"):
                code = self._find_text(le, "{*}itemCode")
                val = _safe_float(self._find_text(le, "{*}resultValue"))
                if "ALT" in code.upper():
                    lf.alt = val
                elif "AST" in code.upper():
                    lf.ast = val
                lf.lab_date = self._find_text(le, "{*}examDate") or lf.lab_date
            return lf if lf.alt is not None or lf.ast is not None else None
        except Exception:
            return None

    async def get_renal_function(self, patient_id: str) -> RenalFunction | None:
        try:
            root = await self._call("getPatientInfo", patientId=patient_id)
            body = _soap_body(root)
            rf = RenalFunction(patient_id=patient_id)
            for le in body.iter("{*}examResult"):
                code = self._find_text(le, "{*}itemCode")
                val = _safe_float(self._find_text(le, "{*}resultValue"))
                if "eGFR" in code.upper():
                    rf.egfr = val
                elif any(kw in code.upper() for kw in ("CR", "CREA", "CREATININE")):
                    rf.creatinine = val
                rf.lab_date = self._find_text(le, "{*}examDate") or rf.lab_date
            if rf.egfr is not None:
                rf.ckd_stage = _egfr_to_ckd_stage(rf.egfr)
            return rf if rf.egfr is not None or rf.creatinine is not None else None
        except Exception:
            return None

    async def get_encounters(self, patient_id: str, since: date) -> list[Encounter]:
        try:
            root = await self._call("getPatientInfo", patientId=patient_id)
            body = _soap_body(root)
            seen: set[str] = set()
            results: list[Encounter] = []
            for ve in body.iter("{*}visitInfo"):
                visit_date = self._find_text(ve, "{*}visitDate")
                if visit_date < since.isoformat():
                    continue
                visit_id = self._find_text(ve, "{*}visitId")
                if visit_id in seen:
                    continue
                seen.add(visit_id)
                results.append(Encounter(
                    id=visit_id,
                    patient_id=patient_id,
                    encounter_type=_zuobiao_visit_type(self._find_text(ve, "{*}visitType")),
                    date=visit_date,
                    department=self._find_text(ve, "{*}deptName"),
                    provider=self._find_text(ve, "{*}doctorName"),
                    reason=self._find_text(ve, "{*}chiefComplaint"),
                ))
            return results
        except Exception:
            return []

    async def close(self) -> None:
        await self.client.aclose()


# ── helpers ──────────────────────────────────────────────────────────────────

def _soap_body(root: ET.Element) -> ET.Element:
    for elem in root.iter():
        if "Body" in elem.tag:
            return elem
    return root


def _safe_float(s: str) -> float | None:
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _zuobiao_gender(code: str) -> str:
    mapping = {"0": "U", "1": "M", "2": "F", "M": "M", "F": "F", "男": "M", "女": "F"}
    return mapping.get(str(code), "U")


def _zuobiao_order_status(code: str) -> str:
    mapping = {"0": "active", "1": "stopped", "2": "completed"}
    return mapping.get(code, "active")


def _zuobiao_diag_status(code: str) -> str:
    mapping = {"0": "active", "1": "resolved", "确诊": "active", "排除": "resolved"}
    return mapping.get(code, "active")


def _zuobiao_visit_type(code: str) -> str:
    mapping = {"1": "outpatient", "2": "inpatient", "3": "emergency", "门诊": "outpatient", "住院": "inpatient", "急诊": "emergency"}
    return mapping.get(code, "outpatient")


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
