import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.experiment import Experiment
from app.models.user import User
from app.schemas.experiment import ExperimentCreate, ExperimentRead
from app.services.mlflow_client import get_or_create_experiment

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("", response_model=list[ExperimentRead])
def list_experiments(db: Session = Depends(get_db)):
    return db.query(Experiment).order_by(Experiment.created_at.desc()).all()


@router.post("", response_model=ExperimentRead, status_code=201)
def create_experiment(
    payload: ExperimentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    experiment = Experiment(**payload.model_dump(), owner_id=current_user.id)

    try:
        experiment.mlflow_experiment_id = get_or_create_experiment(payload.name)
    except Exception:  # noqa: BLE001 — MLflow being unreachable shouldn't block experiment creation
        logger.exception("could not create/lookup MLflow experiment for '%s'", payload.name)

    db.add(experiment)
    db.commit()
    db.refresh(experiment)
    return experiment


@router.get("/{experiment_id}", response_model=ExperimentRead)
def get_experiment(experiment_id: str, db: Session = Depends(get_db)):
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(404, "experiment not found")
    return experiment
