from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root: backend/app/core/config.py -> backend/app -> backend -> repo root
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Central config. Every value has a dev-friendly default so the API boots with
    zero setup on the HPC node (SQLite, no Redis/MinIO required) and is fully
    overridden via env vars / .env when run through docker-compose."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "MLOpsForge"
    ENV: str = "development"
    API_V1_PREFIX: str = "/api/v1"

    # Falls back to a local SQLite file so `uvicorn app.main:app` works with no
    # external services running. docker-compose sets this to the Postgres DSN.
    DATABASE_URL: str = f"sqlite:///{REPO_ROOT}/backend/mlopsforge.db"

    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO / S3-compatible object storage
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "mlopsforge"

    MLFLOW_TRACKING_URI: str = "http://localhost:5000"

    JWT_SECRET_KEY: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24

    # Slurm compute plane, reached over SSH from training-service. See docs/ENVIRONMENT.md
    SLURM_SSH_HOST: str = ""
    SLURM_SSH_USER: str = ""
    SLURM_SSH_KEY_PATH: str = ""
    SLURM_REMOTE_WORKDIR: str = "~/MLSys_Projects/MLOpsForge/_slurm_runs"
    SLURM_DEFAULT_PARTITION: str = "cse-gpu-all"

    TRAINING_SERVICE_URL: str = "http://localhost:8100"

    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    PLUGINS_DIR: str = str(REPO_ROOT / "plugins")


@lru_cache
def get_settings() -> Settings:
    return Settings()
