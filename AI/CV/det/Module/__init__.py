# -*- coding: utf-8 -*-
"""
目标检测常用网络模块：Backbone、Neck、感受野增强、注意力。
使用方式（在 AI/cv/det 或项目根目录下）：
  from Module.backbone import build_resnet, build_darknet, build_cspdarknet
  from Module.neck import build_fpn, build_pan, build_reppan, build_mpan
  from Module.receptive_field import SPP, ASPP, RFB
  from Module.attention import SEBlock, SAM, CBAM
  from Module.blocks import ELAN1, EELAN, RELAN, RepNCSPELAN4, C3k2, C2PSA, RepConv
"""

from .backbone import (
    ResNet, build_resnet, BasicBlock, Bottleneck,
    DarkNet, DarknetBlock, build_darknet,
    CSPDarkNet, CSPLayer, build_cspdarknet,
    EfficientRep, build_efficientrep,
)
from .neck import FPN, build_fpn, PAN, build_pan, RepPAN, build_reppan, MPAN, build_mpan
from .receptive_field import SPP, ASPP, RFB
from .attention import SEBlock, SAM, CBAM
from .blocks import ELAN1, EELAN, RELAN, RepNCSPELAN4, C3k2, C2PSA, RepConv

__all__ = [
    "ResNet", "build_resnet", "BasicBlock", "Bottleneck",
    "DarkNet", "DarknetBlock", "build_darknet",
    "CSPDarkNet", "CSPLayer", "build_cspdarknet",
    "EfficientRep", "build_efficientrep",
    "FPN", "build_fpn", "PAN", "build_pan",
    "RepPAN", "build_reppan",
    "MPAN", "build_mpan",
    "SPP", "ASPP", "RFB",
    "SEBlock", "SAM", "CBAM",
    "ELAN1", "EELAN", "RELAN", "RepNCSPELAN4", "C3k2", "C2PSA", "RepConv",
]
