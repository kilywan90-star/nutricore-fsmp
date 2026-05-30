"""东软 (Neusoft) EMR Adapter — SOAP/XML over CDR.

Interface methods:
  queryPatientById, queryAllergyByPatient, queryLabResultByTime,
  queryMedicationByPatient, queryDiagnosisByPatient
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


NEUSOFT_NS = "http://www.neusoft.com/his/cdr"


class NeusoftAdapter(BaseEMRAdapter):
    """东软 CDR adapter via SOAP/XML."""

    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.client = httpx.AsyncClient(timeout=settings.EMR_TIMEOUT_SECONDS)

    async def _call(self, method: str, **kwargs: str) -> ET.Element:
        params = "".join(f"<{k}>{v}</{k}>" for k, v in kwargs.items())
        soap_body = (
            f'<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">'
            f'<soap:Body><{method} xmlns="{NEUSOFT_NS}">{params}</{method}></soap:Body>'
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

    # ── adapter methods ───────────────────────────────────────────────────────

    async def get_patient(self, patient_id: str) -> FHIRPatient:
        root = await self._call("queryPatientById", patientId=patient_id)
        body = _soap_body(root)
        patient_elem = body.find(".//{*}patient")
        if patient_elem is None:
            return FHIRPatient(id=patient_id)
        return FHIRPatient(
            id=patient_id,
            identifier=self._find_text(patient_elem, "{*}patientId"),
            name=self._find_text(patient_elem, "{*}patientName"),
            gender=_neusoft_gender(self._find_text(patient_elem, "{*}genderCode")),
            birth_date=self._find_text(patient_elem, "{*}birthDate"),
            phone=self._find_text(patient_elem, "{*}phoneNumber"),
            address=self._find_text(patient_elem, "{*}homeAddress"),
        )

    async def get_allergies(self, patient_id: str) -> list[AllergyIntolerance]:
        root = await self._call("queryAllergyByPatient", patientId=patient_id)
        results: list[AllergyIntolerance] = []
        body = _soap_body(root)
        for ae in body.iter("{*}allergyEntry"):
            results.append(AllergyIntolerance(
                id=self._find_text(ae, "{*}allergyId"),
                patient_id=patient_id,
                substance=self._find_text(ae, "{*}allergenName"),
                category=self._find_text(ae, "{*}allergyCategory") or "medication",
                severity=_neusoft_severity(self._find_text(ae, "{*}severity")),
                onset_date=self._find_text(ae, "{*}onsetDate"),
                recorded_date=self._find_text(ae, "{*}recordDate"),
            ))
        return results

    async def get_lab_results(self, patient_id: str, since: date) -> list[Observation]:
        root = await self._call(
            "queryLabResultByTime", patientId=patient_id, startDate=since.isoformat(),
        )
        results: list[Observation] = []
        body = _soap_body(root)
        for le in body.iter("{*}labResult"):
            results.append(Observation(
                id=self._find_text(le, "{*}reportId"),
                patient_id=patient_id,
                code=self._find_text(le, "{*}itemCode"),
                name=self._find_text(le, "{*}itemName"),
                value=_safe_float(self._find_text(le, "{*}resultValue")),
                unit=self._find_text(le, "{*}resultUnit"),
                effective_date=self._find_text(le, "{*}resultDateTime"),
                reference_range=self._find_text(le, "{*}refRange"),
                interpretation=_neusoft_abnormal_flag(self._find_text(le, "{*}abnormalFlag")),
                status="final",
            ))
        return results

    async def get_medications(self, patient_id: str) -> list[MedicationRequest]:
        root = await self._call("queryMedicationByPatient", patientId=patient_id)
        results: list[MedicationRequest] = []
        body = _soap_body(root)
        for me in body.iter("{*}medicationOrder"):
            results.append(MedicationRequest(
                id=self._find_text(me, "{*}orderId"),
                patient_id=patient_id,
                medication_name=self._find_text(me, "{*}drugName"),
                dosage=self._find_text(me, "{*}dosage"),
                frequency=self._find_text(me, "{*}frequency"),
                route=self._find_text(me, "{*}route"),
                start_date=self._find_text(me, "{*}startDate"),
                end_date=self._find_text(me, "{*}stopDate"),
                status=_neusoft_order_status(self._find_text(me, "{*}orderStatus")),
            ))
        return results

    async def get_diagnoses(self, patient_id: str) -> list[Condition]:
        root = await self._call("queryDiagnosisByPatient", patientId=patient_id)
        results: list[Condition] = []
        body = _soap_body(root)
        for de in body.iter("{*}diagnosis"):
            results.append(Condition(
                id=self._find_text(de, "{*}diagId"),
                patient_id=patient_id,
                code=self._find_text(de, "{*}icdCode"),
                name=self._find_text(de, "{*}diagName"),
                severity=self._find_text(de, "{*}severity"),
                onset_date=self._find_text(de, "{*}diagnosisDate"),
                status=_neusoft_diag_status(self._find_text(de, "{*}diagStatus")),
            ))
        return results

    async def get_pregnancy_status(self, patient_id: str) -> PregnancyStatus | None:
        try:
            root = await self._call("queryPatientById", patientId=patient_id)
            body = _soap_body(root)
            pe = body.find(".//{*}patient")
            if pe is None:
                return None
            pregnancy_flag = self._find_text(pe, "{*}pregnancyFlag")
            if pregnancy_flag not in ("1", "true"):
                return None
            gw_text = self._find_text(pe, "{*}gestationalWeeks")
            return PregnancyStatus(
                patient_id=patient_id,
                is_pregnant=True,
                gestational_weeks=int(gw_text) if gw_text else None,
                edd=self._find_text(pe, "{*}edd"),
            )
        except Exception:
            return None

    async def get_liver_function(self, patient_id: str) -> LiverFunction | None:
        try:
            root = await self._call(
                "queryLabResultByTime", patientId=patient_id,
                startDate=date.today().replace(year=date.today().year - 1).isoformat(),
            )
            body = _soap_body(root)
            lf = LiverFunction(patient_id=patient_id)
            for le in body.iter("{*}labResult"):
                code = self._find_text(le, "{*}itemCode")
                val = _safe_float(self._find_text(le, "{*}resultValue"))
                if code in ("ALT", "1742-6"):
                    lf.alt = val
                elif code in ("AST", "1920-8"):
                    lf.ast = val
                lf.lab_date = self._find_text(le, "{*}resultDateTime") or lf.lab_date
            return lf if lf.alt is not None or lf.ast is not None else None
        except Exception:
            return None

    async def get_renal_function(self, patient_id: str) -> RenalFunction | None:
        try:
            root = await self._call(
                "queryLabResultByTime", patientId=patient_id,
                startDate=date.today().replace(year=date.today().year - 1).isoformat(),
            )
            body = _soap_body(root)
            rf = RenalFunction(patient_id=patient_id)
            for le in body.iter("{*}labResult"):
                code = self._find_text(le, "{*}itemCode")
                val = _safe_float(self._find_text(le, "{*}resultValue"))
                if code in ("eGFR", "98979-8"):
                    rf.egfr = val
                elif code in ("Cr", "CREA", "2160-0"):
                    rf.creatinine = val
                rf.lab_date = self._find_text(le, "{*}resultDateTime") or rf.lab_date
            if rf.egfr is not None:
                rf.ckd_stage = _egfr_to_ckd_stage(rf.egfr)
            return rf if rf.egfr is not None or rf.creatinine is not None else None
        except Exception:
            return None

    async def get_encounters(self, patient_id: str, since: date) -> list[Encounter]:
        root = await self._call(
            "queryDiagnosisByPatient", patientId=patient_id,
        )
        results: list[Encounter] = []
        body = _soap_body(root)
        for de in body.iter("{*}diagnosis"):
            enc_date = self._find_text(de, "{*}diagnosisDate")
            if enc_date < since.isoformat():
                continue
            results.append(Encounter(
                id="enc-" + self._find_text(de, "{*}diagId"),
                patient_id=patient_id,
                encounter_type="outpatient",
                date=enc_date,
                department=self._find_text(de, "{*}deptName"),
                provider="",
                reason=self._find_text(de, "{*}diagName"),
            ))
        return results

    async def close(self) -> None:
        await self.client.aclose()


# ── helpers ───────────────────────────────────────────────────────────────────

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


def _neusoft_gender(code: str) -> str:
    mapping = {"0": "U", "1": "M", "2": "F"}
    return mapping.get(code, code or "U")


def _neusoft_severity(code: str) -> str:
    mapping = {"0": "", "1": "mild", "2": "moderate", "3": "severe"}
    return mapping.get(code, code)


def _neusoft_abnormal_flag(code: str) -> str:
    mapping = {"N": "normal", "L": "low", "H": "high", "A": "abnormal"}
    return mapping.get(code, "")


def _neusoft_order_status(code: str) -> str:
    mapping = {"0": "active", "1": "stopped", "2": "completed"}
    return mapping.get(code, "active")


def _neusoft_diag_status(code: str) -> str:
    mapping = {"0": "active", "1": "resolved", "2": "inactive"}
    return mapping.get(code, "active")


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
