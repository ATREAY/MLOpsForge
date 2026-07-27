from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import JobStatus


class JobCreate(BaseModel):
    experiment_id: str
    plugin_name: str
    dataset_version_id: str
    config: dict = {}


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    experiment_id: str
    plugin_id: str
    dataset_version_id: str
    config: dict
    status: JobStatus
    slurm_job_id: str | None
    mlflow_run_id: str | None
    logs_uri: str | None
    checkpoint_uri: str | None
    error_message: str | None
    submitted_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class JobStatusUpdate(BaseModel):
    """Internal-only: training-service reports status changes back through this shape."""

    status: JobStatus
    slurm_job_id: str | None = None
    mlflow_run_id: str | None = None
    logs_uri: str | None = None
    checkpoint_uri: str | None = None
    error_message: str | None = None
