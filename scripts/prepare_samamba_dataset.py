#!/usr/bin/env python3
"""Converts the EPTransNet phishing/scam graph (two networkx MultiDiGraph
pickles — one directed, one undirected, ~30k Ethereum addresses / 1.27M
transaction edges each) into the single .pt file plugins/samamba expects.

This mirrors exactly what train_phish_scam.py's multidigraph_to_pyg() does
(same node features, same min-min + robust-scale normalization, same edge
features) so the real published SAMamba architecture trains on identical
inputs here as in the original research code — the only thing this script
adds is bundling the node->address order (for transductive predict() lookups
later) into the same file, since the platform's dataset registry expects one
file per dataset version.

Must run with the `samamba` conda env (needs torch_geometric + networkx,
which are not platform base dependencies):

    ~/.conda/envs/samamba/bin/python scripts/prepare_samamba_dataset.py \\
        --directed-graph ~/Thesis/SAMamba/datasets_phish_scam/directed-30000.pkl \\
        --undirected-graph ~/Thesis/SAMamba/datasets_phish_scam/undirected-30000.pkl \\
        --output datasets_registry/samamba_eptransnet_graph.pt
"""

import argparse
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plugins.samamba.samamba_core.dataset_pyg import multidigraph_to_pyg, read_graph_from_pickle


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directed-graph", required=True)
    parser.add_argument("--undirected-graph", required=True)
    parser.add_argument("--output", default="datasets_registry/samamba_eptransnet_graph.pt")
    args = parser.parse_args()

    print(f"loading {args.directed_graph} ...")
    sub_g = read_graph_from_pickle(args.directed_graph)
    print(f"loading {args.undirected_graph} ...")
    sub_g_undirected = read_graph_from_pickle(args.undirected_graph)

    # Same node order multidigraph_to_pyg's own node_to_index uses internally,
    # so index i in the saved tensors always corresponds to addresses[i].
    addresses = list(sub_g_undirected.nodes())

    pyg_graph, labeled_node_count = multidigraph_to_pyg(sub_g, sub_g_undirected)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "x": pyg_graph.x,
            "edge_index": pyg_graph.edge_index,
            "edge_attr": pyg_graph.edge_attr,
            "y": pyg_graph.y,
            "addresses": addresses,
        },
        output_path,
    )
    print(
        f"wrote {output_path}: {pyg_graph.num_nodes} nodes, {pyg_graph.edge_index.shape[1]} edges, "
        f"{pyg_graph.x.shape[1]} node features, {pyg_graph.edge_attr.shape[1]} edge features, "
        f"{labeled_node_count} positive (phish/scam) labels"
    )


if __name__ == "__main__":
    main()
