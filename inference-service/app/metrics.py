"""Prometheus metrics for inference-service — the one place actual model
inference latency is observed, since predict() runs in-process here."""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

INFERENCE_LATENCY_SECONDS = Histogram(
    "mlopsforge_inference_latency_seconds",
    "Time spent inside a plugin's predict()",
    ["plugin_entrypoint"],
)
INFERENCE_REQUESTS_TOTAL = Counter(
    "mlopsforge_inference_requests_total",
    "Inference requests by plugin and outcome",
    ["plugin_entrypoint", "outcome"],
)

router = APIRouter()


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
