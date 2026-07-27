"""Logs a finished job's params/metrics/checkpoint to MLflow. Called from
orchestrator.reconcile_job once a job reaches a terminal state — this is the
one place training-service writes to MLflow (see docs/ARCHITECTURE.md)."""

import logging

logger = logging.getLogger(__name__)


def log_run(
    tracking_uri: str,
    experiment_id: str,
    job_id: str,
    plugin_entrypoint: str,
    config: dict,
    metrics: dict[str, float],
    local_checkpoint_path: str | None,
) -> str:
    import mlflow

    mlflow.set_tracking_uri(tracking_uri)
    with mlflow.start_run(experiment_id=experiment_id, run_name=job_id) as run:
        mlflow.log_params(config)
        mlflow.log_metrics(metrics)
        mlflow.set_tags({"job_id": job_id, "plugin_entrypoint": plugin_entrypoint})
        if local_checkpoint_path:
            mlflow.log_artifact(local_checkpoint_path)
        return run.info.run_id
