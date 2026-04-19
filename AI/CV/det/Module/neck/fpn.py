# -*- coding: utf-8 -*-
"""
简化版 FPN（Feature Pyramid Networks）
自顶向下融合 Backbone 多阶段特征，输出统一通道的多尺度特征 P3/P4/P5。
"""

from __future__ import division, print_function
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List

__all__ = ["FPN", "build_fpn"]


class FPN(nn.Module):
    """
    FPN：对 backbone 输出的 [c2,c3,c4,c5]（或 [c3,c4,c5]）做横向 1×1 + 自顶向下融合 + 3×3。
    输出与输入阶段数相同，通道数统一为 out_channels。
    """

    def __init__(
        self,
        in_channels: List[int],
        out_channels: int = 256,
    ):
        super().__init__()
        self.out_channels = out_channels
        self.lateral_convs = nn.ModuleList()
        self.output_convs = nn.ModuleList()
        for ch in in_channels:
            self.lateral_convs.append(
                nn.Conv2d(ch, out_channels, 1)
            )
            self.output_convs.append(
                nn.Conv2d(out_channels, out_channels, 3, padding=1)
            )

    def forward(self, feats: List[torch.Tensor]) -> List[torch.Tensor]:
        """
        feats: backbone 多阶段特征 [c2,c3,c4,c5] 或 [c3,c4,c5]。
        返回 [P2..P5] 或 [P3..P5]，与 feats 长度一致。
        """
        laterals = [conv(f) for conv, f in zip(self.lateral_convs, feats)]
        # 自顶向下
        outs = []
        for i in range(len(laterals) - 1, -1, -1):
            if i == len(laterals) - 1:
                out = laterals[i]
            else:
                up = F.interpolate(
                    outs[-1], size=laterals[i].shape[2:], mode="nearest"
                )
                out = laterals[i] + up
            outs.append(self.output_convs[i](out))
        return list(reversed(outs))


def build_fpn(
    in_channels: List[int], out_channels: int = 256, **kwargs
) -> FPN:
    """构建 FPN。in_channels 与 backbone 各 stage 输出通道数一致。"""
    return FPN(in_channels=in_channels, out_channels=out_channels, **kwargs)


if __name__ == "__main__":
    # 假设 backbone 输出 4 个 stage，通道 [256, 512, 1024, 2048]
    fpn = build_fpn([256, 512, 1024, 2048], out_channels=256)
    feats = [
        torch.randn(2, 256, 56, 56),
        torch.randn(2, 512, 28, 28),
        torch.randn(2, 1024, 14, 14),
        torch.randn(2, 2048, 7, 7),
    ]
    outs = fpn(feats)
    for i, o in enumerate(outs):
        print(f"P{i + 2}: {o.shape}")
