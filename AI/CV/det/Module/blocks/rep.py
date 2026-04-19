# -*- coding: utf-8 -*-
"""
Rep 系列模块（简化版）

主要用于解释/复现 YOLOv6 的 EfficientRep、Rep-PAN，以及 YOLOv7/YOLOv9 中的 RepConv 思想：
- 训练时多分支（3×3、1×1、identity）利于优化
- 推理时可结构重参数化为单个 3×3 卷积（deploy）
"""

from __future__ import division, print_function

from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F

__all__ = ["autopad", "ConvBNAct", "RepConv", "RepBlock"]


def autopad(k: int, p: Optional[int] = None) -> int:
    """Same padding."""
    return k // 2 if p is None else p


class ConvBNAct(nn.Module):
    """Conv2d + BN + SiLU."""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        k: int = 1,
        s: int = 1,
        p: Optional[int] = None,
        g: int = 1,
        act: bool = True,
    ):
        super().__init__()
        self.conv = nn.Conv2d(
            in_channels,
            out_channels,
            k,
            s,
            autopad(k, p),
            groups=g,
            bias=False,
        )
        self.bn = nn.BatchNorm2d(out_channels)
        self.act = nn.SiLU(inplace=True) if act else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.act(self.bn(self.conv(x)))


class RepConv(nn.Module):
    """
    RepConv（RepVGG 风格，简化版）

    - train: 3×3 + 1×1 + identity（可选）三分支求和
    - deploy: 单个 3×3 conv（带 bias）
    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        k: int = 3,
        s: int = 1,
        g: int = 1,
        act: bool = True,
        deploy: bool = False,
    ):
        super().__init__()
        assert k == 3, "本简化实现仅支持 3×3 RepConv"
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.groups = g
        self.deploy = deploy
        self.act = nn.SiLU(inplace=True) if act else nn.Identity()

        if deploy:
            self.rbr_reparam = nn.Conv2d(
                in_channels,
                out_channels,
                kernel_size=3,
                stride=s,
                padding=1,
                groups=g,
                bias=True,
            )
        else:
            self.rbr_dense = nn.Sequential(
                nn.Conv2d(
                    in_channels,
                    out_channels,
                    kernel_size=3,
                    stride=s,
                    padding=1,
                    groups=g,
                    bias=False,
                ),
                nn.BatchNorm2d(out_channels),
            )
            self.rbr_1x1 = nn.Sequential(
                nn.Conv2d(
                    in_channels,
                    out_channels,
                    kernel_size=1,
                    stride=s,
                    padding=0,
                    groups=g,
                    bias=False,
                ),
                nn.BatchNorm2d(out_channels),
            )
            self.rbr_identity = (
                nn.BatchNorm2d(in_channels)
                if out_channels == in_channels and s == 1
                else None
            )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        if self.deploy:
            return self.act(self.rbr_reparam(x))
        out = self.rbr_dense(x) + self.rbr_1x1(x)
        if self.rbr_identity is not None:
            out = out + self.rbr_identity(x)
        return self.act(out)

    @staticmethod
    def _fuse_conv_bn(
        conv: nn.Conv2d, bn: nn.BatchNorm2d
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        w = conv.weight
        mean = bn.running_mean
        var = bn.running_var
        gamma = bn.weight
        beta = bn.bias
        eps = bn.eps

        std = torch.sqrt(var + eps)
        w_fused = w * (gamma / std).reshape(-1, 1, 1, 1)
        b_fused = beta - mean * gamma / std
        return w_fused, b_fused

    def _fuse_identity_bn(self, bn: nn.BatchNorm2d) -> Tuple[torch.Tensor, torch.Tensor]:
        input_dim = self.in_channels // self.groups
        k = torch.zeros(
            (self.out_channels, input_dim, 3, 3),
            device=bn.weight.device,
            dtype=bn.weight.dtype,
        )
        for i in range(self.out_channels):
            k[i, i % input_dim, 1, 1] = 1.0
        mean = bn.running_mean
        var = bn.running_var
        gamma = bn.weight
        beta = bn.bias
        eps = bn.eps
        std = torch.sqrt(var + eps)
        k = k * (gamma / std).reshape(-1, 1, 1, 1)
        b = beta - mean * gamma / std
        return k, b

    def get_equivalent_kernel_bias(self) -> Tuple[torch.Tensor, torch.Tensor]:
        k3, b3 = self._fuse_conv_bn(self.rbr_dense[0], self.rbr_dense[1])
        k1, b1 = self._fuse_conv_bn(self.rbr_1x1[0], self.rbr_1x1[1])
        k1 = F.pad(k1, [1, 1, 1, 1])
        if self.rbr_identity is not None:
            kid, bid = self._fuse_identity_bn(self.rbr_identity)
        else:
            kid = torch.zeros_like(k3)
            bid = torch.zeros_like(b3)
        return k3 + k1 + kid, b3 + b1 + bid

    def switch_to_deploy(self) -> None:
        """将训练态多分支融合为单分支 3×3 conv。"""
        if self.deploy:
            return
        kernel, bias = self.get_equivalent_kernel_bias()
        self.rbr_reparam = nn.Conv2d(
            self.in_channels,
            self.out_channels,
            kernel_size=3,
            stride=self.rbr_dense[0].stride,
            padding=1,
            groups=self.groups,
            bias=True,
        )
        self.rbr_reparam.weight.data = kernel
        self.rbr_reparam.bias.data = bias
        self.deploy = True
        del self.rbr_dense
        del self.rbr_1x1
        if hasattr(self, "rbr_identity"):
            del self.rbr_identity


class RepBlock(nn.Module):
    """RepBlock：RepConv 堆叠 n 次（简化）。"""

    def __init__(self, in_channels: int, out_channels: int, n: int = 1):
        super().__init__()
        assert in_channels == out_channels, "简化版 RepBlock 假设输入输出通道一致"
        self.m = nn.Sequential(
            *[RepConv(out_channels, out_channels) for _ in range(n)]
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.m(x)
