import ipaddress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from starlette.responses import JSONResponse

from src.config import settings
from src.api.router import api_router
from src.api.metrics_middleware import MetricsTrackingMiddleware
from src.services.health_service import system_health, check_database, check_redis
from src.services.logging_config import setup_logging, RequestIDMiddleware
from src.services.metrics import get_metrics

# ---------------------------------------------------------------------------
# Logging — configure before anything else
# ---------------------------------------------------------------------------
setup_logging(debug=settings.DEBUG)

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

# ---------------------------------------------------------------------------
# Middleware (order matters — last added runs first for requests)
# ---------------------------------------------------------------------------
app.add_middleware(MetricsTrackingMiddleware)

app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# ---------------------------------------------------------------------------
# Docker-internal networks for metrics endpoint access
# ---------------------------------------------------------------------------
_INTERNAL_NETWORKS = [
    ipaddress.IPv4Network("10.0.0.0/8"),
    ipaddress.IPv4Network("172.16.0.0/12"),
    ipaddress.IPv4Network("192.168.0.0/16"),
]


def _is_internal_request(request: Request) -> bool:
    """Check if the request originates from an internal/Docker network."""
    client_host = request.client.host if request.client else "127.0.0.1"
    # Allow test client connections
    if client_host == "testclient":
        return True
    try:
        addr = ipaddress.IPv4Address(client_host)
    except ValueError:
        return False
    if addr == ipaddress.IPv4Address("127.0.0.1") or addr == ipaddress.IPv4Address("::1"):
        return True
    return any(addr in net for net in _INTERNAL_NETWORKS)


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
async def health():
    """Full system health — aggregates all dependency checks."""
    result = await system_health()
    status_code = 200 if result["status"] != "unhealthy" else 503
    return JSONResponse(content=result, status_code=status_code)


@app.get("/health/live")
async def health_live():
    """Kubernetes liveness probe — minimal check, just confirms the process is running."""
    return {"status": "ok", "version": settings.VERSION}


@app.get("/health/ready")
async def health_ready():
    """Kubernetes readiness probe — confirms DB and Redis are reachable."""
    db_result = await check_database()
    redis_result = await check_redis()

    status = "ok" if db_result.status != "unhealthy" and redis_result.status != "unhealthy" else "not_ready"
    status_code = 200 if status == "ok" else 503
    return JSONResponse(
        content={
            "status": status,
            "database": db_result.status,
            "redis": redis_result.status,
        },
        status_code=status_code,
    )


# ---------------------------------------------------------------------------
# Prometheus metrics endpoint
# ---------------------------------------------------------------------------


@app.get("/metrics")
async def metrics(request: Request):
    """Prometheus scrape endpoint — internal access only."""
    if not _is_internal_request(request):
        return JSONResponse(
            content={"detail": "Forbidden — internal access only"},
            status_code=403,
        )
    return PlainTextResponse(content=get_metrics(), media_type="text/plain; version=0.0.4")
