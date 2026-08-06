from pathlib import Path
from typing import Any

import numpy as np
import torch
from sklearn.metrics import accuracy_score, f1_score
from torch.utils.data import DataLoader, TensorDataset

from plugins.base.interface import BaseModelPlugin, TrainResult
from plugins.mnist_cnn.data import load_dataset
from plugins.mnist_cnn.model import SimpleCNN

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "learning_rate": {"type": "number", "default": 0.001, "minimum": 0.00001},
        "epochs": {"type": "integer", "default": 3, "minimum": 1},
        "batch_size": {"type": "integer", "default": 128, "minimum": 1},
        "max_train_samples": {"type": "integer", "default": 10000, "minimum": 100},
        "seed": {"type": "integer", "default": 42},
    },
    "required": ["learning_rate", "epochs", "batch_size"],
}


def _device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


class MNISTCNNPlugin(BaseModelPlugin):
    name = "mnist_cnn"
    version = "0.1.0"
    task_type = "image-classification"

    def get_config_schema(self) -> dict:
        return CONFIG_SCHEMA

    def train(self, dataset_path: str, config: dict, output_dir: str) -> TrainResult:
        torch.manual_seed(config.get("seed", 42))
        device = _device()

        data = load_dataset(dataset_path, config)
        model = SimpleCNN(num_classes=10).to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=config["learning_rate"])
        loss_fn = torch.nn.CrossEntropyLoss()

        train_loader = DataLoader(
            TensorDataset(data.train_images.to(device), data.train_labels.to(device)),
            batch_size=config["batch_size"],
            shuffle=True,
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
            test_preds = model(data.test_images.to(device)).argmax(dim=1).cpu()
        metrics = {
            "accuracy": float(accuracy_score(data.test_labels, test_preds)),
            "f1_macro": float(f1_score(data.test_labels, test_preds, average="macro")),
            "trained_on_device": 1.0 if device.type == "cuda" else 0.0,
        }

        checkpoint_path = Path(output_dir) / "checkpoint.pt"
        torch.save({"model_state_dict": model.state_dict(), "num_classes": 10}, checkpoint_path)
        return TrainResult(checkpoint_path=str(checkpoint_path), metrics=metrics)

    def _load_checkpoint(self, model_path: str) -> tuple[SimpleCNN, torch.device]:
        device = _device()
        ckpt = torch.load(model_path, map_location=device, weights_only=False)
        model = SimpleCNN(num_classes=ckpt["num_classes"]).to(device)
        model.load_state_dict(ckpt["model_state_dict"])
        model.eval()
        return model, device

    def evaluate(self, model_path: str, dataset_path: str, config: dict) -> dict[str, float]:
        model, device = self._load_checkpoint(model_path)
        data = load_dataset(dataset_path, config)
        with torch.no_grad():
            preds = model(data.test_images.to(device)).argmax(dim=1).cpu()
        return {
            "accuracy": float(accuracy_score(data.test_labels, preds)),
            "f1_macro": float(f1_score(data.test_labels, preds, average="macro")),
        }

    def predict(self, model_path: str, inputs: Any) -> Any:
        """`inputs` is {"pixels": [[28 floats]*28] or [784 floats]} (0-255 range)
        for a single image, or a list of such dicts for a batch."""
        model, device = self._load_checkpoint(model_path)
        rows = inputs if isinstance(inputs, list) else [inputs]

        arrays = []
        for row in rows:
            pixels = np.array(row["pixels"], dtype=np.float32).reshape(28, 28) / 255.0
            arrays.append(pixels)
        batch = torch.tensor(np.stack(arrays)[:, None, :, :]).to(device)

        with torch.no_grad():
            probs = torch.softmax(model(batch), dim=1).cpu()

        results = [
            {"predicted_digit": int(p.argmax()), "probabilities": p.tolist()} for p in probs
        ]
        return results if isinstance(inputs, list) else results[0]
