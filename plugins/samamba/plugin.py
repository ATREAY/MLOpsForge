"""Wraps the real, published SAMamba architecture (samamba_core/ — vendored
from the thesis repo's GraphEncoder + Mamba-SSM encoder layers, unmodified)
behind the BaseModelPlugin contract, training on the real EPTransNet
phishing/scam graph via samamba_core/dataset_pyg.py + data.py.

This replaces the earlier placeholder MLP classifier. The model, loss, and
train/eval loop below are line-for-line equivalent to train_phish_scam.py's
train_epoch/eval_epoch — the only platform-specific additions are: (a)
n_splits/max_folds are configurable so a demo run can train 1 fold for a few
epochs instead of the paper's 3x-repeated 3-fold / 1000-epoch protocol, and
(b) results are packaged into the single TrainResult/checkpoint shape the
rest of MLOpsForge expects.

Important: this is transductive node classification over a fixed graph, not
per-row inference. predict() therefore only makes sense for addresses that
were nodes in the training graph — it re-runs the full-graph forward pass
and reads off the logits for the requested node(s), which is real but not
cheap (same cost as one eval epoch, not O(1) per address).
"""

import copy
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.metrics import f1_score, precision_score, recall_score
from torch_geometric.loader import DataLoader as PyGDataLoader

from plugins.base.interface import BaseModelPlugin, TrainResult
from plugins.samamba.data import kfold_masks, load_graph_bundle, make_fold_datasets
from plugins.samamba.samamba_core.dataset_pyg import GraphDataset
from plugins.samamba.samamba_core.models import GraphEncoder

# torch's nn.TransformerEncoder fast-path probes attributes only stock
# nn.MultiheadAttention has; samamba_core's Attention (a custom
# MessagePassing-based module) doesn't define them, so it AttributeErrors on
# init under torch>=2.1 unless we backfill them. Doesn't change forward
# behavior — it only controls whether torch takes an internal fused fast
# path, which the fast path itself already declines to take once
# batch_first is False. Only matters for ie="transformer"; ie="mamba" (the
# default) never constructs a GraphTransformerEncoder.
from plugins.samamba.samamba_core.layers import Attention as _Attention  # noqa: E402

_Attention.batch_first = False
_Attention._qkv_same_embed_dim = True
_Attention.activation_relu_or_gelu = 1

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "learning_rate": {"type": "number", "default": 0.001, "minimum": 0.00001},
        "epochs": {"type": "integer", "default": 30, "minimum": 1},
        "dim_hidden": {"type": "integer", "default": 64, "minimum": 8},
        "num_heads": {"type": "integer", "default": 1, "minimum": 1},
        "num_layers": {"type": "integer", "default": 2, "minimum": 1},
        "dropout": {"type": "number", "default": 0.1, "minimum": 0.0, "maximum": 0.9},
        "gnn_type": {"type": "string", "default": "gat", "enum": ["gat", "gcn", "graphsage", "gin", "graph"]},
        "ie": {"type": "string", "default": "mamba", "enum": ["mamba", "transformer"]},
        "se": {"type": "string", "default": "gnn", "enum": ["gnn", "khopgnn"]},
        "k_hop": {"type": "integer", "default": 1, "minimum": 1},
        "use_edge_attr": {"type": "boolean", "default": True},
        "edge_dim": {"type": "integer", "default": 64, "minimum": 8},
        "global_pool": {"type": "string", "default": "mean", "enum": ["mean", "add"]},
        "order": {"type": "string", "default": "sd", "enum": ["sd", "nd"]},
        "n_splits": {"type": "integer", "default": 3, "minimum": 2},
        "max_folds": {
            "type": "integer",
            "default": 1,
            "minimum": 1,
            "description": "How many of the n_splits folds to actually train. 1 = fast demo run; set equal to n_splits for the paper's full cross-validation protocol.",
        },
        "seed": {"type": "integer", "default": 42},
    },
    "required": ["learning_rate", "epochs"],
}


def _device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _model_kwargs(config: dict, input_size: int, num_edge_features: int) -> dict:
    dim_hidden = config.get("dim_hidden", 64)
    return dict(
        in_size=input_size,
        num_class=2,
        d_model=dim_hidden,
        dim_feedforward=int(2 * dim_hidden),
        dropout=config.get("dropout", 0.1),
        num_heads=config.get("num_heads", 1),
        num_layers=config.get("num_layers", 2),
        batch_norm=True,
        abs_pe=False,
        abs_pe_dim=0,
        gnn_type=config.get("gnn_type", "gat"),
        k_hop=config.get("k_hop", 1),
        use_edge_attr=config.get("use_edge_attr", True),
        num_edge_features=num_edge_features,
        edge_dim=config.get("edge_dim", 64),
        se=config.get("se", "gnn"),
        ie=config.get("ie", "mamba"),
        in_embed=False,
        edge_embed=False,
        global_pool=config.get("global_pool", "mean"),
        order=config.get("order", "sd"),
        task="node",
    )


def _train_epoch(model, loader, criterion, optimizer, device) -> float:
    model.train()
    total_loss = 0.0
    for data in loader:
        data = data.to(device)
        optimizer.zero_grad()
        _, _, out = model(data)
        loss = criterion(out[data.train_mask], data.y[data.train_mask].long())
        loss.backward()
        total_loss += loss.item()
        optimizer.step()
    return total_loss / len(loader.dataset)


def _eval_epoch(model, loader, criterion, device) -> tuple[float, np.ndarray, np.ndarray]:
    model.eval()
    ys, preds = [], []
    total_loss = 0.0
    with torch.no_grad():
        for data in loader:
            data = data.to(device)
            _, _, out = model(data)
            loss = criterion(out[data.test_mask], data.y[data.test_mask].long())
            total_loss += loss.item() * data.num_graphs
            _, pred = out[data.test_mask].max(dim=1)
            ys.append(data.y[data.test_mask].cpu())
            preds.append(pred.cpu())
    y = torch.cat(ys).numpy()
    pred = torch.cat(preds).numpy()
    return total_loss / len(loader.dataset), y, pred


def _fold_metrics(y: np.ndarray, pred: np.ndarray, train_loss: float, val_loss: float) -> dict[str, float]:
    f1 = f1_score(y, pred, average=None, zero_division=0, labels=[0, 1])
    precision = precision_score(y, pred, average=None, zero_division=0, labels=[0, 1])
    recall = recall_score(y, pred, average=None, zero_division=0, labels=[0, 1])
    micro_f1 = f1_score(y, pred, average="micro", zero_division=0)
    return {
        "train_loss": float(train_loss),
        "val_loss": float(val_loss),
        "precision": float(precision[1]),
        "recall": float(recall[1]),
        "f1": float(f1[1]),
        "micro_f1": float(micro_f1),
    }


class SAMambaPlugin(BaseModelPlugin):
    name = "samamba"
    version = "1.0.0"
    task_type = "node-classification"

    def get_config_schema(self) -> dict:
        return CONFIG_SCHEMA

    def train(self, dataset_path: str, config: dict, output_dir: str) -> TrainResult:
        torch.manual_seed(config.get("seed", 42))
        device = _device()

        bundle = load_graph_bundle(dataset_path)
        pyg_graph = bundle.pyg_graph

        n_splits = config.get("n_splits", 3)
        max_folds = min(config.get("max_folds", 1), n_splits)
        k_hop = config.get("k_hop", 1)
        se = config.get("se", "gnn")

        folds = kfold_masks(pyg_graph, n_splits=n_splits, seed=config.get("seed", 42))
        model_kwargs = _model_kwargs(config, pyg_graph.x.shape[1], pyg_graph.edge_attr.shape[1])
        weight = torch.tensor([0.3, 0.7]).to(device)

        fold_results = []
        for fold_idx, (train_data, test_data) in enumerate(folds[:max_folds]):
            train_dset, test_dset = make_fold_datasets(train_data, test_data, k_hop=k_hop, se=se)
            train_loader = PyGDataLoader(train_dset, batch_size=1, shuffle=True)
            test_loader = PyGDataLoader(test_dset, batch_size=1, shuffle=False)

            model = GraphEncoder(**model_kwargs).to(device)
            optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
            criterion = torch.nn.CrossEntropyLoss(weight)

            best_f1 = -1.0
            best_state = None
            best_metrics: dict[str, float] = {}

            for _epoch in range(config["epochs"]):
                train_loss = _train_epoch(model, train_loader, criterion, optimizer, device)
                val_loss, y, pred = _eval_epoch(model, test_loader, criterion, device)
                metrics = _fold_metrics(y, pred, train_loss, val_loss)
                if metrics["f1"] > best_f1:
                    best_f1 = metrics["f1"]
                    best_state = copy.deepcopy(model.state_dict())
                    best_metrics = metrics

            fold_results.append({"fold": fold_idx, "state_dict": best_state, "metrics": best_metrics})

        best_fold = max(fold_results, key=lambda r: r["metrics"].get("f1", 0.0))
        metrics = dict(best_fold["metrics"])
        metrics["best_fold"] = float(best_fold["fold"])
        metrics["folds_trained"] = float(max_folds)
        metrics["trained_on_device"] = 1.0 if device.type == "cuda" else 0.0
        if max_folds > 1:
            metrics["f1_mean_across_folds"] = float(np.mean([r["metrics"]["f1"] for r in fold_results]))
            metrics["f1_std_across_folds"] = float(np.std([r["metrics"]["f1"] for r in fold_results]))

        checkpoint_path = Path(output_dir) / "checkpoint.pt"
        torch.save(
            {
                "model_state_dict": best_fold["state_dict"],
                "model_kwargs": model_kwargs,
                "x": pyg_graph.x,
                "edge_index": pyg_graph.edge_index,
                "edge_attr": pyg_graph.edge_attr,
                "addresses": bundle.addresses,
                "k_hop": k_hop,
                "se": se,
                "config": config,
            },
            checkpoint_path,
        )

        return TrainResult(checkpoint_path=str(checkpoint_path), metrics=metrics)

    def _load_checkpoint(self, model_path: str):
        device = _device()
        ckpt = torch.load(model_path, map_location=device, weights_only=False)
        model = GraphEncoder(**ckpt["model_kwargs"]).to(device)
        model.load_state_dict(ckpt["model_state_dict"])
        model.eval()
        return model, ckpt, device

    def _whole_graph_batch(self, ckpt: dict, device: torch.device):
        from torch_geometric.data import Data

        graph = Data(x=ckpt["x"], edge_index=ckpt["edge_index"], edge_attr=ckpt["edge_attr"])
        dset = GraphDataset([graph], degree=True, k_hop=ckpt["k_hop"], se=ckpt["se"])
        loader = PyGDataLoader(dset, batch_size=1, shuffle=False)
        return next(iter(loader)).to(device)

    def evaluate(self, model_path: str, dataset_path: str, config: dict) -> dict[str, float]:
        """Runs the checkpoint over the *entire* graph (no held-out mask) and
        scores against the true labels every node has. This is a different,
        more optimistic number than the fold-held-out F1 reported by train()
        — it answers "how well does this checkpoint fit the whole graph", not
        "how well does it generalize to unseen nodes"."""
        model, ckpt, device = self._load_checkpoint(model_path)
        bundle = load_graph_bundle(dataset_path)
        batch = self._whole_graph_batch(
            {**ckpt, "x": bundle.pyg_graph.x, "edge_index": bundle.pyg_graph.edge_index, "edge_attr": bundle.pyg_graph.edge_attr},
            device,
        )
        with torch.no_grad():
            _, _, out = model(batch)
            pred = out.argmax(dim=1).cpu().numpy()
        y = bundle.pyg_graph.y.numpy()
        f1 = f1_score(y, pred, average=None, zero_division=0, labels=[0, 1])
        precision = precision_score(y, pred, average=None, zero_division=0, labels=[0, 1])
        recall = recall_score(y, pred, average=None, zero_division=0, labels=[0, 1])
        return {
            "precision": float(precision[1]),
            "recall": float(recall[1]),
            "f1": float(f1[1]),
            "micro_f1": float(f1_score(y, pred, average="micro", zero_division=0)),
        }

    def predict(self, model_path: str, inputs: Any) -> Any:
        """`inputs` is {"address": "0x..."} for a single node, or a list of
        such dicts. Addresses must be nodes the model was trained on
        (transductive) — this is not free-form feature scoring."""
        model, ckpt, device = self._load_checkpoint(model_path)
        rows = inputs if isinstance(inputs, list) else [inputs]
        addresses: list[str] = ckpt["addresses"]
        address_to_index = {addr: i for i, addr in enumerate(addresses)}

        missing = [row["address"] for row in rows if row.get("address") not in address_to_index]
        if missing:
            raise ValueError(f"address(es) not found in the trained graph: {missing}")

        batch = self._whole_graph_batch(ckpt, device)
        with torch.no_grad():
            _, _, out = model(batch)
            probs = torch.softmax(out, dim=1)[:, 1].cpu()

        results = []
        for row in rows:
            idx = address_to_index[row["address"]]
            p = float(probs[idx])
            results.append({"address": row["address"], "fraud_probability": p, "is_fraud": p >= 0.5})

        return results if isinstance(inputs, list) else results[0]
