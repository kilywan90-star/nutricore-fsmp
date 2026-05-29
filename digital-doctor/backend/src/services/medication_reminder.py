from dataclasses import dataclass
from datetime import datetime
from src.models.patient import MedicationReminder


@dataclass
class ReminderSchedule:
    drug_name: str
    dosage: str
    time: str


def generate_daily_schedule(reminders: list[MedicationReminder]) -> list[ReminderSchedule]:
    schedule: list[ReminderSchedule] = []
    for r in reminders:
        if not r.is_active:
            continue
        for t in r.time_of_day:
            schedule.append(ReminderSchedule(drug_name=r.drug_name, dosage=r.dosage, time=t))
    schedule.sort(key=lambda s: s.time)
    return schedule


def check_missed_doses(
    reminders: list[MedicationReminder],
    taken_times: set[str],
    current_time: str | None = None,
) -> list[ReminderSchedule]:
    if current_time is None:
        now = datetime.now()
        current_time = now.strftime("%H:%M")

    missed: list[ReminderSchedule] = []
    for r in reminders:
        if not r.is_active:
            continue
        for t in r.time_of_day:
            if t <= current_time and t not in taken_times:
                missed.append(ReminderSchedule(drug_name=r.drug_name, dosage=r.dosage, time=t))
    return missed


def format_reminder_text(schedule: list[ReminderSchedule]) -> str:
    if not schedule:
        return "今日无用药提醒"
    lines = ["今日用药提醒："]
    for s in schedule:
        lines.append(f"  {s.time} — {s.drug_name} {s.dosage}")
    return "\n".join(lines)
