"""Loads a per-address Ethereum transaction feature table and prepares train/val
tensors. Expects a CSV with one row per address, numeric feature columns, and a
binary label column (default name "FLAG", overridable via config["label_column"])
— matching the shape of the public Ethereum Fraud Detection datasets this plugin
targets (e.g. total txns, avg value sent/received, time between first/last txn).

Non-numeric / identifier columns (address, hash, index) are dropped automatically
rather than requiring a hand-maintained feature list, since exact schemas vary
slightly between dataset sources.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

DEFAULT_LABEL_COLUMN = "FLAG"
DROP_COLUMN_KEYWORDS = ("address", "hash", "index", "unnamed")


@dataclass
class PreparedDataset:
    X_train: torch.Tensor
    y_train: torch.Tensor
    X_val: torch.Tensor
    y_val: torch.Tensor
    feature_names: list[str]


def _select_feature_columns(df: pd.DataFrame, label_column: str) -> list[str]:
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    return [
        c
        for c in numeric_cols
        if c != label_column and not any(kw in c.lower() for kw in DROP_COLUMN_KEYWORDS)
    ]


def load_dataset(csv_path: str, config: dict, fit_scaler: StandardScaler | None = None) -> tuple[PreparedDataset, StandardScaler]:
    df = pd.read_csv(csv_path)
    label_column = config.get("label_column", DEFAULT_LABEL_COLUMN)
    if label_column not in df.columns:
        raise ValueError(
            f"label column '{label_column}' not found in {csv_path}; "
            f"set config['label_column'] to override the default '{DEFAULT_LABEL_COLUMN}'"
        )

    feature_cols = _select_feature_columns(df, label_column)
    if not feature_cols:
        raise ValueError(f"no usable numeric feature columns found in {csv_path}")

    df = df.dropna(subset=feature_cols + [label_column])
    X = df[feature_cols].to_numpy(dtype=np.float32)
    y = df[label_column].to_numpy(dtype=np.float32)

    scaler = fit_scaler or StandardScaler().fit(X)
    X = scaler.transform(X).astype(np.float32)

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=config.get("seed", 42), stratify=y if len(np.unique(y)) > 1 else None
    )

    prepared = PreparedDataset(
        X_train=torch.tensor(X_train),
        y_train=torch.tensor(y_train),
        X_val=torch.tensor(X_val),
        y_val=torch.tensor(y_val),
        feature_names=feature_cols,
    )
    return prepared, scaler


def load_all(
    csv_path: str, config: dict, scaler: StandardScaler, feature_names: list[str]
) -> tuple[torch.Tensor, torch.Tensor]:
    """For evaluate()/predict(): scores every row against an already-fitted
    scaler + feature set from a checkpoint, with no train/val split."""
    df = pd.read_csv(csv_path)
    label_column = config.get("label_column", DEFAULT_LABEL_COLUMN)

    missing = [c for c in feature_names if c not in df.columns]
    if missing:
        raise ValueError(f"dataset at {csv_path} is missing feature columns the checkpoint expects: {missing}")

    X = scaler.transform(df[feature_names].to_numpy(dtype=np.float32)).astype(np.float32)
    y = df[label_column].to_numpy(dtype=np.float32) if label_column in df.columns else np.full(len(df), np.nan, dtype=np.float32)
    return torch.tensor(X), torch.tensor(y)
