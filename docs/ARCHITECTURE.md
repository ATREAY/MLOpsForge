# Architecture

## Guiding principle

The platform never imports a model-specific module. Everything it knows about SAMamba, GCN, or any future model
comes through the `BaseModelPlugin` contract in [`plugins/base/`](../plugins/base). Adding a new model means
adding a new plugin directory — zero changes to `backend/` or `training-service/`.

## Services

### 1. `backend/` — FastAPI gateway (the brain)

Owns all state and business logic. Sub-routers under `app/api/v1/`:

| Router | Responsibility |
|---|---|
| `auth` | JWT login/refresh, user management |
| `datasets` | Dataset registry: register, version, fetch metadata, presigned upload/download via MinIO |
| `plugins` | List registered model plugins and their config schema (for the frontend to render a form) |
| `experiments` | Create/list experiment runs; proxies MLflow for metrics/artifacts |
| `jobs` | Submit training job → delegates to `training-service`; poll status; fetch logs |
| `models` | Model registry: versions, stage transitions (staging/production/archived), metadata |
| `inference` | Serve predictions from a registered model version |
| `metrics` | Prometheus-scrape-friendly `/metrics` plus app-level aggregate endpoints for the dashboard |

Talks to: PostgreSQL (system of record), Redis (job status cache / pub-sub for live updates), MinIO (artifacts),
MLflow (tracking server, via its REST API), and `training-service` (internal HTTP call).

### 2. `training-service/` — Slurm orchestration

A focused internal service (not directly exposed to the internet). Given a job request
`{plugin_name, dataset_id, config, gpu_count}`:

1. Look up the plugin's `train.py` entrypoint and its Slurm resource defaults (`plugins/<name>/plugin.yaml`).
2. Render a job script from `training-service/slurm_templates/train_job.sh.j2`.
3. Open an SSH connection (paramiko) to the HPC login node, SFTP the script + a resolved config JSON up,
   run `sbatch`, capture the Slurm job ID.
4. Persist `{internal_job_id -> slurm_job_id}` and poll `squeue`/`sacct` on an interval (or on-demand) to update
   status: `QUEUED -> RUNNING -> FINISHED | FAILED | CANCELLED`.
5. On completion, SFTP checkpoints/logs back and push them to MinIO; write final metrics into MLflow.

This is the one place SSH credentials to the HPC cluster live. See `training-service/app/slurm_client.py`.

### 3. `plugins/` — model plugin contract

```python
class BaseModelPlugin(ABC):
    name: str
    version: str

    def get_config_schema(self) -> dict: ...      # JSON schema -> rendered as a form in the UI
    def train(self, dataset_path: str, config: dict, output_dir: str) -> TrainResult: ...
    def evaluate(self, model_path: str, dataset_path: str, config: dict) -> dict: ...
    def predict(self, model_path: str, inputs: Any) -> Any: ...
    def load(self, model_path: str): ...
```

Each plugin ships its own `requirements.txt` (installed into the Slurm job's env, not the control plane) and a
`plugin.yaml` declaring default resources (GPUs, partition, time limit) and its config schema. `plugins/samamba/`
is the reference implementation for Ethereum fraud detection; `plugins/gcn_baseline/` exists specifically to
prove the interface is not SAMamba-shaped.

### 4. `inference-service/` — model serving

The one service outside a Slurm job that actually imports and runs plugin code. Given `{plugin_entrypoint,
model_path, inputs}`, it dynamically loads the plugin (same `plugins.base.registry.load_plugin` training-service's
`run_train.py` uses) and calls `predict()`. Kept separate from the backend specifically so the backend never
needs torch/sklearn/etc. installed — the backend's `/inference/predict/{model_version_id}` route resolves a
model version into those three fields (via the model registry) before calling this service, so external callers
only ever need a model version id, never an internal checkpoint path.

v1 reloads the checkpoint from disk per request — correct, not optimized; see
`inference-service/README.md` for the caching/scaling notes and a known gap around checkpoint paths
crossing machines under Docker.

### 5. `frontend/` — React dashboard

Pages: Dashboard, Datasets, Experiments, Training (submit + queue view), Models (registry), Compare (config +
live-MLflow-metrics comparison across finished runs). Talks only to `backend/`'s REST API; never touches Slurm,
MLflow, MinIO, or inference-service directly. An Inference page (try a registered model against arbitrary
inputs) is not built yet — today the inference API is curl/script-only.

### 6. Data stores

- **PostgreSQL** — system of record: `users`, `datasets`, `dataset_versions`, `experiments`, `jobs`,
  `model_versions`, `plugins`. See `backend/app/models/`.
- **Redis** — declared in config/docker-compose but not actually wired into any code path yet. The originally
  planned job-status pub/sub (see `docs/ROADMAP.md`'s history) ended up built differently — see the WebSocket
  note below — so Redis remains unused. Not removed, since it's cheap to keep declared for whatever actually
  needs it first.
- **Kafka** — not part of the control plane's own request/response path; it backs `streaming-service`'s
  near-real-time transaction scoring demo (a producer simulating a live feed, a consumer scoring through the
  real inference API). See section 8 below.
- **MinIO** — blob storage for dataset files, checkpoints, plots, logs. Postgres stores metadata + MinIO keys,
  never the blobs themselves.
- **MLflow** — experiment/run tracking and its own model registry backing store; the backend's `/experiments`
  and `/models` routers are a thin layer over MLflow's REST API plus MLOpsForge-specific metadata (which plugin,
  which Slurm job, which dataset version) that MLflow doesn't natively model.

### 7. `streaming-service/` — near-real-time transaction scoring (Kafka)

A producer/consumer pair, not a long-running server like the other services — invoked on demand the way
`scripts/register_dataset.py` is, not started in tmux/Compose permanently. `producer.py` streams real rows
from the Ethereum fraud dataset to a `ethereum-transactions` Kafka topic, standing in for whatever real
upstream system would produce these events. `consumer.py` subscribes, scores each transaction through the
*same* authenticated `POST /inference/predict/{model_version_id}` endpoint anything else would use — no
shortcut that bypasses the platform to score faster — and publishes results to `ethereum-fraud-scores`. Proves
the inference path is fast enough for a streaming use case (39–163ms per transaction, verified), not just
batch/on-demand calls.

## Job lifecycle (end to end)

```
POST /api/v1/jobs {plugin: "samamba", dataset_version_id: 7, config: {...}}
  → backend validates config against plugin's schema, creates Job row (status=QUEUED)
  → backend calls training-service internal API
  → training-service renders sbatch script, SSHes to HPC, runs sbatch → slurm_job_id=42891
  → training-service updates Job row, backend broadcasts the new status to every connected
    WebSocket client via an in-process connection manager (app/core/ws.py) — correct for
    today's single-process deployment; would need Redis pub/sub across multiple replicas
  → frontend WebSocket client receives QUEUED → RUNNING as squeue reflects it
  → on Slurm completion, training-service pulls checkpoint+logs, pushes to MinIO,
    logs final metrics to MLflow, sets Job status=FINISHED
  → frontend shows the run in Experiments with metrics, and the checkpoint appears in Models
    (as a candidate version, pending manual promotion to "production")
```

## What "general" actually means here

The suggestion doc this project is based on lists a `Feature Store` and `Kafka streaming` as future phases.
Feature Store remains deliberately deferred (see `docs/ROADMAP.md`) — it adds real infrastructure surface area
without being needed to prove the plugin-based, Slurm-backed platform story. Kafka streaming was built (see
section 7) once the core platform was solid enough that a streaming demo actually meant something rather than
being infrastructure for infrastructure's sake.
