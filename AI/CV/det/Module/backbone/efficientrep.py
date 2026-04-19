# -*- coding: utf-8 -*-
"""
EfficientRep Backbone（简化版，YOLOv6 风格）

核心要点：
- 使用 RepConv/RepBlock（训练多分支，推理可融合）
- 多个 stage 输出多尺度特征，通常给 Neck（如 Rep-PAN / PAN / FPN）
"""

from __future__ import division, print_function

from typing import List, Tuple

import torch
import torch.nn as nn

from ..blocks.rep import RepConv, RepBlock
from ..receptive_field.spp_aspp_rfb import SPP

__all__ = ["EfficientRep", "build_efficientrep"]


class EfficientRep(nn.Module):
    """
    简化版 EfficientRep：
      stem(stride=2) -> stage2(stride=2) -> stage3 -> stage4 -> stage5(+SPP 可选)

    forward 返回 (c3, c4, c5) 三尺度特征，便于对接常见检测 neck。
    """

    def __init__(
        self,
        in_channels: int = 3,
        channels_list: List[int] = (64, 128, 256, 512, 1024),
        num_repeats: List[int] = (1, 1, 3, 3, 1),
        use_spp: bool = True,
    ):
        super().__init__()
        assert len(channels_list) == 5
        assert len(num_repeats) == 5

        c0, c1, c2, c3, c4 = channels_list

        self.stem = RepConv(in_channels, c0, s=2)

        self.stage2 = nn.Sequential(
            RepConv(c0, c1, s=2),
            RepBlock(c1, c1, n=num_repeats[1]),
        )
        self.stage3 = nn.Sequential(
            RepConv(c1, c2, s=2),
            RepBlock(c2, c2, n=num_repeats[2]),
        )
        self.stage4 = nn.Sequential(
            RepConv(c2, c3, s=2),
            RepBlock(c3, c3, n=num_repeats[3]),
        )
        self.stage5 = nn.Sequential(
            RepConv(c3, c4, s=2),
            RepBlock(c4, c4, n=num_repeats[4]),
        )
        self.spp = SPP(c4, c4) if use_spp else nn.Identity()

    def forward(
        self, x: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        x = self.stem(x)
        x = self.stage2(x)
        c3 = self.stage3(x)
        c4 = self.stage4(c3)
        c5 = self.spp(self.stage5(c4))
        return c3, c4, c5


def build_efficientrep(
    in_channels: int = 3,
    channels_list: List[int] = (64, 128, 256, 512, 1024),
    num_repeats: List[int] = (1, 1, 3, 3, 1),
    use_spp: bool = True,
    **kwargs,
) -> EfficientRep:
    return EfficientRep(
        in_channels=in_channels,
        channels_list=list(channels_list),
        num_repeats=list(num_repeats),
        use_spp=use_spp,
        **kwargs,
    )


if __name__ == "__main__":
    m = build_efficientrep()
    x = torch.randn(2, 3, 640, 640)
    outs = m(x)
    print([o.shape for o in outs])
