from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.model_version import ModelVersion
from app.models.plugin import Plugin
from app.schemas.inference import PredictRequest, PredictResponse
from app.services.inference_client import InferenceServiceError, predict as run_inference

router = APIRouter(prefix="/inference", tags=["inference"])


@router.post("/predict/{model_version_id}", response_model=PredictResponse)
def predict(model_version_id: str, payload: PredictRequest, db: Session = Depends(get_db)):
    """Callers only ever need a model version id — the backend resolves that
    into the plugin entrypoint + checkpoint path inference-service actually
    needs, so no internal file paths leak past this API."""
    model_version = db.get(ModelVersion, model_version_id)
    if model_version is None:
        raise HTTPException(404, "model version not found")

    plugin = db.get(Plugin, model_version.plugin_id)
    if plugin is None:
        raise HTTPException(409, "model version references a plugin that no longer exists")

    try:
        result = run_inference(
            plugin_entrypoint=plugin.entrypoint,
            model_path=model_version.artifact_uri,
            inputs=payload.inputs,
        )
    except InferenceServiceError as exc:
        raise HTTPException(502, f"inference failed: {exc}") from exc

    return PredictResponse(model_version_id=model_version.id, model_name=model_version.name, prediction=result)
