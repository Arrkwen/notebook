# -*- coding: utf-8 -*-
"""
目标检测常用 Loss 函数实现（NumPy + 可选 PyTorch）
用于配合《目标检测的loss发展路径综述.md》学习与复现。
"""

from __future__ import division, print_function
import numpy as np

# 尝试导入 PyTorch，若无则仅使用 NumPy
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


# --------------- 工具：框格式转换与面积/交集 ---------------

def _box_xyxy_to_xywh(box):
    """ [x1,y1,x2,y2] -> [cx,cy,w,h] """
    x1, y1, x2, y2 = box[..., 0], box[..., 1], box[..., 2], box[..., 3]
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    w = x2 - x1
    h = y2 - y1
    return np.stack([cx, cy, w, h], axis=-1) if isinstance(box, np.ndarray) else torch.stack([cx, cy, w, h], dim=-1)


def _area_xyxy(box):
    """ box: (..., 4) x1,y1,x2,y2, 返回面积 """
    x1, y1, x2, y2 = box[..., 0], box[..., 1], box[..., 2], box[..., 3]
    w = np.maximum(x2 - x1, 0) if isinstance(box, np.ndarray) else torch.clamp(x2 - x1, min=0)
    h = np.maximum(y2 - y1, 0) if isinstance(box, np.ndarray) else torch.clamp(y2 - y1, min=0)
    return w * h


def _intersection_xyxy(box_a, box_b):
    """ 两个 (...,4) xyxy 框的交集面积 """
    x1 = np.maximum(box_a[..., 0], box_b[..., 0]) if isinstance(box_a, np.ndarray) else torch.maximum(box_a[..., 0], box_b[..., 0])
    y1 = np.maximum(box_a[..., 1], box_b[..., 1]) if isinstance(box_a, np.ndarray) else torch.maximum(box_a[..., 1], box_b[..., 1])
    x2 = np.minimum(box_a[..., 2], box_b[..., 2]) if isinstance(box_a, np.ndarray) else torch.minimum(box_a[..., 2], box_b[..., 2])
    y2 = np.minimum(box_a[..., 3], box_b[..., 3]) if isinstance(box_a, np.ndarray) else torch.minimum(box_a[..., 3], box_b[..., 3])
    w = np.maximum(x2 - x1, 0) if isinstance(box_a, np.ndarray) else torch.clamp(x2 - x1, min=0)
    h = np.maximum(y2 - y1, 0) if isinstance(box_a, np.ndarray) else torch.clamp(y2 - y1, min=0)
    return w * h


def _enclose_xyxy(box_a, box_b):
    """ 最小外接矩形 (xyxy) """
    x1 = np.minimum(box_a[..., 0], box_b[..., 0]) if isinstance(box_a, np.ndarray) else torch.minimum(box_a[..., 0], box_b[..., 0])
    y1 = np.minimum(box_a[..., 1], box_b[..., 1]) if isinstance(box_a, np.ndarray) else torch.minimum(box_a[..., 1], box_b[..., 1])
    x2 = np.maximum(box_a[..., 2], box_b[..., 2]) if isinstance(box_a, np.ndarray) else torch.maximum(box_a[..., 2], box_b[..., 2])
    y2 = np.maximum(box_a[..., 3], box_b[..., 3]) if isinstance(box_a, np.ndarray) else torch.maximum(box_a[..., 3], box_b[..., 3])
    return np.stack([x1, y1, x2, y2], axis=-1) if isinstance(box_a, np.ndarray) else torch.stack([x1, y1, x2, y2], dim=-1)


# --------------- 0. L2 / MSE ---------------

def mse_loss_np(pred, target, reduction="mean"):
    """ L2/MSE：逐元素平方差。pred/target 同 shape，如 (N,4)。 """
    diff = (pred - target) ** 2
    if reduction == "mean":
        return np.mean(diff)
    if reduction == "sum":
        return np.sum(diff)
    return diff


# --------------- 1. Smooth L1 ---------------

def smooth_l1_np(pred, target, beta=1.0):
    """ pred/target: (N,4) 或 (4,) 表示 [x,y,w,h] 或 [x1,y1,x2,y2] 的回归残差均可 """
    diff = np.abs(pred - target)
    return np.where(diff < beta, 0.5 * diff ** 2 / beta, diff - 0.5 * beta)


def smooth_l1_loss_np(pred, target, beta=1.0, reduction="mean"):
    """ Smooth L1 loss, reduction in ['mean','sum','none'] """
    loss = smooth_l1_np(pred, target, beta)
    if reduction == "mean":
        return np.mean(loss)
    if reduction == "sum":
        return np.sum(loss)
    return loss


# --------------- 2. IoU / GIoU / DIoU / CIoU (NumPy, xyxy) ---------------

def iou_np(pred, target, eps=1e-7):
    """ pred, target: (..., 4) xyxy. 返回 IoU 标量或数组 """
    inter = _intersection_xyxy(pred, target)
    area_a = _area_xyxy(pred)
    area_b = _area_xyxy(target)
    union = area_a + area_b - inter
    return inter / (union + eps)


def giou_np(pred, target, eps=1e-7):
    """ GIoU """
    inter = _intersection_xyxy(pred, target)
    area_a = _area_xyxy(pred)
    area_b = _area_xyxy(target)
    union = area_a + area_b - inter
    iou = inter / (union + eps)
    enclose = _enclose_xyxy(pred, target)
    area_c = _area_xyxy(enclose)
    giou = iou - (area_c - union) / (area_c + eps)
    return giou


def diou_np(pred, target, eps=1e-7):
    """ DIoU: IoU - 中心距离惩罚 """
    inter = _intersection_xyxy(pred, target)
    area_a = _area_xyxy(pred)
    area_b = _area_xyxy(target)
    union = area_a + area_b - inter
    iou = inter / (union + eps)
    # 中心点
    pred_xy = (pred[..., :2] + pred[..., 2:4]) / 2
    tgt_xy = (target[..., :2] + target[..., 2:4]) / 2
    rho2 = np.sum((pred_xy - tgt_xy) ** 2, axis=-1)
    enclose = _enclose_xyxy(pred, target)
    c2 = (enclose[..., 2] - enclose[..., 0]) ** 2 + (enclose[..., 3] - enclose[..., 1]) ** 2 + eps
    diou = iou - rho2 / c2
    return diou


def ciou_np(pred, target, eps=1e-7):
    """ CIoU: DIoU + 宽高比一致性 """
    inter = _intersection_xyxy(pred, target)
    area_a = _area_xyxy(pred)
    area_b = _area_xyxy(target)
    union = area_a + area_b - inter
    iou = inter / (union + eps)
    pred_xy = (pred[..., :2] + pred[..., 2:4]) / 2
    tgt_xy = (target[..., :2] + target[..., 2:4]) / 2
    rho2 = np.sum((pred_xy - tgt_xy) ** 2, axis=-1)
    enclose = _enclose_xyxy(pred, target)
    c2 = (enclose[..., 2] - enclose[..., 0]) ** 2 + (enclose[..., 3] - enclose[..., 1]) ** 2 + eps
    # 宽高比 v
    pred_wh = pred[..., 2:4] - pred[..., :2]
    tgt_wh = target[..., 2:4] - target[..., :2]
    v = (4 / (np.pi ** 2)) * (np.arctan(tgt_wh[..., 0] / (tgt_wh[..., 1] + eps)) - np.arctan(pred_wh[..., 0] / (pred_wh[..., 1] + eps))) ** 2
    alpha = v / (1 - iou + v + eps)
    ciou = iou - rho2 / c2 - alpha * v
    return ciou

def eiou_np(pred, target, eps=1e-7):
    """ EIoU: IoU + 中心距离 + 宽、高分别的惩罚。框格式 xyxy。 """
    inter = _intersection_xyxy(pred, target)
    area_a = _area_xyxy(pred)
    area_b = _area_xyxy(target)
    union = area_a + area_b - inter
    iou = inter / (union + eps)
    pred_xy = (pred[..., :2] + pred[..., 2:4]) / 2
    tgt_xy = (target[..., :2] + target[..., 2:4]) / 2
    rho2_center = np.sum((pred_xy - tgt_xy) ** 2, axis=-1)
    enclose = _enclose_xyxy(pred, target)
    w_c = (enclose[..., 2] - enclose[..., 0]) + eps
    h_c = (enclose[..., 3] - enclose[..., 1]) + eps
    c2 = w_c ** 2 + h_c ** 2
    pred_wh = pred[..., 2:4] - pred[..., :2]
    tgt_wh = target[..., 2:4] - target[..., :2]
    rho2_w = (pred_wh[..., 0] - tgt_wh[..., 0]) ** 2
    rho2_h = (pred_wh[..., 1] - tgt_wh[..., 1]) ** 2
    eiou = iou - rho2_center / c2 - rho2_w / (w_c ** 2) - rho2_h / (h_c ** 2)
    return eiou

def siou_np(pred, target, eps=1e-7):
    """
    SIoU 简化实现：IoU - 角度项 - 距离项 - 形状项。
    角度：预测中心与 gt 中心连线与 x 轴夹角，希望两框朝向一致。
    此处用「中心距离归一化」与「宽高比差异」近似角度与形状。
    """
    inter = _intersection_xyxy(pred, target)
    area_a = _area_xyxy(pred)
    area_b = _area_xyxy(target)
    union = area_a + area_b - inter
    iou = inter / (union + eps)
    pred_xy = (pred[..., :2] + pred[..., 2:4]) / 2
    tgt_xy = (target[..., :2] + target[..., 2:4]) / 2
    pred_wh = pred[..., 2:4] - pred[..., :2]
    tgt_wh = target[..., 2:4] - target[..., :2]
    # 中心距离
    rho2 = np.sum((pred_xy - tgt_xy) ** 2, axis=-1)
    enclose = _enclose_xyxy(pred, target)
    c2 = (enclose[..., 2] - enclose[..., 0]) ** 2 + (enclose[..., 3] - enclose[..., 1]) ** 2 + eps
    # 角度项近似：sigma = max(w_pred, h_pred)，ch = 两中心差，sin(2*theta) 相关
    sigma_w = np.maximum(pred_wh[..., 0], pred_wh[..., 1]) + eps
    ch = np.sqrt(rho2 + eps)
    sin_alpha = np.clip(ch / (sigma_w + 1e-7), 0, 1)
    angle_cost = 1 - 2 * sin_alpha ** 2  # 简化
    # 距离项
    distance_cost = rho2 / c2
    # 形状项：宽高比差异
    w_ratio = pred_wh[..., 0] / (tgt_wh[..., 0] + eps)
    h_ratio = pred_wh[..., 1] / (tgt_wh[..., 1] + eps)
    shape_cost = np.abs(w_ratio - 1) + np.abs(h_ratio - 1)
    omega = 0.25  # 形状权重
    siou = iou - 0.5 * (angle_cost * distance_cost + omega * shape_cost)
    return siou

def alpha_iou_np(pred, target, alpha=1.0, eps=1e-7, base="iou"):
    """
    α-IoU: 对 base IoU 做幂次，base in ('iou','giou','diou','ciou')。
    alpha=1 即原 IoU；alpha>1 高 IoU 处梯度更大。
    """
    if base == "iou":
        u = iou_np(pred, target, eps)
    elif base == "giou":
        u = giou_np(pred, target, eps)
    elif base == "diou":
        u = diou_np(pred, target, eps)
    elif base == "ciou":
        u = ciou_np(pred, target, eps)
    else:
        u = iou_np(pred, target, eps)
    return np.power(np.clip(u, 0, 1), alpha)

def loss_iou_np(pred, target, eps=1e-7):
    return 1 - iou_np(pred, target, eps)


def loss_giou_np(pred, target, eps=1e-7):
    return 1 - giou_np(pred, target, eps)


def loss_diou_np(pred, target, eps=1e-7):
    return 1 - diou_np(pred, target, eps)


def loss_ciou_np(pred, target, eps=1e-7):
    return 1 - ciou_np(pred, target, eps)


def loss_eiou_np(pred, target, eps=1e-7):
    return 1 - eiou_np(pred, target, eps)


def loss_siou_np(pred, target, eps=1e-7):
    return 1 - siou_np(pred, target, eps)


def loss_alpha_iou_np(pred, target, alpha=1.0, eps=1e-7, base="iou"):
    return 1 - alpha_iou_np(pred, target, alpha, eps, base)


# --------------- 3. Cross Entropy (二分类) ---------------

def ce_binary_np(p, y, eps=1e-7, reduction="mean"):
    """ 二分类交叉熵。p: 预测正类概率 (0~1), y: 真实 0/1。 """
    p = np.clip(p, eps, 1 - eps)
    ce = -(y * np.log(p) + (1 - y) * np.log(1 - p))
    if reduction == "mean":
        return np.mean(ce)
    if reduction == "sum":
        return np.sum(ce)
    return ce


# --------------- 4. Focal Loss (NumPy, 二分类) ---------------

def focal_loss_np(p, target_cls, gamma=2.0, alpha=0.25, eps=1e-7):
    """
    p: 预测正类概率 (0~1), shape (N,) 或标量
    target_cls: 真实标签 0 或 1, shape 与 p 一致
    """
    pt = np.where(target_cls == 1, p, 1 - p)
    alpha_t = np.where(target_cls == 1, alpha, 1 - alpha)
    w = alpha_t * (1 - pt) ** gamma
    ce = -np.log(np.clip(pt, eps, 1 - eps))
    return w * ce


# --------------- 5. Varifocal Loss (VFL) ---------------

def varifocal_loss_np(p, q, gamma=2.0, eps=1e-7):
    """
    p: 预测正类概率 (0~1), shape (N,)
    q: 连续质量标签 (如 IoU)，正样本 q in [0,1]，负样本 q=0
    正样本加权 q，负样本加权 1；正样本用 (q-p)^gamma，负样本用 p^gamma。
    """
    p = np.clip(p, eps, 1 - eps)
    # 正样本: -q * (q - p)^gamma * log(p)  负样本: -(1-q) * p^gamma * log(1-p)
    pos_mask = q > 0
    loss_pos = -q * np.power(np.abs(q - p), gamma) * np.log(p)
    loss_neg = -(1 - q) * np.power(p, gamma) * np.log(1 - p)
    loss = np.where(pos_mask, loss_pos, loss_neg)
    return loss


# --------------- 6. Quality Focal Loss (QFL) ---------------

def sigmoid_np(x):
    """ 数值稳定的 sigmoid """
    x = np.clip(x, -20, 20)
    return 1.0 / (1.0 + np.exp(-x))


def qfl_np(logit, y_quality, beta=2.0, eps=1e-7):
    """
    logit: 分类 logit（未 sigmoid）, shape (N,)
    y_quality: 正样本为连续质量 [0,1]（如 IoU），负样本为 0
    L_QFL = -|y - sigma(p)|^beta * ((1-y)*log(1-sigma(p)) + y*log(sigma(p)))
    """
    sigma = sigmoid_np(logit)
    sigma = np.clip(sigma, eps, 1 - eps)
    weight = np.power(np.abs(y_quality - sigma), beta)
    ce = -(1 - y_quality) * np.log(1 - sigma) - y_quality * np.log(sigma)
    return weight * ce


# --------------- 7. Distribution Focal Loss (DFL) ---------------

def dfl_np(pred_dist, y, y_min=0.0, y_max=1.0, n_bins=16, eps=1e-7):
    """
    单条边（或单维）的 DFL。
    pred_dist: (N, n_bins) 或 (n_bins,)，每个样本对 n_bins 个格点的 logit（未 softmax）
    y: (N,) 或标量，真实连续坐标，落在 [y_min, y_max]
    将 y 映射到 bin 索引：bin 范围 [0, n_bins-1]，对应 [y_min, y_max]。
    """
    pred_dist = np.asarray(pred_dist)
    y = np.asarray(y)
    if pred_dist.ndim == 1:
        pred_dist = pred_dist[np.newaxis, :]
        y = np.array([y])
    N = pred_dist.shape[0]
    # y 在 [y_min, y_max] 中的归一化位置 [0, 1]，再乘 (n_bins-1) 得到连续 bin 位置
    t = (y - y_min) / (y_max - y_min + eps)
    t = np.clip(t, 0, 1) * (n_bins - 1)  # 连续索引，如 5.3 表示在 5 和 6 之间
    i_low = np.floor(t).astype(np.int32)
    i_high = np.minimum(i_low + 1, n_bins - 1)
    i_low = np.clip(i_low, 0, n_bins - 1)
    # 线性插值权重
    w_high = t - i_low
    w_low = 1.0 - w_high
    # softmax 使 pred_dist 变为概率
    pred_dist = np.clip(pred_dist, -20, 20)
    exp_d = np.exp(pred_dist - np.max(pred_dist, axis=1, keepdims=True))
    prob = exp_d / (np.sum(exp_d, axis=1, keepdims=True) + eps)
    # DFL: -((y_high - y)*log(S_low) + (y - y_low)*log(S_high))，这里用 bin 索引
    # 在连续索引 t 下，y 对应 t，S_low = prob[i_low], S_high = prob[i_high]
    s_low = prob[np.arange(N), i_low]
    s_high = prob[np.arange(N), i_high]
    s_low = np.clip(s_low, eps, 1)
    s_high = np.clip(s_high, eps, 1)
    # DFL: -((y_high-y)*log(S_low) + (y-y_low)*log(S_high))，即 w_low*log(S_low)+w_high*log(S_high)
    loss = -(w_low * np.log(s_low) + w_high * np.log(s_high))
    return loss


# --------------- PyTorch 版本（可选） ---------------

if HAS_TORCH:

    def smooth_l1_loss_torch(pred, target, beta=1.0, reduction="mean"):
        return F.smooth_l1_loss(pred, target, beta=beta, reduction=reduction)

    def _area_xyxy_torch(box):
        w = torch.clamp(box[..., 2] - box[..., 0], min=0)
        h = torch.clamp(box[..., 3] - box[..., 1], min=0)
        return w * h

    def _inter_torch(box_a, box_b):
        x1 = torch.maximum(box_a[..., 0], box_b[..., 0])
        y1 = torch.maximum(box_a[..., 1], box_b[..., 1])
        x2 = torch.minimum(box_a[..., 2], box_b[..., 2])
        y2 = torch.minimum(box_a[..., 3], box_b[..., 3])
        w = torch.clamp(x2 - x1, min=0)
        h = torch.clamp(y2 - y1, min=0)
        return w * h

    def _enclose_torch(box_a, box_b):
        x1 = torch.minimum(box_a[..., 0], box_b[..., 0])
        y1 = torch.minimum(box_a[..., 1], box_b[..., 1])
        x2 = torch.maximum(box_a[..., 2], box_b[..., 2])
        y2 = torch.maximum(box_a[..., 3], box_b[..., 3])
        return torch.stack([x1, y1, x2, y2], dim=-1)

    def giou_torch(pred, target, eps=1e-7):
        inter = _inter_torch(pred, target)
        area_a = _area_xyxy_torch(pred)
        area_b = _area_xyxy_torch(target)
        union = area_a + area_b - inter
        iou = inter / (union + eps)
        enclose = _enclose_torch(pred, target)
        area_c = _area_xyxy_torch(enclose)
        giou = iou - (area_c - union) / (area_c + eps)
        return giou

    def diou_torch(pred, target, eps=1e-7):
        inter = _inter_torch(pred, target)
        area_a = _area_xyxy_torch(pred)
        area_b = _area_xyxy_torch(target)
        union = area_a + area_b - inter
        iou = inter / (union + eps)
        pred_xy = (pred[..., :2] + pred[..., 2:4]) / 2
        tgt_xy = (target[..., :2] + target[..., 2:4]) / 2
        rho2 = torch.sum((pred_xy - tgt_xy) ** 2, dim=-1)
        enclose = _enclose_torch(pred, target)
        c2 = (enclose[..., 2] - enclose[..., 0]) ** 2 + (enclose[..., 3] - enclose[..., 1]) ** 2 + eps
        return iou - rho2 / c2

    def ciou_torch(pred, target, eps=1e-7):
        inter = _inter_torch(pred, target)
        area_a = _area_xyxy_torch(pred)
        area_b = _area_xyxy_torch(target)
        union = area_a + area_b - inter
        iou = inter / (union + eps)
        pred_xy = (pred[..., :2] + pred[..., 2:4]) / 2
        tgt_xy = (target[..., :2] + target[..., 2:4]) / 2
        rho2 = torch.sum((pred_xy - tgt_xy) ** 2, dim=-1)
        enclose = _enclose_torch(pred, target)
        c2 = (enclose[..., 2] - enclose[..., 0]) ** 2 + (enclose[..., 3] - enclose[..., 1]) ** 2 + eps
        pred_wh = pred[..., 2:4] - pred[..., :2]
        tgt_wh = target[..., 2:4] - target[..., :2]
        v = (4 / (3.14159265 ** 2)) * (torch.atan(tgt_wh[..., 0] / (tgt_wh[..., 1] + eps)) - torch.atan(pred_wh[..., 0] / (pred_wh[..., 1] + eps))) ** 2
        alpha = v / (1 - iou + v + eps)
        return iou - rho2 / c2 - alpha * v

    class FocalLoss(nn.Module):
        def __init__(self, gamma=2.0, alpha=0.25, reduction="mean"):
            super().__init__()
            self.gamma = gamma
            self.alpha = alpha
            self.reduction = reduction

        def forward(self, logits, targets):
            """ logits: (N,C) 或 (N,), targets: (N,) 类别索引或 0/1 """
            if logits.dim() == 1:
                p = torch.sigmoid(logits)
                pt = torch.where(targets == 1, p, 1 - p)
                alpha_t = torch.where(targets == 1, self.alpha, 1 - self.alpha)
            else:
                p = F.softmax(logits, dim=1)
                pt = p.gather(1, targets.view(-1, 1)).squeeze(1)
                alpha_t = self.alpha
            w = alpha_t * (1 - pt) ** self.gamma
            ce = F.cross_entropy(logits, targets, reduction="none")
            loss = w * ce
            if self.reduction == "mean":
                return loss.mean()
            if self.reduction == "sum":
                return loss.sum()
            return loss


# --------------- 简单测试 ---------------

def _test_np():
    np.random.seed(42)
    # 随机框
    pred = np.array([[10, 10, 50, 50]], dtype=np.float32)
    target = np.array([[12, 12, 52, 48]], dtype=np.float32)

    print("=== NumPy 测试 (xyxy) ===")
    print("pred  ", pred[0])
    print("target", target[0])
    print("IoU   ", iou_np(pred, target)[0])
    print("GIoU  ", giou_np(pred, target)[0])
    print("DIoU  ", diou_np(pred, target)[0])
    print("CIoU  ", ciou_np(pred, target)[0])
    print("L_iou ", loss_iou_np(pred, target)[0])
    print("L_giou", loss_giou_np(pred, target)[0])

    # Smooth L1：用残差
    pred_xywh = _box_xyxy_to_xywh(pred)
    tgt_xywh = _box_xyxy_to_xywh(target)
    print("Smooth L1 (xywh)", smooth_l1_loss_np(pred_xywh, tgt_xywh))

    # Focal
    p = np.array([0.9, 0.1, 0.7])
    t = np.array([1, 0, 1])
    print("Focal Loss (easy,hard,easy)", focal_loss_np(p, t))

    # MSE, EIoU, SIoU, α-IoU
    print("MSE (xyxy)", mse_loss_np(pred, target))
    print("EIoU", eiou_np(pred, target)[0], "L_EIoU", loss_eiou_np(pred, target)[0])
    print("SIoU", siou_np(pred, target)[0], "L_SIoU", loss_siou_np(pred, target)[0])
    print("α-IoU (alpha=2)", alpha_iou_np(pred, target, alpha=2)[0], "L_αIoU", loss_alpha_iou_np(pred, target, alpha=2)[0])
    # CE, VFL, QFL
    print("CE binary", ce_binary_np(p, t))
    q = np.array([0.8, 0.0, 0.6])  # 质量标签：正样本用 IoU，负样本 0
    print("VFL", varifocal_loss_np(p, q))
    logit = np.array([1.5, -1.0, 0.5])
    print("QFL", qfl_np(logit, q))
    # DFL：模拟一条边的分布预测，y 在 [0,16] 对应 16 个 bin
    pred_bins = np.random.randn(2, 16).astype(np.float32)
    y_edge = np.array([5.3, 10.7])
    print("DFL", dfl_np(pred_bins, y_edge, y_min=0, y_max=15, n_bins=16))


if __name__ == "__main__":
    _test_np()
    if HAS_TORCH:
        print("\n=== PyTorch 可用，可在此扩展训练脚本 ===")
