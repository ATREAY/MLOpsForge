# MLOpsForge

**A production-grade, model-agnostic ML infrastructure platform** — train, track, register, deploy, and monitor
any PyTorch model on a Slurm/HPC GPU cluster, controlled entirely from a web dashboard.

The first workload demonstrated on the platform is **Ethereum fraud detection using SAMamba** (a graph/sequence
model), but SAMamba is a *plugin*, not the platform. Any model that implements the `BaseModelPlugin` interface
(see [`plugins/`](plugins/)) can be trained, tracked, and served the same way.

> "I built reusable ML infrastructure. SAMamba is one of the supported workloads used to demonstrate it."

## Why this exists

Most ML course projects look like `dataset -> train.py -> accuracy`. MLOpsForge instead looks like what an
ML platform/infra team actually builds: separate services for dataset management, training orchestration,
experiment tracking, model registry, inference, and monitoring — talking to each other over well-defined APIs,
with a real HPC scheduler (Slurm) as the compute backend instead of a single local GPU.

## Architecture

MLOpsForge is split into a **control plane** (stateless-ish services you run anywhere with Docker) and a
**compute plane** (a Slurm HPC cluster, reached over SSH). This split is deliberate, not incidental: it mirrors
how real organizations run a cloud/on-prem control plane against an on-prem or HPC GPU cluster they don't fully
control, and it's also a hard constraint of the dev environment this was built in (see
[`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md)).

```
                                   CONTROL PLANE (Docker, runs anywhere)
 ┌──────────────────────────────────────────────────────────────────────────────────┐
 │                                 React Dashboard                                  │
 └───────────────────────────────────┬──────────────────────────────────────────────┘
                                      │  REST / WebSocket
                              FastAPI Gateway (backend/)
                                      │
        ┌───────────┬────────────────┼─────────────────┬───────────────┐
        │           │                │                  │               │
     Dataset     Training       Experiment          Deployment      Monitoring
     Manager      Service        Tracking            Service          Service
        │           │                │                  │               │
        │      (SSH client)         MLflow          FastAPI/Torch    Prometheus
        │           │                │                  │               │
        └───────────┼────────────────┴──────────────────┴───────────────┘
                     │
              PostgreSQL + Redis + MinIO (object storage)
                     │
                     │  SSH (paramiko) — sbatch / squeue / sacct / sftp
                     ▼
 ┌──────────────────────────────────────────────────────────────────────────────────┐
 │                     COMPUTE PLANE — Slurm HPC Cluster                            │
 │        login node  →  sbatch job.sh  →  Slurm scheduler  →  GPU node             │
 │        (DGX A100 / P100 / V100)  →  runs a registered model plugin               │
 │        → writes checkpoints/logs → control plane pulls results back over SFTP    │
 └──────────────────────────────────────────────────────────────────────────────────┘
```

Full component-by-component breakdown: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Repository layout

```
MLOpsForge/
├── backend/            FastAPI control-plane API: auth, datasets, experiments, jobs, models, metrics
├── plugins/            Model plugin implementations (BaseModelPlugin contract). SAMamba lives here.
├── training-service/   Slurm orchestration: job templates, SSH client, sbatch/squeue/sacct polling
├── sdk/                Python client SDK — how a plugin author or script talks to the platform
├── frontend/           React + TypeScript dashboard
├── infra/              docker-compose stack: Postgres, Redis, MLflow, MinIO, nginx, Prometheus, Grafana
├── examples/           End-to-end example: Ethereum fraud detection with the SAMamba plugin
├── datasets_registry/  Local dataset staging area (gitignored; real data lives in MinIO/HPC storage)
├── scripts/            Dev/ops scripts (bootstrap, seed data, deploy)
└── docs/               Architecture, roadmap, environment notes, ADRs
```

## Status

Early build — see [`docs/ROADMAP.md`](docs/ROADMAP.md) for the phased plan and current progress.

## Tech stack

| Layer                | Technology |
|-----------------------|------------|
| Frontend              | React, TypeScript, Vite, TailwindCSS, shadcn/ui, React Query |
| Backend gateway       | FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic |
| Database              | PostgreSQL |
| Cache / task state    | Redis |
| Training compute      | PyTorch, Slurm (real HPC cluster), submitted via SSH (paramiko) |
| Experiment tracking   | MLflow |
| Object storage        | MinIO (S3-compatible) |
| Monitoring            | Prometheus + Grafana |
| Inference             | FastAPI + Torch (v1) → Triton Inference Server (v2) |
| Containerization      | Docker Compose (control plane only — compute plane is bare-metal Slurm) |
| Reverse proxy         | Nginx |

## License

MIT — see [LICENSE](LICENSE).
