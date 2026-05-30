"""卫宁 (Winning) WinDHP 5.5 EMR Adapter — SOAP/XML.

Known methods:
  getPatientInfo(codetype, code) — codetype: 1=住院号 2=卡号 3=唯一号
  queryOrder(patientId, startDate, endDate)
  exportReport(patientId)
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


WINNING_NS = "http://www.winning.com.cn/WinDHP"


class WinningAdapter(BaseEMRAdapter):
    """卫宁 WinDHP 5.5 adapter via SOAP/XML."""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.client = httpx.AsyncClient(timeout=settings.EMR_TIMEOUT_SECONDS)

    async def _call(self, method: str, **kwargs: str) -> ET.Element:
        params = "".join(f"<{k}>{v}</{k}>" for k, v in kwargs.items())
        soap_body = (
            f'<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
            f'<soap:Body><{method} xmlns="{WINNING_NS}">{params}</{method}></soap:Body>'
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
        # Try codetype 3 (唯一号) first, then 2 (卡号), then 1 (住院号)
        for codetype in ("3", "2", "1"):
            try:
                root = await self._call("getPatientInfo", codetype=codetype, code=patient_id)
                body = _soap_body(root)
                pe = body.find(".//{*}patientInfo")
                if pe is not None:
                    return FHIRPatient(
                        id=patient_id,
                        identifier=self._find_text(pe, "{*}patientCode"),
                        name=self._find_text(pe, "{*}patientName"),
                        gender=_winning_gender(self._find_text(pe, "{*}sex")),
                        birth_date=self._find_text(pe, "{*}birthday"),
                        phone=self._find_text(pe, "{*}mobile"),
                        address=self._find_text(pe, "{*}address"),
                    )
            except Exception:
                continue
        return FHIRPatient(id=patient_id)

    async def get_allergies(self, patient_id: str) -> list[AllergyIntolerance]:
        try:
            root = await self._call("getPatientInfo", codetype="3", code=patient_id)
            body = _soap_body(root)
            pe = body.find(".//{*}patientInfo")
            if pe is None:
                return []
            results: list[AllergyIntolerance] = []
            for ae in pe.iter("{*}allergy"):
                results.append(AllergyIntolerance(
                    id=self._find_text(ae, "{*}allergyId"),
                    patient_id=patient_id,
                    substance=self._find_text(ae, "{*}allergen"),
                    category="medication",
                    severity=self._find_text(ae, "{*}allergyLevel"),
                    onset_date=self._find_text(ae, "{*}occurDate"),
                ))
            return results
        except Exception:
            return []

    async def get_lab_results(self, patient_id: str, since: date) -> list[Observation]:
        try:
            root = await self._call(
                "queryOrder",
                patientId=patient_id,
                startDate=since.isoformat(),
                endDate=date.today().isoformat(),
            )
            body = _soap_body(root)
            results: list[Observation] = []
            for le in body.iter("{*}orderResult"):
                results.append(Observation(
                    id=self._find_text(le, "{*}orderId"),
                    patient_id=patient_id,
                    code=self._find_text(le, "{*}itemCode"),
                    name=self._find_text(le, "{*}itemName"),
                    value=_safe_float(self._find_text(le, "{*}result")),
                    unit=self._find_text(le, "{*}unit"),
                    effective_date=self._find_text(le, "{*}reportDate"),
                    reference_range=self._find_text(le, "{*}refRange"),
                    status="final",
                ))
            return results
        except Exception:
            return []

    async def get_medications(self, patient_id: str) -> list[MedicationRequest]:
        try:
            root = await self._call(
                "queryOrder",
                patientId=patient_id,
                startDate="2020-01-01",
                endDate=date.today().isoformat(),
            )
            body = _soap_body(root)
            results: list[MedicationRequest] = []
            for me in body.iter("{*}medOrder"):
                results.append(MedicationRequest(
                    id=self._find_text(me, "{*}orderId"),
                    patient_id=patient_id,
                    medication_name=self._find_text(me, "{*}drugName"),
                    dosage=self._find_text(me, "{*}dosage"),
                    frequency=self._find_text(me, "{*}freqCode"),
                    route=self._find_text(me, "{*}routeCode"),
                    start_date=self._find_text(me, "{*}startDate"),
                    end_date=self._find_text(me, "{*}endDate"),
                    status="active",
                ))
            return results
        except Exception:
            return []

    async def get_diagnoses(self, patient_id: str) -> list[Condition]:
        try:
            root = await self._call("getPatientInfo", codetype="3", code=patient_id)
            body = _soap_body(root)
            pe = body.find(".//{*}patientInfo")
            if pe is None:
                return []
            results: list[Condition] = []
            for de in pe.iter("{*}diagnosis"):
                results.append(Condition(
                    id=self._find_text(de, "{*}diagId"),
                    patient_id=patient_id,
                    code=self._find_text(de, "{*}icdCode"),
                    name=self._find_text(de, "{*}diagName"),
                    onset_date=self._find_text(de, "{*}diagDate"),
                    status="active",
                ))
            return results
        except Exception:
            return []

    async def get_pregnancy_status(self, patient_id: str) -> PregnancyStatus | None:
        return None

    async def get_liver_function(self, patient_id: str) -> LiverFunction | None:
        try:
            root = await self._call(
                "queryOrder",
                patientId=patient_id,
                startDate=date.today().replace(year=date.today().year - 1).isoformat(),
                endDate=date.today().isoformat(),
            )
            body = _soap_body(root)
            lf = LiverFunction(patient_id=patient_id)
            for le in body.iter("{*}orderResult"):
                code = self._find_text(le, "{*}itemCode")
                val = _safe_float(self._find_text(le, "{*}result"))
                if "ALT" in code.upper():
                    lf.alt = val
                elif "AST" in code.upper():
                    lf.ast = val
                lf.lab_date = self._find_text(le, "{*}reportDate") or lf.lab_date
            return lf if lf.alt is not None or lf.ast is not None else None
        except Exception:
            return None

    async def get_renal_function(self, patient_id: str) -> RenalFunction | None:
        try:
            root = await self._call(
                "queryOrder",
                patientId=patient_id,
                startDate=date.today().replace(year=date.today().year - 1).isoformat(),
                endDate=date.today().isoformat(),
            )
            body = _soap_body(root)
            rf = RenalFunction(patient_id=patient_id)
            for le in body.iter("{*}orderResult"):
                code = self._find_text(le, "{*}itemCode")
                val = _safe_float(self._find_text(le, "{*}result"))
                if "eGFR" in code.upper():
                    rf.egfr = val
                elif "Cr" in code.upper() or "CREA" in code.upper():
                    rf.creatinine = val
                rf.lab_date = self._find_text(le, "{*}reportDate") or rf.lab_date
            if rf.egfr is not None:
                rf.ckd_stage = _egfr_to_ckd_stage(rf.egfr)
            return rf if rf.egfr is not None or rf.creatinine is not None else None
        except Exception:
            return None

    async def get_encounters(self, patient_id: str, since: date) -> list[Encounter]:
        try:
            root = await self._call(
                "queryOrder",
                patientId=patient_id,
                startDate=since.isoformat(),
                endDate=date.today().isoformat(),
            )
            body = _soap_body(root)
            seen: set[str] = set()
            results: list[Encounter] = []
            for oe in body.iter("{*}orderResult"):
                enc_id = self._find_text(oe, "{*}visitId")
                if enc_id in seen:
                    continue
                seen.add(enc_id)
                results.append(Encounter(
                    id=enc_id,
                    patient_id=patient_id,
                    encounter_type=self._find_text(oe, "{*}visitType"),
                    date=self._find_text(oe, "{*}visitDate"),
                    department=self._find_text(oe, "{*}deptName"),
                    provider=self._find_text(oe, "{*}doctorName"),
                    reason="",
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


def _winning_gender(code: str) -> str:
    mapping = {"0": "U", "1": "M", "2": "F", "男": "M", "女": "F"}
    return mapping.get(code, "U")


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
