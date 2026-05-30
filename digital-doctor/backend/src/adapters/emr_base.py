"""EMR Adapter Base — abstract interface and shared FHIR-like data models.

Each vendor adapter (neusoft, winning, bsoft, wonders, xintong, zuobiao,
fhir_standard, noop) implements BaseEMRAdapter to translate its proprietary
EHR/HIS interface into these simplified internal representations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


# ── Internal data models (simplified FHIR, not full spec) ──────────────────────

@dataclass
class FHIRPatient:
    """Simplified Patient resource used internally by drug checker and services."""
    id: str
    identifier: str = ""
    name: str = ""
    gender: str = ""          # M | F | U
    birth_date: str = ""      # ISO date string
    phone: str = ""
    address: str = ""


@dataclass
class AllergyIntolerance:
    """Patient allergy or intolerance record."""
    id: str
    patient_id: str
    substance: str               # e.g. "青霉素", "Penicillin"
    category: str = "medication" # medication | food | environment
    severity: str = ""           # mild | moderate | severe
    status: str = "active"       # active | inactive | resolved
    reaction: str = ""
    onset_date: str = ""
    recorded_date: str = ""


@dataclass
class Observation:
    """Lab test result / vital sign observation."""
    id: str
    patient_id: str
    code: str           # LOINC or local code
    name: str = ""      # Display name e.g. "空腹血糖"
    value: float | None = None
    unit: str = ""
    effective_date: str = ""     # ISO datetime
    reference_range: str = ""
    interpretation: str = ""     # low | normal | high | abnormal
    status: str = "final"        # registered | preliminary | final | amended


@dataclass
class MedicationRequest:
    """Prescribed or active medication record."""
    id: str
    patient_id: str
    medication_name: str
    dosage: str = ""
    frequency: str = ""          # qd | bid | tid | qid
    route: str = ""              # po | iv | sc | im
    start_date: str = ""
    end_date: str = ""
    status: str = "active"       # active | stopped | completed


@dataclass
class Condition:
    """Diagnosis / problem list entry."""
    id: str
    patient_id: str
    code: str = ""               # ICD-10
    name: str = ""               # e.g. "2型糖尿病"
    category: str = "diagnosis"  # diagnosis | complaint | complication
    severity: str = ""
    onset_date: str = ""
    status: str = "active"       # active | resolved | inactive


@dataclass
class PregnancyStatus:
    """Pregnancy screening result for medication safety checks."""
    patient_id: str
    is_pregnant: bool = False
    gestational_weeks: int | None = None
    edd: str = ""                # estimated delivery date (ISO)
    last_confirmed_date: str = ""


@dataclass
class LiverFunction:
    """Liver function summary for drug safety (hepatotoxic drugs)."""
    patient_id: str
    alt: float | None = None           # U/L
    ast: float | None = None           # U/L
    alt_ratio: float | None = None     # ALT / ULN
    child_pugh_class: str = ""         # A | B | C | ""
    cirrhosis_status: str = ""         # none | compensated | decompensated
    lab_date: str = ""


@dataclass
class RenalFunction:
    """Renal function summary for drug dosing (renally cleared drugs)."""
    patient_id: str
    egfr: float | None = None          # mL/min/1.73m²
    creatinine: float | None = None    # umol/L
    ckd_stage: int = 0                 # 0 = no CKD, 1-5 = CKD stage
    dialysis_status: str = ""          # none | hemodialysis | peritoneal_dialysis
    lab_date: str = ""


@dataclass
class Encounter:
    """Clinical visit / admission record."""
    id: str
    patient_id: str
    encounter_type: str = ""     # outpatient | inpatient | emergency | virtual
    date: str = ""               # ISO datetime
    department: str = ""
    provider: str = ""
    reason: str = ""
    discharge_disposition: str = ""


# ── Base adapter ────────────────────────────────────────────────────────────────

class BaseEMRAdapter(ABC):
    """Abstract interface every EMR vendor adapter must implement.

    Each method returns simplified internal models (dataclasses above),
    NOT full FHIR resources.
    """

    @abstractmethod
    async def get_patient(self, patient_id: str) -> FHIRPatient:
        """Retrieve patient demographics by internal ID or identifier."""
        ...

    @abstractmethod
    async def get_allergies(self, patient_id: str) -> list[AllergyIntolerance]:
        """All reported allergies and intolerances for a patient."""
        ...

    @abstractmethod
    async def get_lab_results(self, patient_id: str, since: date) -> list[Observation]:
        """Lab / diagnostic test results since a given date."""
        ...

    @abstractmethod
    async def get_medications(self, patient_id: str) -> list[MedicationRequest]:
        """Active and recent medication orders for a patient."""
        ...

    @abstractmethod
    async def get_diagnoses(self, patient_id: str) -> list[Condition]:
        """Problem list / active diagnoses for a patient."""
        ...

    @abstractmethod
    async def get_pregnancy_status(self, patient_id: str) -> PregnancyStatus | None:
        """Pregnancy status if applicable; None if male or unknown."""
        ...

    @abstractmethod
    async def get_liver_function(self, patient_id: str) -> LiverFunction | None:
        """Most recent liver function panel; None if unavailable."""
        ...

    @abstractmethod
    async def get_renal_function(self, patient_id: str) -> RenalFunction | None:
        """Most recent renal function panel; None if unavailable."""
        ...

    @abstractmethod
    async def get_encounters(self, patient_id: str, since: date) -> list[Encounter]:
        """Clinical encounters since a given date."""
        ...

    async def close(self) -> None:
        """Release underlying HTTP client / connections."""
        pass
