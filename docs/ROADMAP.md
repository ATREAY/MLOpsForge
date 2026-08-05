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
      **visually confirmed in a real browser** (VS Code Remote-SSH port-forwarding from the HPC node), every
      page correctly rendering live data: the real Cora dataset, the real experiment + its MLflow link, the
      real finished job with its Slurm job id, the real promoted model with real accuracy/GPU-confirmation
      metrics. Read path confirmed end to end; submitting a *new* job by clicking through the Training page
      (rather than curl) is the one interaction still untried.
- [x] Docker Compose for the control plane (Postgres, Redis, MLflow, MinIO, backend, frontend) — written and
      reviewed, but **not yet run end-to-end** (no Docker in the dev environment); see `infra/README.md`

**Exit criteria:** submit a SAMamba training job from the dashboard, watch it run on the Slurm cluster, see
metrics land in MLflow, and promote the resulting checkpoint to the model registry — all through the UI.

Every piece of this has been verified individually against real infrastructure (the actual Slurm cluster, a
real local MLflow server, a live backend instance, a real frontend build) except the two things that need an
environment this one doesn't have: `docker compose up` itself, and a browser to click through the UI. Both are
the natural first steps on a machine that has Docker/a browser — see `infra/README.md` and `frontend/README.md`.

**Full exit criteria met once, without the UI (2026-07-27):** ran backend + training-service + a real local
MLflow server together (bare processes in tmux, no Docker), against the real Slurm cluster, on a real dataset
(`scripts/prepare_cora_dataset.py` — the classic Cora citation network, not synthetic data): registered the
dataset, created an experiment (linked to a real MLflow experiment), submitted a `gcn_baseline` job entirely
through the HTTP API, watched it go `submitted → finished` via the API (not squeue directly — proving
training-service's poller → backend callback loop works), and promoted it to the model registry with real
metrics pulled from MLflow (88.7% accuracy, `trained_on_device: 1.0` confirming real GPU use). This also caught
and fixed two real bugs: plugins never moved tensors to `cuda` (silently CPU-only regardless of what Slurm
allocated), and the backend hardcoded a Docker-only callback hostname that would have silently broken outside
Docker. The only remaining gap to a fully complete Phase 1 is driving this same flow through the **frontend**
instead of curl, and doing it all via **Docker Compose** instead of bare processes.

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
