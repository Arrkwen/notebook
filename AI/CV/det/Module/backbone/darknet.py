# -*- coding: utf-8 -*-
"""
简化版 DarkNet 骨干网络（YOLOv2/v3 风格）
由 3×3 / 1×1 卷积与残差块堆叠，输出多阶段特征供检测头使用。
"""

from __future__ import division, print_function
import torch
import torch.nn as nn
from typing import List

__all__ = ["DarkNet", "DarknetBlock", "build_darknet"]


class DarknetBlock(nn.Module):
    """
    单个 DarkNet 块：1×1 降维 + 3×3 + 残差。
    输入输出通道相同，便于堆叠。
    """

    def __init__(self, in_ch: int, out_ch: int):
        super().__init__()
        assert in_ch == out_ch
        hidden = out_ch // 2
        self.conv1 = nn.Conv2d(in_ch, hidden, 1, bias=False)
        self.bn1 = nn.BatchNorm2d(hidden)
        self.conv2 = nn.Conv2d(hidden, out_ch, 3, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(out_ch)
        self.act = nn.LeakyReLU(0.1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        identity = x
        out = self.act(self.bn1(self.conv1(x)))
        out = self.act(self.bn2(self.conv2(out)))
        return out + identity


class DarkNet(nn.Module):
    """
    简化版 DarkNet：多个 Stage，每个 Stage 内含若干 DarknetBlock。
    forward 返回多阶段特征 [c2, c3, c4, c5]，与常见 FPN 输入对齐。
    """

    def __init__(
        self,
        in_channels: int = 3,
        out_channels: List[int] = (64, 128, 256, 512),  # 各 stage 输出通道
        num_blocks: List[int] = (1, 2, 8, 8),  # 各 stage 内 block 数（YOLOv3 风格）
    ):
        super().__init__()
        self.out_channels = list(out_channels)
        layers = []
        ch = in_channels
        for i, (out_ch, n_block) in enumerate(zip(out_channels, num_blocks)):
            # 下采样：3×3 stride=2
            layers.append(nn.Sequential(
                nn.Conv2d(ch, out_ch, 3, stride=2, padding=1, bias=False),
                nn.BatchNorm2d(out_ch),
                nn.LeakyReLU(0.1),
            ))
            ch = out_ch
            for _ in range(n_block):
                layers.append(DarknetBlock(ch, ch))
        self.layers = nn.ModuleList(layers)
        # 每个 stage 的结束索引：第一个 stage 1 个 conv；后续每个 stage 1 conv + n_block 个 block
        self.stage_ends = []
        idx = 0
        for i, n_block in enumerate(num_blocks):
            idx += 1 + n_block  # 1 个下采样 conv + n_block 个 block
            self.stage_ends.append(idx)

    def forward(self, x: torch.Tensor) -> List[torch.Tensor]:
        feats = []
        idx = 0
        for end in self.stage_ends:
            while idx < end:
                x = self.layers[idx](x)
                idx += 1
            feats.append(x)
        return feats


def build_darknet(
    in_channels: int = 3,
    out_channels: List[int] = (64, 128, 256, 512),
    num_blocks: List[int] = (1, 2, 8, 8),
    **kwargs
) -> DarkNet:
    """构建 DarkNet 骨干。"""
    return DarkNet(
        in_channels=in_channels,
        out_channels=out_channels,
        num_blocks=num_blocks,
        **kwargs
    )


if __name__ == "__main__":
    model = build_darknet()
    x = torch.randn(2, 3, 416, 416)
    outs = model(x)
    for i, o in enumerate(outs):
        print(f"Stage {i + 2}: {o.shape}")
