# Plugins

A plugin is the only way a model gets trained, evaluated, or served on MLOpsForge. The backend and
`training-service` never import model-specific code — they only ever see the contract defined in
[`base/interface.py`](base/interface.py).

## Adding a new model

1. Create `plugins/<your_model>/`.
2. Implement `BaseModelPlugin` in `plugin.py` (see `samamba/plugin.py` for the reference implementation).
3. Write `plugin.yaml` declaring the plugin's identity, config schema, and default Slurm resources.
4. List any extra Python deps in `requirements.txt` — these get installed into the Slurm job's environment,
   never into the control plane.
5. Call `POST /api/v1/plugins/sync` (or restart the backend) to pick it up.

That's the entire integration surface. Nothing in `backend/` or `training-service/` changes.

## The contract

```python
class BaseModelPlugin(ABC):
    def get_config_schema(self) -> dict: ...
    def train(self, dataset_path: str, config: dict, output_dir: str) -> TrainResult: ...
    def evaluate(self, model_path: str, dataset_path: str, config: dict) -> dict[str, float]: ...
    def predict(self, model_path: str, inputs: Any) -> Any: ...
```

`run_train.py` is the actual CLI entrypoint the Slurm job script invokes — it loads a plugin by its
`module.path:ClassName` entrypoint string, calls `train()`, and writes `result.json` (checkpoint path +
metrics) to `output_dir` so `training-service` knows what happened without parsing stdout.

## Plugins in this repo

| Plugin | Task type | Purpose |
|---|---|---|
| `samamba/` | `graph-classification` | Ethereum fraud detection — the platform's flagship workload. Model body is currently a placeholder (see its README) pending the real SAMamba architecture. |
| `gcn_baseline/` | `node-classification` | Deliberately unrelated to SAMamba — exists solely to prove the plugin interface is model-agnostic, not shaped around one paper. |
| `mnist_cnn/` | `image-classification` | A third, maximally-different plugin (image data, CNN, deliberately CPU-only resource declaration) — proves the interface generalizes across data modalities, not just model architectures. |
