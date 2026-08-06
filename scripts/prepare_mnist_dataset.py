#!/usr/bin/env python3
"""Downloads the classic MNIST handwritten digit dataset (60,000 train +
10,000 test 28x28 images) and combines the four raw IDX files into a single
.npz — the format plugins/mnist_cnn expects, and consistent with how every
other dataset in this platform registers as one file. No auth/API key needed.

Usage:
    python scripts/prepare_mnist_dataset.py --output datasets_registry/mnist.npz
"""

import argparse
import gzip
import tempfile
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np

BASE_URL = "https://ossci-datasets.s3.amazonaws.com/mnist/"
FILES = {
    "train_images": "train-images-idx3-ubyte.gz",
    "train_labels": "train-labels-idx1-ubyte.gz",
    "test_images": "t10k-images-idx3-ubyte.gz",
    "test_labels": "t10k-labels-idx1-ubyte.gz",
}


def _read_idx_images(path: Path) -> np.ndarray:
    with gzip.open(path, "rb") as f:
        magic = int.from_bytes(f.read(4), "big")
        assert magic == 2051, f"unexpected magic number {magic} in {path}"
        n = int.from_bytes(f.read(4), "big")
        rows = int.from_bytes(f.read(4), "big")
        cols = int.from_bytes(f.read(4), "big")
        data = np.frombuffer(f.read(n * rows * cols), dtype=np.uint8)
        return data.reshape(n, rows, cols)


def _read_idx_labels(path: Path) -> np.ndarray:
    with gzip.open(path, "rb") as f:
        magic = int.from_bytes(f.read(4), "big")
        assert magic == 2049, f"unexpected magic number {magic} in {path}"
        n = int.from_bytes(f.read(4), "big")
        return np.frombuffer(f.read(n), dtype=np.uint8)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="datasets_registry/mnist.npz")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        local_paths = {}
        for key, filename in FILES.items():
            dest = tmp / filename
            urlretrieve(BASE_URL + filename, dest)
            local_paths[key] = dest

        arrays = {
            "train_images": _read_idx_images(local_paths["train_images"]),
            "train_labels": _read_idx_labels(local_paths["train_labels"]),
            "test_images": _read_idx_images(local_paths["test_images"]),
            "test_labels": _read_idx_labels(local_paths["test_labels"]),
        }

    np.savez(output_path, **arrays)
    print(
        f"wrote {output_path}: {arrays['train_images'].shape[0]} train images, "
        f"{arrays['test_images'].shape[0]} test images, {arrays['train_images'].shape[1:]} shape"
    )


if __name__ == "__main__":
    main()
