#!/usr/bin/env python3
"""Downloads the classic Cora citation network dataset and converts it into
the .npz format plugins/gcn_baseline expects (features, labels, edge_index,
train_mask, val_mask). Cora needs no API key/auth — 2708 papers, 1433 binary
word-presence features, 5429 citation edges, 7 subject-area classes. This is
the platform's first real (non-synthetic) node-classification dataset.

Usage:
    python scripts/prepare_cora_dataset.py --output datasets_registry/cora.npz
"""

import argparse
import tarfile
import tempfile
from pathlib import Path
from urllib.request import urlretrieve

import numpy as np

CORA_URL = "https://linqs-data.soe.ucsc.edu/public/lbc/cora.tgz"


def download_and_extract(dest_dir: Path) -> Path:
    with tempfile.NamedTemporaryFile(suffix=".tgz") as tmp:
        urlretrieve(CORA_URL, tmp.name)
        with tarfile.open(tmp.name) as tar:
            tar.extractall(dest_dir)
    return dest_dir / "cora"


def convert(cora_dir: Path, output_path: Path, seed: int) -> None:
    paper_ids: list[str] = []
    features: list[list[int]] = []
    labels_raw: list[str] = []

    with (cora_dir / "cora.content").open() as f:
        for line in f:
            parts = line.strip().split("\t")
            paper_ids.append(parts[0])
            features.append([int(x) for x in parts[1:-1]])
            labels_raw.append(parts[-1])

    id_to_idx = {pid: i for i, pid in enumerate(paper_ids)}
    classes = sorted(set(labels_raw))
    class_to_idx = {c: i for i, c in enumerate(classes)}
    labels = np.array([class_to_idx[c] for c in labels_raw], dtype=np.int64)
    features_arr = np.array(features, dtype=np.float32)

    edges = []
    with (cora_dir / "cora.cites").open() as f:
        for line in f:
            cited, citing = line.strip().split("\t")
            if cited in id_to_idx and citing in id_to_idx:
                edges.append((id_to_idx[citing], id_to_idx[cited]))
    edge_index = np.array(edges, dtype=np.int64).T

    rng = np.random.default_rng(seed)
    num_nodes = len(paper_ids)
    idx = rng.permutation(num_nodes)
    train_mask = np.zeros(num_nodes, dtype=bool)
    val_mask = np.zeros(num_nodes, dtype=bool)
    train_mask[idx[: int(0.7 * num_nodes)]] = True
    val_mask[idx[int(0.7 * num_nodes) :]] = True

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        output_path,
        features=features_arr,
        labels=labels,
        edge_index=edge_index,
        train_mask=train_mask,
        val_mask=val_mask,
    )
    print(
        f"wrote {output_path}: {num_nodes} nodes, {edge_index.shape[1]} directed edges, "
        f"{features_arr.shape[1]} features, {len(classes)} classes {classes}"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="datasets_registry/cora.npz")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmp_dir:
        cora_dir = download_and_extract(Path(tmp_dir))
        convert(cora_dir, Path(args.output), args.seed)


if __name__ == "__main__":
    main()
