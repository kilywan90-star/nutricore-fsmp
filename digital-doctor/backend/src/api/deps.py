from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.services.llm_client import llm_client
from src.services.risk_assessment import calculate_diabetes_risk
from src.services.report_interpreter import interpret_lab_report
from src.services.glucose_tracker import calculate_glucose_stats, analyze_glucose_trend, TimeInRange
from src.services.medication_reminder import generate_daily_schedule, check_missed_doses
from src.services.health_coach import HealthCoach, CoachContext
from src.services.alert_engine import check_glucose_alerts
from src.services.patient_manager import get_patient_list, get_patient_detail
from src.engine.rule_engine import RuleEngine
from src.engine.rule_loader import RuleLoader

security = HTTPBearer(auto_error=False)

_rule_engine: RuleEngine | None = None
_health_coach: HealthCoach | None = None


def get_rule_engine() -> RuleEngine:
    global _rule_engine
    if _rule_engine is None:
        loader = RuleLoader()
        rules = loader.load("t2dm_guidelines_v1")
        _rule_engine = RuleEngine(rules)
    return _rule_engine


def get_health_coach() -> HealthCoach:
    global _health_coach
    if _health_coach is None:
        _health_coach = HealthCoach()
    return _health_coach
