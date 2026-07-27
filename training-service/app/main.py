import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from app.config import get_settings
from app.orchestrator import cancel_job, submit_job
from app.poller import JobPoller
from app.schemas import SubmitRequest, SubmitResponse
from app.slurm_client import SlurmCommandError
from app.state_store import JobStateStore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()
store = JobStateStore(settings.STATE_FILE)
poller = JobPoller(store, settings.SLURM_POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    poller.start()
    logger.info("job poller started (interval=%ss)", settings.SLURM_POLL_INTERVAL_SECONDS)
    yield
    poller.stop()


app = FastAPI(title="MLOpsForge Training Service", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/submit", response_model=SubmitResponse)
def submit(payload: SubmitRequest):
    try:
        result = submit_job(
            store=store,
            job_id=payload.job_id,
            plugin_entrypoint=payload.plugin_entrypoint,
            dataset_uri=payload.dataset_uri,
            config=payload.config,
            resources=payload.resources,
            callback_url=payload.callback_url,
            mlflow_experiment_id=payload.mlflow_experiment_id,
            mlflow_tracking_uri=payload.mlflow_tracking_uri,
        )
    except SlurmCommandError as exc:
        raise HTTPException(502, f"Slurm submission failed: {exc}") from exc
    return result


@app.post("/cancel/{slurm_job_id}")
def cancel(slurm_job_id: str):
    try:
        cancel_job(store, slurm_job_id)
    except SlurmCommandError as exc:
        raise HTTPException(502, f"scancel failed: {exc}") from exc
    return {"status": "cancel requested"}


@app.get("/jobs/{job_id}")
def get_job_state(job_id: str):
    record = store.get(job_id)
    if record is None:
        raise HTTPException(404, "job not tracked by this training-service instance")
    return record
