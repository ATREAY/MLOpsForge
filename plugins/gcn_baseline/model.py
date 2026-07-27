import torch
from torch import nn


class GCNLayer(nn.Module):
    """A single graph-convolution: A_norm @ X @ W. No external graph library —
    the platform's plugin interface shouldn't require one just to prove itself
    model-agnostic."""

    def __init__(self, in_dim: int, out_dim: int):
        super().__init__()
        self.linear = nn.Linear(in_dim, out_dim, bias=True)

    def forward(self, x: torch.Tensor, a_norm: torch.Tensor) -> torch.Tensor:
        return a_norm @ self.linear(x)


class GCN(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, num_classes: int):
        super().__init__()
        self.layer1 = GCNLayer(input_dim, hidden_dim)
        self.layer2 = GCNLayer(hidden_dim, num_classes)
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(0.5)

    def forward(self, x: torch.Tensor, a_norm: torch.Tensor) -> torch.Tensor:
        h = self.relu(self.layer1(x, a_norm))
        h = self.dropout(h)
        return self.layer2(h, a_norm)  # raw logits per class
