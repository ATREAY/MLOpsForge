# SAMamba plugin — Ethereum phishing/scam detection

## Status: the real, published architecture

`samamba_core/` is vendored, unmodified, from the thesis repo's `samamba/` package — the same
`GraphEncoder`, GAT-based structure extractor, and Mamba-SSM (`mamba_ssm.Mamba`, real CUDA kernels) long-range
encoder layers used to produce the paper's results, not a placeholder MLP. `samamba_core/dataset_pyg.py` is
the published `datasets_phish_scam/phish_scam_dataset_pyg.py` transform (`multidigraph_to_pyg`, k-fold
`dataset_split`, `GraphDataset`), also unmodified.

What's platform-specific is everything around the vendored core: `data.py` (loads the single-file graph
bundle, builds configurable k-fold masks), `plugin.py` (wires the real train/eval loop — line-for-line
equivalent to `train_phish_scam.py`'s `train_epoch`/`eval_epoch` — into the `BaseModelPlugin` contract), and
`plugin.yaml` (config schema + its own conda env, since `mamba-ssm`/`causal-conv1d` ship compiled CUDA kernels
that don't belong in the shared training-service venv).

## Dataset: EPTransNet

30,000 Ethereum addresses, ~1.27M transaction edges, 352 labeled phishing/scam addresses (a directed graph
for node features — in/out-degree, transaction amounts, timestamps — and an undirected graph for edges and
labels, matching the published preprocessing exactly). Prepared into a single registrable file via:

```bash
~/.conda/envs/samamba/bin/python scripts/prepare_samamba_dataset.py \
    --directed-graph ~/Thesis/SAMamba/datasets_phish_scam/directed-30000.pkl \
    --undirected-graph ~/Thesis/SAMamba/datasets_phish_scam/undirected-30000.pkl \
    --output datasets_registry/samamba_eptransnet_graph.pt
```

Register it the normal way (`scripts/register_dataset.py --storage-mode local --file
datasets_registry/samamba_eptransnet_graph.pt --task-type node-classification`).

## This is transductive node classification, not per-row scoring

The whole graph is one training example — node features are fixed, and what changes per fold is which
30k node indices are masked `train` vs `test`. There's no notion of an "unseen" address with its own feature
row the way the old placeholder (or a typical tabular fraud model) worked. Consequences:

- `train()` trains `max_folds` of the `n_splits` k-fold splits (defaults: 1 fold, 30 epochs — a real but scaled-
  down run; set `max_folds: n_splits` and `epochs: 1000` to reproduce the paper's full 3×-repeated 3-fold
  protocol, at real compute cost).
- `evaluate()` scores the checkpoint against the *entire* graph's true labels (no mask) — a different,
  more optimistic number than the held-out fold F1 `train()` reports.
- `predict()` takes `{"address": "0x..."}` (or a list of these) and only works for addresses that were nodes
  in the training graph — it reruns the full-graph forward pass and reads off the logits for the requested
  node(s). Not O(1) per address; same cost as one eval epoch.

`train()`/`evaluate()`/`predict()` are all verified directly against real checkpoints: `train()` through a
real Slurm job on an A100 (`ie: mamba`, real CUDA kernels); `evaluate()`/`predict()` both via a CPU smoke
test (`transformer` variant, for cheap iteration) and, separately, a real standalone GPU job that reloaded
that same trained `ie=mamba` checkpoint and ran a real forward pass (correct `(30000, 2)` output shape,
<1s once past cold-start imports). But **`inference-service` cannot currently serve this plugin** (its
shared venv lacks `torch_geometric`, and `mamba-ssm`'s kernels need CUDA even at inference time, which that
non-GPU service doesn't have). See `inference-service/README.md`'s "Known gap" section. Call `predict()`
directly, as below, until that's addressed.

## Config

See `plugin.yaml` → `config_schema` for the full list. Highlights: `ie` (`mamba` — the real SSM encoder — or
`transformer`, the paper's structure-aware-transformer ablation), `gnn_type` (structure extractor, default
`gat`), `se` (`gnn` subtree extractor by default; `khopgnn` does real per-node k-hop subgraph extraction and
is much slower at this graph size), `max_folds`/`n_splits`/`epochs` (scaled-down vs. full protocol).

## Running it standalone (outside the platform, for local iteration)

Must use the `samamba` conda env (`torch_geometric`, `mamba_ssm`, `causal_conv1d` are not in the platform's
shared venv):

```python
from plugins.samamba.plugin import SAMambaPlugin

plugin = SAMambaPlugin()
result = plugin.train(
    dataset_path="datasets_registry/samamba_eptransnet_graph.pt",
    config={"learning_rate": 1e-3, "epochs": 5, "max_folds": 1, "n_splits": 3},
    output_dir="/tmp/samamba_run",
)
print(result.metrics)
```
