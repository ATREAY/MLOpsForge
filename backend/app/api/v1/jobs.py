import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.dataset import DatasetVersion
from app.models.enums import JobStatus
from app.models.experiment import Experiment
from app.models.job import Job
from app.models.plugin import Plugin
from app.models.user import User
from app.schemas.job import JobCreate, JobRead, JobStatusUpdate
from app.services.training_client import TrainingServiceError, cancel_job, submit_job

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=list[JobRead])
def list_jobs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Job).order_by(Job.created_at.desc()).all()


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    return job


@router.post("", response_model=JobRead, status_code=201)
def create_job(payload: JobCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    experiment = db.get(Experiment, payload.experiment_id)
    if experiment is None:
        raise HTTPException(404, "experiment not found")

    plugin = db.query(Plugin).filter(Plugin.name == payload.plugin_name).one_or_none()
    if plugin is None:
        raise HTTPException(404, f"plugin '{payload.plugin_name}' not found — is it registered?")

    dataset_version = db.get(DatasetVersion, payload.dataset_version_id)
    if dataset_version is None:
        raise HTTPException(404, "dataset version not found")

    job = Job(
        experiment_id=experiment.id,
        plugin_id=plugin.id,
        dataset_version_id=dataset_version.id,
        config=payload.config,
        status=JobStatus.QUEUED,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        result = submit_job(
            job_id=job.id,
            plugin_entrypoint=plugin.entrypoint,
            dataset_uri=dataset_version.storage_uri,
            config=payload.config,
            resources=plugin.default_resources,
            mlflow_experiment_id=experiment.mlflow_experiment_id,
        )
        job.status = JobStatus.SUBMITTED
        job.slurm_job_id = result.get("slurm_job_id")
        job.submitted_at = datetime.now(timezone.utc)
    except TrainingServiceError as exc:
        logger.exception("failed to submit job %s to training-service", job.id)
        job.status = JobStatus.FAILED
        job.error_message = str(exc)

    db.commit()
    db.refresh(job)
    return job


@router.patch("/{job_id}/status", response_model=JobRead)
def update_job_status(job_id: str, payload: JobStatusUpdate, db: Session = Depends(get_db)):
    """Internal callback used by training-service to report Slurm state
    transitions. Not intended for the frontend — the frontend reads job state
    via GET /jobs, populated from these updates."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "job not found")

    job.status = payload.status
    if payload.slurm_job_id:
        job.slurm_job_id = payload.slurm_job_id
    if payload.mlflow_run_id:
        job.mlflow_run_id = payload.mlflow_run_id
    if payload.logs_uri:
        job.logs_uri = payload.logs_uri
    if payload.checkpoint_uri:
        job.checkpoint_uri = payload.checkpoint_uri
    if payload.error_message:
        job.error_message = payload.error_message

    now = datetime.now(timezone.utc)
    if payload.status == JobStatus.RUNNING and job.started_at is None:
        job.started_at = now
    if payload.status in (JobStatus.FINISHED, JobStatus.FAILED, JobStatus.CANCELLED):
        job.finished_at = now

    db.commit()
    db.refresh(job)
    return job


@router.post("/{job_id}/cancel", response_model=JobRead)
def cancel_job_endpoint(job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    if job.status in (JobStatus.FINISHED, JobStatus.FAILED, JobStatus.CANCELLED):
        raise HTTPException(409, f"job already in terminal state '{job.status.value}'")
    if job.slurm_job_id is None:
        raise HTTPException(409, "job has no slurm_job_id yet, nothing to cancel")

    try:
        cancel_job(job.slurm_job_id)
    except TrainingServiceError as exc:
        raise HTTPException(502, f"failed to cancel via training-service: {exc}") from exc

    job.status = JobStatus.CANCELLED
    job.finished_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(job)
    return job
