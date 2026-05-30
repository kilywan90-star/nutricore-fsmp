"""FHIR R4 Complete Resource Models.

Provides full FHIR R4 resource classes with from_fhir_resource() / to_fhir_json()
for bidirectional conversion between internal data structures and FHIR JSON.

Resource types covered:
  - Patient
  - Condition (diagnosis / problem)
  - MedicationRequest (prescription)
  - AllergyIntolerance
  - DiagnosticReport
  - CarePlan
  - Procedure
  - Immunization
  - DocumentReference
"""

from __future__ import annotations

from typing import Any


class FHIRPatient:
    """FHIR R4 Patient resource."""

    def __init__(
        self,
        id: str = "",
        name: str = "",
        gender: str = "unknown",
        birth_date: str = "",
        identifier: str = "",
    ):
        self.id = id
        self.name = name
        self.gender = gender
        self.birth_date = birth_date
        self.identifier = identifier

    @classmethod
    def from_fhir_resource(cls, fhir_json: dict) -> FHIRPatient:
        names = fhir_json.get("name", [{}])
        family = names[0].get("family", "") if names else ""
        given_list = names[0].get("given", []) if names else []
        given = given_list[0] if given_list else ""
        name = f"{family}{given}"

        gender_map = {"male": "male", "female": "female", "other": "other", "unknown": "unknown"}
        gender = gender_map.get(fhir_json.get("gender", "unknown"), "unknown")

        identifiers = fhir_json.get("identifier", [])
        identifier = identifiers[0].get("value", "") if identifiers else ""

        return cls(
            id=fhir_json.get("id", ""),
            name=name,
            gender=gender,
            birth_date=fhir_json.get("birthDate", ""),
            identifier=identifier,
        )

    def to_fhir_json(self) -> dict:
        result: dict[str, Any] = {
            "resourceType": "Patient",
            "id": self.id,
            "gender": self.gender,
            "birthDate": self.birth_date,
        }
        if self.name:
            # Split last-first if possible for FHIR HumanName format
            result["name"] = [{"use": "official", "text": self.name}]
        if self.identifier:
            result["identifier"] = [
                {"system": "urn:oid:2.16.156.10011.1.1", "value": self.identifier}
            ]
        return result


class FHIRCondition:
    """FHIR R4 Condition resource — diagnosis or problem."""

    def __init__(
        self,
        id: str = "",
        patient_id: str = "",
        code: str = "",
        code_system: str = "http://snomed.info/sct",
        code_display: str = "",
        clinical_status: str = "active",
        verification_status: str = "confirmed",
        onset_date: str = "",
        recorded_date: str = "",
        recorder: str = "",
    ):
        self.id = id
        self.patient_id = patient_id
        self.code = code
        self.code_system = code_system
        self.code_display = code_display
        self.clinical_status = clinical_status
        self.verification_status = verification_status
        self.onset_date = onset_date
        self.recorded_date = recorded_date
        self.recorder = recorder

    @classmethod
    def from_fhir_resource(cls, fhir_json: dict) -> FHIRCondition:
        coding = fhir_json.get("code", {}).get("coding", [{}])[0]
        subject_ref = fhir_json.get("subject", {}).get("reference", "")
        patient_id = subject_ref.replace("Patient/", "") if subject_ref else ""
        recorder_ref = fhir_json.get("recorder", {}).get("reference", "")
        recorder = recorder_ref.replace("Practitioner/", "") if recorder_ref else ""

        return cls(
            id=fhir_json.get("id", ""),
            patient_id=patient_id,
            code=coding.get("code", ""),
            code_system=coding.get("system", "http://snomed.info/sct"),
            code_display=coding.get("display", ""),
            clinical_status=fhir_json.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "active"),
            verification_status=fhir_json.get("verificationStatus", {}).get("coding", [{}])[0].get("code", "confirmed"),
            onset_date=fhir_json.get("onsetDateTime", ""),
            recorded_date=fhir_json.get("recordedDate", ""),
            recorder=recorder,
        )

    def to_fhir_json(self) -> dict:
        return {
            "resourceType": "Condition",
            "id": self.id,
            "clinicalStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                        "code": self.clinical_status,
                    }
                ]
            },
            "verificationStatus": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                        "code": self.verification_status,
                    }
                ]
            },
            "code": {
                "coding": [
                    {
                        "system": self.code_system,
                        "code": self.code,
                        "display": self.code_display,
                    }
                ],
                "text": self.code_display,
            },
            "subject": {"reference": f"Patient/{self.patient_id}"} if self.patient_id else {},
            "onsetDateTime": self.onset_date,
            "recordedDate": self.recorded_date,
            "recorder": {"reference": f"Practitioner/{self.recorder}"} if self.recorder else {},
        }


class FHIRMedicationRequest:
    """FHIR R4 MedicationRequest resource — prescription / medication order."""

    def __init__(
        self,
        id: str = "",
        patient_id: str = "",
        medication_code: str = "",
        medication_name: str = "",
        dosage: str = "",
        route: str = "",
        frequency: str = "",
        start_date: str = "",
        end_date: str = "",
        prescriber: str = "",
        status: str = "active",
    ):
        self.id = id
        self.patient_id = patient_id
        self.medication_code = medication_code
        self.medication_name = medication_name
        self.dosage = dosage
        self.route = route
        self.frequency = frequency
        self.start_date = start_date
        self.end_date = end_date
        self.prescriber = prescriber
        self.status = status

    @classmethod
    def from_fhir_resource(cls, fhir_json: dict) -> FHIRMedicationRequest:
        subject_ref = fhir_json.get("subject", {}).get("reference", "")
        patient_id = subject_ref.replace("Patient/", "") if subject_ref else ""
        requester_ref = fhir_json.get("requester", {}).get("reference", "")
        prescriber = requester_ref.replace("Practitioner/", "") if requester_ref else ""

        med_cc = fhir_json.get("medicationCodeableConcept", {})
        med_coding = med_cc.get("coding", [{}])[0]
        med_name = med_coding.get("display", "") or med_cc.get("text", "")

        dosage_instruction = fhir_json.get("dosageInstruction", [{}])
        dosage_text = ""
        route_text = ""
        freq_text = ""
        if dosage_instruction:
            di = dosage_instruction[0]
            dosage_text = di.get("text", "")
            route_coding = di.get("route", {}).get("coding", [{}])
            if route_coding:
                route_text = route_coding[0].get("display", "")
            timing = di.get("timing", {})
            freq_text = timing.get("code", {}).get("text", "")

        validity = fhir_json.get("dispenseRequest", {}).get("validityPeriod", {})
        start_date = validity.get("start", "")
        end_date = validity.get("end", "")

        return cls(
            id=fhir_json.get("id", ""),
            patient_id=patient_id,
            medication_code=med_coding.get("code", ""),
            medication_name=med_name,
            dosage=dosage_text,
            route=route_text,
            frequency=freq_text,
            start_date=start_date,
            end_date=end_date,
            prescriber=prescriber,
            status=fhir_json.get("status", "active"),
        )

    def to_fhir_json(self) -> dict:
        result: dict[str, Any] = {
            "resourceType": "MedicationRequest",
            "id": self.id,
            "status": self.status,
            "intent": "order",
            "medicationCodeableConcept": {
                "coding": [
                    {
                        "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                        "code": self.medication_code,
                        "display": self.medication_name,
                    }
                ],
                "text": self.medication_name,
            },
            "subject": {"reference": f"Patient/{self.patient_id}"} if self.patient_id else {},
            "dosageInstruction": [
                {
                    "text": self.dosage,
                    "route": {
                        "coding": [
                            {
                                "system": "http://snomed.info/sct",
                                "code": "",
                                "display": self.route,
                            }
                        ]
                    },
                    "timing": {
                        "code": {"text": self.frequency},
                    },
                }
            ],
            "dispenseRequest": {
                "validityPeriod": {
                    "start": self.start_date,
                    "end": self.end_date,
                }
            },
        }
        if self.prescriber:
            result["requester"] = {"reference": f"Practitioner/{self.prescriber}"}
        return result


class FHIRAllergyIntolerance:
    """FHIR R4 AllergyIntolerance resource."""

    def __init__(
        self,
        id: str = "",
        patient_id: str = "",
        substance: str = "",
        reaction: str = "",
        severity: str = "mild",
        onset: str = "",
        recorded_date: str = "",
        recorder: str = "",
    ):
        self.id = id
        self.patient_id = patient_id
        self.substance = substance
        self.reaction = reaction
        self.severity = severity
        self.onset = onset
        self.recorded_date = recorded_date
        self.recorder = recorder

    @classmethod
    def from_fhir_resource(cls, fhir_json: dict) -> FHIRAllergyIntolerance:
        subject_ref = fhir_json.get("patient", {}).get("reference", "")
        patient_id = subject_ref.replace("Patient/", "") if subject_ref else ""
        recorder_ref = fhir_json.get("recorder", {}).get("reference", "")
        recorder = recorder_ref.replace("Practitioner/", "") if recorder_ref else ""

        substance_code = fhir_json.get("code", {}).get("coding", [{}])[0]
        substance = substance_code.get("display", "")

        reactions = fhir_json.get("reaction", [])
        reaction_text = ""
        sev = "mild"
        if reactions:
            r = reactions[0]
            reaction_text = r.get("description", "")
            sev = r.get("severity", "mild")
            manifestations = r.get("manifestation", [{}])
            if not reaction_text and manifestations:
                reaction_text = manifestations[0].get("coding", [{}])[0].get("display", "")

        return cls(
            id=fhir_json.get("id", ""),
            patient_id=patient_id,
            substance=substance,
            reaction=reaction_text,
            severity=sev,
            onset=fhir_json.get("onsetDateTime", ""),
            recorded_date=fhir_json.get("recordedDate", ""),
            recorder=recorder,
        )

    def to_fhir_json(self) -> dict:
        result: dict[str, Any] = {
            "resourceType": "AllergyIntolerance",
            "id": self.id,
            "clinicalStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical", "code": "active"}]
            },
            "verificationStatus": {
                "coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification", "code": "confirmed"}]
            },
            "code": {
                "coding": [
                    {"system": "http://snomed.info/sct", "code": "", "display": self.substance}
                ],
                "text": self.substance,
            },
            "patient": {"reference": f"Patient/{self.patient_id}"} if self.patient_id else {},
            "onsetDateTime": self.onset,
            "recordedDate": self.recorded_date,
            "reaction": [
                {
                    "manifestation": [
                        {"coding": [{"system": "http://snomed.info/sct", "code": "", "display": self.reaction}]}
                    ],
                    "severity": self.severity,
                }
            ],
        }
        if self.recorder:
            result["recorder"] = {"reference": f"Practitioner/{self.recorder}"}
        return result


class FHIRDiagnosticReport:
    """FHIR R4 DiagnosticReport resource — lab / imaging report."""

    def __init__(
        self,
        id: str = "",
        patient_id: str = "",
        report_type: str = "",
        issued_date: str = "",
        conclusion: str = "",
        findings: dict | None = None,
        imaging_study_ref: str = "",
    ):
        self.id = id
        self.patient_id = patient_id
        self.report_type = report_type
        self.issued_date = issued_date
        self.conclusion = conclusion
        self.findings = findings or {}
        self.imaging_study_ref = imaging_study_ref

    @classmethod
    def from_fhir_resource(cls, fhir_json: dict) -> FHIRDiagnosticReport:
        subject_ref = fhir_json.get("subject", {}).get("reference", "")
        patient_id = subject_ref.replace("Patient/", "") if subject_ref else ""

        type_coding = fhir_json.get("code", {}).get("coding", [{}])[0]
        report_type = type_coding.get("display", "") or type_coding.get("code", "")

        study_refs = fhir_json.get("imagingStudy", [])
        imaging_ref = study_refs[0].get("reference", "") if study_refs else ""

        return cls(
            id=fhir_json.get("id", ""),
            patient_id=patient_id,
            report_type=report_type,
            issued_date=fhir_json.get("issued", ""),
            conclusion=fhir_json.get("conclusion", ""),
            findings=fhir_json.get("presentedForm", {}),
            imaging_study_ref=imaging_ref,
        )

    def to_fhir_json(self) -> dict:
        result: dict[str, Any] = {
            "resourceType": "DiagnosticReport",
            "id": self.id,
            "status": "final",
            "code": {
                "coding": [
                    {"system": "http://loinc.org", "code": "", "display": self.report_type}
                ],
                "text": self.report_type,
            },
            "subject": {"reference": f"Patient/{self.patient_id}"} if self.patient_id else {},
            "issued": self.issued_date,
            "conclusion": self.conclusion,
            "presentedForm": self.findings,
        }
        if self.imaging_study_ref:
            result["imagingStudy"] = [{"reference": self.imaging_study_ref}]
        return result


class FHIRCarePlan:
    """FHIR R4 CarePlan resource."""

    def __init__(
        self,
        id: str = "",
        patient_id: str = "",
        category: str = "",
        title: str = "",
        description: str = "",
        start_date: str = "",
        end_date: str = "",
        status: str = "active",
        activities: list[dict] | None = None,
    ):
        self.id = id
        self.patient_id = patient_id
        self.category = category
        self.title = title
        self.description = description
        self.start_date = start_date
        self.end_date = end_date
        self.status = status
        self.activities = activities or []

    @classmethod
    def from_fhir_resource(cls, fhir_json: dict) -> FHIRCarePlan:
        subject_ref = fhir_json.get("subject", {}).get("reference", "")
        patient_id = subject_ref.replace("Patient/", "") if subject_ref else ""

        category_coding = fhir_json.get("category", [{}])[0].get("coding", [{}])
        category = category_coding[0].get("display", "") if category_coding else ""

        period = fhir_json.get("period", {})
        activities: list[dict] = []
        for act in fhir_json.get("activity", []):
            detail = act.get("detail", {})
            activities.append({
                "description": detail.get("description", ""),
                "status": detail.get("status", "not-started"),
                "scheduled": str(detail.get("scheduledTiming", detail.get("scheduledString", ""))),
            })

        return cls(
            id=fhir_json.get("id", ""),
            patient_id=patient_id,
            category=category,
            title=fhir_json.get("title", ""),
            description=fhir_json.get("description", ""),
            start_date=period.get("start", ""),
            end_date=period.get("end", ""),
            status=fhir_json.get("status", "active"),
            activities=activities,
        )

    def to_fhir_json(self) -> dict:
        return {
            "resourceType": "CarePlan",
            "id": self.id,
            "status": self.status,
            "intent": "plan",
            "category": [
                {
                    "coding": [
                        {"system": "http://snomed.info/sct", "code": "", "display": self.category}
                    ],
                    "text": self.category,
                }
            ],
            "title": self.title,
            "description": self.description,
            "subject": {"reference": f"Patient/{self.patient_id}"} if self.patient_id else {},
            "period": {
                "start": self.start_date,
                "end": self.end_date,
            },
            "activity": [
                {
                    "detail": {
                        "description": act.get("description", ""),
                        "status": act.get("status", "not-started"),
                        "scheduledString": act.get("scheduled", ""),
                    }
                }
                for act in self.activities
            ],
        }


class FHIRProcedure:
    """FHIR R4 Procedure resource."""

    def __init__(
        self,
        id: str = "",
        patient_id: str = "",
        procedure_code: str = "",
        procedure_name: str = "",
        performed_date: str = "",
        performer: str = "",
        outcome: str = "",
    ):
        self.id = id
        self.patient_id = patient_id
        self.procedure_code = procedure_code
        self.procedure_name = procedure_name
        self.performed_date = performed_date
        self.performer = performer
        self.outcome = outcome

    @classmethod
    def from_fhir_resource(cls, fhir_json: dict) -> FHIRProcedure:
        subject_ref = fhir_json.get("subject", {}).get("reference", "")
        patient_id = subject_ref.replace("Patient/", "") if subject_ref else ""

        proc_coding = fhir_json.get("code", {}).get("coding", [{}])[0]
        performers = fhir_json.get("performer", [])
        performer_ref = ""
        if performers:
            performer_ref = performers[0].get("actor", {}).get("reference", "").replace("Practitioner/", "")

        performed = fhir_json.get("performedDateTime", fhir_json.get("performedString", ""))

        return cls(
            id=fhir_json.get("id", ""),
            patient_id=patient_id,
            procedure_code=proc_coding.get("code", ""),
            procedure_name=proc_coding.get("display", ""),
            performed_date=str(performed),
            performer=performer_ref,
            outcome=fhir_json.get("outcome", {}).get("text", ""),
        )

    def to_fhir_json(self) -> dict:
        result: dict[str, Any] = {
            "resourceType": "Procedure",
            "id": self.id,
            "status": "completed",
            "code": {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": self.procedure_code,
                        "display": self.procedure_name,
                    }
                ],
                "text": self.procedure_name,
            },
            "subject": {"reference": f"Patient/{self.patient_id}"} if self.patient_id else {},
            "performedDateTime": self.performed_date,
            "outcome": {"text": self.outcome},
        }
        if self.performer:
            result["performer"] = [{"actor": {"reference": f"Practitioner/{self.performer}"}}]
        return result


class FHIRImmunization:
    """FHIR R4 Immunization resource."""

    def __init__(
        self,
        id: str = "",
        patient_id: str = "",
        vaccine_code: str = "",
        vaccine_name: str = "",
        date: str = "",
        lot_number: str = "",
        manufacturer: str = "",
    ):
        self.id = id
        self.patient_id = patient_id
        self.vaccine_code = vaccine_code
        self.vaccine_name = vaccine_name
        self.date = date
        self.lot_number = lot_number
        self.manufacturer = manufacturer

    @classmethod
    def from_fhir_resource(cls, fhir_json: dict) -> FHIRImmunization:
        subject_ref = fhir_json.get("patient", {}).get("reference", "")
        patient_id = subject_ref.replace("Patient/", "") if subject_ref else ""

        vax = fhir_json.get("vaccineCode", {}).get("coding", [{}])[0]
        occurrence = fhir_json.get("occurrenceDateTime", fhir_json.get("occurrenceString", ""))

        return cls(
            id=fhir_json.get("id", ""),
            patient_id=patient_id,
            vaccine_code=vax.get("code", ""),
            vaccine_name=vax.get("display", ""),
            date=str(occurrence),
            lot_number=fhir_json.get("lotNumber", ""),
            manufacturer=fhir_json.get("manufacturer", {}).get("display", ""),
        )

    def to_fhir_json(self) -> dict:
        return {
            "resourceType": "Immunization",
            "id": self.id,
            "status": "completed",
            "vaccineCode": {
                "coding": [
                    {
                        "system": "http://hl7.org/fhir/sid/cvx",
                        "code": self.vaccine_code,
                        "display": self.vaccine_name,
                    }
                ],
                "text": self.vaccine_name,
            },
            "patient": {"reference": f"Patient/{self.patient_id}"} if self.patient_id else {},
            "occurrenceDateTime": self.date,
            "lotNumber": self.lot_number,
            "manufacturer": {"display": self.manufacturer} if self.manufacturer else {},
        }


class FHIRDocumentReference:
    """FHIR R4 DocumentReference resource."""

    def __init__(
        self,
        id: str = "",
        patient_id: str = "",
        document_type: str = "",
        date: str = "",
        content_url: str = "",
        mime_type: str = "application/pdf",
    ):
        self.id = id
        self.patient_id = patient_id
        self.document_type = document_type
        self.date = date
        self.content_url = content_url
        self.mime_type = mime_type

    @classmethod
    def from_fhir_resource(cls, fhir_json: dict) -> FHIRDocumentReference:
        subject_ref = fhir_json.get("subject", {}).get("reference", "")
        patient_id = subject_ref.replace("Patient/", "") if subject_ref else ""

        type_coding = fhir_json.get("type", {}).get("coding", [{}])[0]
        doc_type = type_coding.get("display", "") or type_coding.get("code", "")

        content = fhir_json.get("content", [{}])[0]
        attachment = content.get("attachment", {})
        content_url = attachment.get("url", "")
        mime_type = attachment.get("contentType", "application/pdf")

        return cls(
            id=fhir_json.get("id", ""),
            patient_id=patient_id,
            document_type=doc_type,
            date=fhir_json.get("date", ""),
            content_url=content_url,
            mime_type=mime_type,
        )

    def to_fhir_json(self) -> dict:
        return {
            "resourceType": "DocumentReference",
            "id": self.id,
            "status": "current",
            "type": {
                "coding": [
                    {"system": "http://loinc.org", "code": "", "display": self.document_type}
                ],
                "text": self.document_type,
            },
            "subject": {"reference": f"Patient/{self.patient_id}"} if self.patient_id else {},
            "date": self.date,
            "content": [
                {
                    "attachment": {
                        "contentType": self.mime_type,
                        "url": self.content_url,
                    }
                }
            ],
        }
