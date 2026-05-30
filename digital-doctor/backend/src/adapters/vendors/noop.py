"""NoOp EMR Adapter — returns empty results when no EMR is connected."""

from datetime import date

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


class NoOpAdapter(BaseEMRAdapter):
    """Stub adapter for deployments with no EMR integration.

    All methods return empty / None — safe no-op implementation.
    """

    def __init__(self, endpoint: str = ""):
        self.endpoint = endpoint

    async def get_patient(self, patient_id: str) -> FHIRPatient:
        return FHIRPatient(id=patient_id)

    async def get_allergies(self, patient_id: str) -> list[AllergyIntolerance]:
        return []

    async def get_lab_results(self, patient_id: str, since: date) -> list[Observation]:
        return []

    async def get_medications(self, patient_id: str) -> list[MedicationRequest]:
        return []

    async def get_diagnoses(self, patient_id: str) -> list[Condition]:
        return []

    async def get_pregnancy_status(self, patient_id: str) -> PregnancyStatus | None:
        return None

    async def get_liver_function(self, patient_id: str) -> LiverFunction | None:
        return None

    async def get_renal_function(self, patient_id: str) -> RenalFunction | None:
        return None

    async def get_encounters(self, patient_id: str, since: date) -> list[Encounter]:
        return []
