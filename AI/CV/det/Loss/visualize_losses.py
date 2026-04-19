# -*- coding: utf-8 -*-
"""
目标检测 Loss 可视化脚本
生成：IoU 族损失随预测框变化曲线、Focal Loss 权重曲线等。
运行：python visualize_losses.py
图片保存在当前目录。
"""

from __future__ import division, print_function
import numpy as np
import sys
import os

# 将当前目录加入 path，便于引用 loss_functions
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loss_functions import (
    iou_np, giou_np, diou_np, ciou_np,
    loss_iou_np, loss_giou_np, loss_diou_np, loss_ciou_np,
    smooth_l1_loss_np, focal_loss_np,
    _box_xyxy_to_xywh,
)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def _ensure_dir():
    d = os.path.dirname(os.path.abspath(__file__))
    os.chdir(d)


def plot_iou_family_1d():
    """ 固定真实框，预测框沿 x 轴平移，绘制 IoU / GIoU / DIoU / CIoU 及对应 loss """
    _ensure_dir()
    # 真实框 [x1,y1,x2,y2]，100x100，中心 (100, 100)
    gt = np.array([[50, 50, 150, 150]], dtype=np.float32)
    # 预测框：宽高比与 gt 差异大 (40x160)，使 CIoU 的形状项 v 明显，CIoU 与 DIoU 分离
    cx = np.linspace(0, 200, 201)
    w_pred, h_pred = 40.0, 160.0
    x1 = cx - w_pred / 2
    x2 = cx + w_pred / 2
    y1 = 100 - h_pred / 2
    y2 = 100 + h_pred / 2
    pred = np.stack([x1, np.full_like(cx, y1), x2, np.full_like(cx, y2)], axis=1).astype(np.float32)
    gt_tile = np.tile(gt, (len(pred), 1))

    iou = iou_np(pred, gt_tile)
    giou = giou_np(pred, gt_tile)
    diou = diou_np(pred, gt_tile)
    ciou = ciou_np(pred, gt_tile)
    liou = loss_iou_np(pred, gt_tile)
    lgiou = loss_giou_np(pred, gt_tile)
    ldiou = loss_diou_np(pred, gt_tile)
    lciou = loss_ciou_np(pred, gt_tile)

    # 显式颜色 + 线型，便于区分；增加第三子图显示 DIoU - CIoU（形状惩罚）
    fig, axes = plt.subplots(3, 1, figsize=(10, 10))
    axes[0].plot(cx, iou, label="IoU", color="C0", linestyle="-", linewidth=2)
    axes[0].plot(cx, giou, label="GIoU", color="C1", linestyle="--", linewidth=2)
    axes[0].plot(cx, diou, label="DIoU", color="C2", linestyle="-.", linewidth=2)
    axes[0].plot(cx, ciou, label="CIoU", color="C3", linestyle=":", linewidth=2)
    axes[0].set_ylabel("Score (higher better)")
    axes[0].set_xlabel("Pred box center x")
    axes[0].legend(loc="best", framealpha=0.9)
    axes[0].set_title("IoU family: score vs horizontal shift (pred 40x160, gt 100x100)")
    axes[0].grid(True, alpha=0.3)
    axes[0].axvline(100, color="gray", linestyle="--", alpha=0.7)

    axes[1].plot(cx, liou, label="L_IoU", color="C0", linestyle="-", linewidth=2)
    axes[1].plot(cx, lgiou, label="L_GIoU", color="C1", linestyle="--", linewidth=2)
    axes[1].plot(cx, ldiou, label="L_DIoU", color="C2", linestyle="-.", linewidth=2)
    axes[1].plot(cx, lciou, label="L_CIoU", color="C3", linestyle=":", linewidth=2)
    axes[1].set_ylabel("Loss (lower better)")
    axes[1].set_xlabel("Pred box center x")
    axes[1].legend(loc="best", framealpha=0.9)
    axes[1].set_title("IoU family: loss vs horizontal shift (pred 40x160, gt 100x100)")
    axes[1].grid(True, alpha=0.3)
    axes[1].axvline(100, color="gray", linestyle="--", alpha=0.7)

    # 第三子图：DIoU - CIoU = 形状惩罚项，使 CIoU 与 DIoU 的差异可见
    axes[2].plot(cx, diou - ciou, color="C4", linewidth=2, label="DIoU - CIoU (shape penalty)")
    axes[2].axhline(0, color="gray", linestyle="--", alpha=0.5)
    axes[2].set_ylabel("DIoU - CIoU")
    axes[2].set_xlabel("Pred box center x")
    axes[2].legend(loc="best", framealpha=0.9)
    axes[2].set_title("CIoU adds shape penalty: CIoU = DIoU - alpha*v (v=aspect ratio term)")
    axes[2].grid(True, alpha=0.3)
    axes[2].axvline(100, color="gray", linestyle="--", alpha=0.7)
    plt.tight_layout()
    out = "iou_family_1d.png"
    plt.savefig(out, dpi=120)
    plt.close()
    print("已保存:", out)


def plot_smooth_l1_vs_iou():
    """ 同一平移设定下，Smooth L1（基于中心+宽高）与 IoU Loss 对比 """
    _ensure_dir()
    gt = np.array([[50, 50, 150, 150]], dtype=np.float32)
    cx = np.linspace(50, 150, 101)
    w, h = 100, 100
    pred_xyxy = np.stack([
        cx - w / 2, np.full_like(cx, 50),
        cx + w / 2, np.full_like(cx, 150)
    ], axis=1).astype(np.float32)
    gt_tile = np.tile(gt, (len(pred_xyxy), 1))

    pred_xywh = _box_xyxy_to_xywh(pred_xyxy)
    gt_xywh = _box_xyxy_to_xywh(gt_tile)
    sl1 = np.array([smooth_l1_loss_np(pred_xywh[i:i+1], gt_xywh[i:i+1]) for i in range(len(pred_xywh))])
    liou = loss_iou_np(pred_xyxy, gt_tile)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(cx, sl1, label="Smooth L1(xywh)")
    ax.plot(cx, liou, label="L_IoU")
    ax.set_xlabel("Pred box center x")
    ax.set_ylabel("Loss")
    ax.legend()
    ax.set_title("Smooth L1 vs IoU Loss (pred box shifts along x)")
    ax.grid(True, alpha=0.3)
    out = "smooth_l1_vs_iou.png"
    plt.savefig(out, dpi=120)
    plt.close()
    print("已保存:", out)


def plot_focal_weight():
    """ Focal Loss 中 (1-pt)^gamma 随 pt 变化，展示对易样本的降权 """
    _ensure_dir()
    pt = np.linspace(0.01, 0.99, 99)
    for g in [0, 1, 2, 5]:
        w = (1 - pt) ** g
        plt.plot(pt, w, label=r"$\gamma$={}".format(g))
    plt.xlabel(r"$p_t$ (prob of correct class)")
    plt.ylabel(r"$(1-p_t)^\gamma$ (sample weight)")
    plt.title("Focal Loss weight: easy samples (pt->1) down-weighted")
    plt.legend()
    plt.grid(True, alpha=0.3)
    out = "focal_weight_curve.png"
    plt.savefig(out, dpi=120)
    plt.close()
    print("已保存:", out)


def plot_iou_2d_heatmap():
    """ 预测框在 2D 平面上平移时，IoU 与 GIoU 的热力图（中心对齐处最大） """
    _ensure_dir()
    gt = np.array([[50, 50, 150, 150]], dtype=np.float32)
    xs = np.linspace(0, 200, 41)
    ys = np.linspace(0, 200, 41)
    XX, YY = np.meshgrid(xs, ys)
    iou_grid = np.zeros_like(XX)
    giou_grid = np.zeros_like(XX)
    for i in range(XX.shape[0]):
        for j in range(XX.shape[1]):
            cx, cy = XX[i, j], YY[i, j]
            pred = np.array([[cx - 50, cy - 50, cx + 50, cy + 50]], dtype=np.float32)
            iou_grid[i, j] = iou_np(pred, gt)[0]
            giou_grid[i, j] = giou_np(pred, gt)[0]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    im0 = axes[0].pcolormesh(XX, YY, iou_grid, shading="auto", cmap="viridis")
    axes[0].set_xlabel("Pred box center x")
    axes[0].set_ylabel("Pred box center y")
    axes[0].set_title("IoU (gt center 100,100)")
    axes[0].plot(100, 100, "r*", markersize=12)
    plt.colorbar(im0, ax=axes[0])

    im1 = axes[1].pcolormesh(XX, YY, giou_grid, shading="auto", cmap="viridis")
    axes[1].set_xlabel("Pred box center x")
    axes[1].set_ylabel("Pred box center y")
    axes[1].set_title("GIoU (gt center 100,100)")
    axes[1].plot(100, 100, "r*", markersize=12)
    plt.colorbar(im1, ax=axes[1])
    plt.tight_layout()
    out = "iou_giou_2d_heatmap.png"
    plt.savefig(out, dpi=120)
    plt.close()
    print("已保存:", out)


def main():
    if not HAS_MATPLOTLIB:
        print("请安装 matplotlib: pip install matplotlib")
        return
    plot_iou_family_1d()
    plot_smooth_l1_vs_iou()
    plot_focal_weight()
    plot_iou_2d_heatmap()
    print("全部可视化已生成。")


if __name__ == "__main__":
    main()
