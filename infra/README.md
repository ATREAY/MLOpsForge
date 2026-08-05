# infra — control-plane Docker Compose stack

Brings up everything except the compute plane (see [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)): Postgres,
Redis, MinIO, MLflow, the backend API, training-service, inference-service, the frontend, and Prometheus +
Grafana for monitoring. Run this on a machine with Docker — not necessarily the Slurm cluster itself (see
[`docs/ENVIRONMENT.md`](../docs/ENVIRONMENT.md) for why).

## Services

| Service | Image/build | Port | Purpose |
|---|---|---|---|
| `postgres` | `postgres:16-alpine` | 5432 | System of record for the backend; also backs MLflow (separate `mlflow` database — see `postgres/init.sql`, since MLflow's own table names would otherwise collide with the backend's) |
| `redis` | `redis:7-alpine` | 6379 | Job status cache / pub-sub (wired up in Phase 2) |
| `minio` | `minio/minio` | 9000 (API), 9001 (console) | Object storage for datasets, checkpoints, MLflow artifacts |
| `mlflow` | built from `mlflow/Dockerfile` | 5000 | Tracking server, backed by Postgres + MinIO |
| `backend` | built from `../backend/Dockerfile` | 8000 | FastAPI gateway |
| `training-service` | built from `../training-service/Dockerfile` | 8100 | Slurm SSH orchestration |
| `inference-service` | built from `../inference-service/Dockerfile` | 8200 | Loads a plugin and serves predictions |
| `frontend` | built from `../frontend/Dockerfile` | 8080 | React dashboard, served by nginx, which also proxies `/api` to `backend` |
| `prometheus` | `prom/prometheus:v2.54.1` | 9090 | Scrapes `backend:8000/metrics` and `inference-service:8200/metrics` |
| `grafana` | `grafana/grafana:11.2.0` | 3000 | Dashboards over Prometheus — provisioned automatically from `grafana/provisioning/` and `grafana/dashboards/mlopsforge.json`; default login `admin`/`admin` |

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

Prometheus and Grafana specifically *were* verified — as standalone binaries (not via Docker, same as
MLflow) scraping/visualizing the real backend and inference-service running in this session. The
`prometheus.yml` scrape config and `grafana/provisioning/`/`grafana/dashboards/mlopsforge.json` files
committed here are the Docker-oriented versions (service-name targets/datasource URL); what was actually run
used `127.0.0.1`-targeted copies outside the repo. The dashboard JSON itself is identical either way and is
confirmed valid — Grafana parsed it, provisioned it without error, and its panels return real data through the
Prometheus datasource proxy.
