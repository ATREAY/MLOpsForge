"""Loads a plugin dynamically and runs its predict() — the one place outside
a Slurm job that plugin code actually executes. Kept as its own service
(rather than folded into the backend) so the backend never needs plugin
runtime deps (torch, sklearn, ...) installed — see docs/ARCHITECTURE.md.

v1: reloads the checkpoint from disk on every request (correct, not fast —
matches the "FastAPI + Torch v1, Triton v2" plan in the architecture doc).
No model caching yet; add it here first if latency becomes a problem.
"""

import logging
import sys
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException

# Unlike training-service, this service DOES import plugin code, so the repo
# root (parent of plugins/) needs to be importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from plugins.base.registry import load_plugin  # noqa: E402

from app.metrics import INFERENCE_LATENCY_SECONDS, INFERENCE_REQUESTS_TOTAL  # noqa: E402
from app.metrics import router as metrics_router  # noqa: E402
from app.schemas import PredictRequest, PredictResponse  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="MLOpsForge Inference Service", version="0.1.0")
app.include_router(metrics_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/predict", response_model=PredictResponse)
def predict(payload: PredictRequest):
    if not Path(payload.model_path).exists():
        raise HTTPException(404, f"checkpoint not found at {payload.model_path}")

    try:
        plugin = load_plugin(payload.plugin_entrypoint)
    except (ValueError, TypeError) as exc:
        raise HTTPException(400, f"invalid plugin entrypoint: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 — a plugin whose deps aren't installed here (e.g. samamba's
        # torch_geometric/mamba_ssm not being in this service's shared venv) must surface as a clear 422,
        # not fall through to FastAPI's generic unhandled-500
        raise HTTPException(422, f"failed to load plugin '{payload.plugin_entrypoint}': {exc}") from exc

    start = time.perf_counter()
    try:
        result = plugin.predict(payload.model_path, payload.inputs)
    except Exception as exc:  # noqa: BLE001 — surface any plugin failure as a 422, not a 500 crash
        INFERENCE_REQUESTS_TOTAL.labels(plugin_entrypoint=payload.plugin_entrypoint, outcome="error").inc()
        logger.exception("predict() failed for %s", payload.plugin_entrypoint)
        raise HTTPException(422, f"prediction failed: {exc}") from exc

    INFERENCE_LATENCY_SECONDS.labels(plugin_entrypoint=payload.plugin_entrypoint).observe(time.perf_counter() - start)
    INFERENCE_REQUESTS_TOTAL.labels(plugin_entrypoint=payload.plugin_entrypoint, outcome="success").inc()
    return PredictResponse(prediction=result)
