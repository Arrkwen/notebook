# Neck 特征融合颈部

Neck 位于 Backbone 与 Head 之间，负责**融合多尺度特征**，使检测器同时利用浅层细节（小目标、边缘）与深层语义（大目标、类别）。

本目录按时间线梳理并实现：

- **FPN（2017）**
- **PANet（2018）**：论文名；核心是“bottom-up path augmentation”
- **PAN（工程常用叫法）**：很多 YOLO 系列把“PANet 的 bottom-up 路径”简写为 PAN
- **Rep-PAN（YOLOv6, 2022）**：在 PAN 拓扑上用 RepConv/RepBlock 提升部署效率
- **MPAN（Multi-PAN，工程变体）**：多次路径聚合（multi-pass）直观实现

---

## 1. FPN（Feature Pyramid Networks）

**出处：** Feature Pyramid Networks for Object Detection (CVPR 2017)

**思想：** 构建**自顶向下**的特征金字塔：深层特征上采样后与浅层特征逐元素相加，再经 3×3 卷积得到每层输出，形成多尺度、语义增强的金字塔。

**结构示意：**

```
         C5 ──→ [1×1] ──→ P5 ──────────────────────────────→ 输出 P5
          ↑                │
          │            [上采样]
          │                ↓
         C4 ──→ [1×1] ──→ (+) ──→ [3×3] ──→ P4 ───────────→ 输出 P4
          ↑                ↑
          |            [上采样]
          |                ↓
         C3 ──→ [1×1] ──→ (+) ──→ [3×3] ──→ P3 ───────────→ 输出 P3
          ...
```

- **横向连接**：Backbone 的 C3、C4、C5 等先经 1×1 卷积统一通道，再与自上而下路径融合。
- **自顶向下**：从 P5 开始，上采样后与下一级横向特征相加，再 3×3 卷积得到 P4、P3 等。
- 输出 **P3、P4、P5**（及可选 P2、P6）送入检测头，实现多尺度预测。

---

## 2. PANet / PAN（Path Aggregation Network）

**出处：** Path Aggregation Network for Instance Segmentation (CVPR 2018)

**思想：** 在 FPN 的**自顶向下**金字塔基础上，再增加一条**自底向上**的路径，把浅层精确定位信息向上传递，增强整条路径的定位能力。

**补充：PANet vs PAN**

- **PANet（CVPR 2018）**是论文完整方法，除 bottom-up 路径外还包含如 Adaptive Feature Pooling 等组件。
- 但在很多工程实现（尤其 YOLO 系）里，大家常把“bottom-up path augmentation + 常规融合”简写成 **PAN**。

**结构示意：**

```
Backbone:  C3 ─── C4 ─── C5
              \    |    /
FPN 自顶向下:   P3 ← P4 ← P5
               |    |    |
PAN 自底向上:   N3 → N4 → N5  （下采样 + 融合）
```

- **FPN 部分**：与上面相同，得到 P3、P4、P5。
- **PAN 部分**：从 N3=P3 开始，经 3×3 stride=2 下采样后与 P4 融合得 N4；同理 N4 下采样与 P5 融合得 N5。
- 最终用 **N3、N4、N5** 做多尺度预测，既有语义又有精确定位信息。

在 YOLOv4、YOLOv5 等中，Neck 常为 **CSPDarkNet + SPP + FPN/PAN** 的组合。

---

## 3. Rep-PAN（YOLOv6，2022）

**动机：** 在保持 PAN 拓扑的前提下，把多分支训练结构通过“结构重参数化”在推理时融合为单路径卷积，提高硬件友好性。

**常见做法：**

- 用 `RepConv/RepBlock` 替换部分 CSP/常规卷积块
- 仍然遵循“top-down + bottom-up”的融合顺序

对应实现：`reppan.py`（输入 `(c3,c4,c5)`，输出 `(p3,p4,p5)`）。

---

## 4. MPAN（Multi-PAN / MPANet，工程变体）

公开资料中 **MPANet** 并不是一个统一标准的“同名论文/结构”，但在工程里常见的思路是：

- 把 PAN 的“路径聚合”做不止一次（multi-pass），让融合迭代收敛

对应实现：`mpan.py`（教学版：堆叠多次 `PAN`）。

---

## 小结

| 结构 | 方向       | 作用                     |
|------|------------|--------------------------|
| FPN  | 自顶向下   | 语义信息向浅层传递       |
| PANet/PAN | 自顶向下 + 自底向上 | 语义 + 精确定位，路径聚合 |
| Rep-PAN | 同上（替换算子） | 在 PAN 拓扑上提升部署效率 |
| MPAN | 多次路径聚合 | 迭代式融合（工程变体） |

实现见 `fpn.py`、`pan.py`、`reppan.py`、`mpan.py`。
