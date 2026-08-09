"""Loads the single-file EPTransNet graph bundle (see
scripts/prepare_samamba_dataset.py) and builds k-fold train/test node masks
over it using the real SAMamba GraphDataset pipeline
(samamba_core/dataset_pyg.py), unchanged from the published code.

The "dataset" here is one graph — 30k Ethereum addresses, ~1.27M transaction
edges — with per-node train_mask/test_mask columns swapped in per fold,
exactly as train_phish_scam.py's dataset_split() does. This is a transductive
node-classification setup, not a row-per-sample table: there is no held-out
"new" data distinct from the graph itself, only different node splits of it.
"""

from dataclasses import dataclass

import torch
from sklearn.model_selection import KFold
from torch_geometric.data import Data

from plugins.samamba.samamba_core.dataset_pyg import GraphDataset


@dataclass
class GraphBundle:
    pyg_graph: Data
    addresses: list[str]


def load_graph_bundle(dataset_path: str) -> GraphBundle:
    bundle = torch.load(dataset_path, weights_only=False)
    pyg_graph = Data(
        x=bundle["x"],
        edge_index=bundle["edge_index"],
        edge_attr=bundle["edge_attr"],
        y=bundle["y"],
    )
    return GraphBundle(pyg_graph=pyg_graph, addresses=bundle["addresses"])


def kfold_masks(pyg_graph: Data, n_splits: int, seed: int) -> list[tuple[Data, Data]]:
    """Same logic as the published dataset_split(), with n_splits made
    configurable (the original hardcodes 3) so a scaled-down run can still ask
    for fewer/more folds without touching the vendored core."""
    kf = KFold(n_splits=n_splits, shuffle=True, random_state=seed)
    folds = []
    for train_index, test_index in kf.split(pyg_graph.y):
        train_mask = torch.zeros(pyg_graph.num_nodes, dtype=torch.bool)
        test_mask = torch.zeros(pyg_graph.num_nodes, dtype=torch.bool)
        train_mask[train_index] = True
        test_mask[test_index] = True

        train_dataset = pyg_graph.clone()
        test_dataset = pyg_graph.clone()
        train_dataset.train_mask = train_mask
        test_dataset.test_mask = test_mask

        folds.append((train_dataset, test_dataset))
    return folds


def make_fold_datasets(train_data: Data, test_data: Data, k_hop: int, se: str) -> tuple[GraphDataset, GraphDataset]:
    train_dset = GraphDataset([train_data], degree=True, k_hop=k_hop, se=se)
    test_dset = GraphDataset([test_data], degree=True, k_hop=k_hop, se=se)
    return train_dset, test_dset
