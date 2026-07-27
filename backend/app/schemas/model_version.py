from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ModelStage


class ModelVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    version: int
    job_id: str
    plugin_id: str
    dataset_version_id: str
    artifact_uri: str
    metrics: dict
    stage: ModelStage
    created_at: datetime


class ModelStageUpdate(BaseModel):
    stage: ModelStage
