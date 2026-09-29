from fastapi import APIRouter, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from app.providers.triage_factory import triage_manager

router = APIRouter(tags=["Metrics"])

# Prometheus Metrics Definitions
HTTP_REQUESTS_TOTAL = Counter(
    "civicpulse_http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status"]
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "civicpulse_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"]
)

TRIAGE_FALLBACK_TOTAL = Counter(
    "civicpulse_triage_fallback_total",
    "Total times AI triage fell back to rule-based triage"
)


@router.get("/metrics")
async def prometheus_metrics():
    """Exposes application metrics in official Prometheus text format."""
    # Synchronize fallback counter from triage_manager
    # Note: Using set or reset to reflect current manager state
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
