# -*- coding: utf-8 -*-
"""
简化版 PAN（Path Aggregation Network）
在 FPN 自顶向下金字塔基础上，再增加自底向上路径，增强定位信息传递。
"""

from __future__ import division, print_function
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List

from .fpn import FPN

__all__ = ["PAN", "build_pan"]


class PAN(nn.Module):
    """
    PAN = FPN（自顶向下）+ 自底向上路径。
    输入为 backbone 多阶段特征，先过 FPN 得 P3~P5，再自底向上融合得 N3~N5。
    """

    def __init__(
        self,
        in_channels: List[int],
        out_channels: int = 256,
    ):
        super().__init__()
        self.fpn = FPN(in_channels=in_channels, out_channels=out_channels)
        self.out_channels = out_channels
        n = len(in_channels)
        # 自底向上：每层用 3×3 stride=2 下采样后与上一层融合
        self.down_convs = nn.ModuleList()
        for i in range(n - 1):
            self.down_convs.append(
                nn.Conv2d(out_channels, out_channels, 3, stride=2, padding=1)
            )

    def forward(self, feats: List[torch.Tensor]) -> List[torch.Tensor]:
        # FPN 自顶向下
        ps = self.fpn(feats)
        # 自底向上：N0 = P0, N_i = Down(N_{i-1}) + P_i
        ns = [ps[0]]
        for i in range(1, len(ps)):
            down = self.down_convs[i - 1](ns[-1])
            # 对齐尺寸（若下采样后与 P_i 尺寸不一致则插值）
            if down.shape[2:] != ps[i].shape[2:]:
                down = F.interpolate(
                    down, size=ps[i].shape[2:], mode="nearest"
                )
            ns.append(down + ps[i])
        return ns


def build_pan(
    in_channels: List[int], out_channels: int = 256, **kwargs
) -> PAN:
    """构建 PAN。"""
    return PAN(in_channels=in_channels, out_channels=out_channels, **kwargs)


if __name__ == "__main__":
    pan = build_pan([256, 512, 1024, 2048], out_channels=256)
    feats = [
        torch.randn(2, 256, 56, 56),
        torch.randn(2, 512, 28, 28),
        torch.randn(2, 1024, 14, 14),
        torch.randn(2, 2048, 7, 7),
    ]
    outs = pan(feats)
    for i, o in enumerate(outs):
        print(f"N{i + 2}: {o.shape}")
