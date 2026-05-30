"""HL7 v2 to FHIR R4 mapper.

Converts parsed HL7 message dicts into FHIR resource model instances.
"""

from __future__ import annotations

from src.adapters.fhir_resources import (
    FHIRMedicationRequest,
    FHIRPatient,
)


class HL7ToFHIRMapper:
    """Map HL7 v2 parsed data to FHIR R4 resource instances."""

    @staticmethod
    def adt_to_fhir_patient(adt_data: dict) -> FHIRPatient:
        """Convert an ADT parsed dict to a FHIRPatient."""
        return FHIRPatient(
            id=adt_data.get("patient_id", ""),
            name=adt_data.get("name", ""),
            gender=adt_data.get("gender", "unknown"),
            birth_date=adt_data.get("birth_date", ""),
            identifier=adt_data.get("patient_id", ""),
        )

    @staticmethod
    def oru_to_fhir_observations(oru_data: dict) -> list[dict]:
        """Convert an ORU parsed dict to a list of FHIR Observation dicts.

        Returns list of dicts conforming to FHIR R4 Observation JSON structure.
        """
        patient_id = oru_data.get("patient_id", "")
        observations: list[dict] = []

        for obs_data in oru_data.get("observations", []):
            obs = {
                "resourceType": "Observation",
                "id": "",
                "status": "final",
                "category": [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                "code": "laboratory",
                            }
                        ]
                    }
                ],
                "code": {
                    "coding": [
                        {
                            "system": "http://loinc.org",
                            "code": obs_data.get("test_code", ""),
                            "display": obs_data.get("test_name", ""),
                        }
                    ],
                    "text": obs_data.get("test_name", ""),
                },
                "subject": {"reference": f"Patient/{patient_id}"},
                "effectiveDateTime": obs_data.get("result_date", ""),
                "valueQuantity": {
                    "value": obs_data.get("result_value"),
                    "unit": obs_data.get("unit", ""),
                },
                "referenceRange": [],
                "interpretation": [],
            }

            ref_range = obs_data.get("reference_range", "")
            if ref_range:
                obs["referenceRange"] = [{"text": ref_range}]

            flag = obs_data.get("abnormal_flag", "")
            if flag:
                flag_map = {"L": "L", "H": "H", "LL": "LL", "HH": "HH", "A": "A"}
                code = flag_map.get(flag, "A")
                obs["interpretation"] = [
                    {
                        "coding": [
                            {
                                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                                "code": code,
                            }
                        ]
                    }
                ]

            observations.append(obs)

        return observations

    @staticmethod
    def orm_to_fhir_medication_requests(orm_data: dict) -> list[dict]:
        """Convert an ORM parsed dict to a list of FHIR MedicationRequest dicts.

        Returns list of dicts conforming to FHIR R4 MedicationRequest JSON structure.
        """
        patient_id = orm_data.get("patient_id", "")
        requests: list[dict] = []

        for med in orm_data.get("medication_orders", []):
            req = {
                "resourceType": "MedicationRequest",
                "id": med.get("order_number", ""),
                "status": "active",
                "intent": "order",
                "medicationCodeableConcept": {
                    "coding": [
                        {
                            "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                            "code": med.get("drug_code", ""),
                            "display": med.get("drug_name", ""),
                        }
                    ],
                    "text": med.get("drug_name", ""),
                },
                "subject": {"reference": f"Patient/{patient_id}"},
                "dosageInstruction": [
                    {
                        "text": med.get("dose", ""),
                        "route": {
                            "coding": [
                                {
                                    "system": "http://snomed.info/sct",
                                    "code": "",
                                    "display": med.get("route", ""),
                                }
                            ]
                        },
                        "timing": {
                            "code": {"text": med.get("frequency", "")}
                        },
                    }
                ],
                "dispenseRequest": {
                    "validityPeriod": {
                        "start": med.get("start_date", ""),
                    }
                },
            }

            ordering_doctor = med.get("ordering_doctor", "")
            if ordering_doctor:
                req["requester"] = {"reference": f"Practitioner/{ordering_doctor}"}

            requests.append(req)

        return requests
