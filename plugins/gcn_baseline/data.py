"""Graph data loading for the GCN baseline. Expects a .npz file with:

    features    (N, F) float32   node feature matrix
    labels      (N,)   int64     class per node
    edge_index  (2, E) int64     [source_nodes; target_nodes]
    train_mask  (N,)   bool
    val_mask    (N,)   bool

`synthesize_toy_graph` exists purely for local smoke-testing this plugin
without a real dataset registered yet — it is not a production data path and
nothing in `plugin.py` calls it.
"""

from dataclasses import dataclass

import numpy as np
import torch


@dataclass
class GraphData:
    features: torch.Tensor
    labels: torch.Tensor
    a_norm: torch.Tensor
    train_mask: torch.Tensor
    val_mask: torch.Tensor


def _normalize_adjacency(edge_index: np.ndarray, num_nodes: int) -> torch.Tensor:
    """Symmetric normalization D^-1/2 (A + I) D^-1/2, dense — fine at the toy
    scale this plugin targets; a real deployment would use a sparse tensor."""
    a = np.zeros((num_nodes, num_nodes), dtype=np.float32)
    a[edge_index[0], edge_index[1]] = 1.0
    a[edge_index[1], edge_index[0]] = 1.0  # treat the graph as undirected
    a += np.eye(num_nodes, dtype=np.float32)

    deg = a.sum(axis=1)
    deg_inv_sqrt = np.power(deg, -0.5, where=deg > 0)
    deg_inv_sqrt[deg == 0] = 0.0
    d_mat = np.diag(deg_inv_sqrt)
    a_norm = d_mat @ a @ d_mat
    return torch.tensor(a_norm, dtype=torch.float32)


def load_graph_dataset(npz_path: str) -> GraphData:
    npz = np.load(npz_path)
    num_nodes = npz["features"].shape[0]
    return GraphData(
        features=torch.tensor(npz["features"], dtype=torch.float32),
        labels=torch.tensor(npz["labels"], dtype=torch.long),
        a_norm=_normalize_adjacency(npz["edge_index"], num_nodes),
        train_mask=torch.tensor(npz["train_mask"], dtype=torch.bool),
        val_mask=torch.tensor(npz["val_mask"], dtype=torch.bool),
    )


def synthesize_toy_graph(path: str, num_nodes: int = 200, num_features: int = 16, num_classes: int = 3, seed: int = 0) -> None:
    rng = np.random.default_rng(seed)
    labels = rng.integers(0, num_classes, size=num_nodes)

    # Features correlated with label so the model has something learnable, plus noise.
    features = rng.normal(size=(num_nodes, num_features)).astype(np.float32)
    features += labels[:, None] * 0.5

    # Random edges, biased towards connecting same-label nodes (assortative graph).
    edges = []
    for _ in range(num_nodes * 4):
        u = rng.integers(0, num_nodes)
        same_label_pool = np.where(labels == labels[u])[0]
        v = rng.choice(same_label_pool) if rng.random() < 0.8 and len(same_label_pool) > 1 else rng.integers(0, num_nodes)
        if u != v:
            edges.append((u, v))
    edge_index = np.array(edges, dtype=np.int64).T

    idx = rng.permutation(num_nodes)
    train_mask = np.zeros(num_nodes, dtype=bool)
    val_mask = np.zeros(num_nodes, dtype=bool)
    train_mask[idx[: int(0.7 * num_nodes)]] = True
    val_mask[idx[int(0.7 * num_nodes) :]] = True

    np.savez(path, features=features, labels=labels, edge_index=edge_index, train_mask=train_mask, val_mask=val_mask)
