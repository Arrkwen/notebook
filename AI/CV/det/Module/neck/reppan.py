# -*- coding: utf-8 -*-
"""
Rep-PAN Neck（简化版，YOLOv6 风格）

输入：来自 backbone 的 (c3, c4, c5)
输出：融合后的 (p3, p4, p5)
"""

from __future__ import division, print_function

from typing import Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

from ..blocks.rep import ConvBNAct, RepBlock

__all__ = ["RepPAN", "build_reppan"]


class RepPAN(nn.Module):
    """
    简化版 Rep-PAN：
    - top-down: c5 -> up + c4 -> p4 ; p4 -> up + c3 -> p3
    - bottom-up: p3 -> down + p4 -> n4 ; n4 -> down + c5_reduce -> n5
    """

    def __init__(
        self,
        in_channels: Tuple[int, int, int] = (256, 512, 1024),
        out_channels: int = 256,
        num_repeats: int = 2,
    ):
        super().__init__()
        c3, c4, c5 = in_channels
        self.reduce_c5 = ConvBNAct(c5, out_channels, 1, 1)
        self.reduce_p4 = ConvBNAct(out_channels, out_channels, 1, 1)

        self.p4_block = RepBlock(out_channels, out_channels, n=num_repeats)
        self.p3_block = RepBlock(out_channels, out_channels, n=num_repeats)

        self.down_p3 = ConvBNAct(out_channels, out_channels, 3, 2)
        self.down_p4 = ConvBNAct(out_channels, out_channels, 3, 2)
        self.n4_block = RepBlock(out_channels, out_channels, n=num_repeats)
        self.n5_block = RepBlock(out_channels, out_channels, n=num_repeats)

        self.lateral_c4 = ConvBNAct(c4, out_channels, 1, 1)
        self.lateral_c3 = ConvBNAct(c3, out_channels, 1, 1)

    def forward(
        self, feats: Tuple[torch.Tensor, torch.Tensor, torch.Tensor]
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        c3, c4, c5 = feats

        p5 = self.reduce_c5(c5)
        p5_up = F.interpolate(p5, size=c4.shape[2:], mode="nearest")
        p4 = self.p4_block(self.lateral_c4(c4) + p5_up)

        p4_up = F.interpolate(p4, size=c3.shape[2:], mode="nearest")
        p3 = self.p3_block(self.lateral_c3(c3) + p4_up)

        n4 = self.n4_block(self.down_p3(p3) + self.reduce_p4(p4))
        n5 = self.n5_block(self.down_p4(n4) + p5)
        return p3, n4, n5


def build_reppan(
    in_channels: Tuple[int, int, int] = (256, 512, 1024),
    out_channels: int = 256,
    num_repeats: int = 2,
    **kwargs,
) -> RepPAN:
    return RepPAN(
        in_channels=in_channels,
        out_channels=out_channels,
        num_repeats=num_repeats,
        **kwargs,
    )


if __name__ == "__main__":
    neck = build_reppan((256, 512, 1024), 256, 2)
    feats = (
        torch.randn(2, 256, 80, 80),
        torch.randn(2, 512, 40, 40),
        torch.randn(2, 1024, 20, 20),
    )
    outs = neck(feats)
    print([o.shape for o in outs])
