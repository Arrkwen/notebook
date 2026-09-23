import time

import torch

from solution import (
    check_flash_attn,
    official_flash_attn,
    tl_flash_attn_v1,
    tl_flash_attn_v2,
    tl_flash_attn_v3,
)

CASES = [
    # B, H, S, D, causal；S 从非对齐小序列到 4096，并覆盖更大 B/H 与非因果
    (1, 8, 128, 64, True),
    (1, 64, 128, 64, True),
    (1, 64, 512, 64, True),
    (1, 64, 512, 128, True),
    (8, 64, 512, 128, True),
    (8, 64, 1024, 128, True),
    (8, 64, 4096, 128, True),
    (32, 64, 4096, 128, True),
    (32, 64, 4096, 128, False),
    
]

VARIANTS = [
    ("v1", tl_flash_attn_v1),
    ("v2", tl_flash_attn_v2),
    ("v3", tl_flash_attn_v3),
]


def timed(fn, warmup=10, repeat=50):
    for _ in range(warmup):
        fn()
    torch.cuda.synchronize()
    start = time.perf_counter()
    for _ in range(repeat):
        fn()
    torch.cuda.synchronize()
    return (time.perf_counter() - start) * 1e3 / repeat


def bench_iters(flops):
    if flops >= 1e14:
        return 1, 3
    if flops >= 1e13:
        return 2, 5
    if flops >= 1e12:
        return 5, 10
    return 10, 50


def qkv_nbytes(batch, heads, seq, dim):
    return 3 * batch * heads * seq * dim * 2


def gpu_free_bytes():
    free, _total = torch.cuda.mem_get_info()
    return int(free)


def pytorch_attn(q, k, v, is_causal):
    return official_flash_attn(q, k, v, is_causal)


def attn_flops(batch, heads, seq, dim, causal):
    # QK^T + PV, each 2*B*H*S*S*D; causal 大约扫一半
    flops = 4.0 * batch * heads * seq * seq * dim
    return flops * 0.5 if causal else flops


def attn_bytes(batch, heads, seq, dim, causal):
    # 有效 HBM：读 Q 一遍、写 O 一遍；K/V 非因果各一遍，因果约一半
    elem = 2  # float16
    q_o = 2 * batch * heads * seq * dim * elem
    kv = 2 * batch * heads * seq * dim * elem
    if causal:
        kv *= 0.5
    return q_o + kv


def gbps(nbytes, ms):
    return nbytes / ms / 1e6


def tflops(flops, ms):
    return flops / ms / 1e9


def _disp_len(text):
    return sum(2 if ord(ch) > 127 else 1 for ch in text)


def cell(text, width, align="left"):
    text = str(text)
    pad = max(width - _disp_len(text), 0)
    if align == "right":
        return " " * pad + text
    if align == "center":
        left = pad // 2
        return " " * left + text + " " * (pad - left)
    return text + " " * pad


COLS = [
    ("版本", 4, "left"),
    ("规模", 18, "left"),
    ("因果", 4, "center"),
    ("正确", 4, "center"),
    ("TL(ms)", 8, "right"),
    ("FA(ms)", 8, "right"),
    ("TL算力", 10, "right"),
    ("FA算力", 10, "right"),
    ("TL带宽", 10, "right"),
    ("FA带宽", 10, "right"),
    ("加速", 7, "right"),
]


def row(values):
    return "  ".join(
        cell(value, width, align) for value, (_, width, align) in zip(values, COLS)
    )


free0, total0 = torch.cuda.mem_get_info()
print(f"GPU 可见显存 {total0 / 1024**3:.1f} GiB，当前空闲 {free0 / 1024**3:.1f} GiB")
print("对照：官方 flash_attn（flash_attn.flash_attn_func）")
print(row(name for name, _, _ in COLS))
print("-" * _disp_len(row(name for name, _, _ in COLS)))

for case_idx, (batch, heads, seq, dim, causal) in enumerate(CASES):
    torch.cuda.empty_cache()
    size = f"{batch}x{heads}x{seq}x{dim}"
    need = qkv_nbytes(batch, heads, seq, dim)
    # QKV + 一份输出 + flash_attn workspace，预留 2GiB
    if gpu_free_bytes() < need + 2 * 1024**3:
        print()
        print(f"跳过 {size}：QKV 约 {need / 1024**3:.1f} GiB，空闲 {gpu_free_bytes() / 1024**3:.1f} GiB")
        continue

    q = torch.randn(batch, heads, seq, dim, device="cuda", dtype=torch.float16)
    k = torch.randn_like(q)
    v = torch.randn_like(q)
    flops = attn_flops(batch, heads, seq, dim, causal)
    nbytes = attn_bytes(batch, heads, seq, dim, causal)
    warmup, repeat = bench_iters(flops)
    try:
        pt_ms = timed(lambda: pytorch_attn(q, k, v, causal), warmup, repeat)
    except torch.OutOfMemoryError:
        torch.cuda.empty_cache()
        pt_ms = None
    if case_idx:
        print()
    for name, fn in VARIANTS:
        try:
            out = fn(q, k, v, is_causal=causal)
            ok = check_flash_attn(out, q, k, v, is_causal=causal)
            del out
            tl_ms = timed(lambda: fn(q, k, v, is_causal=causal), warmup, repeat)
        except torch.OutOfMemoryError:
            torch.cuda.empty_cache()
            print(row([name, size, "是" if causal else "否", "OOM", "-", "-", "-", "-", "-", "-", "-"]))
            continue
        pt_ms_s = "-" if pt_ms is None else f"{pt_ms:.3f}"
        pt_flops_s = "-" if pt_ms is None else f"{tflops(flops, pt_ms):.2f} TF"
        pt_bw_s = "-" if pt_ms is None else f"{gbps(nbytes, pt_ms):.1f} GB/s"
        speed_s = "-" if pt_ms is None else f"{pt_ms / tl_ms:.2f}x"
        print(
            row(
                [
                    name,
                    size,
                    "是" if causal else "否",
                    "是" if ok else "否",
                    f"{tl_ms:.3f}",
                    pt_ms_s,
                    f"{tflops(flops, tl_ms):.2f} TF",
                    pt_flops_s,
                    f"{gbps(nbytes, tl_ms):.1f} GB/s",
                    pt_bw_s,
                    speed_s,
                ]
            )
        )
        if not ok:
            raise SystemExit(f"correctness failed: {name} {size}")
    del q, k, v
    torch.cuda.empty_cache()
