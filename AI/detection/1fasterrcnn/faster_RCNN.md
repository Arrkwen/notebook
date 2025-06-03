# 相关文章和代码

### 目标检测发展历程：RCNN -> SPPNet -> Fast RCNN -> Faster RCNN

目标检测技术从传统方法发展到深度学习时代，经历了多个重要的里程碑。RCNN、SPPNet、Fast RCNN、Faster RCNN 代表了深度学习目标检测方法的发展过程，主要围绕速度和精度的改进。

## **1. RCNN (Region-based Convolutional Neural Network, 2014)**

 **论文** ：《Rich feature hierarchies for accurate object detection and semantic segmentation》

 **核心思想** ：

* 采用 **Selective Search** 方法生成  **候选区域（Region Proposals）** ，通常约 2000 个。
* 每个候选区域通过 **CNN（如 AlexNet）** 提取特征。
* 用 **SVM** 进行对每个候选区域进行二分类，并用 **回归器** 进行边界框修正。

 **缺点** ：

* 计算量大，速度慢，每张图像需要计算 2000 次 CNN，因为每张图都要产生2000个候选区域。
* 存储占用大，需要保存大量特征。对CNN提取的特征要保存到文件中，用于后续的SVM和回归器修正。
* 训练复杂，涉及多个独立步骤（SS产生候选特征， CNN特征提取、SVM分类、边界框回归）。

---

## **2. SPPNet (Spatial Pyramid Pooling Network, 2014)**

 **论文** ：《Spatial Pyramid Pooling in Deep Convolutional Networks for Visual Recognition》

 **核心思想** ：

* 在 CNN 的最后一层加入 **SPP(Spatial Pyramid Pooling)** 层，使得输入图像可以是 **任意尺寸** ，减少对固定尺寸输入的依赖。
* **共享特征计算** ：整个图像仅需通过一次 CNN，而不是对每个候选区域都单独计算 CNN，极大提高计算效率。
* 在 ROI（候选区域）上使用 **SPP** 进行特征提取，使得每个候选区域都能得到固定维度的特征，随后进行分类和边界框回归。

 **优点** ：

* **速度提升** ：SPPNet 相较于 RCNN，CNN 只需执行一次前向传播，而不是 2000 次，提高了计算效率（因为RCNN是对候选区域提特征，而SPPNet是对原图提特征，的到featureMap之后，再让bbox去对应特征图，找到候选区域，在faster-rcnn文中去详解）
* **兼容不同输入尺寸** ，不需要对图像进行裁剪或缩放。

 **缺点** ：

* 仍然需要 **Selective Search** 生成候选区域，影响速度。
* 分类和边界框回归仍然是独立步骤，不是端到端训练。

---

## **3. Fast RCNN (2015)**

 **论文** ：《Fast R-CNN》

 **核心思想** ：

* 通过 **ROI Pooling** 取代 SPP，进一步提升计算效率和训练稳定性。
* 将整个目标检测过程整合为 **端到端** 的单一网络，使得分类和边界框回归可以  **同时训练** 。
* 共享 CNN 特征计算，提高速度。

 **改进点** ：

1. **整合训练** ：Fast RCNN 可以在同一个网络中同时进行分类和边界框回归，而 SPPNet 需要分步训练。
2. **ROI Pooling** 取代了 SPP，简化了网络结构，同时避免了 SPPNet 训练时的一些梯度传播问题。
3. **计算效率更高** ：

* 整张图片经过 CNN 提取特征（只需执行一次 CNN）。
* 通过 **ROI Pooling** 计算不同候选区域的特征，减少冗余计算。

 **优点** ：

* 相较于 RCNN 训练更高效，速度提高 9 倍，测试速度提高 213 倍。
* 端到端训练，提高检测效果。

 **缺点** ：

* 仍然使用 **Selective Search** 生成候选区域，这仍然是速度瓶颈。

---

## **4. Faster RCNN (2015, 提出 RPN 进行端到端检测)**

 **论文** ：《Faster R-CNN: Towards Real-Time Object Detection with Region Proposal Networks》

 **核心思想** ：

* 通过引入 **RPN（Region Proposal Network）** 取代 Selective Search，彻底摆脱了外部候选区域生成的瓶颈，使目标检测完全基于 CNN 进行  **端到端训练** 。

 **改进点** ：

1. **RPN 取代 Selective Search** ：

* RPN 也是一个 CNN 子网络，可以直接在特征图上生成候选框（region proposals）。
* 通过 **anchor boxes** 机制，生成不同尺度和比例的候选区域。
* 共享主干 CNN 计算，提高检测速度。

1. **完全端到端训练** ：

* RPN 生成的候选区域直接送入 Fast RCNN 进行分类和回归，不再依赖外部区域提取方法。

 **优点** ：

* **速度更快** ：Faster RCNN 速度比 Fast RCNN 提高 10 倍。
* **端到端优化** ，无需外部步骤，提高了检测精度和稳定性。

 **缺点** ：

* 仍然较慢，相比于后续的 YOLO、SSD 这类单阶段目标检测方法，Faster RCNN 仍然属于  **两阶段（Two-stage）方法** ，速度仍有限。

---

## **总结对比**

| 方法                  | 主要创新                  | 速度                               | 端到端训练 | 主要缺陷                  |
| --------------------- | ------------------------- | ---------------------------------- | ---------- | ------------------------- |
| **RCNN**        | Selective Search + CNN    | **慢** （2000次CNN前向传播） | ✗         | 计算量大，存储占用高      |
| **SPPNet**      | SPP 共享 CNN 特征         | **比 RCNN 快**               | ✗         | 仍然依赖 Selective Search |
| **Fast RCNN**   | ROI Pooling, 端到端训练   | **比 SPPNet 快**             | ✓         | 仍然依赖 Selective Search |
| **Faster RCNN** | RPN 取代 Selective Search | **比 Fast RCNN 快**          | ✓         | 仍然是 Two-stage 方法     |

Faster RCNN 之后，目标检测进入了实时检测（Real-Time Detection）时代，如：

* **YOLO** （You Only Look Once）：单阶段检测，提高速度，适合实时应用。
* **SSD** （Single Shot MultiBox Detector）：类似 YOLO，但兼顾多尺度检测。

Faster RCNN 仍然是 **高精度目标检测** 任务中的主流方法之一，尤其在需要精确定位的任务（如医学影像检测、自动驾驶）中仍然被广泛使用。

## **5 Faster RCNN解读**

1  论文相关：[论文翻译](https://gitee.com/traveler_zhao/DeepLearningPapersTranslation)

2  论文：[大白话解析fasterRCNN](https://blog.csdn.net/weixin_42310154/article/details/119889682), [一文读懂faster_RCNN](https://zhuanlan.zhihu.com/p/31426458), [详解anchor的生成过程](https://blog.csdn.net/sinat_33486980/article/details/81099093)

3  pytorch代码：[github](https://github.com/bubbliiiing/faster-rcnn-pytorch.git)
