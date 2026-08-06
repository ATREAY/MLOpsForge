"""Fires a webhook when a job reaches a terminal state (finished/failed/cancelled).

One mechanism deliberately serves both "webhook" and "Slack" from the
roadmap — a Slack incoming webhook *is* a webhook. Including a "text" field
alongside the structured job data means the exact same payload renders
correctly if NOTIFICATION_WEBHOOK_URL happens to be a Slack incoming webhook
URL, with no Slack-specific code path needed.

Email intentionally not implemented — needs SMTP credentials this
environment doesn't have configured. See docs/ROADMAP.md.
"""

import logging

import httpx

from app.core.config import get_settings
from app.models.job import Job

logger = logging.getLogger(__name__)

_EMOJI = {"finished": "✅", "failed": "❌", "cancelled": "🛑"}


def notify_job_terminal(job: Job) -> None:
    settings = get_settings()
    if not settings.NOTIFICATION_WEBHOOK_URL:
        return

    status = job.status.value
    text = f"{_EMOJI.get(status, 'ℹ️')} Job {job.id[:8]} {status}"
    if job.error_message:
        text += f" — {job.error_message}"

    payload = {
        "text": text,  # Slack incoming webhooks render this field directly
        "job_id": job.id,
        "status": status,
        "experiment_id": job.experiment_id,
        "plugin_id": job.plugin_id,
        "slurm_job_id": job.slurm_job_id,
        "error_message": job.error_message,
        "submitted_at": job.submitted_at.isoformat() if job.submitted_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }

    try:
        httpx.post(settings.NOTIFICATION_WEBHOOK_URL, json=payload, timeout=10).raise_for_status()
    except httpx.HTTPError:
        logger.exception("failed to deliver job notification webhook for job %s", job.id)
