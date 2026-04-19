# -*- coding: utf-8 -*-
"""
简化版 ResNet 骨干网络
用于目标检测时通常取 C2/C3/C4/C5 多阶段特征送入 FPN 等 Neck。
"""

from __future__ import division, print_function
import torch
import torch.nn as nn
from typing import List, Optional

__all__ = ["ResNet", "build_resnet", "BasicBlock", "Bottleneck"]


def conv3x3(in_ch: int, out_ch: int, stride: int = 1) -> nn.Conv2d:
    return nn.Conv2d(in_ch, out_ch, 3, stride=stride, padding=1, bias=False)


def conv1x1(in_ch: int, out_ch: int, stride: int = 1) -> nn.Conv2d:
    return nn.Conv2d(in_ch, out_ch, 1, stride=stride, bias=False)


class BasicBlock(nn.Module):
    """ResNet-18/34 使用的块：两个 3×3 卷积 + 残差连接。"""

    def __init__(
        self, in_ch: int, out_ch: int, stride: int = 1,
        downsample: Optional[nn.Module] = None
    ):
        super().__init__()
        self.conv1 = conv3x3(in_ch, out_ch, stride)
        self.bn1 = nn.BatchNorm2d(out_ch)
        self.conv2 = conv3x3(out_ch, out_ch)
        self.bn2 = nn.BatchNorm2d(out_ch)
        self.downsample = downsample
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        identity = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        if self.downsample is not None:
            identity = self.downsample(x)
        out += identity
        return self.relu(out)


class Bottleneck(nn.Module):
    """ResNet-50/101/152 使用的块：1×1 降维 → 3×3 → 1×1 升维 + 残差。"""

    expansion = 4

    def __init__(
        self,
        in_ch: int,
        mid_ch: int,
        stride: int = 1,
        downsample: Optional[nn.Module] = None,
    ):
        super().__init__()
        self.conv1 = conv1x1(in_ch, mid_ch)
        self.bn1 = nn.BatchNorm2d(mid_ch)
        self.conv2 = conv3x3(mid_ch, mid_ch, stride)
        self.bn2 = nn.BatchNorm2d(mid_ch)
        self.conv3 = conv1x1(mid_ch, mid_ch * self.expansion)
        self.bn3 = nn.BatchNorm2d(mid_ch * self.expansion)
        self.downsample = downsample
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        identity = x
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.relu(self.bn2(self.conv2(out)))
        out = self.bn3(self.conv3(out))
        if self.downsample is not None:
            identity = self.downsample(x)
        out += identity
        return self.relu(out)


class ResNet(nn.Module):
    """
    简化版 ResNet，支持 18/34/50 配置。
    forward 返回多阶段特征列表 [c2, c3, c4, c5]，通道数由 out_channels 指定。
    """

    def __init__(
        self,
        depth: int = 50,
        in_channels: int = 3,
        out_channels: List[int] = (256, 512, 1024, 2048),  # C2~C5
        stem_ch: int = 64,
    ):
        super().__init__()
        self.out_channels = list(out_channels)
        block = BasicBlock if depth in (18, 34) else Bottleneck
        if depth in (18, 34):
            num_blocks = {18: [2, 2, 2, 2], 34: [3, 4, 6, 3]}[depth]
        else:
            num_blocks = {
                50: [3, 4, 6, 3],
                101: [3, 4, 23, 3],
                152: [3, 8, 36, 3],
            }.get(depth, [3, 4, 6, 3])

        self.stem = nn.Sequential(
            nn.Conv2d(
                in_channels, stem_ch, 7, stride=2, padding=3, bias=False
            ),
            nn.BatchNorm2d(stem_ch),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(3, stride=2, padding=1),
        )
        ch_in = stem_ch
        self.stages = nn.ModuleList()
        for i, (n, ch_out) in enumerate(zip(num_blocks, self.out_channels)):
            downsample = None
            if block is Bottleneck:
                mid_ch = ch_out // block.expansion
                if ch_in != ch_out:
                    downsample = nn.Sequential(
                        conv1x1(ch_in, ch_out, stride=2 if i > 0 else 1),
                        nn.BatchNorm2d(ch_out),
                    )
                stride_i = 2 if i > 0 else 1
                layers = [
                    block(ch_in, mid_ch, stride=stride_i, downsample=downsample)
                ]
                ch_in = ch_out
                for _ in range(1, n):
                    layers.append(block(ch_in, mid_ch))
                ch_in = ch_out
            else:
                if ch_in != ch_out or (i > 0):
                    stride = 2 if i > 0 else 1
                    downsample = nn.Sequential(
                        conv1x1(ch_in, ch_out, stride=stride),
                        nn.BatchNorm2d(ch_out),
                    )
                stride_i = 2 if i > 0 else 1
                layers = [
                    block(ch_in, ch_out, stride=stride_i, downsample=downsample)
                ]
                ch_in = ch_out
                for _ in range(1, n):
                    layers.append(block(ch_in, ch_out))
            self.stages.append(nn.Sequential(*layers))

    def forward(self, x: torch.Tensor) -> List[torch.Tensor]:
        x = self.stem(x)
        feats = []
        for stage in self.stages:
            x = stage(x)
            feats.append(x)
        return feats


def build_resnet(depth: int = 50, in_channels: int = 3, **kwargs) -> ResNet:
    """构建 ResNet 骨干，depth 常用 18/34/50。"""
    return ResNet(depth=depth, in_channels=in_channels, **kwargs)


if __name__ == "__main__":
    model = build_resnet(50, in_channels=3)
    x = torch.randn(2, 3, 224, 224)
    outs = model(x)
    for i, o in enumerate(outs):
        print(f"C{i + 2}: {o.shape}")  # C2~C5
