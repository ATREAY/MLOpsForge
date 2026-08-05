from typing import Any

from pydantic import BaseModel


class PredictRequest(BaseModel):
    plugin_entrypoint: str
    model_path: str
    inputs: Any


class PredictResponse(BaseModel):
    prediction: Any
