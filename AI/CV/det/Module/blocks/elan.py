# -*- coding: utf-8 -*-
"""
ELAN / GELAN 系列 Block（简化版）

参考思路：
- YOLOv7：ELAN / E-ELAN（层聚合、concat 多级特征，控制梯度路径）
- YOLOv9：GELAN（Generalized ELAN），常见实现形态里会出现 ELAN1、RepNCSPELAN4 等模块
"""

from __future__ import division, print_function

import torch
import torch.nn as nn

from .rep import ConvBNAct, RepBlock, RepConv

__all__ = ["ELAN1", "EELAN", "RELAN", "RepNCSPELAN4"]


def _channel_shuffle(x: torch.Tensor, groups: int) -> torch.Tensor:
    """Channel Shuffle（简化），常用于 group conv 后的信息交换。"""
    if groups <= 1:
        return x
    b, c, h, w = x.shape
    assert c % groups == 0
    x = x.view(b, groups, c // groups, h, w)
    x = x.transpose(1, 2).contiguous()
    return x.view(b, c, h, w)


class ELAN1(nn.Module):
    """
    ELAN1（简化）

    结构（类似 Ultralytics / YOLOv9 common.py）：
      cv1: 1×1 (c1 -> c3)，然后按通道一分为二
      分支: 3×3 -> 3×3
      concat([part1, part2, conv(part2), conv(conv(part2))]) -> cv4 1×1 输出
    """

    def __init__(self, c1: int, c2: int, c3: int, c4: int):
        super().__init__()
        assert c3 % 2 == 0, "c3 需为偶数以便 chunk(2)"
        self.c = c3 // 2
        self.cv1 = ConvBNAct(c1, c3, k=1, s=1)
        self.cv2 = ConvBNAct(c3 // 2, c4, k=3, s=1)
        self.cv3 = ConvBNAct(c4, c4, k=3, s=1)
        self.cv4 = ConvBNAct(c3 + 2 * c4, c2, k=1, s=1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = list(self.cv1(x).chunk(2, 1))
        y.append(self.cv2(y[-1]))
        y.append(self.cv3(y[-1]))
        return self.cv4(torch.cat(y, 1))


class EELAN(nn.Module):
    """
    E-ELAN（Extended ELAN，教学简化版）

    关键思想（YOLOv7）：expand / shuffle / merge cardinality。
    这里用 group conv + channel shuffle 近似表达“shuffle+merge”的味道，
    方便理解其与 ELAN 的关系（不追求与原实现完全一致）。
    """

    def __init__(self, c1: int, c2: int, c3: int, c4: int, groups: int = 2):
        super().__init__()
        assert c3 % 2 == 0
        self.groups = groups
        self.cv1 = ConvBNAct(c1, c3, 1, 1)
        self.cv2 = ConvBNAct(c3 // 2, c4, 3, 1, g=groups)
        self.cv3 = ConvBNAct(c4, c4, 3, 1, g=groups)
        self.cv4 = ConvBNAct(c3 + 2 * c4, c2, 1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = list(self.cv1(x).chunk(2, 1))
        y2 = _channel_shuffle(self.cv2(y[-1]), self.groups)
        y3 = _channel_shuffle(self.cv3(y2), self.groups)
        y.extend([y2, y3])
        return self.cv4(torch.cat(y, 1))


class RELAN(nn.Module):
    """
    R-ELAN（Re-parameterized ELAN，教学简化版）

    用 RepConv 替换 ELAN 分支中的常规卷积，使训练态多分支、推理态可融合。
    """

    def __init__(self, c1: int, c2: int, c3: int, c4: int):
        super().__init__()
        assert c3 % 2 == 0
        self.cv1 = ConvBNAct(c1, c3, 1, 1)
        self.cv2 = RepConv(c3 // 2, c4, s=1)
        self.cv3 = RepConv(c4, c4, s=1)
        self.cv4 = ConvBNAct(c3 + 2 * c4, c2, 1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = list(self.cv1(x).chunk(2, 1))
        y.append(self.cv2(y[-1]))
        y.append(self.cv3(y[-1]))
        return self.cv4(torch.cat(y, 1))


class _RepCSP(nn.Module):
    """RepCSP（极简）：CSP 两路 + RepBlock。"""

    def __init__(self, c1: int, c2: int, n: int = 1, e: float = 0.5):
        super().__init__()
        c_ = int(c2 * e)
        self.cv1 = ConvBNAct(c1, c_, 1, 1)
        self.cv2 = ConvBNAct(c1, c_, 1, 1)
        self.m = RepBlock(c_, c_, n=n)
        self.cv3 = ConvBNAct(2 * c_, c2, 1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.cv3(torch.cat([self.m(self.cv1(x)), self.cv2(x)], dim=1))


class RepNCSPELAN4(nn.Module):
    """
    RepNCSPELAN4（简化，覆盖 GELAN 常用形态）

    结构（与 Ultralytics `RepNCSPELAN4` 近似）：
      cv1: 1×1 (c1 -> c3) split
      cv2: RepCSP + 3×3
      cv3: RepCSP + 3×3
      cv4: 1×1 fuse
    """

    def __init__(self, c1: int, c2: int, c3: int, c4: int, n: int = 1):
        super().__init__()
        assert c3 % 2 == 0, "c3 需为偶数以便 chunk(2)"
        self.c = c3 // 2
        self.cv1 = ConvBNAct(c1, c3, 1, 1)
        self.cv2 = nn.Sequential(
            _RepCSP(c3 // 2, c4, n=n),
            ConvBNAct(c4, c4, 3, 1),
        )
        self.cv3 = nn.Sequential(
            _RepCSP(c4, c4, n=n),
            ConvBNAct(c4, c4, 3, 1),
        )
        self.cv4 = ConvBNAct(c3 + 2 * c4, c2, 1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = list(self.cv1(x).chunk(2, 1))
        y.append(self.cv2(y[-1]))
        y.append(self.cv3(y[-1]))
        return self.cv4(torch.cat(y, 1))
