"""Loads MNIST from the combined .npz produced by
scripts/prepare_mnist_dataset.py (train_images, train_labels, test_images,
test_labels) — the four raw IDX files get combined into one file so this
dataset registers the same way every other dataset in the platform does: one
file, one DatasetVersion.
"""

from dataclasses import dataclass

import numpy as np
import torch


@dataclass
class MNISTData:
    train_images: torch.Tensor  # (N, 1, 28, 28) float32, normalized to [0, 1]
    train_labels: torch.Tensor  # (N,) int64
    test_images: torch.Tensor
    test_labels: torch.Tensor


def load_dataset(npz_path: str, config: dict) -> MNISTData:
    npz = np.load(npz_path)
    train_images = (npz["train_images"].astype(np.float32) / 255.0)[:, None, :, :]
    test_images = (npz["test_images"].astype(np.float32) / 255.0)[:, None, :, :]

    max_train_samples = config.get("max_train_samples")
    if max_train_samples:
        rng = np.random.default_rng(config.get("seed", 42))
        idx = rng.choice(len(train_images), size=min(max_train_samples, len(train_images)), replace=False)
        train_images = train_images[idx]
        train_labels = npz["train_labels"][idx]
    else:
        train_labels = npz["train_labels"]

    return MNISTData(
        train_images=torch.tensor(train_images),
        train_labels=torch.tensor(train_labels.astype(np.int64)),
        test_images=torch.tensor(test_images),
        test_labels=torch.tensor(npz["test_labels"].astype(np.int64)),
    )
