from src.services.llm_client import LLMClient, llm_client
from src.services.risk_assessment import calculate_diabetes_risk, RiskLevel
from src.services.report_interpreter import interpret_lab_report
from src.services.glucose_tracker import calculate_glucose_stats, analyze_glucose_trend, TimeInRange
from src.services.medication_reminder import generate_daily_schedule, check_missed_doses, ReminderSchedule
from src.services.health_coach import HealthCoach, CoachContext
from src.services.alert_engine import check_glucose_alerts, check_compliance_alerts
from src.services.patient_manager import get_patient_list, get_patient_detail
from src.services.backup_service import create_backup, list_backups, verify_backup, get_backup_stats
from src.services.diagnosis_engine import differential_diagnosis, calculate_confidence
from src.services.homa_calculator import calculate_homa_ir, calculate_homa_beta
from src.services.explainability import ExplainabilityEngine, explainability_engine, generate_explanation_summary
from src.services import prompts
from src.services.notification_service import (
    schedule_medication_reminders,
    send_pending_notifications,
    send_sms,
    check_and_alert_doctor,
    format_template,
    format_medication_reminder,
    format_alert_notification,
)
