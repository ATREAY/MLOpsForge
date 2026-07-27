"""Placeholder classifier standing in for the real SAMamba architecture.

TODO(real SAMamba): replace this MLP with the actual Selective-Attention/Mamba
block from the thesis work. The plugin.py train/evaluate/predict lifecycle,
data loading, checkpoint format, and MLflow logging are all already correct —
only this module needs to change. Keep the constructor signature
(input_dim, hidden_dim) and the forward() -> raw logit contract so the rest of
the plugin doesn't need touching.
"""

import torch
from torch import nn


class PlaceholderSAMambaClassifier(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)  # raw logit, apply sigmoid outside for probability
