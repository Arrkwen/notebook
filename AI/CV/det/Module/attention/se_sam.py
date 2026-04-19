# -*- coding: utf-8 -*-
"""
注意力模块：SE（通道注意力）、SAM（空间注意力）的简化实现。
"""

from __future__ import division, print_function
import torch
import torch.nn as nn
__all__ = ["SEBlock", "SAM", "CBAM"]


class SEBlock(nn.Module):
    """
    通道注意力：全局平均池化 → FC → ReLU → FC → Sigmoid → 通道乘。
    """

    def __init__(self, channels: int, reduction: int = 16):
        super().__init__()
        mid = max(channels // reduction, 8)
        self.fc = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(channels, mid),
            nn.ReLU(inplace=True),
            nn.Linear(mid, channels),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        w = self.fc(x)
        w = w.unsqueeze(-1).unsqueeze(-1)
        return x * w


class SAM(nn.Module):
    """
    空间注意力：通道 MaxPool+AvgPool → concat → 7×7 Conv → Sigmoid → 空间乘。
    """

    def __init__(self, kernel_size: int = 7):
        super().__init__()
        self.conv = nn.Conv2d(2, 1, kernel_size, padding=kernel_size // 2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        avg = torch.mean(x, dim=1, keepdim=True)
        mx, _ = torch.max(x, dim=1, keepdim=True)
        w = torch.cat([avg, mx], dim=1)
        w = torch.sigmoid(self.conv(w))
        return x * w


class CBAM(nn.Module):
    """
    简化版 CBAM：先 SE 通道注意力，再 SAM 空间注意力。
    """

    def __init__(
        self, channels: int, reduction: int = 16, spatial_kernel: int = 7
    ):
        super().__init__()
        self.channel_att = SEBlock(channels, reduction)
        self.spatial_att = SAM(spatial_kernel)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.channel_att(x)
        x = self.spatial_att(x)
        return x


if __name__ == "__main__":
    B, C, H, W = 2, 64, 28, 28
    x = torch.randn(B, C, H, W)

    se = SEBlock(C, reduction=16)
    print("SE out:", se(x).shape)

    sam = SAM(kernel_size=7)
    print("SAM out:", sam(x).shape)

    cbam = CBAM(C, reduction=16)
    print("CBAM out:", cbam(x).shape)
