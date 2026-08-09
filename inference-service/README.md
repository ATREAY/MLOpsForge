# inference-service

Serves predictions from a registered model. The one service outside a Slurm job that actually imports and
runs plugin code — see the module docstring in `app/main.py` and [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)
for why that's kept separate from the backend.

## API

`POST /predict`
```json
{
  "plugin_entrypoint": "plugins.gcn_baseline.plugin:GCNBaselinePlugin",
  "model_path": "/absolute/path/to/checkpoint.pt",
  "inputs": { "dataset_path": "...", "node_indices": [12, 47] }
}
```
`inputs` is passed straight through to the plugin's `predict()` — its shape is plugin-specific (see each
plugin's docstring; `samamba` takes `{"address": "0x..."}` or a list of these — transductive over the graph
it was trained on, see the known gap below — `gcn_baseline` takes `{"dataset_path": ..., "node_indices": [...]}`,
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

**Known gap: the real `samamba` plugin cannot serve here.** Unlike training-service (which gained a
per-plugin `python_bin` override — see `plugins/samamba/plugin.yaml` — specifically so the real SAMamba's
`mamba-ssm`/`causal-conv1d`/`torch_geometric` deps don't have to live in the shared venv every other plugin's
Slurm job uses), this service imports plugin code **in-process** rather than subprocess-exec'ing a
plugin-specific interpreter. Confirmed live: `POST /inference/predict/{model_version_id}` for a real
`samamba` checkpoint 502s with `ModuleNotFoundError: No module named 'torch_geometric'`. Installing
`torch_geometric` here wouldn't fully fix it either — `mamba-ssm`'s CUDA kernels error on CPU
(`mamba_inner_fn` requires a CUDA tensor), and this service is architecturally part of the non-GPU control
plane (see `docs/ARCHITECTURE.md`'s compute/control plane split). Serving real Mamba-based predictions would
need either a GPU-backed inference deployment or a subprocess-per-plugin-interpreter redesign mirroring
training-service's — neither built here; `plugin.predict()` itself is verified correct directly (see
`plugins/samamba/README.md`), just not reachable through this service today. `gcn_baseline` and `mnist_cnn`
are unaffected — their deps already live in the shared venv.

## Running locally

```bash
pip install -e .
uvicorn app.main:app --reload --port 8200
```
