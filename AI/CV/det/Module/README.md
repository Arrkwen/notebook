# 目标检测常用网络模块（简化实现）

本目录提供检测任务中常用的 **Backbone**、**Neck**、**感受野增强模块** 和 **注意力模块** 的简化 PyTorch 实现，便于理解原理与复现。每个子目录配有原理解释，部分配有结构示意图。

---

## 一、目录结构

```text
Module/
├── README.md                 # 本说明
├── __init__.py               # 统一导出
├── demo_modules.ipynb        # Notebook 演示
├── images/                   # 示意图
├── blocks/                   # 积木模块（ELAN/GELAN/Rep/C2PSA 等）
├── backbone/                 # 骨干网络
│   ├── README.md             # 原理：按时间线梳理常见 backbone / block
│   ├── resnet.py             # ResNet 简化版
│   ├── darknet.py            # DarkNet 简化版
│   ├── cspdarknet.py         # CSPDarkNet 简化版
│   └── efficientrep.py       # EfficientRep（YOLOv6）简化版
├── neck/                     # 特征融合颈部
│   ├── README.md             # 原理：按时间线梳理 FPN/PANet/Rep-PAN/MPAN
│   ├── fpn.py                # Feature Pyramid Network
│   ├── pan.py                # PAN（bottom-up path augmentation）
│   ├── reppan.py             # Rep-PAN（YOLOv6）简化版
│   └── mpan.py               # MPAN（Multi-PAN 工程变体）简化版
├── receptive_field/          # 感受野增强
│   ├── README.md             # 原理：SPP / ASPP / RFB
│   ├── spp_aspp_rfb.py       # SPP, ASPP, RFB 实现
│   └── images/               # 可选结构图
└── attention/                # 注意力模块
    ├── README.md             # 原理：SE / SAM
    └── se_sam.py             # SE 通道注意力、SAM 空间注意力
```

---

## 二、整体流程示意

典型单阶段检测器（如 YOLO 系列）的组成可概括为：

```text
输入图像 → Backbone(特征提取) → Neck(多尺度融合) → Head(分类+回归)
                ↑                      ↑
            ResNet/DarkNet/CSP    FPN/PAN + 可选 SPP/ASPP
            可选加 SE/SAM 等注意力
```

- **Backbone**：将图像变为多层级特征图（浅层细节、深层语义）。
- **Neck**：融合不同尺度的特征，使小目标与大目标都能被充分利用。
- **感受野模块**：在某一层上扩大有效感受野（SPP/ASPP/RFB），利于大目标与上下文。
- **注意力**：通道注意力(SE)重标定通道重要性，空间注意力(SAM)突出空间位置。

---

## 三、使用方式

在 Python 中可按需导入：

```python
from Module.backbone import (
    build_resnet, build_darknet, build_cspdarknet, build_efficientrep,
)
from Module.neck import build_fpn, build_pan, build_reppan, build_mpan
from Module.receptive_field import SPP, ASPP, RFB
from Module.attention import SEBlock, SAM, CBAM
from Module.blocks import ELAN1, RepNCSPELAN4, C3k2, C2PSA, RepConv
```

各子目录的 `README.md` 中有更详细的公式与结构说明，代码文件内也有注释与简单用法示例。

**示意图：** 可将整体结构图放在 `Module/images/` 下（如 `det_module_overview.png`），用于说明 Backbone → Neck → Head 及 SPP/SE 等插接位置。

---

## 四、时间线索引（Backbone / Neck）

- **2016**：ResNet（Backbone）→ `backbone/resnet.py`
- **2016-2018**：DarkNet（Backbone）→ `backbone/darknet.py`
- **2019-2020**：CSPDarkNet（Backbone）→ `backbone/cspdarknet.py`
- **2017**：FPN（Neck）→ `neck/fpn.py`
- **2018**：PANet/PAN（Neck）→ `neck/pan.py`
- **2022**：EfficientRep（Backbone）→ `backbone/efficientrep.py`
- **2022**：Rep-PAN（Neck）→ `neck/reppan.py`
- **2022**：ELAN / E-ELAN（Block 家族）→ `blocks/elan.py`
- **2024**：GELAN（Block 家族）→ `blocks/elan.py`（`RepNCSPELAN4`）
- **近年工程常见**：C3k2 / C2PSA（Block）→ `blocks/ultralytics_blocks.py`
