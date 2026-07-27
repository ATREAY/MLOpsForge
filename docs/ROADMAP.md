# Roadmap

Phased so there's always a working, demoable slice. Check items off as they land; keep this file honest —
it's the fastest way to answer "what's actually done" in a future session or an interview.

## Phase 1 — Foundation (train one real model end to end)

- [x] Repo scaffold, architecture docs
- [x] Backend core: FastAPI skeleton, config, SQLAlchemy models, Alembic migration for initial schema
- [x] `BaseModelPlugin` interface + plugin registry + `plugins/samamba` (placeholder model body, real lifecycle) +
      `plugins/gcn_baseline` (proves the interface is model-agnostic) — both verified end-to-end via `run_train.py`
- [x] Dataset Manager: dataset/version CRUD + presigned-upload API (backend), versioned in Postgres, files
      staged for MinIO, plus `scripts/register_dataset.py` for onboarding a real dataset — verified end-to-end
      against a live backend instance
- [x] Training Service: Slurm SSH client, job script templating, submit + poll — **verified against the real
      HPC cluster**: submitted an actual sbatch job to `cse-gpu-all`, watched QUEUED→RUNNING→FINISHED via
      squeue/sacct, recovered checkpoint + metrics
- [x] MLflow integration: experiment create/lookup, run logging (params/metrics/checkpoint artifact) on job
      completion, metrics readback for the registry — **verified against a real local MLflow server**
- [x] Model Registry: promote a finished run's checkpoint to a versioned model, with real metrics pulled
      from MLflow
- [x] React frontend: Datasets, Training (submit + live queue), Experiments, Models pages wired to the API —
      build verified (npm ci + tsc + vite build clean, dev server's /api proxy confirmed against a live
      backend); **not yet visually checked in a real browser**, no browser available in the dev environment
- [ ] Docker Compose for the control plane (Postgres, Redis, MLflow, MinIO, backend, frontend, nginx)

**Exit criteria:** submit a SAMamba training job from the dashboard, watch it run on the Slurm cluster, see
metrics land in MLflow, and promote the resulting checkpoint to the model registry — all through the UI.

## Phase 2 — Serve and observe

- [ ] Inference API: load a registered model version, serve predictions over REST
- [ ] Auth: JWT login, per-user experiment/job scoping
- [ ] Prometheus metrics (job queue depth, training duration, inference latency) + Grafana dashboards
- [ ] WebSocket live job status instead of polling
- [ ] Basic notifications on job completion/failure (webhook, then Slack/email)

## Phase 3 — Only if time permits before placements

- [ ] A second real model plugin beyond SAMamba/GCN baseline, submitted end to end, to prove reusability
      wasn't a paper exercise
- [ ] Explainability: attention/subgraph visualization for SAMamba predictions
- [ ] Triton Inference Server as an alternative serving backend
- [ ] Kafka streaming ingestion for near-real-time transaction scoring
- [ ] Multi-run comparison view in the dashboard

## Explicitly out of scope for now

Feature store, multi-tenant RBAC beyond basic auth, autoscaling the Slurm partition, anything requiring root
on the HPC cluster. Revisit only if a specific interview conversation calls for it.
