# -*- coding: utf-8 -*-
"""
感受野增强模块：SPP、ASPP、RFB 的简化实现。
"""

from __future__ import division, print_function
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Tuple

__all__ = ["SPP", "ASPP", "RFB"]


class SPP(nn.Module):
    """
    Spatial Pyramid Pooling：多尺度 MaxPool + concat + 1×1。
    kernel_sizes 如 (5,9,13)，各分支池化+1×1 后与恒等分支 concat 再 1×1 融合。
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_sizes: Tuple[int, ...] = (5, 9, 13),
    ):
        super().__init__()
        self.pools = nn.ModuleList()
        mid_ch = in_channels // (len(kernel_sizes) + 1)
        self.conv_branches = nn.ModuleList()
        for k in kernel_sizes:
            self.pools.append(nn.MaxPool2d(kernel_size=k, stride=1, padding=k // 2))
            self.conv_branches.append(nn.Conv2d(in_channels, mid_ch, 1))
        self.identity_conv = nn.Conv2d(in_channels, mid_ch, 1)
        total_ch = mid_ch * (len(kernel_sizes) + 1)
        self.fuse = nn.Conv2d(total_ch, out_channels, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        outs = [self.identity_conv(x)]
        for pool, conv in zip(self.pools, self.conv_branches):
            outs.append(conv(pool(x)))
        return self.fuse(torch.cat(outs, dim=1))


class ASPP(nn.Module):
    """
    多膨胀率 3×3 空洞卷积 + 全局池化分支，concat 后 1×1。
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        rates: Tuple[int, ...] = (6, 12, 18),
        mid_channels: int = 256,
    ):
        super().__init__()
        self.branches = nn.ModuleList()
        for r in rates:
            self.branches.append(
                nn.Sequential(
                    nn.Conv2d(in_channels, mid_channels, 3, padding=r, dilation=r),
                    nn.BatchNorm2d(mid_channels),
                    nn.ReLU(inplace=True),
                )
            )
        self.global_branch = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_channels, mid_channels, 1),
            nn.BatchNorm2d(mid_channels),
            nn.ReLU(inplace=True),
        )
        total_ch = mid_channels * (len(rates) + 1)
        self.project = nn.Sequential(
            nn.Conv2d(total_ch, out_channels, 1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        outs = [branch(x) for branch in self.branches]
        g = self.global_branch(x)
        g = F.interpolate(g, size=outs[0].shape[2:], mode="nearest")
        outs.append(g)
        return self.project(torch.cat(outs, dim=1))


class RFB(nn.Module):
    """
    多分支 1×1 + 不同膨胀率 3×3，concat 后 1×1。简化版 3 分支，膨胀率 1,2,3。
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        rates: Tuple[int, ...] = (1, 2, 3),
        mid_channels: int = 64,
    ):
        super().__init__()
        self.branches = nn.ModuleList()
        for r in rates:
            self.branches.append(
                nn.Sequential(
                    nn.Conv2d(in_channels, mid_channels, 1),
                    nn.BatchNorm2d(mid_channels),
                    nn.ReLU(inplace=True),
                    nn.Conv2d(mid_channels, mid_channels, 3, padding=r, dilation=r),
                    nn.BatchNorm2d(mid_channels),
                    nn.ReLU(inplace=True),
                )
            )
        total_ch = mid_channels * len(rates)
        self.project = nn.Conv2d(total_ch, out_channels, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        outs = [branch(x) for branch in self.branches]
        return self.project(torch.cat(outs, dim=1))


if __name__ == "__main__":
    B, C, H, W = 2, 256, 14, 14
    x = torch.randn(B, C, H, W)

    spp = SPP(C, 256)
    print("SPP out:", spp(x).shape)

    aspp = ASPP(C, 256)
    print("ASPP out:", aspp(x).shape)

    rfb = RFB(C, 256)
    print("RFB out:", rfb(x).shape)
