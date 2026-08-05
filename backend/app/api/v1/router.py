from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.v1 import auth, datasets, experiments, health, inference, jobs, models_registry, plugins, ws

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)

# jobs.router is gated per-endpoint, not here — it has one internal-only
# endpoint (training-service's status callback) that must stay unauthenticated.
api_router.include_router(jobs.router)

# ws.router authenticates by hand (token query param, not a header) — see
# its module docstring — so it isn't wrapped in the standard dependency list.
api_router.include_router(ws.router)

_authenticated = [Depends(get_current_user)]
api_router.include_router(datasets.router, dependencies=_authenticated)
api_router.include_router(plugins.router, dependencies=_authenticated)
api_router.include_router(experiments.router, dependencies=_authenticated)
api_router.include_router(models_registry.router, dependencies=_authenticated)
api_router.include_router(inference.router, dependencies=_authenticated)
