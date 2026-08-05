# inference-service

Serves predictions from a registered model. The one service outside a Slurm job that actually imports and
runs plugin code — see the module docstring in `app/main.py` and [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
for why that's kept separate from the backend.

## API

`POST /predict`
```json
{
  "plugin_entrypoint": "plugins.samamba.plugin:SAMambaPlugin",
  "model_path": "/absolute/path/to/checkpoint.pt",
  "inputs": { "avg_val_sent": 3.5, "avg_val_received": 0.8, "total_transactions": 35 }
}
```
`inputs` is passed straight through to the plugin's `predict()` — its shape is plugin-specific (see each
plugin's docstring; `samamba` takes a flat feature dict, `gcn_baseline` takes `{"dataset_path": ..., "node_indices": [...]}`
since a node's prediction only makes sense in the context of its graph).

The backend never calls this directly with a model_path/entrypoint from the outside world — `POST
/api/v1/inference/predict/{model_version_id}` on the backend looks those up from the model registry first, so
callers only ever need a model version id, not internal file paths.

## Status

v1: reloads the checkpoint from disk on every request — correct, not optimized. No caching yet; the natural
place to add it is here (keyed by `(plugin_entrypoint, model_path)`) if serving latency ever matters, before
reaching for something heavier like Triton (the Phase 3 plan).

**Known gap (Docker only):** `model_path` today is a path on the Slurm cluster's filesystem — training-service
never uploads checkpoints anywhere else. That's transparent when everything runs on one machine (how this was
built and verified — this service, the backend, and the Slurm cluster all see the same filesystem), but a
Dockerized `inference-service` on a different host won't be able to read that path. Fix, when it matters:
either share the checkpoint directory as a volume, or have training-service push checkpoints to MinIO (it
already does this pattern for datasets — see `dataset_resolver.py`) and have this service pull from there
instead of trusting a bare local path.

## Running locally

```bash
pip install -e .
uvicorn app.main:app --reload --port 8200
```
