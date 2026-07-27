# SAMamba plugin — Ethereum fraud detection

## Status: placeholder model body

`model.py`'s `PlaceholderSAMambaClassifier` is a plain MLP, not the real SAMamba architecture. Everything
around it — data loading (`data.py`), the train/evaluate/predict lifecycle (`plugin.py`), checkpoint format,
and config schema (`plugin.yaml`) — is real and wired into the platform end to end. Swapping in the actual
SAMamba architecture means changing `model.py` only; see the `TODO(real SAMamba)` markers in `model.py` and
`requirements.txt`.

## Expected dataset format

A CSV with one row per Ethereum address: numeric behavioral features (transaction counts, average value
sent/received, time between first/last transaction, etc.) plus a binary label column (default `FLAG`,
override via `config["label_column"]`). Identifier-like columns (address, hash, index) are dropped
automatically. This matches the shape of the public Ethereum Fraud Detection datasets used in the fraud
detection literature this plugin targets.

## Config

See `plugin.yaml` → `config_schema`: `learning_rate`, `epochs`, `batch_size`, `hidden_dim`, `seed`.

## Running it standalone (outside the platform, for local iteration)

```python
from plugins.samamba.plugin import SAMambaPlugin

plugin = SAMambaPlugin()
result = plugin.train(
    dataset_path="path/to/ethereum_transactions.csv",
    config={"learning_rate": 1e-3, "epochs": 20, "batch_size": 64, "hidden_dim": 64},
    output_dir="/tmp/samamba_run",
)
print(result.metrics)
```
