# digital-doctor/backend/src/models/__init__.py
from src.models.user import User, UserRole
from src.models.patient import Patient, GlucoseRecord, MedicationReminder
from src.models.clinical import LabReport, Alert, AlertSeverity
