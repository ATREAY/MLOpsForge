from typing import Any

from pydantic import BaseModel


class PredictRequest(BaseModel):
    inputs: Any


class PredictResponse(BaseModel):
    model_version_id: str
    model_name: str
    prediction: Any
