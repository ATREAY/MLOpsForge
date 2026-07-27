from fastapi import APIRouter

from app.api.v1 import datasets, experiments, health, jobs, models_registry, plugins

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(datasets.router)
api_router.include_router(plugins.router)
api_router.include_router(experiments.router)
api_router.include_router(jobs.router)
api_router.include_router(models_registry.router)
