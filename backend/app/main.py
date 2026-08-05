import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.metrics import router as metrics_router
from app.db.session import SessionLocal
from app.services.plugin_registry import sync_plugin_registry
from app.services.storage import ensure_bucket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    try:
        ensure_bucket()
    except Exception:  # noqa: BLE001 — MinIO being unreachable shouldn't block backend startup
        logger.exception("could not ensure MinIO bucket '%s' exists", settings.S3_BUCKET)

    db = SessionLocal()
    try:
        synced = sync_plugin_registry(db, settings.PLUGINS_DIR)
        logger.info("startup: %d plugin(s) registered", len(synced))
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.APP_NAME, version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    app.include_router(metrics_router)  # deliberately not under API_V1_PREFIX — unauthenticated, for Prometheus
    return app


app = create_app()
