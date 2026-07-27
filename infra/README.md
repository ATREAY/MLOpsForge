# infra — control-plane Docker Compose stack

Brings up everything except the compute plane (see [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)): Postgres,
Redis, MinIO, MLflow, the backend API, training-service, and the frontend. Run this on a machine with Docker —
not necessarily the Slurm cluster itself (see [`docs/ENVIRONMENT.md`](../docs/ENVIRONMENT.md) for why).

## Services

| Service | Image/build | Port | Purpose |
|---|---|---|---|
| `postgres` | `postgres:16-alpine` | 5432 | System of record for the backend; also backs MLflow (separate `mlflow` database — see `postgres/init.sql`, since MLflow's own table names would otherwise collide with the backend's) |
| `redis` | `redis:7-alpine` | 6379 | Job status cache / pub-sub (wired up in Phase 2) |
| `minio` | `minio/minio` | 9000 (API), 9001 (console) | Object storage for datasets, checkpoints, MLflow artifacts |
| `mlflow` | built from `mlflow/Dockerfile` | 5000 | Tracking server, backed by Postgres + MinIO |
| `backend` | built from `../backend/Dockerfile` | 8000 | FastAPI gateway |
| `training-service` | built from `../training-service/Dockerfile` | 8100 | Slurm SSH orchestration |
| `frontend` | built from `../frontend/Dockerfile` | 8080 | React dashboard, served by nginx, which also proxies `/api` to `backend` |

## Running it

```bash
cd infra
cp .env.example .env   # fill in real secrets and Slurm connection details
docker compose up --build
```

Then open http://localhost:8080.

## The Slurm SSH key

`training-service` needs a **dedicated** SSH private key (not your personal one) authorized on the Slurm
cluster's `~/.ssh/authorized_keys` — see [`training-service/README.md`](../training-service/README.md) for how
one was generated and verified for this project. Point `SLURM_SSH_KEY_HOST_PATH` in `.env` at it; compose
mounts it read-only into the container.

## Status: not yet run through `docker compose up`

This compose file and both custom Dockerfiles (`backend/Dockerfile`, `training-service/Dockerfile`,
`mlflow/Dockerfile`) were written and reviewed carefully, but this dev environment has no Docker installed
(see `docs/ENVIRONMENT.md`) — so unlike the rest of this repo, **this stack has not been brought up and
verified end-to-end**. Every individual piece it wires together *has* been verified in isolation (backend
against a live SQLite/Postgres-shaped DB, training-service against the real Slurm cluster, MLflow against a
real local tracking server, the frontend build against a live backend) — what's unverified is specifically the
Docker Compose orchestration itself: build contexts, env var wiring, service startup ordering, and the
MinIO/Postgres/MLflow container images actually working together. Run `docker compose up --build` on a
machine with Docker and fix whatever compose-specific issues come up before considering Phase 1 complete.
