# digital-doctor/backend/tests/test_medication_reminder.py
import pytest
from datetime import date
from src.services.medication_reminder import (
    ReminderSchedule,
    generate_daily_schedule,
    check_missed_doses,
)
from src.models.patient import MedicationReminder


def make_reminder(drug: str, dosage: str, freq: str, times: list[str]):
    return MedicationReminder(
        drug_name=drug,
        dosage=dosage,
        frequency=freq,
        time_of_day=times,
        start_date=date(2026, 5, 1),
        is_active=True,
    )


def test_generate_daily_schedule_bid():
    reminders = [make_reminder("二甲双胍", "500mg", "bid", ["08:00", "18:00"])]
    schedule = generate_daily_schedule(reminders)
    assert len(schedule) == 2
    assert schedule[0].drug_name == "二甲双胍"
    assert schedule[0].time == "08:00"


def test_generate_daily_schedule_multiple_drugs():
    reminders = [
        make_reminder("二甲双胍", "500mg", "bid", ["08:00", "18:00"]),
        make_reminder("阿卡波糖", "50mg", "tid", ["08:00", "12:00", "18:00"]),
    ]
    schedule = generate_daily_schedule(reminders)
    times_8 = [s for s in schedule if s.time == "08:00"]
    assert len(times_8) == 2


def test_check_missed_no_doses():
    reminders = [make_reminder("二甲双胍", "500mg", "bid", ["08:00", "18:00"])]
    taken = {"08:00", "18:00"}
    missed = check_missed_doses(reminders, taken, current_time="23:59")
    assert len(missed) == 0


def test_check_missed_doses():
    reminders = [make_reminder("二甲双胍", "500mg", "bid", ["08:00", "18:00"])]
    taken = {"08:00"}
    missed = check_missed_doses(reminders, taken, current_time="23:59")
    assert len(missed) == 1
    assert missed[0].time == "18:00"
