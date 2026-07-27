# training-service

Submits, polls, and reconciles training jobs on the Slurm compute plane over SSH. See
[`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md#2-training-service--slurm-orchestration) for the full design.

## How it works

- `POST /submit` — renders `slurm_templates/train_job.sh.j2`, SFTPs it (plus a resolved config.json and, if the
  dataset lives in MinIO, the dataset file itself) to the Slurm cluster, runs `sbatch`, and returns the Slurm
  job id.
- A background thread (`app/poller.py`) polls every tracked job's state via `squeue`/`sacct` on an interval and
  PATCHes the backend's `/jobs/{id}/status` whenever the state changes.
- On completion, it reads `result.json` (written by `plugins/base/run_train.py` on the Slurm side) back over
  SFTP to get the checkpoint path and reports it to the backend.
- `POST /cancel/{slurm_job_id}` — runs `scancel`.

Job tracking state lives in a flat JSON file (`app/state_store.py`), not a database — the system of record for
job history is the backend's Postgres; this service only needs to remember what to keep polling.

## Verified against a real cluster

This was tested against the actual Slurm cluster it was built for (IIT-H CSE, `cse-gpu-all` partition):
a dedicated SSH keypair submitted a real `sbatch` job running the `gcn_baseline` plugin end to end —
`QUEUED -> RUNNING -> FINISHED`, checkpoint + metrics recovered, backend callback fired correctly. See
git history for the throwaway smoke test script (removed after verification; not part of the service).

## Configuration

Copy `.env.example` to `.env` and fill in:

- `SLURM_SSH_HOST` / `SLURM_SSH_USER` / `SLURM_SSH_KEY_PATH` — a **dedicated** keypair for this service, added
  to `~/.ssh/authorized_keys` on the Slurm cluster. Don't reuse a personal key.
- `SLURM_REPO_PATH` — where this repo is checked out on the Slurm cluster's filesystem (needs `plugins/` and a
  Python environment with each plugin's dependencies installed).
- `SLURM_PYTHON_BIN` — the interpreter on the Slurm side to run `python -m plugins.base.run_train` with.

## Running locally

```bash
pip install -e .
cp .env.example .env  # edit it
uvicorn app.main:app --reload --port 8100
```
