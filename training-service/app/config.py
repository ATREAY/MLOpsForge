from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SERVICE_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    HOST: str = "0.0.0.0"
    PORT: int = 8100

    # SSH connection to the Slurm login node. See docs/ENVIRONMENT.md — this is
    # the one place credentials to the compute plane live.
    SLURM_SSH_HOST: str = "localhost"
    SLURM_SSH_PORT: int = 22
    SLURM_SSH_USER: str = ""
    SLURM_SSH_KEY_PATH: str = ""

    # Where, on the Slurm cluster's filesystem, this repo is checked out and job
    # working directories get created under.
    SLURM_REPO_PATH: str = ""
    SLURM_REMOTE_WORKDIR: str = ""  # defaults to f"{SLURM_REPO_PATH}/_slurm_runs" if unset
    SLURM_PYTHON_BIN: str = "python3"

    SLURM_DEFAULT_PARTITION: str = "cse-gpu-all"
    SLURM_POLL_INTERVAL_SECONDS: int = 15

    # Only needed if dataset_uri values use the s3:// scheme — see dataset_resolver.py
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"

    # Default MLflow tracking server; overridden per-submission by the
    # mlflow_tracking_uri the backend sends (see schemas.SubmitRequest), so this
    # is only used as a fallback.
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"

    # State file tracking {internal_job_id -> tracking info} across restarts.
    STATE_FILE: str = str(SERVICE_ROOT / "_state" / "jobs.json")

    def remote_workdir(self) -> str:
        return self.SLURM_REMOTE_WORKDIR or f"{self.SLURM_REPO_PATH}/_slurm_runs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
