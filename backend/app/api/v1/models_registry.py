import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.job import Job
from app.models.model_version import ModelVersion
from app.schemas.model_version import ModelStageUpdate, ModelVersionRead
from app.services.mlflow_client import get_run_metrics

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=list[ModelVersionRead])
def list_model_versions(name: str | None = None, db: Session = Depends(get_db)):
    query = db.query(ModelVersion)
    if name:
        query = query.filter(ModelVersion.name == name)
    return query.order_by(ModelVersion.name, ModelVersion.version.desc()).all()


@router.get("/{model_version_id}", response_model=ModelVersionRead)
def get_model_version(model_version_id: str, db: Session = Depends(get_db)):
    model_version = db.get(ModelVersion, model_version_id)
    if model_version is None:
        raise HTTPException(404, "model version not found")
    return model_version


@router.post("/from-job/{job_id}", response_model=ModelVersionRead, status_code=201)
def register_model_from_job(job_id: str, name: str, db: Session = Depends(get_db)):
    """Promote a finished job's checkpoint into the model registry as a new
    version. Called by training-service on job completion, or manually from the
    dashboard for a run the training-service didn't auto-register."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "job not found")
    if job.status.value != "finished":
        raise HTTPException(409, "job has not finished successfully")
    if not job.checkpoint_uri:
        raise HTTPException(409, "job has no checkpoint recorded yet")

    metrics: dict[str, float] = {}
    if job.mlflow_run_id:
        try:
            metrics = get_run_metrics(job.mlflow_run_id)
        except Exception:  # noqa: BLE001 — a registry promotion shouldn't fail just because MLflow is unreachable
            logger.exception("could not fetch metrics from MLflow run %s", job.mlflow_run_id)

    existing_count = db.query(ModelVersion).filter(ModelVersion.name == name).count()
    model_version = ModelVersion(
        name=name,
        version=existing_count + 1,
        job_id=job.id,
        plugin_id=job.plugin_id,
        dataset_version_id=job.dataset_version_id,
        artifact_uri=job.checkpoint_uri,
        metrics=metrics,
    )
    db.add(model_version)
    db.commit()
    db.refresh(model_version)
    return model_version


@router.patch("/{model_version_id}/stage", response_model=ModelVersionRead)
def update_model_stage(model_version_id: str, payload: ModelStageUpdate, db: Session = Depends(get_db)):
    model_version = db.get(ModelVersion, model_version_id)
    if model_version is None:
        raise HTTPException(404, "model version not found")
    model_version.stage = payload.stage
    db.commit()
    db.refresh(model_version)
    return model_version
