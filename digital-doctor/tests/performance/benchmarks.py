"""
Standalone performance benchmarks for digital-doctor services.

Runs concurrent benchmarks against core service functions without needing
a running server. Measures p50/p95/p99 latencies and writes a CSV report.

Usage:
    cd digital-doctor/backend
    python -m tests.performance.benchmarks

Or directly:
    python digital-doctor/tests/performance/benchmarks.py
"""

from __future__ import annotations

import asyncio
import csv
import json
import os
import random
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Awaitable

# Allow running from project root or backend directory
_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CONCURRENCY = 100
TIMEOUT_S = 30.0
OUTPUT_CSV = Path(__file__).resolve().parent / "benchmark_results.csv"

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class BenchmarkResult:
    name: str
    total: int
    success: int
    failure: int
    p50_ms: float
    p95_ms: float
    p99_ms: float
    min_ms: float
    max_ms: float
    mean_ms: float
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------


async def _run_concurrent(
    name: str,
    fn: Callable[[], Awaitable[Any]],
    count: int = CONCURRENCY,
) -> BenchmarkResult:
    latencies: list[float] = []
    errors: list[str] = []
    success = 0
    failure = 0

    async def worker():
        nonlocal success, failure
        start = time.perf_counter()
        try:
            await asyncio.wait_for(fn(), timeout=TIMEOUT_S)
            elapsed = (time.perf_counter() - start) * 1000
            latencies.append(elapsed)
            success += 1
        except Exception as e:
            failure += 1
            errors.append(str(e)[:200])

    tasks = [asyncio.create_task(worker()) for _ in range(count)]
    await asyncio.gather(*tasks)

    latencies.sort()
    if not latencies:
        return BenchmarkResult(
            name=name, total=count, success=0, failure=failure,
            p50_ms=0, p95_ms=0, p99_ms=0, min_ms=0, max_ms=0, mean_ms=0,
            errors=errors,
        )

    return BenchmarkResult(
        name=name,
        total=count,
        success=success,
        failure=failure,
        p50_ms=_percentile(latencies, 50),
        p95_ms=_percentile(latencies, 95),
        p99_ms=_percentile(latencies, 99),
        min_ms=round(latencies[0], 2),
        max_ms=round(latencies[-1], 2),
        mean_ms=round(statistics.mean(latencies), 2),
        errors=errors,
    )


def _percentile(sorted_data: list[float], pct: float) -> float:
    if not sorted_data:
        return 0.0
    idx = int((pct / 100.0) * (len(sorted_data) - 1))
    return round(sorted_data[idx], 2)


# ---------------------------------------------------------------------------
# Benchmark 1: Risk Assessment (target < 50ms p95)
# ---------------------------------------------------------------------------


async def benchmark_risk_assessment() -> BenchmarkResult:
    from src.services.risk_assessment import calculate_diabetes_risk

    def call():
        return calculate_diabetes_risk(
            age=random.randint(25, 75),
            bmi=round(random.uniform(18.5, 35.0), 1),
            waist_circumference=round(random.uniform(60.0, 120.0), 1),
            family_history=random.choice([True, False]),
            physical_activity=random.choice(["high", "moderate", "low"]),
            fasting_glucose=round(random.uniform(3.5, 12.0), 1),
            has_hypertension=random.choice([True, False]),
        )

    return await _run_concurrent("risk-assessment-100", call)


# ---------------------------------------------------------------------------
# Benchmark 2: Glucose Log Writes (target < 30ms p95)
# ---------------------------------------------------------------------------

# Test glucose values (pre-computed to isolate the measurement)
_TEST_GLUCOSE_VALUES = [
    [round(random.uniform(3.5, 11.0), 1) for _ in range(7)]
    for _ in range(CONCURRENCY)
]


async def benchmark_glucose_stats() -> BenchmarkResult:
    from src.services.glucose_tracker import calculate_glucose_stats, TimeInRange

    def call():
        values = random.choice(_TEST_GLUCOSE_VALUES)
        stats = calculate_glucose_stats(values)
        tir = TimeInRange(values)
        return {**stats, "time_in_range": {"in_range_pct": tir.in_range_pct}}

    return await _run_concurrent("glucose-stats-100", call)


# ---------------------------------------------------------------------------
# Benchmark 3: Health Coach Chat (target < 2s p95, LLM dependent)
# ---------------------------------------------------------------------------

_TEST_COACH_MESSAGES = [
    "我今天空腹血糖6.8，比平时高一点，需要注意什么？",
    "最近总是觉得口渴，是不是血糖控制不好了？",
    "我今天晚餐后两小时血糖9.5，正常吗？",
    "运动后血糖反而升高了，这是为什么？",
    "我该在什么时间测血糖最准确？",
    "最近经常出现低血糖，应该怎么调整饮食？",
    "我感觉头晕乏力，是不是药物副作用？",
    "二甲双胍应该饭前还是饭后服用？",
] * 13  # 104 messages for 100 concurrent calls


async def benchmark_health_coach() -> BenchmarkResult:
    """Benchmark health coach with mock replies (no LLM dependency)."""
    from src.services.health_coach import HealthCoach, CoachContext

    coach = HealthCoach()

    def call():
        ctx = CoachContext(
            patient_id="benchmark-patient",
            recent_fpg=[round(random.uniform(3.5, 8.0), 1) for _ in range(3)],
            recent_ppg=[round(random.uniform(4.0, 11.0), 1) for _ in range(3)],
            hba1c=round(random.uniform(5.5, 9.0), 1),
            medications=random.choice([["二甲双胍"], ["二甲双胍", "胰岛素"], []]),
            diet_adherence=random.choice(["良好", "一般", "较差"]),
            exercise_adherence=random.choice(["良好", "一般", "较差"]),
        )
        msg = random.choice(_TEST_COACH_MESSAGES)
        is_urgent = coach._has_urgent_keywords(msg)
        reply = coach._mock_reply(ctx, msg)
        return {"reply": reply, "is_urgent": is_urgent}

    return await _run_concurrent("health-coach-100", call)


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------


def write_csv_report(results: list[BenchmarkResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "benchmark", "total", "success", "failure", "success_rate",
            "p50_ms", "p95_ms", "p99_ms", "min_ms", "max_ms", "mean_ms",
        ])
        for r in results:
            rate = (r.success / r.total * 100) if r.total else 0
            writer.writerow([
                r.name, r.total, r.success, r.failure, f"{rate:.1f}%",
                r.p50_ms, r.p95_ms, r.p99_ms, r.min_ms, r.max_ms, r.mean_ms,
            ])
    print(f"Report written to {path}")


def print_results(results: list[BenchmarkResult]) -> None:
    print("\n" + "=" * 80)
    print("PERFORMANCE BENCHMARK RESULTS")
    print("=" * 80)
    for r in results:
        status = "PASS" if r.failure == 0 else f"FAIL ({r.failure} errors)"
        print(f"\n  {r.name}: {status}")
        print(f"    Requests: {r.total} | Success: {r.success} | Failure: {r.failure}")
        print(f"    Latency  p50={r.p50_ms}ms  p95={r.p95_ms}ms  p99={r.p99_ms}ms")
        print(f"    Min={r.min_ms}ms  Max={r.max_ms}ms  Mean={r.mean_ms}ms")

        # Target checks
        if "risk-assessment" in r.name:
            target = 50
            ok = r.p95_ms <= target
            print(f"    Target p95 < {target}ms: {'PASS' if ok else 'FAIL'} (actual {r.p95_ms}ms)")
        elif "glucose-stats" in r.name:
            target = 30
            ok = r.p95_ms <= target
            print(f"    Target p95 < {target}ms: {'PASS' if ok else 'FAIL'} (actual {r.p95_ms}ms)")
        elif "health-coach" in r.name:
            target = 2000
            ok = r.p95_ms <= target
            print(f"    Target p95 < {target}ms: {'PASS' if ok else 'FAIL'} (actual {r.p95_ms}ms)")

        if r.errors:
            print(f"    Errors (first 3):")
            for err in r.errors[:3]:
                print(f"      - {err}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> list[BenchmarkResult]:
    print(f"Running {CONCURRENCY}-concurrent benchmarks...")
    print(f"Timeout per call: {TIMEOUT_S}s")
    print()

    results: list[BenchmarkResult] = []

    print("[1/3] Risk assessment...")
    results.append(await benchmark_risk_assessment())

    print("[2/3] Glucose statistics...")
    results.append(await benchmark_glucose_stats())

    print("[3/3] Health coach (mock)...")
    results.append(await benchmark_health_coach())

    return results


if __name__ == "__main__":
    results = asyncio.run(main())
    print_results(results)
    write_csv_report(results, OUTPUT_CSV)

    # Exit non-zero if any benchmark had failures
    total_failures = sum(r.failure for r in results)
    if total_failures > 0:
        sys.exit(1)
