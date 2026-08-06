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
      **visually confirmed in a real browser** (VS Code Remote-SSH port-forwarding from the HPC node), both
      the read path (every page rendering live data correctly) and the write path (a real job submitted by
      clicking through the Training page, landed correctly, ran on real Slurm, finished on its own)
- [x] Docker Compose for the control plane (Postgres, Redis, MLflow, MinIO, backend, frontend) — written and
      reviewed; **deliberately not run yet** — see "On Docker" below for why that's a real decision, not a gap

**Exit criteria:** submit a training job from the dashboard, watch it run on the Slurm cluster, see metrics
land in MLflow, and promote the resulting checkpoint to the model registry — all through the UI. **Met in full
as of 2026-08-05** (see below).

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
Docker.

**Frontend visually confirmed against this live session (2026-07-27):** forwarded the Vite dev server's port
over VS Code Remote-SSH and opened the real dashboard in a real browser. Every page matched the live backend
state exactly (Dashboard counts, the Cora dataset, the experiment's MLflow link, the finished job with its
Slurm job id, the promoted model's real metrics) — not a mockup.

**The actual flagship workload run on real data for the first time (2026-08-05):** found a real, no-auth
Ethereum fraud dataset (13,920 real addresses, 6,283 fraud / 7,637 normal — same schema the `samamba` plugin
expects, sourced from a public GitHub repo, see `datasets_registry/` — not the Kaggle original since that
needs API credentials this environment doesn't have) and ran it through the exact same live session: registered
via the API, `samamba` job submitted, ran as a real GPU sbatch job, promoted to the registry as
`samamba-ethereum-fraud-detector` v1 — **87.7% accuracy, 86.0% F1, `trained_on_device: 1.0`**. Until this point
every real-data run had used `gcn_baseline`; this is the first time the project's actual namesake workload
trained on its actual target problem rather than synthetic test data.

**Write path confirmed too (2026-08-05):** submitted a `gcn_baseline` job by actually clicking through the
Training page — experiment, plugin, dataset, dataset version, defaults left as rendered by the plugin's
`config_schema` — and clicked "Submit training job". Watched it land in the backend (config matched the
form's rendered defaults exactly, confirming the click actually drove the API rather than something stale),
go out as real Slurm job `33696`, and finish (`submitted → running → finished`) entirely on its own via the
Training page's 5s poll, no manual intervention after the click. **Phase 1's exit criteria is met in full.**

### On Docker

Deliberately not run yet — this is a decision, not an oversight. Everything above (backend, both plugins, the
real Slurm/GPU cluster, real MLflow, dataset registration, the model registry, and both the read and write
paths of the real frontend in a real browser) is proven working as bare processes. Docker Compose doesn't add
any *capability* on top of that — it's the same code, the same Slurm SSH connection, the same everything.
What it buys is eliminating manual setup risk (matching Python/Node versions, port collisions, path bugs —
all things this session actually hit and had to debug by hand) and making the repo runnable by someone who
isn't the person who built it. That's worth doing before handing this repo to anyone else or writing it up for
an audience that will actually try to run it, but not before then. Revisit `infra/README.md` when that need
actually arrives.

## Phase 2 — Serve and observe

- [x] Inference API: new `inference-service` dynamically loads a plugin and runs `predict()`; backend's
      `POST /inference/predict/{model_version_id}` resolves a model version into plugin+checkpoint first, so
      callers never need internal paths. **Verified against both real registered models** in the live tmux
      session: `samamba-ethereum-fraud-detector` correctly flagged a known-fraud address
      (`fraud_probability: 0.72`), `gcn-cora-classifier` correctly classified real Cora nodes. Known gap:
      checkpoint paths don't cross machines yet under Docker — see `inference-service/README.md`. No frontend
      page yet (API/script only).
- [x] Auth: JWT login (`/auth/register`, `/auth/login`, `/auth/me`), every route except health/auth/the
      internal job-status callback now requires a valid token. Datasets and experiments get tagged with
      `owner_id` on creation ("scoping" = ownership tracked, not visibility restricted — no per-user hiding of
      others' resources, deliberately, matching "no multi-tenant RBAC" in the out-of-scope list below).
      Frontend gained real Login/Register pages and now gates the whole app behind a token, stored in
      localStorage and attached to every request; a 401 anywhere clears the token and bounces to `/login`.
      `scripts/register_dataset.py` updated to authenticate (`--email/--password`, `--register` to create the
      account). **Verified live**: registered a real user, confirmed every protected route 401s without a
      token and works with one, confirmed training-service's unauthenticated status callback still works
      (this was the one endpoint that had to stay open), and ran one more full job end to end
      (submit-with-token → real Slurm run → unauthenticated callback updates it → finished) to prove nothing
      else broke.
- [x] Prometheus metrics (job queue depth, training duration, inference latency) + Grafana dashboards.
      Hand-rolled with `prometheus_client` (not an auto-instrumentation library) so `/metrics` exposes exactly
      these platform-specific signals rather than a generic HTTP firehose: backend exposes
      `mlopsforge_job_queue_depth`, `mlopsforge_jobs_total{status}`, `mlopsforge_job_duration_seconds{status}`
      (observed in the job-status callback on every terminal transition); inference-service exposes
      `mlopsforge_inference_latency_seconds{plugin_entrypoint}` and `mlopsforge_inference_requests_total{...,
      outcome}`. Both `/metrics` routes are deliberately unauthenticated (mounted outside the JWT-gated
      router) since Prometheus can't send a bearer token. A 5-panel Grafana dashboard
      (`infra/grafana/dashboards/mlopsforge.json`) covers all of it. **Verified live**: downloaded real
      Prometheus/Grafana binaries (not Docker — same pattern as MLflow earlier), generated real jobs and
      predictions, confirmed both scrape targets `up`, queried real numbers back through Prometheus directly
      and through Grafana's datasource proxy (the exact path dashboard panels use), and confirmed Grafana
      provisioned the datasource + dashboard JSON without error. Docker Compose versions of the configs
      (service-name targets) are committed but not yet run through `docker compose up` — see `infra/README.md`.
- [x] WebSocket live job status instead of polling. Backend: `GET /api/v1/ws/jobs`, in-process broadcast
      (correct for today's single-process deployment; would need Redis pub/sub across multiple replicas —
      not built since nothing here runs more than one backend process), token auth via query param since
      browsers can't set a WS handshake header, unauthenticated connections rejected at the HTTP level (403)
      by closing before `accept()`. Broadcasts from all three places a job's status actually changes
      (`create_job`, the internal status callback, cancel). Frontend: `useJobsLiveUpdates()` patches pushes
      straight into the shared `["jobs"]` React Query cache, mounted once in `Layout` so Dashboard/Training/
      Models all get live updates for free; polling dropped from 5s to a 30s fallback (not removed — safety
      net if the socket drops), with basic reconnect-with-delay built in. **Verified with a real Python
      WebSocket test client** (not just code review): confirmed the 403 rejection without a token, then
      watched real status transitions (`submitted → finished`) arrive as live pushes while a real job ran on
      Slurm — and separately confirmed the connection succeeds through the actual Vite proxy path the browser
      uses, not just directly against the backend.
- [x] Basic notifications on job completion/failure. One mechanism deliberately serves both "webhook" and
      "Slack" from this line item — a Slack incoming webhook *is* a webhook; `notify_job_terminal`
      (`backend/app/services/notifications.py`) includes a `text` field alongside the structured job data, so
      the exact same payload renders correctly if `NOTIFICATION_WEBHOOK_URL` happens to be a Slack incoming
      webhook URL, no Slack-specific code needed. Fires from all three places a job reaches a terminal state:
      immediate submission failure, training-service's status callback (finished/failed/cancelled), and manual
      cancellation. Email intentionally not built — needs SMTP credentials this environment doesn't have.
      **Verified live**: pointed a real local HTTP receiver at the webhook URL, submitted a job through to
      completion and confirmed the exact expected payload arrived (checkmark emoji, real Slurm job id, correct
      timestamps), then separately verified the cancellation code path with a second job (🛑 emoji, `cancelled`
      status) — two different code paths, both confirmed firing correctly.

This completes Phase 2 in full: Inference API, Auth, Monitoring, WebSocket live status, and Notifications —
every item verified against real infrastructure generating real data, not mocked.

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
