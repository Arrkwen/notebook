# -*- coding: utf-8 -*-
"""
Ultralytics 风格 Block（简化版）

目标：
- 给出 C2f / C3k2 / C2PSA 这些“工程常见名字”的直观结构
- 保持依赖最小、可运行、便于阅读（不追求与官方逐行一致）
"""

from __future__ import division, print_function

import torch
import torch.nn as nn
import torch.nn.functional as F

__all__ = ["Conv", "Bottleneck", "C2f", "C3k2", "PSABlock", "C2PSA"]


class Conv(nn.Module):
    """Conv2d + BN + SiLU（贴近 Ultralytics 默认风格）。"""

    def __init__(
        self,
        c1: int,
        c2: int,
        k: int = 1,
        s: int = 1,
        g: int = 1,
        act: bool = True,
    ):
        super().__init__()
        p = k // 2
        self.conv = nn.Conv2d(c1, c2, k, s, p, groups=g, bias=False)
        self.bn = nn.BatchNorm2d(c2)
        self.act = nn.SiLU(inplace=True) if act else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.act(self.bn(self.conv(x)))


class Bottleneck(nn.Module):
    """简化 Bottleneck：1×1 -> 3×3，可选 shortcut。"""

    def __init__(
        self, c1: int, c2: int, shortcut: bool = True, g: int = 1, e: float = 0.5
    ):
        super().__init__()
        c_ = int(c2 * e)
        self.cv1 = Conv(c1, c_, 1, 1)
        self.cv2 = Conv(c_, c2, 3, 1, g=g)
        self.add = shortcut and c1 == c2

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = self.cv2(self.cv1(x))
        return x + y if self.add else y


class C2f(nn.Module):
    """
    C2f（简化）：cv1 生成 2*c 通道并 split，重复 n 个 block，
    concat 中间特征后用 cv2 融合。
    """

    def __init__(
        self,
        c1: int,
        c2: int,
        n: int = 1,
        shortcut: bool = False,
        g: int = 1,
        e: float = 0.5,
    ):
        super().__init__()
        self.c = int(c2 * e)
        self.cv1 = Conv(c1, 2 * self.c, 1, 1)
        self.cv2 = Conv((2 + n) * self.c, c2, 1, 1)
        self.m = nn.ModuleList(
            Bottleneck(self.c, self.c, shortcut, g, e=1.0) for _ in range(n)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        y = list(self.cv1(x).chunk(2, 1))
        for m in self.m:
            y.append(m(y[-1]))
        return self.cv2(torch.cat(y, 1))


class _C3k(nn.Module):
    """C3k（简化）：内部用 2 个 Bottleneck 作为“k=2”的直观实现。"""

    def __init__(self, c1: int, c2: int, shortcut: bool = True, g: int = 1):
        super().__init__()
        assert c1 == c2
        self.m = nn.Sequential(
            Bottleneck(c1, c2, shortcut=shortcut, g=g, e=1.0),
            Bottleneck(c2, c2, shortcut=shortcut, g=g, e=1.0),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.m(x)


class C3k2(C2f):
    """
    C3k2（简化）：继承 C2f，把内部 m 替换为 Bottleneck 或 C3k（每个单元内部 2 层）。

    对应 Ultralytics 里常见签名：C3k2(c1, c2, n=..., c3k=..., e=..., g=..., shortcut=...)
    """

    def __init__(
        self,
        c1: int,
        c2: int,
        n: int = 1,
        c3k: bool = False,
        e: float = 0.5,
        g: int = 1,
        shortcut: bool = True,
    ):
        super().__init__(c1, c2, n=n, shortcut=shortcut, g=g, e=e)
        if c3k:
            self.m = nn.ModuleList(
                _C3k(self.c, self.c, shortcut=shortcut, g=g) for _ in range(n)
            )
        else:
            self.m = nn.ModuleList(
                Bottleneck(self.c, self.c, shortcut=shortcut, g=g, e=1.0)
                for _ in range(n)
            )


class PSABlock(nn.Module):
    """
    PSA（Position-wise Spatial Attention）极简块。

    实现要点（教学版，不等价官方）：
    - 用 1×1 conv 得到每个通道的空间 logits，在 H×W 维做 softmax
    - 用该权重对特征做加权汇聚得到 context，再与输入残差相加
    - 再接一个轻量 FFN（1×1 expand + 1×1 project）
    """

    def __init__(self, c: int, attn_ratio: float = 0.5):
        super().__init__()
        mid = max(int(c * attn_ratio), 8)
        self.attn = nn.Conv2d(c, c, 1, 1, 0)
        self.ffn = nn.Sequential(
            Conv(c, mid, 1, 1),
            Conv(mid, c, 1, 1, act=False),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        b, c, h, w = x.shape
        logits = self.attn(x).view(b, c, h * w)
        weights = F.softmax(logits, dim=-1).view(b, c, h, w)
        context = (x * weights).sum(dim=(2, 3), keepdim=True)
        x = x + context
        return x + self.ffn(x)


class C2PSA(C2f):
    """
    C2PSA（简化）：C2f 结构，但重复单元替换为 PSABlock。

    官方通常要求 c1 == c2；这里也保持这个约束，方便直接插入 backbone/neck。
    """

    def __init__(self, c1: int, c2: int, n: int = 1, e: float = 0.5):
        assert c1 == c2
        super().__init__(c1, c2, n=n, shortcut=False, g=1, e=e)
        self.m = nn.ModuleList(
            PSABlock(self.c, attn_ratio=0.5) for _ in range(n)
        )
