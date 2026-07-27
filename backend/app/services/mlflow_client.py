"""Thin wrapper around the MLflow tracking client. MLflow is the source of
truth for run params/metrics/artifacts (see docs/ARCHITECTURE.md) — Postgres
only stores the ids needed to look a run up (Experiment.mlflow_experiment_id,
Job.mlflow_run_id) plus a metrics snapshot on ModelVersion for fast listing.

Every call here is wrapped by the caller in a try/except: MLflow being
unreachable (e.g. during local dev without the full docker-compose stack up)
should degrade the platform, not break it.
"""

import logging

from mlflow.tracking import MlflowClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _client() -> MlflowClient:
    return MlflowClient(tracking_uri=get_settings().MLFLOW_TRACKING_URI)


def get_or_create_experiment(name: str) -> str:
    client = _client()
    experiment = client.get_experiment_by_name(name)
    if experiment is not None:
        return experiment.experiment_id
    return client.create_experiment(name)


def get_run_metrics(run_id: str) -> dict[str, float]:
    run = _client().get_run(run_id)
    return dict(run.data.metrics)
