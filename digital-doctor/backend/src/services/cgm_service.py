"""CGM data import, metrics calculation, and pattern detection."""

import uuid
import math
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.cgm import CGMRecord, CGMSession, CGMDevice
from src.models.patient import Patient
from src.services.cgm_parser import parse_cgm_file, detect_device_from_filename

TARGET_LOW = 3.9
TARGET_HIGH = 10.0
TIGHT_HIGH = 7.8
BATCH_SIZE = 500


async def import_cgm_data(
    patient_id: uuid.UUID,
    file_content: bytes,
    file_format: str,
    filename: str,
    db: AsyncSession,
) -> CGMSession:
    """Import a CGM data file, create session + records using batch insert.

    Returns the created CGMSession with metrics populated.
    """
    device_type_str = detect_device_from_filename(filename) if file_format == "auto" else (
        "unknown" if file_format in ("generic_json",) else file_format
    )

    try:
        device_type = CGMDevice(device_type_str)
    except ValueError:
        device_type = CGMDevice.UNKNOWN

    readings = parse_cgm_file(file_content, file_format, filename)
    if not readings:
        raise ValueError("No valid readings found in file")

    readings.sort(key=lambda r: r["timestamp"])

    sensor_start = readings[0]["timestamp"]
    sensor_end = readings[-1]["timestamp"]

    # Calculate basic stats
    values = [r["value_mmol_l"] for r in readings]
    n = len(values)
    avg = round(sum(values) / n, 1)
    variance = sum((v - avg) ** 2 for v in values) / n
    std = round(math.sqrt(variance), 2)
    cv = round(std / avg * 100, 1) if avg > 0 else None

    # GMI (Glucose Management Indicator) = 3.31 + 0.02392 * mean_glucose_mgdl
    avg_mgdl = avg * 18.018
    gmi = round(3.31 + 0.02392 * avg_mgdl, 1)

    # TIR / TAR / TBR
    in_range = sum(1 for v in values if TARGET_LOW <= v <= TARGET_HIGH)
    above = sum(1 for v in values if v > TARGET_HIGH)
    below = sum(1 for v in values if v < TARGET_LOW)
    tir_pct = round(in_range / n * 100, 1)
    tar_pct = round(above / n * 100, 1)
    tbr_pct = round(below / n * 100, 1)
    tight = sum(1 for v in values if TARGET_LOW <= v <= TIGHT_HIGH)
    ttr_pct = round(tight / n * 100, 1)

    # MAGE — Mean Amplitude of Glycemic Excursion
    mage = _calculate_mage(values)

    session = CGMSession(
        patient_id=patient_id,
        device_type=device_type,
        sensor_start=sensor_start,
        sensor_end=sensor_end,
        total_readings=n,
        avg_glucose=avg,
        estimated_hba1c=gmi,
        cv_percent=cv,
        time_in_range_pct=tir_pct,
        time_above_range_pct=tar_pct,
        time_below_range_pct=tbr_pct,
        time_in_tight_range_pct=ttr_pct,
        mage=mage,
        source_file_name=filename,
    )
    db.add(session)
    await db.flush()

    # Batch insert records
    records_batch = []
    for r in readings:
        records_batch.append(CGMRecord(
            patient_id=patient_id,
            session_id=session.id,
            device_type=device_type,
            timestamp=r["timestamp"],
            value_mmol_l=r["value_mmol_l"],
            trend_direction=r.get("trend_direction"),
            is_manual_calibration=r.get("is_manual_calibration", False),
            raw_data=r.get("raw_data"),
        ))
        if len(records_batch) >= BATCH_SIZE:
            db.add_all(records_batch)
            await db.flush()
            records_batch = []

    if records_batch:
        db.add_all(records_batch)
        await db.flush()

    await db.commit()
    await db.refresh(session)
    return session


async def calculate_cgm_metrics(session_id: uuid.UUID, db: AsyncSession) -> dict[str, Any]:
    """Calculate or recalculate AGP (Ambulatory Glucose Profile) metrics for a session."""
    stmt = select(CGMSession).where(CGMSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise ValueError(f"CGMSession {session_id} not found")

    records_stmt = (
        select(CGMRecord)
        .where(CGMRecord.session_id == session_id)
        .order_by(CGMRecord.timestamp)
    )
    records_result = await db.execute(records_stmt)
    records = records_result.scalars().all()

    if not records:
        return {"session_id": str(session_id), "total_readings": 0}

    values = [r.value_mmol_l for r in records]
    n = len(values)
    avg = round(sum(values) / n, 1)
    variance = sum((v - avg) ** 2 for v in values) / n
    std = round(math.sqrt(variance), 2)
    cv = round(std / avg * 100, 1) if avg > 0 else None

    avg_mgdl = avg * 18.018
    gmi = round(3.31 + 0.02392 * avg_mgdl, 1)

    in_range = sum(1 for v in values if TARGET_LOW <= v <= TARGET_HIGH)
    above = sum(1 for v in values if v > TARGET_HIGH)
    below = sum(1 for v in values if v < TARGET_LOW)
    tir_pct = round(in_range / n * 100, 1)
    tar_pct = round(above / n * 100, 1)
    tbr_pct = round(below / n * 100, 1)
    tight = sum(1 for v in values if TARGET_LOW <= v <= TIGHT_HIGH)
    ttr_pct = round(tight / n * 100, 1)

    mage = _calculate_mage(values)

    # Update session with calculated metrics
    session.avg_glucose = avg
    session.estimated_hba1c = gmi
    session.cv_percent = cv
    session.time_in_range_pct = tir_pct
    session.time_above_range_pct = tar_pct
    session.time_below_range_pct = tbr_pct
    session.time_in_tight_range_pct = ttr_pct
    session.mage = mage
    session.total_readings = n

    await db.commit()

    return {
        "session_id": str(session_id),
        "total_readings": n,
        "avg_glucose": avg,
        "estimated_hba1c": gmi,
        "cv_percent": cv,
        "time_in_range_pct": tir_pct,
        "time_above_range_pct": tar_pct,
        "time_below_range_pct": tbr_pct,
        "time_in_tight_range_pct": ttr_pct,
        "mage": mage,
    }


async def get_cgm_summary(patient_id: uuid.UUID, days: int = 14, db: AsyncSession = None) -> dict[str, Any]:
    """Get last N days CGM summary for the patient dashboard."""
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)

    records_stmt = (
        select(CGMRecord)
        .where(
            and_(
                CGMRecord.patient_id == patient_id,
                CGMRecord.timestamp >= cutoff,
            )
        )
        .order_by(CGMRecord.timestamp)
    )
    records_result = await db.execute(records_stmt)
    records = records_result.scalars().all()

    sessions_stmt = (
        select(CGMSession)
        .where(
            and_(
                CGMSession.patient_id == patient_id,
                CGMSession.sensor_end >= cutoff if CGMSession.sensor_end is not None else True,
            )
        )
        .order_by(CGMSession.sensor_start.desc())
    )
    sessions_result = await db.execute(sessions_stmt)
    sessions = sessions_result.scalars().all()

    active_session = None
    for s in sessions:
        if s.sensor_end is None or s.sensor_end >= cutoff:
            active_session = s
            break

    if not records:
        return {
            "patient_id": str(patient_id),
            "days": days,
            "has_data": False,
            "total_readings": 0,
        }

    values = [r.value_mmol_l for r in records]
    n = len(values)
    avg = round(sum(values) / n, 1)

    in_range = sum(1 for v in values if TARGET_LOW <= v <= TARGET_HIGH)
    above = sum(1 for v in values if v > TARGET_HIGH)
    below = sum(1 for v in values if v < TARGET_LOW)

    # Hourly profile for 24h glucose curve
    hourly_buckets: dict[int, list[float]] = {h: [] for h in range(24)}
    for r in records:
        hourly_buckets[r.timestamp.hour].append(r.value_mmol_l)

    hourly_profile = {}
    for h in range(24):
        vals = hourly_buckets[h]
        if vals:
            sorted_vals = sorted(vals)
            nv = len(sorted_vals)
            q1_idx = max(0, int(nv * 0.25))
            q3_idx = min(nv - 1, int(nv * 0.75))
            hourly_profile[str(h)] = {
                "hour": h,
                "median": round(sorted_vals[nv // 2], 1),
                "q1": round(sorted_vals[q1_idx], 1),
                "q3": round(sorted_vals[q3_idx], 1),
                "count": nv,
            }

    # Weekly TIR trend over past month
    weekly_tir = _calculate_weekly_tir(patient_id, db)

    return {
        "patient_id": str(patient_id),
        "days": days,
        "has_data": True,
        "total_readings": n,
        "avg_glucose": avg,
        "time_in_range_pct": round(in_range / n * 100, 1) if n > 0 else 0,
        "time_above_range_pct": round(above / n * 100, 1) if n > 0 else 0,
        "time_below_range_pct": round(below / n * 100, 1) if n > 0 else 0,
        "active_session": {
            "id": str(active_session.id),
            "device_type": active_session.device_type.value,
            "sensor_start": active_session.sensor_start.isoformat(),
            "avg_glucose": active_session.avg_glucose,
            "estimated_hba1c": active_session.estimated_hba1c,
            "cv_percent": active_session.cv_percent,
        } if active_session else None,
        "recent_sessions": [
            {
                "id": str(s.id),
                "device_type": s.device_type.value,
                "sensor_start": s.sensor_start.isoformat(),
                "sensor_end": s.sensor_end.isoformat() if s.sensor_end else None,
                "total_readings": s.total_readings,
                "avg_glucose": s.avg_glucose,
                "estimated_hba1c": s.estimated_hba1c,
                "time_in_range_pct": s.time_in_range_pct,
            }
            for s in sessions[:5]
        ],
        "hourly_profile": hourly_profile,
        "weekly_tir_trend": weekly_tir,
    }


async def detect_patterns(session_id: uuid.UUID, db: AsyncSession) -> list[dict[str, Any]]:
    """Detect glycemic patterns from a CGM session.

    Looks for:
    - Dawn phenomenon (morning hyperglycemia 4-8 AM)
    - Postprandial spikes (glucose increase after meals)
    - Nocturnal hypoglycemia (low glucose 12-6 AM)
    - Somogyi effect (rebound hyperglycemia after nocturnal hypo)
    """
    records_stmt = (
        select(CGMRecord)
        .where(CGMRecord.session_id == session_id)
        .order_by(CGMRecord.timestamp)
    )
    result = await db.execute(records_stmt)
    records = result.scalars().all()

    if not records:
        return []

    patterns = []

    # ── Dawn phenomenon detection ──
    # Morning (4-8 AM) glucose consistently > 10.0 mmol/L
    dawn_records = [r for r in records if 4 <= r.timestamp.hour < 8]
    if len(dawn_records) >= 6:
        dawn_avg = sum(r.value_mmol_l for r in dawn_records) / len(dawn_records)
        dawn_high_count = sum(1 for r in dawn_records if r.value_mmol_l > TARGET_HIGH)
        if dawn_avg > TARGET_HIGH and dawn_high_count >= len(dawn_records) * 0.5:
            # Check delta from pre-dawn (2-4 AM)
            predawn = [r for r in records if 0 <= r.timestamp.hour < 4]
            if predawn:
                predawn_avg = sum(r.value_mmol_l for r in predawn) / len(predawn)
                delta = dawn_avg - predawn_avg
                if delta > 1.5:
                    patterns.append({
                        "type": "dawn_phenomenon",
                        "label": "黎明现象",
                        "description": f"清晨血糖持续升高，平均{dawn_avg:.1f} mmol/L，较凌晨升高{delta:.1f} mmol/L",
                        "severity": "warning" if dawn_avg > 13.0 else "info",
                        "recommendation": "建议调整晚餐或睡前胰岛素剂量，增加睡前基础胰岛素或睡前二甲双胍",
                        "details": {
                            "dawn_avg": round(dawn_avg, 1),
                            "predawn_avg": round(predawn_avg, 1),
                            "delta": round(delta, 1),
                            "high_proportion": round(dawn_high_count / len(dawn_records) * 100, 1),
                        },
                    })

    # ── Nocturnal hypoglycemia ──
    # Night (0-6 AM) glucose consistently < 3.9
    night_records = [r for r in records if 0 <= r.timestamp.hour < 6]
    if len(night_records) >= 6:
        night_low = sum(1 for r in night_records if r.value_mmol_l < TARGET_LOW)
        night_low_pct = night_low / len(night_records) * 100
        if night_low_pct >= 3:
            patterns.append({
                "type": "nocturnal_hypoglycemia",
                "label": "夜间低血糖风险",
                "description": f"夜间(0-6时)低血糖比例为{night_low_pct:.1f}%，存在夜间低血糖风险",
                "severity": "warning" if night_low_pct > 10 else "info",
                "recommendation": "建议睡前加餐或减少晚餐前胰岛素剂量，监测睡前血糖",
                "details": {
                    "night_low_percent": round(night_low_pct, 1),
                    "night_min": round(min(r.value_mmol_l for r in night_records), 1),
                    "night_avg": round(sum(r.value_mmol_l for r in night_records) / len(night_records), 1),
                },
            })

    # ── Postprandial spikes ──
    # After typical meal times (7-9, 11-13, 17-19), check for spikes 1-2h later
    meal_windows = {"breakfast": (7, 10), "lunch": (11, 14), "dinner": (17, 20)}
    spike_detected = False
    spike_details = []

    for meal, (start_h, end_h) in meal_windows.items():
        meal_period = [r for r in records if start_h <= r.timestamp.hour < end_h]
        if not meal_period:
            continue
        # Look for values > 10.0 during this window
        spikes = [r for r in meal_period if r.value_mmol_l > TARGET_HIGH]
        if len(spikes) >= len(meal_period) * 0.3:
            spike_detected = True
            pre_window = [r for r in records if (start_h - 1) <= r.timestamp.hour < start_h]
            pre_avg = sum(r.value_mmol_l for r in pre_window) / len(pre_window) if pre_window else None
            peak = max(r.value_mmol_l for r in meal_period)
            spike_details.append({
                "meal": meal,
                "pre_meal_avg": round(pre_avg, 1) if pre_avg else None,
                "peak": round(peak, 1),
                "spike_count": len(spikes),
                "spike_pct": round(len(spikes) / len(meal_period) * 100, 1),
            })

    if spike_detected:
        meal_names = {"breakfast": "早餐", "lunch": "午餐", "dinner": "晚餐"}
        affected = [meal_names[sd["meal"]] for sd in spike_details]
        patterns.append({
            "type": "postprandial_spikes",
            "label": "餐后高血糖",
            "description": f"餐后血糖升高明显，影响餐: {', '.join(affected)}",
            "severity": "warning" if any(sd["peak"] > 13.0 for sd in spike_details) else "info",
            "recommendation": "建议餐前短效胰岛素调整（如门冬胰岛素），或使用GLP-1受体激动剂、SGLT-2抑制剂",
            "details": spike_details,
        })

    # ── Somogyi effect ──
    # Rebound morning hyperglycemia after nocturnal hypo
    if night_records and len(records) > 0:
        night_low_exist = any(r.value_mmol_l < TARGET_LOW for r in night_records)
        morning_records = [r for r in records if 6 <= r.timestamp.hour < 10]
        if night_low_exist and morning_records:
            morning_avg = sum(r.value_mmol_l for r in morning_records) / len(morning_records)
            night_min = min(r.value_mmol_l for r in night_records)
            if morning_avg > TARGET_HIGH and night_min < 3.0:
                patterns.append({
                    "type": "somogyi_effect",
                    "label": "Somogyi效应",
                    "description": f"夜间低血糖({night_min:.1f} mmol/L)后清晨反映性高血糖({morning_avg:.1f} mmol/L)",
                    "severity": "warning",
                    "recommendation": "减少睡前胰岛素剂量，避免夜间低血糖；睡前适当加餐，监测凌晨2-3时血糖",
                    "details": {
                        "night_min": round(night_min, 1),
                        "morning_avg": round(morning_avg, 1),
                    },
                })

    return patterns


# ── Internal helpers ─────────────────────────────────────────────────────


def _calculate_mage(values: list[float]) -> float | None:
    """Calculate Mean Amplitude of Glycemic Excursion.

    MAGE is the average of glycemic excursions exceeding 1 SD.
    """
    if len(values) < 3:
        return None

    avg = sum(values) / len(values)
    variance = sum((v - avg) ** 2 for v in values) / len(values)
    sd = math.sqrt(variance)

    excursions = []
    direction = None  # 'up' or 'down'
    peak = values[0]
    trough = values[0]

    for i in range(1, len(values)):
        curr = values[i]
        prev = values[i - 1]

        if direction is None:
            if curr > prev:
                direction = "up"
                trough = prev
                peak = curr
            elif curr < prev:
                direction = "down"
                peak = prev
                trough = curr
        elif direction == "up":
            if curr >= prev:
                peak = curr
            else:
                # Turn down
                excursion = peak - trough
                if excursion >= sd:
                    excursions.append(excursion)
                direction = "down"
                trough = curr
        else:  # direction == "down"
            if curr <= prev:
                trough = curr
            else:
                # Turn up
                excursion = peak - trough
                if excursion >= sd:
                    excursions.append(excursion)
                direction = "up"
                peak = curr

    # Final excursion
    if direction == "up":
        excursion = peak - trough
    else:
        excursion = peak - trough
    if excursion >= sd:
        excursions.append(excursion)

    if not excursions:
        return round(sd, 2)

    return round(sum(excursions) / len(excursions), 2)


async def _calculate_weekly_tir(patient_id: uuid.UUID, db: AsyncSession) -> list[dict]:
    """Calculate TIR trend by week for past 4 weeks."""
    results = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for week_offset in range(3, -1, -1):
        week_end = now - timedelta(weeks=week_offset)
        week_start = week_end - timedelta(weeks=1)

        stmt = select(CGMRecord).where(
            and_(
                CGMRecord.patient_id == patient_id,
                CGMRecord.timestamp >= week_start,
                CGMRecord.timestamp < week_end,
            )
        )
        result = await db.execute(stmt)
        week_records = result.scalars().all()

        if week_records:
            values = [r.value_mmol_l for r in week_records]
            in_range = sum(1 for v in values if TARGET_LOW <= v <= TARGET_HIGH)
            tir = round(in_range / len(values) * 100, 1)
            results.append({
                "week_start": week_start.isoformat()[:10],
                "week_end": week_end.isoformat()[:10],
                "tir_pct": tir,
                "reading_count": len(values),
            })
        else:
            results.append({
                "week_start": week_start.isoformat()[:10],
                "week_end": week_end.isoformat()[:10],
                "tir_pct": None,
                "reading_count": 0,
            })

    return results
