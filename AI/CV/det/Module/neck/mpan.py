# -*- coding: utf-8 -*-
"""
MPAN（Multi-PAN）Neck（简化版）

说明：
“MPANet / MPAN”在公开文献中并不是一个像 FPN/PANet 那样统一的标准名词，
工程里更常见的是“在 PAN 结构上做多次（multi-pass）自顶向下+自底向上融合”的做法。

这里给出一个教学版：PAN 堆叠两次（可配置次数），用于直观理解“多次路径聚合”。
"""

from __future__ import division, print_function

from typing import List

import torch
import torch.nn as nn

from .pan import PAN

__all__ = ["MPAN", "build_mpan"]


class MPAN(nn.Module):
    """堆叠多个 PAN 的简化实现。"""

    def __init__(
        self, in_channels: List[int], out_channels: int = 256, num_passes: int = 2
    ):
        super().__init__()
        assert num_passes >= 1
        self.passes = nn.ModuleList(
            [
                PAN(in_channels=in_channels, out_channels=out_channels)
                for _ in range(num_passes)
            ]
        )

    def forward(self, feats: List[torch.Tensor]) -> List[torch.Tensor]:
        x = feats
        for p in self.passes:
            x = p(x)
        return x


def build_mpan(
    in_channels: List[int], out_channels: int = 256, num_passes: int = 2, **kwargs
) -> MPAN:
    return MPAN(
        in_channels=in_channels,
        out_channels=out_channels,
        num_passes=num_passes,
        **kwargs,
    )


if __name__ == "__main__":
    m = build_mpan([256, 512, 1024, 2048], 256, 2)
    feats = [
        torch.randn(2, 256, 56, 56),
        torch.randn(2, 512, 28, 28),
        torch.randn(2, 1024, 14, 14),
        torch.randn(2, 2048, 7, 7),
    ]
    outs = m(feats)
    print([o.shape for o in outs])
