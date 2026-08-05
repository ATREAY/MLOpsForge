"""Backend's client for the internal inference-service API. Same pattern as
training_client.py: a separate HTTP service rather than importing plugin code
into the backend, since predict() needs each plugin's runtime deps (torch,
sklearn, ...) that the backend deliberately doesn't carry."""

from typing import Any

import httpx

from app.core.config import get_settings


class InferenceServiceError(RuntimeError):
    pass


def predict(plugin_entrypoint: str, model_path: str, inputs: Any) -> Any:
    settings = get_settings()
    payload = {"plugin_entrypoint": plugin_entrypoint, "model_path": model_path, "inputs": inputs}
    try:
        resp = httpx.post(f"{settings.INFERENCE_SERVICE_URL}/predict", json=payload, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise InferenceServiceError(exc.response.text) from exc
    except httpx.HTTPError as exc:
        raise InferenceServiceError(str(exc)) from exc
    return resp.json()["prediction"]
