"""Prometheus metrics definitions for digital-doctor.

Provides counters, histograms, and gauges for:
- HTTP request volume and latency
- LLM usage (requests, tokens)
- Clinical operational metrics
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_client.core import CollectorRegistry

_registry = CollectorRegistry(auto_describe=True)

# -----------------------------------------------------------------
# HTTP metrics
# -----------------------------------------------------------------

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests served",
    ["method", "endpoint", "status_code"],
    registry=_registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=_registry,
)

# -----------------------------------------------------------------
# LLM metrics
# -----------------------------------------------------------------

llm_requests_total = Counter(
    "llm_requests_total",
    "Total LLM requests",
    ["model", "status"],  # status: success / error / fallback
    registry=_registry,
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total tokens consumed by LLM calls",
    ["type"],  # type: input / output
    registry=_registry,
)

# -----------------------------------------------------------------
# Clinical / operational metrics
# -----------------------------------------------------------------

active_patients_gauge = Gauge(
    "active_patients",
    "Number of active patients in the system",
    registry=_registry,
)

alerts_unacknowledged_gauge = Gauge(
    "alerts_unacknowledged",
    "Number of unacknowledged clinical alerts",
    registry=_registry,
)

disk_free_pct_gauge = Gauge(
    "disk_free_pct",
    "Available disk space on data volume (percent)",
    registry=_registry,
)

# -----------------------------------------------------------------
# Metric update helpers
# -----------------------------------------------------------------


def get_metrics() -> bytes:
    """Return Prometheus text format metrics."""
    return generate_latest(_registry)
