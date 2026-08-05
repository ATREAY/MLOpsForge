"""Prometheus metrics — hand-rolled with prometheus_client rather than an
auto-instrumentation library, so /metrics exposes exactly the
platform-specific signals the roadmap asks for (job queue depth, job
duration) instead of a generic HTTP-metrics firehose. Mounted directly on the
top-level app (not under API_V1_PREFIX), so it's unauthenticated at the
conventional /metrics path Prometheus expects, and never touches the JWT gate
applied to api_router.
"""

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, Histogram, generate_latest
from sqlalchemy import func

from app.db.session import SessionLocal
from app.models.enums import JobStatus
from app.models.job import Job

JOBS_BY_STATUS = Gauge("mlopsforge_jobs_total", "Jobs by current status", ["status"])
JOB_QUEUE_DEPTH = Gauge("mlopsforge_job_queue_depth", "Jobs currently queued, submitted, or running")
JOB_DURATION_SECONDS = Histogram(
    "mlopsforge_job_duration_seconds",
    "Wall-clock time from submission to a terminal state",
    ["status"],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600, float("inf")),
)

_ACTIVE_STATUSES = {JobStatus.QUEUED.value, JobStatus.SUBMITTED.value, JobStatus.RUNNING.value}


def _refresh_job_gauges() -> None:
    """Runs on every /metrics scrape rather than being kept continuously in
    sync — simpler and correct by construction (always reflects current DB
    state), at the cost of one small grouped query per scrape."""
    db = SessionLocal()
    try:
        rows = db.query(Job.status, func.count(Job.id)).group_by(Job.status).all()
        counts = {status.value: count for status, count in rows}
        for status in JobStatus:
            JOBS_BY_STATUS.labels(status=status.value).set(counts.get(status.value, 0))
        JOB_QUEUE_DEPTH.set(sum(counts.get(s, 0) for s in _ACTIVE_STATUSES))
    finally:
        db.close()


router = APIRouter()


@router.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    _refresh_job_gauges()
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
