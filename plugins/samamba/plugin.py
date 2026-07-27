from pathlib import Path
from typing import Any

import torch
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from torch.utils.data import DataLoader, TensorDataset

from plugins.base.interface import BaseModelPlugin, TrainResult
from plugins.samamba.data import load_all, load_dataset
from plugins.samamba.model import PlaceholderSAMambaClassifier

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "learning_rate": {"type": "number", "default": 0.001, "minimum": 0.00001},
        "epochs": {"type": "integer", "default": 20, "minimum": 1},
        "batch_size": {"type": "integer", "default": 64, "minimum": 1},
        "hidden_dim": {"type": "integer", "default": 64, "minimum": 8},
        "seed": {"type": "integer", "default": 42},
    },
    "required": ["learning_rate", "epochs", "batch_size"],
}


def _binary_metrics(y_true, y_pred) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
    }


class SAMambaPlugin(BaseModelPlugin):
    name = "samamba"
    version = "0.1.0"
    task_type = "graph-classification"

    def get_config_schema(self) -> dict:
        return CONFIG_SCHEMA

    def train(self, dataset_path: str, config: dict, output_dir: str) -> TrainResult:
        torch.manual_seed(config.get("seed", 42))

        data, scaler = load_dataset(dataset_path, config)
        model = PlaceholderSAMambaClassifier(
            input_dim=len(data.feature_names), hidden_dim=config.get("hidden_dim", 64)
        )
        optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
        loss_fn = torch.nn.BCEWithLogitsLoss()

        train_loader = DataLoader(
            TensorDataset(data.X_train, data.y_train), batch_size=config["batch_size"], shuffle=True
        )

        model.train()
        for _epoch in range(config["epochs"]):
            for xb, yb in train_loader:
                optimizer.zero_grad()
                loss = loss_fn(model(xb), yb)
                loss.backward()
                optimizer.step()

        model.eval()
        with torch.no_grad():
            val_probs = torch.sigmoid(model(data.X_val))
            val_preds = (val_probs >= 0.5).float()
        metrics = _binary_metrics(data.y_val.numpy(), val_preds.numpy())

        checkpoint_path = Path(output_dir) / "checkpoint.pt"
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "input_dim": len(data.feature_names),
                "hidden_dim": config.get("hidden_dim", 64),
                "feature_names": data.feature_names,
                "scaler": scaler,
                "config": config,
            },
            checkpoint_path,
        )

        return TrainResult(checkpoint_path=str(checkpoint_path), metrics=metrics)

    def _load_checkpoint(self, model_path: str) -> tuple[PlaceholderSAMambaClassifier, dict]:
        ckpt = torch.load(model_path, map_location="cpu", weights_only=False)
        model = PlaceholderSAMambaClassifier(input_dim=ckpt["input_dim"], hidden_dim=ckpt["hidden_dim"])
        model.load_state_dict(ckpt["model_state_dict"])
        model.eval()
        return model, ckpt

    def evaluate(self, model_path: str, dataset_path: str, config: dict) -> dict[str, float]:
        model, ckpt = self._load_checkpoint(model_path)
        X, y = load_all(dataset_path, config, ckpt["scaler"], ckpt["feature_names"])
        with torch.no_grad():
            preds = (torch.sigmoid(model(X)) >= 0.5).float()
        return _binary_metrics(y.numpy(), preds.numpy())

    def predict(self, model_path: str, inputs: Any) -> Any:
        """`inputs` is a dict of {feature_name: value} for a single address, or a
        list of such dicts for a batch."""
        model, ckpt = self._load_checkpoint(model_path)
        rows = inputs if isinstance(inputs, list) else [inputs]
        feature_names = ckpt["feature_names"]

        missing = [f for row in rows for f in feature_names if f not in row]
        if missing:
            raise ValueError(f"prediction input missing required feature(s): {sorted(set(missing))}")

        X = torch.tensor([[float(row[f]) for f in feature_names] for row in rows], dtype=torch.float32)
        X = torch.tensor(ckpt["scaler"].transform(X.numpy()), dtype=torch.float32)

        with torch.no_grad():
            probs = torch.sigmoid(model(X)).tolist()

        results = [{"fraud_probability": p, "is_fraud": p >= 0.5} for p in probs]
        return results if isinstance(inputs, list) else results[0]
