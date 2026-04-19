"""
MLP importance scorer architecture.
Input: 1154-dim feature vector
Output: scalar 0.0-1.0
"""
import torch
import torch.nn as nn


class ImportanceMLP(nn.Module):
    def __init__(self, input_dim=1154):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return self.net(x).squeeze(-1)
