# Backbone 骨干网络

Backbone 负责从输入图像中提取多尺度特征，为后续 Neck 和 Head 提供语义与细节信息。

本目录按“**时间线 + 结构家族**”补充一些检测常用骨干/块：ResNet、DarkNet、CSPDarkNet、EfficientRep，以及 ELAN/GELAN 相关块（见 `Module/blocks/`）。

---

## 时间线（粗略）

- **2016**：ResNet（残差）
- **2016-2018**：DarkNet（YOLOv2/v3）
- **2019-2020**：CSPNet → CSPDarkNet（YOLOv4/v5）
- **2022**：EfficientRep（YOLOv6，RepConv/重参数化）
- **2022**：ELAN / E-ELAN（YOLOv7，层聚合/梯度路径规划）
- **2024**：GELAN（YOLOv9，Generalized ELAN）

---

## 1. ResNet（残差网络）

**出处：** Deep Residual Learning for Image Recognition (CVPR 2016)

**核心思想：** 通过 **残差连接** \( y = F(x) + x \) 缓解深层网络退化与梯度消失，使网络可以堆得很深。

**结构示意：**

```
输入 x ──┬──→ [Conv/BN/ReLU] → [Conv/BN] → (+) → ReLU → 输出 y
         │                              ↑
         └──────────────────────────────┘
                     shortcut
```

- **BasicBlock**：两个 3×3 卷积，通道数不变，用于较浅的 ResNet-18/34。
- **Bottleneck**：1×1 降维 → 3×3 → 1×1 升维，用于 ResNet-50/101/152。
- 下采样时 shortcut 用 1×1 卷积或 stride=2 对齐尺寸与通道。

在检测中常取 **C2、C3、C4、C5** 多阶段特征送入 FPN/PAN 等 Neck。

---

## 2. DarkNet

**出处：** YOLOv2/v3 使用的骨干，由多个 **DarknetBlock**（卷积 + 残差）堆叠而成。

**特点：**

- 全部使用 **3×3** 和 **1×1** 卷积，结构简单。
- 每个 Stage 内先 1×1 降维再 3×3，类似 Bottleneck 的轻量版。
- 无 BatchNorm 的原始 DarkNet 也有广泛应用；带 BN 的版本训练更稳定。

**典型 Stage 结构：**

```
输入 → [1×1 Conv] → [3×3 Conv] → (+) → 输出
         ↑______________|
               shortcut
```

常用于 YOLOv2/v3，输出多尺度特征供检测头使用。

---

## 3. CSPDarkNet（CSP + DarkNet）

**出处：** YOLOv4 / YOLOv5 等，结合 **CSP (Cross Stage Partial)** 与 DarkNet 风格块。

**CSP 思想：** 将特征在通道上分为两路：一路经过多个 DarkNet Block，另一路直接恒等；最后在通道维拼接。这样既复用特征又减少计算、缓解重复梯度。

**结构示意：**

```
                     ┌→ [Part B: 多个 DarkNet Block] ─┐
输入 → [Part A: 1×1] → split →                          concat → [1×1] → 输出
                     └→ [Part B': 恒等/下采样] ────────┘
```

- **CSPLayer**：先 1×1 卷积，再按通道 split → 一路进多个 BaseBlock，一路直通 → concat → 1×1。
- 每个 Stage 内可含多个 CSPLayer，形成 CSPDarkNet 的 Stage。

相比纯 DarkNet，CSP 在相近精度下计算更少、梯度更均衡，适合作为检测 Backbone。

---

## 小结

| 骨干       | 核心机制     | 常见用途           |
|------------|--------------|--------------------|
| ResNet     | 残差连接     | Faster R-CNN、RetinaNet、DETR 等 |
| DarkNet    | 3×3/1×1 块   | YOLOv2、YOLOv3     |
| CSPDarkNet | CSP + 残差块 | YOLOv4、YOLOv5 等  |

本目录下的 `resnet.py`、`darknet.py`、`cspdarknet.py` 为上述结构的**简化实现**，便于阅读和接入自己的检测框架。

---

## 4. EfficientRep（YOLOv6，2022）

**定位：** Backbone（更偏“硬件友好”的 CNN 设计）。

**关键点：**

- **RepConv/RepBlock**：训练态多分支（3×3、1×1、identity）→ 推理态可融合为单 3×3，提高部署效率。
- 多个 stage 输出多尺度特征，常见输出为 **(C3,C4,C5)** 供 Neck（Rep-PAN/PAN/FPN）使用。

对应实现：`efficientrep.py`（教学简化版）。

---

## 5. ELAN / E-ELAN / GELAN（YOLOv7/YOLOv9）

这类名字更多指“**层聚合的 block 家族**”，常被用作 backbone 的主要计算单元：

- **ELAN**：多分支/多层特征串联后 concat，再 1×1 融合（强调梯度路径可控）。
- **E-ELAN**：在 ELAN 上引入“expand/shuffle/merge cardinality”等思想，增强容量而不破坏梯度路径。
- **GELAN**：把 ELAN 推广为“可替换计算块”的框架（YOLOv9 常用 RepConv/RepCSP 等作为计算块）。

对应简化实现放在 `Module/blocks/`：

- `ELAN1`（ELAN）、`EELAN`（E-ELAN 教学版）、`RELAN`（R-ELAN 教学版）
- `RepNCSPELAN4`（常见 GELAN/YOLOv9 形态之一）

---

## 6. C3k2 / C2PSA（工程常见 Block）

这两个更多是 Ultralytics 系列里常见的模块名（通常作为 backbone/neck 的内部块）：

- **C3k2**：基于 `C2f` 的变体，内部单元可切换为更“深”的子块。
- **C2PSA**：`C2f` + position-wise spatial attention（PSA 的简化形态）。

对应简化实现：`Module/blocks/ultralytics_blocks.py`。
