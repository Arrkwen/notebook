# -*- coding: utf-8 -*-
"""
各 Loss 函数「劣势」的具象化 Case 演示
通过具体数值与对比，说明综述中提到的劣势在代码/数据上的表现。
依赖：同目录下 loss_functions.py
"""

from __future__ import division, print_function
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loss_functions import (
    iou_np,
    giou_np,
    diou_np,
    ciou_np,
    eiou_np,
    siou_np,
    loss_iou_np,
    loss_giou_np,
    loss_diou_np,
    loss_ciou_np,
    loss_eiou_np,
    loss_siou_np,
    loss_alpha_iou_np,
    smooth_l1_loss_np,
    mse_loss_np,
    ce_binary_np,
    focal_loss_np,
    varifocal_loss_np,
    qfl_np,
    dfl_np,
    _box_xyxy_to_xywh,
    _area_xyxy,
    _intersection_xyxy,
)

EPS = 1e-7


# -----------------------------------------------------------------------------
# 1. L2 / MSE 劣势 Case
# -----------------------------------------------------------------------------


def case_mse_scale_sensitivity():
    """
    劣势：与 IoU 不直接对应、尺度敏感
    同一像素误差，大框 IoU 影响小、小框影响大，但 MSE 相同。
    """
    print("\n" + "=" * 60)
    print("【Case 1】L2/MSE：尺度敏感、与 IoU 脱节")
    print("=" * 60)

    # 真实框：小框 10x10，大框 100x100
    gt_small = np.array([[0, 0, 10, 10]], dtype=np.float32)
    gt_large = np.array([[0, 0, 100, 100]], dtype=np.float32)

    # 预测框：都向右下角偏移 5 像素（同一「像素误差」）
    pred_small = np.array([[5, 5, 15, 15]], dtype=np.float32)  # 与 gt 有交集
    pred_large = np.array([[5, 5, 105, 105]], dtype=np.float32)

    mse_small = mse_loss_np(pred_small, gt_small)
    mse_large = mse_loss_np(pred_large, gt_large)
    iou_small = iou_np(pred_small, gt_small)[0]
    iou_large = iou_np(pred_large, gt_large)[0]

    print("同一「像素偏移」5px：")
    print("  小框 (10x10)  MSE = {:.4f}  IoU = {:.4f}".format(mse_small, iou_small))
    print("  大框 (100x100) MSE = {:.4f}  IoU = {:.4f}".format(mse_large, iou_large))
    print("→ MSE 量级接近，但小框 IoU 明显更低，说明优化 MSE 与优化 IoU 不一致。")
    print("→ 大框差 5px、小框差 5px 对 MSE 贡献类似，对 IoU 影响差异很大（尺度敏感）。")


def case_mse_large_error_gradient():
    """
    劣势：大误差时梯度大，易不稳定
    梯度 ∝ (pred - target)，离群预测会导致梯度爆炸。
    """
    print("\n" + "=" * 60)
    print("【Case 2】L2/MSE：大误差时梯度大")
    print("=" * 60)

    target = np.array([10.0, 10.0, 20.0, 20.0])
    for err_scale in [1.0, 10.0, 100.0]:
        pred = target + err_scale
        mse = mse_loss_np(pred, target)
        # 梯度 = 2*(pred - target)，这里用相对量说明
        grad_scale = 2 * err_scale
        print("  误差尺度 {:.0f}  →  MSE = {:.2f}  →  梯度量级 ∝ {:.0f}".format(err_scale, mse, grad_scale))
    print("→ 误差越大，梯度线性增大，一次坏预测就可能导致更新过大、训练震荡。")


# -----------------------------------------------------------------------------
# 2. Smooth L1 劣势 Case
# -----------------------------------------------------------------------------


def case_smooth_l1_ignores_geometry():
    """
    劣势：坐标独立回归、未考虑几何关系
    中心重合、面积相同但宽高比相反 → Smooth L1 可很小，IoU 却很低。
    """
    print("\n" + "=" * 60)
    print("【Case 3】Smooth L1：不考虑几何，与 IoU 脱节")
    print("=" * 60)

    # 真实框：中心 (50,50)，宽 20 高 40
    gt = np.array([[40, 30, 60, 70]], dtype=np.float32)  # cx=50, cy=50, w=20, h=40
    # 预测框：中心 (50,50)，宽 40 高 20（面积相同，宽高比相反）
    pred = np.array([[30, 40, 70, 60]], dtype=np.float32)  # cx=50, cy=50, w=40, h=20

    gt_xywh = _box_xyxy_to_xywh(gt)
    pred_xywh = _box_xyxy_to_xywh(pred)
    sl1 = smooth_l1_loss_np(pred_xywh, gt_xywh)
    iou = iou_np(pred, gt)[0]

    print("真实框：中心 (50,50)，宽 20 高 40")
    print("预测框：中心 (50,50)，宽 40 高 20（面积相同，宽高比颠倒）")
    print("  Smooth L1 (xywh) = {:.4f}".format(sl1))
    print("  IoU              = {:.4f}".format(iou))
    print("→ 中心、面积都对，Smooth L1 较小，但 IoU 很低，形状完全不对。")
    print("→ 说明 Smooth L1 不显式考虑「重叠形状」，与评测指标脱节。")


# -----------------------------------------------------------------------------
# 3. IoU Loss 劣势 Case
# -----------------------------------------------------------------------------


def case_iou_zero_gradient_when_no_overlap():
    """
    劣势：无重叠时 IoU=0，梯度为 0，无法学习
    预测框与真实框不交时，稍微移动预测框，IoU/Loss 不变。
    """
    print("\n" + "=" * 60)
    print("【Case 4】IoU Loss：无重叠时梯度为 0")
    print("=" * 60)

    gt = np.array([[50, 50, 100, 100]], dtype=np.float32)
    # 不重叠：预测框在右侧
    pred_far = np.array([[120, 50, 170, 100]], dtype=np.float32)
    pred_near = np.array([[105, 50, 155, 100]], dtype=np.float32)  # 仍不重叠

    loss_far = loss_iou_np(pred_far, gt)[0]
    loss_near = loss_iou_np(pred_near, gt)[0]
    iou_far = iou_np(pred_far, gt)[0]
    iou_near = iou_np(pred_near, gt)[0]

    print("真实框 [50,50,100,100]，预测框均不与之重叠：")
    print("  预测 [120,50,170,100]  →  IoU={:.4f}  L_IoU={:.4f}".format(iou_far, loss_far))
    print("  预测 [105,50,155,100]  →  IoU={:.4f}  L_IoU={:.4f}".format(iou_near, loss_near))
    print("→ 不重叠时 IoU 恒为 0、Loss 恒为 1，移动预测框不会改变 Loss，梯度为 0。")
    print("→ 模型无法从「完全没压中」的预测中得到「该往哪移」的信息。")


def case_iou_gradient_variance():
    """
    劣势：不同重叠程度梯度差异大，收敛不平滑
    """
    print("\n" + "=" * 60)
    print("【Case 5】IoU Loss：不同重叠下 Loss 变化率差异大")
    print("=" * 60)

    gt = np.array([[50, 50, 100, 100]], dtype=np.float32)
    # 沿 x 方向平移 1 像素，看 Loss 变化
    base = np.array([[51, 50, 101, 100]], dtype=np.float32)  # 几乎完全重叠
    shift_lo = np.array([[52, 50, 102, 100]], dtype=np.float32)
    base_mid = np.array([[75, 50, 125, 100]], dtype=np.float32)  # 部分重叠
    shift_mid = np.array([[76, 50, 126, 100]], dtype=np.float32)

    d_lo = loss_iou_np(shift_lo, gt)[0] - loss_iou_np(base, gt)[0]
    d_mid = loss_iou_np(shift_mid, gt)[0] - loss_iou_np(base_mid, gt)[0]
    print("真实框 [50,50,100,100]，预测框沿 x 右移 1px：")
    print("  高重叠 (IoU≈1) 时 Loss 变化 ≈ {:.6f}".format(d_lo))
    print("  中重叠 (IoU≈0.2) 时 Loss 变化 ≈ {:.6f}".format(d_mid))
    print("→ 同样 1px 位移，在不同重叠程度下对 Loss 的影响差异很大，优化曲面不均匀。")


# -----------------------------------------------------------------------------
# 4. GIoU 劣势 Case
# -----------------------------------------------------------------------------


def case_giou_degenerate_when_containing():
    """
    劣势：两框包含关系时退化为 IoU，惩罚项为 0
    """
    print("\n" + "=" * 60)
    print("【Case 6】GIoU：包含关系时退化为 IoU")
    print("=" * 60)

    gt = np.array([[60, 60, 90, 90]], dtype=np.float32)
    # 预测框完全包含 gt
    pred_contains = np.array([[50, 50, 100, 100]], dtype=np.float32)

    iou_val = iou_np(pred_contains, gt)[0]
    giou_val = giou_np(pred_contains, gt)[0]
    print("真实框 [60,60,90,90]，预测框 [50,50,100,100]（完全包含 gt）")
    print("  IoU  = {:.4f}".format(iou_val))
    print("  GIoU = {:.4f}".format(giou_val))
    print("→ 此时最小外接矩形 C = 预测框，C\\(A∪B) 为空，GIoU 惩罚项为 0，GIoU = IoU。")
    print("→ 若只需「缩小预测框以对齐边界」，梯度主要来自 IoU，可能偏弱。")


# -----------------------------------------------------------------------------
# 5. DIoU 劣势 Case
# -----------------------------------------------------------------------------


def case_diou_no_aspect_ratio():
    """
    劣势：未直接约束宽高比，中心对齐+重叠时 DIoU 可很高但形状错
    """
    print("\n" + "=" * 60)
    print("【Case 7】DIoU：不约束宽高比")
    print("=" * 60)

    # 真实：竖长条
    gt = np.array([[45, 20, 55, 80]], dtype=np.float32)  # w=10, h=60
    # 预测：中心重合、面积接近，但是横扁
    pred = np.array([[25, 45, 75, 55]], dtype=np.float32)  # w=50, h=10, 面积 500；gt 面积 600

    diou_val = diou_np(pred, gt)[0]
    iou_val = iou_np(pred, gt)[0]
    print("真实框：竖长条 [45,20,55,80] (w=10, h=60)")
    print("预测框：横扁   [25,45,75,55] (w=50, h=10)，中心与 gt 重合")
    print("  IoU  = {:.4f}".format(iou_val))
    print("  DIoU = {:.4f}".format(diou_val))
    print("→ 中心距离为 0，DIoU 主要看 IoU；若重叠尚可，DIoU 不差，但宽高比完全错误。")
    print("→ 说明 DIoU 不直接约束「形状一致」。")


# -----------------------------------------------------------------------------
# 6. CIoU 劣势 Case（数值与极端形状）
# -----------------------------------------------------------------------------


def case_ciou_numerical_and_extreme_shape():
    """
    劣势：alpha/v 在 h 很小时易数值不稳定；极端宽高比时 v 主导
    """
    print("\n" + "=" * 60)
    print("【Case 8】CIoU：数值稳定与极端宽高比")
    print("=" * 60)

    # 极端扁框：高非常小
    gt = np.array([[0, 0, 100, 1]], dtype=np.float32)
    pred = np.array([[0, 0, 100, 2]], dtype=np.float32)
    # 正常框
    gt_n = np.array([[0, 0, 100, 50]], dtype=np.float32)
    pred_n = np.array([[0, 0, 100, 55]], dtype=np.float32)

    ciou_flat = ciou_np(pred, gt)[0]
    ciou_normal = ciou_np(pred_n, gt_n)[0]
    print("极端扁框：gt 高=1, pred 高=2")
    print("  CIoU = {:.6f}".format(ciou_flat))
    print("正常框：gt 高=50, pred 高=55")
    print("  CIoU = {:.6f}".format(ciou_normal))
    print("→ 极端扁框时 arctan(w/h) 很大，v 易变大，实现中需对 h 做 clamp、分母加 eps 防 NaN。")
    print("→ 极端形状下 v 可能主导 loss，需在具体数据上权衡或截断。")


# -----------------------------------------------------------------------------
# 7. Cross Entropy 劣势 Case
# -----------------------------------------------------------------------------


def case_ce_imbalance_and_easy_dominant():
    """
    劣势：正负极不平衡时负样本主导梯度；难易样本同权
    """
    print("\n" + "=" * 60)
    print("【Case 9】Cross Entropy：负样本主导与易样本占优")
    print("=" * 60)

    # 模拟：100 个负样本 p=0.1（预测正确），1 个正样本 p=0.6（预测偏弱）
    n_neg, n_pos = 100, 1
    p_neg = np.full(n_neg, 0.1)
    y_neg = np.zeros(n_neg)
    p_pos = np.array([0.6])
    y_pos = np.ones(1)

    ce_neg = ce_binary_np(p_neg, y_neg)
    ce_pos = ce_binary_np(p_pos, y_pos)
    total_ce = ce_binary_np(np.concatenate([p_neg, p_pos]), np.concatenate([y_neg, y_pos]))
    # 总 loss = (n_neg * ce_neg + n_pos * ce_pos) / (n_neg + n_pos)，负样本在总 loss 中的占比
    sum_neg = n_neg * ce_neg
    sum_pos = n_pos * ce_pos
    ratio = sum_neg / (sum_neg + sum_pos + 1e-9)

    print("假设 100 个负样本（p=0.1）、1 个正样本（p=0.6）")
    print("  负样本平均 CE ≈ {:.4f}  正样本 CE ≈ {:.4f}".format(ce_neg, ce_pos))
    print("  总 loss 中负样本项占比 ≈ {:.1%}".format(ratio))
    print("→ 负样本数量多，总 loss 被负样本主导，模型易偏向「全预测成背景」。")
    print("→ 且易分类的负样本和难分类的正样本权重相同，易样本多时会拖慢对难样本的学习。")


# -----------------------------------------------------------------------------
# 8. Focal Loss 劣势 Case
# -----------------------------------------------------------------------------


def case_focal_no_quality_and_tuning():
    """
    劣势：分数不表示「框质量」；gamma/alpha 需调参
    """
    print("\n" + "=" * 60)
    print("【Case 10】Focal Loss：无质量建模与超参敏感")
    print("=" * 60)

    # 两个正样本：一个 p=0.9（易），一个 p=0.6（难），FL 会压低易样本权重
    p_easy = np.array([0.9])
    p_hard = np.array([0.6])
    y = np.array([1.0])
    fl_easy = focal_loss_np(p_easy, y)[0]
    fl_hard = focal_loss_np(p_hard, y)[0]
    ce_easy = -np.log(0.9)
    ce_hard = -np.log(0.6)
    print("正样本 (y=1)：易 p=0.9 vs 难 p=0.6")
    print("  CE:   易={:.4f}  难={:.4f}".format(ce_easy, ce_hard))
    print("  FL:   易={:.4f}  难={:.4f}".format(fl_easy, fl_hard))
    print("→ FL 自动压低易样本权重；但 gamma/alpha 不同，易/难权重比会变，需按数据集调。")
    print("→ 分类头输出的是「是否为目标」的置信度，不直接表示「框与 gt 的 IoU」；")
    print("  高分数 ≠ 高 IoU，NMS 时无法直接当定位质量用，需 VFL/QFL 等把 IoU 写进目标。")


# -----------------------------------------------------------------------------
# 9. Varifocal Loss：实现与标签复杂
# -----------------------------------------------------------------------------


def case_vfl_complexity_note():
    """ VFL 劣势：实现与数据标签设计稍复杂 """
    print("\n" + "=" * 60)
    print("【Case 11】Varifocal Loss：实现与标签复杂")
    print("=" * 60)
    # 数值示例：正样本需连续 q，负样本 q=0
    p = np.array([0.9, 0.2, 0.7])
    q = np.array([0.85, 0.0, 0.6])  # 正样本用 IoU 作 q，负样本 0
    vfl = varifocal_loss_np(p, q)
    print("正样本 q=IoU、负样本 q=0 时，VFL 需为每个样本准备连续标签：")
    print("  p = [0.9, 0.2, 0.7],  q = [0.85, 0, 0.6]  →  VFL = {}".format(vfl))
    print("VFL 需要为每个正样本构造连续标签 q（如与 gt 的 IoU），而不是 0/1。")
    print("数据管线中要：1）算每个 anchor 与对应 gt 的 IoU；2）把 IoU 写入 target；")
    print("3）loss 里正负样本分支、加权方式与 CE/FL 不同。")
    print("→ 相比 CE/Focal，实现和调试成本更高，适合已有 IoU 标注或联合质量估计的框架。")


# -----------------------------------------------------------------------------
# 10. EIoU / SIoU / α-IoU 劣势 Case
# -----------------------------------------------------------------------------


def case_eiou_extra_terms():
    """ EIoU 劣势：公式项多、极端扁/长框需防除零 """
    print("\n" + "=" * 60)
    print("【Case 12】EIoU：项多与极端形状")
    print("=" * 60)
    gt = np.array([[10, 10, 50, 50]], dtype=np.float32)
    pred = np.array([[12, 12, 52, 48]], dtype=np.float32)
    print("EIoU 含 IoU + 中心 + 宽 + 高 共 4 类项，实现与调试比 CIoU 略繁琐。")
    print("  pred [12,12,52,48] vs gt [10,10,50,50]  →  EIoU = {:.4f}, L_EIoU = {:.4f}".format(
        eiou_np(pred, gt)[0], loss_eiou_np(pred, gt)[0]))
    # 极端扁框
    gt_flat = np.array([[0, 0, 100, 1]], dtype=np.float32)
    pred_flat = np.array([[0, 0, 100, 2]], dtype=np.float32)
    print("极端扁框 (h=1 vs h=2)：EIoU = {:.4f}".format(eiou_np(pred_flat, gt_flat)[0]))
    print("→ 外接矩形 w_c 很大、h_c 很小时，h_c^2 需加 eps 或 clamp 防数值问题。")


def case_siou_complex_and_sensitive():
    """ SIoU 劣势：公式复杂、对框分布敏感 """
    print("\n" + "=" * 60)
    print("【Case 13】SIoU：公式复杂与超参敏感")
    print("=" * 60)
    gt = np.array([[50, 50, 100, 100]], dtype=np.float32)
    pred = np.array([[55, 55, 105, 95]], dtype=np.float32)
    iou_val = iou_np(pred, gt)[0]
    siou_val = siou_np(pred, gt)[0]
    print("SIoU 含角度项、距离项、形状项，实现需处理角度与归一化。")
    print("  IoU = {:.4f},  SIoU = {:.4f},  L_SIoU = {:.4f}".format(iou_val, siou_val, loss_siou_np(pred, gt)[0]))
    print("→ 不同实现/论文对角度项定义略有差异，超参与框分布敏感，需按数据集调。")


def case_alpha_iou_tuning():
    """ α-IoU 劣势：alpha 需调参，过大则低 IoU 梯度过小 """
    print("\n" + "=" * 60)
    print("【Case 14】α-IoU：alpha 需调参")
    print("=" * 60)
    gt = np.array([[50, 50, 100, 100]], dtype=np.float32)
    pred_high = np.array([[51, 51, 99, 99]], dtype=np.float32)   # 高 IoU
    pred_low = np.array([[80, 50, 130, 100]], dtype=np.float32)  # 低 IoU
    for a in [0.5, 1.0, 2.0, 3.0]:
        l_high = loss_alpha_iou_np(pred_high, gt, alpha=a)[0]
        l_low = loss_alpha_iou_np(pred_low, gt, alpha=a)[0]
        print("  alpha={:.1f}  高 IoU 样本 L={:.4f}  低 IoU 样本 L={:.4f}".format(a, l_high, l_low))
    print("→ alpha 越大，低 IoU 样本的 loss 相对越小，梯度被压低，难样本难以拉回；需按任务调 alpha。")


# -----------------------------------------------------------------------------
# 11. QFL / DFL 劣势 Case
# -----------------------------------------------------------------------------


def case_qfl_quality_label():
    """ QFL 劣势：需构造质量标签、beta 与实现 """
    print("\n" + "=" * 60)
    print("【Case 15】QFL：质量标签与 beta")
    print("=" * 60)
    # 正样本：质量 y=0.8（如 IoU），预测 logit 不同
    logit = np.array([1.0, 0.5, 2.0])
    y_q = np.array([0.8, 0.8, 0.8])
    loss = qfl_np(logit, y_q, beta=2.0)
    print("正样本质量标签 y=0.8，预测 logit=[1, 0.5, 2]  →  QFL = {}".format(loss))
    print("→ 训练时每个正样本都要算与 gt 的 IoU 作为 y，数据管线复杂；beta 需调参。")


def case_dfl_bins_and_decode():
    """ DFL 劣势：输出维度增加、格点需设定、与解码衔接 """
    print("\n" + "=" * 60)
    print("【Case 16】DFL：bin 数与解码")
    print("=" * 60)
    n_bins = 16
    # 模拟一条边的分布：真实 y=5.3，期望分布集中在 5、6 附近
    np.random.seed(42)
    pred_dist = np.random.randn(3, n_bins).astype(np.float32) * 0.5
    y_edge = np.array([5.3, 10.7, 2.1])
    loss = dfl_np(pred_dist, y_edge, y_min=0, y_max=15, n_bins=n_bins)
    print("每条边从 1 个标量变为 {} 个 bin 的分布，四条边则 head 输出维度增加。".format(n_bins))
    print("  y_edge = [5.3, 10.7, 2.1],  DFL = {}".format(loss))
    print("→ 格点范围 [y_min, y_max] 与 n_bins 需按数据集设定；推理时需用分布期望解码，与 NMS 等衔接。")


# -----------------------------------------------------------------------------
# 运行全部 Case
# -----------------------------------------------------------------------------


def run_all_cases():
    case_mse_scale_sensitivity()
    case_mse_large_error_gradient()
    case_smooth_l1_ignores_geometry()
    case_iou_zero_gradient_when_no_overlap()
    case_iou_gradient_variance()
    case_giou_degenerate_when_containing()
    case_diou_no_aspect_ratio()
    case_ciou_numerical_and_extreme_shape()
    case_ce_imbalance_and_easy_dominant()
    case_focal_no_quality_and_tuning()
    case_vfl_complexity_note()
    case_eiou_extra_terms()
    case_siou_complex_and_sensitive()
    case_alpha_iou_tuning()
    case_qfl_quality_label()
    case_dfl_bins_and_decode()
    print("\n" + "=" * 60)
    print("以上 Case 与《目标检测的loss发展路径综述.md》中「劣势」一一对应，便于理解。")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    run_all_cases()
