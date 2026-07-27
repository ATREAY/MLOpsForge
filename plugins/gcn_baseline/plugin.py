from pathlib import Path
from typing import Any

import torch
from sklearn.metrics import accuracy_score, f1_score

from plugins.base.interface import BaseModelPlugin, TrainResult
from plugins.gcn_baseline.data import load_graph_dataset
from plugins.gcn_baseline.model import GCN

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "learning_rate": {"type": "number", "default": 0.01, "minimum": 0.00001},
        "epochs": {"type": "integer", "default": 100, "minimum": 1},
        "hidden_dim": {"type": "integer", "default": 16, "minimum": 4},
        "weight_decay": {"type": "number", "default": 0.0005},
        "seed": {"type": "integer", "default": 42},
    },
    "required": ["learning_rate", "epochs"],
}


class GCNBaselinePlugin(BaseModelPlugin):
    name = "gcn_baseline"
    version = "0.1.0"
    task_type = "node-classification"

    def get_config_schema(self) -> dict:
        return CONFIG_SCHEMA

    def train(self, dataset_path: str, config: dict, output_dir: str) -> TrainResult:
        torch.manual_seed(config.get("seed", 42))
        graph = load_graph_dataset(dataset_path)
        num_classes = int(graph.labels.max().item()) + 1

        model = GCN(
            input_dim=graph.features.shape[1], hidden_dim=config.get("hidden_dim", 16), num_classes=num_classes
        )
        optimizer = torch.optim.Adam(
            model.parameters(), lr=config["learning_rate"], weight_decay=config.get("weight_decay", 5e-4)
        )
        loss_fn = torch.nn.CrossEntropyLoss()

        model.train()
        for _epoch in range(config["epochs"]):
            optimizer.zero_grad()
            logits = model(graph.features, graph.a_norm)
            loss = loss_fn(logits[graph.train_mask], graph.labels[graph.train_mask])
            loss.backward()
            optimizer.step()

        model.eval()
        with torch.no_grad():
            val_preds = model(graph.features, graph.a_norm)[graph.val_mask].argmax(dim=1)
        val_labels = graph.labels[graph.val_mask]
        metrics = {
            "accuracy": float(accuracy_score(val_labels, val_preds)),
            "f1_macro": float(f1_score(val_labels, val_preds, average="macro", zero_division=0)),
        }

        checkpoint_path = Path(output_dir) / "checkpoint.pt"
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "input_dim": graph.features.shape[1],
                "hidden_dim": config.get("hidden_dim", 16),
                "num_classes": num_classes,
            },
            checkpoint_path,
        )
        return TrainResult(checkpoint_path=str(checkpoint_path), metrics=metrics)

    def _load_checkpoint(self, model_path: str) -> GCN:
        ckpt = torch.load(model_path, map_location="cpu", weights_only=False)
        model = GCN(input_dim=ckpt["input_dim"], hidden_dim=ckpt["hidden_dim"], num_classes=ckpt["num_classes"])
        model.load_state_dict(ckpt["model_state_dict"])
        model.eval()
        return model

    def evaluate(self, model_path: str, dataset_path: str, config: dict) -> dict[str, float]:
        model = self._load_checkpoint(model_path)
        graph = load_graph_dataset(dataset_path)
        with torch.no_grad():
            preds = model(graph.features, graph.a_norm)[graph.val_mask].argmax(dim=1)
        labels = graph.labels[graph.val_mask]
        return {
            "accuracy": float(accuracy_score(labels, preds)),
            "f1_macro": float(f1_score(labels, preds, average="macro", zero_division=0)),
        }

    def predict(self, model_path: str, inputs: Any) -> Any:
        """`inputs` is {"dataset_path": ..., "node_indices": [...]}, since a GCN's
        prediction for a node is only meaningful in the context of its graph."""
        model = self._load_checkpoint(model_path)
        graph = load_graph_dataset(inputs["dataset_path"])
        with torch.no_grad():
            logits = model(graph.features, graph.a_norm)
            probs = torch.softmax(logits, dim=1)

        node_indices = inputs.get("node_indices", list(range(graph.features.shape[0])))
        return [
            {"node_index": i, "predicted_class": int(probs[i].argmax()), "probabilities": probs[i].tolist()}
            for i in node_indices
        ]
