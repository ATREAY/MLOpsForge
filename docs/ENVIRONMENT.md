# Development environment notes

These constraints were discovered on the primary dev machine (an IIT-H CSE HPC login node) and shape several
architecture decisions below. Re-check them if you move to a different machine.

## What's available where

**HPC login node** (`cs25mtech14023` home dir):
- `sbatch` / `squeue` / `sinfo` / `sacct` — real Slurm cluster, partitions include `cse-gpu-all` with
  DGX A100/P100/V100 nodes.
- No Docker, no Singularity/Apptainer, no Node/npm, no system Postgres/Redis, no root.
- Module system (`module avail`) has CUDA/cuDNN/PyTorch-adjacent packages (transformers, datasets, deepspeed,
  accelerate) but nothing for the control-plane stack.
- **Home directory quota is nearly full** (5.1GB free out of 250GB — `Thesis/` and `GReaT_paper/` account for
  ~160GB of the user's unrelated work). Treat this filesystem as code-only for this project: no datasets, no
  node_modules, no built Docker images, no large checkpoints committed or cached here.

**Dev machine / laptop** (wherever you run `docker compose up`):
- Assumed to have Docker + Docker Compose and Node available. This is where the control plane actually runs.

## Why the control plane / compute plane split

Given the above, the platform cannot run as a single `docker-compose up` on the HPC node the way the original
design doc assumed. Instead:

- **Control plane** (React, FastAPI, Postgres, Redis, MLflow, MinIO, Prometheus, Grafana) runs via Docker
  Compose on any machine with Docker — a laptop, a cloud VM, or eventually a proper server. This repo is
  developed on the HPC node (code only, lightweight) and synced/cloned to wherever Docker actually runs.
- **Compute plane** is this Slurm cluster, reached exclusively over **SSH** from the `training-service`. The
  training service never assumes it's running on the same filesystem as Slurm — it authenticates over SSH
  (paramiko), writes a generated job script, runs `sbatch`, polls `squeue`/`sacct` for status, and pulls
  checkpoints/logs back over SFTP into MinIO.
- This mirrors a real pattern: a cloud-hosted ML platform driving an on-prem/HPC cluster it doesn't own the
  OS of. It's a deliberate design, not a workaround — call it out as such in interviews.

## Implication for local dev without Docker

If you're iterating on the HPC node itself (e.g. testing the Slurm SSH client, or a plugin's `train()` function
directly), use a plain Python virtualenv/conda env and SQLite instead of the full Compose stack — see
`backend/app/core/config.py` for the `DATABASE_URL` fallback. Don't try to stand up Postgres/Redis/MinIO here.
