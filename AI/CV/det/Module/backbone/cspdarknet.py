# -*- coding: utf-8 -*-
"""
简化版 CSPDarkNet 骨干（YOLOv4/v5 风格）
在 DarkNet 块基础上引入 CSP(Cross Stage Partial)，减少计算并改善梯度流。
"""

from __future__ import division, print_function
import torch
import torch.nn as nn
from typing import List

from .darknet import DarknetBlock

__all__ = ["CSPDarkNet", "CSPLayer", "build_cspdarknet"]


class CSPLayer(nn.Module):
    """
    CSP 层：通道 split → 一路经多个 BaseBlock，一路直通 → concat → 1×1。
    """

    def __init__(self, in_ch: int, out_ch: int, num_blocks: int):
        super().__init__()
        mid_ch = out_ch // 2
        self.conv1 = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.LeakyReLU(0.1),
        )
        self.split_ch = mid_ch
        self.conv2 = nn.Conv2d(out_ch, mid_ch, 1, bias=False)
        self.conv3 = nn.Conv2d(out_ch, mid_ch, 1, bias=False)
        self.blocks = nn.Sequential(
            *[DarknetBlock(mid_ch, mid_ch) for _ in range(num_blocks)]
        )
        self.conv4 = nn.Sequential(
            nn.Conv2d(mid_ch * 2, out_ch, 1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.LeakyReLU(0.1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv1(x)
        left = self.conv2(x)
        right = self.conv3(x)
        right = self.blocks(right)
        out = torch.cat([left, right], dim=1)
        return self.conv4(out)


class CSPDarkNet(nn.Module):
    """
    简化版 CSPDarkNet：stem + 多个 CSPLayer。
    返回多阶段特征 [c2, c3, c4, c5]。
    """

    def __init__(
        self,
        in_channels: int = 3,
        out_channels: List[int] = (64, 128, 256, 512),
        num_blocks: List[int] = (1, 2, 8, 8),
    ):
        super().__init__()
        self.out_channels = list(out_channels)
        self.stem = nn.Sequential(
            nn.Conv2d(in_channels, 32, 3, stride=1, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.LeakyReLU(0.1),
            nn.Conv2d(32, 64, 3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.LeakyReLU(0.1),
        )
        ch_in = 64
        self.stages = nn.ModuleList()
        for out_ch, n in zip(out_channels, num_blocks):
            self.stages.append(CSPLayer(ch_in, out_ch, num_blocks=n))
            ch_in = out_ch

    def forward(self, x: torch.Tensor) -> List[torch.Tensor]:
        x = self.stem(x)
        feats = [x]
        for stage in self.stages:
            x = stage(x)
            feats.append(x)
        return feats


def build_cspdarknet(
    in_channels: int = 3,
    out_channels: List[int] = (64, 128, 256, 512),
    num_blocks: List[int] = (1, 2, 8, 8),
    **kwargs
) -> CSPDarkNet:
    """构建 CSPDarkNet 骨干。"""
    return CSPDarkNet(
        in_channels=in_channels,
        out_channels=out_channels,
        num_blocks=num_blocks,
        **kwargs
    )


if __name__ == "__main__":
    model = build_cspdarknet()
    x = torch.randn(2, 3, 416, 416)
    outs = model(x)
    for i, o in enumerate(outs):
        print(f"Stage {i + 1}: {o.shape}")
