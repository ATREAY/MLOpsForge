"""Backend's client for the internal training-service API. Kept as a separate
HTTP service (rather than sharing DB models) so training-service can be scaled,
deployed, or restarted independently of the API gateway, and so its SSH
credentials to the Slurm cluster never need to be reachable from the frontend."""

import httpx

from app.core.config import get_settings


class TrainingServiceError(RuntimeError):
    pass


def submit_job(
    job_id: str,
    plugin_entrypoint: str,
    dataset_uri: str,
    config: dict,
    resources: dict,
    mlflow_experiment_id: str | None,
) -> dict:
    settings = get_settings()
    payload = {
        "job_id": job_id,
        "plugin_entrypoint": plugin_entrypoint,
        "dataset_uri": dataset_uri,
        "config": config,
        "resources": resources,
        "mlflow_experiment_id": mlflow_experiment_id,
        "mlflow_tracking_uri": settings.MLFLOW_TRACKING_URI,
        "callback_url": f"http://backend:8000{settings.API_V1_PREFIX}/jobs/{job_id}/status",
    }
    try:
        resp = httpx.post(f"{settings.TRAINING_SERVICE_URL}/submit", json=payload, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise TrainingServiceError(str(exc)) from exc
    return resp.json()


def cancel_job(slurm_job_id: str) -> None:
    settings = get_settings()
    try:
        resp = httpx.post(f"{settings.TRAINING_SERVICE_URL}/cancel/{slurm_job_id}", timeout=15)
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise TrainingServiceError(str(exc)) from exc
