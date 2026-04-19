# Blocks（积木模块）

很多“骨干/颈部”的名字（如 **ELAN / E-ELAN / GELAN / Rep-PAN / EfficientRep / C3k2 / C2PSA**）本质上是由一组可复用的 **Block** 组合出来的。
因此这里单独建一个 `blocks/`，把它们拆成更易读的“积木”，再在 `backbone/` 与 `neck/` 中按需组装。

---

## 一、时间线（粗略）

- **2017**：FPN（Neck 的经典起点）
- **2018**：PANet（在 FPN 上增加自底向上路径）
- **2022**：YOLOv6：**EfficientRep（Backbone）** + **Rep-PAN（Neck）**（RepConv/结构重参数化）
- **2022**：YOLOv7：**ELAN / E-ELAN**（层聚合、控制梯度路径）
- **2024**：YOLOv9：**GELAN**（Generalized ELAN，可用不同计算块替换）
- **近年工程实现**：Ultralytics 系列：**C3k2**（C2f 的变体）、**C2PSA**（C2f + PSA 注意力）

> 说明：不同 repo/论文对命名与实现细节会有差异，这里以“**结构思想 + 可运行的简化实现**”为目标。

---

## 二、本目录包含

- **`rep.py`**：`RepConv`、`RepBlock`（可选 `switch_to_deploy()`）
- **`elan.py`**：`ELAN1` / `RepNCSPELAN4`（覆盖 ELAN/GELAN 常见形态）
- **`elan.py`** 同时给出 `EELAN`（E-ELAN 教学版）与 `RELAN`（R-ELAN 教学版）
- **`ultralytics_blocks.py`**：`C2f` / `C3k2` / `C2PSA`（Ultralytics 风格的简化版本）
