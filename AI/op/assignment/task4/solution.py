"""TileLang Flash Attention (forward) on MetaX C500 / MACA.

Layout: Q/K/V/O = [B, H, S, D] float16, accumulate in float32.
Math:   O = softmax(scale * Q @ K^T + mask) @ V
        scale = 1 / sqrt(D)
        causal mask: q_idx + (Sk - Sq) >= k_idx  (supports decode with cache)
        GQA: H_q % H_kv == 0, K/V head = q_head // groups
"""

import functools

import torch
import torch.nn.functional as F
import tilelang
import tilelang.language as T

# log2(e): fold into scale so T.exp2(x * scale) == exp(x / sqrt(D))
LOG2E = 1.44269504
# C500 per-CTA shared memory is 64KB. TileLang adds ~2KB alignment on top of buffers.
C500_SMEM_LIMIT = 65536
SMEM_PAD = 2048
FP16_BYTES = 2


def _align_up(value: int, align: int) -> int:
    return (value + align - 1) // align * align


def _pad_seq(tensor: torch.Tensor, seq_len: int, aligned: int) -> torch.Tensor:
    if seq_len == aligned:
        return tensor
    return F.pad(tensor, (0, 0, 0, aligned - seq_len))


@tilelang.jit(
    out_idx=[3],
    pass_configs={
        tilelang.PassConfigKey.TL_ENABLE_FAST_MATH: True,
    },
)
def _flashattn_factory(
    batch,
    heads,
    seq_q,
    seq_kv,
    dim,
    is_causal,
    valid_seq_q,
    valid_seq_kv,
    groups,
    block_M,
    block_N,
    num_stages,
    threads,
):
    """Lazy-mode factory. Shapes are compile-time constants (padded).

    valid_seq_* are the original unpadded lengths used only for masking.
    """
    scale = (1.0 / dim) ** 0.5 * LOG2E
    past_len = valid_seq_kv - valid_seq_q
    q_shape = [batch, heads, seq_q, dim]
    kv_shape = [batch, heads // groups, seq_kv, dim]
    dtype = T.float16
    accum_dtype = T.float32

    @T.prim_func
    def main(
        Q: T.Tensor(q_shape, dtype),
        K: T.Tensor(kv_shape, dtype),
        V: T.Tensor(kv_shape, dtype),
        Output: T.Tensor(q_shape, dtype),
    ):
        # Grid: bx = Q-tile along sequence, by = head, bz = batch.
        # FullRow so each warp owns whole score rows and can reduce max/sum locally.
        with T.Kernel(T.ceildiv(seq_q, block_M), heads, batch, threads=threads) as (bx, by, bz):
            Q_shared = T.alloc_shared([block_M, dim], dtype)
            K_shared = T.alloc_shared([block_N, dim], dtype)
            V_shared = T.alloc_shared([block_N, dim], dtype)
            acc_s = T.alloc_fragment([block_M, block_N], accum_dtype)
            acc_s_cast = T.alloc_fragment([block_M, block_N], dtype)
            acc_o = T.alloc_fragment([block_M, dim], accum_dtype)
            scores_max = T.alloc_fragment([block_M], accum_dtype)
            scores_max_prev = T.alloc_fragment([block_M], accum_dtype)
            scores_scale = T.alloc_fragment([block_M], accum_dtype)
            scores_sum = T.alloc_fragment([block_M], accum_dtype)
            logsum = T.alloc_fragment([block_M], accum_dtype)

            T.copy(Q[bz, by, bx * block_M : (bx + 1) * block_M, :], Q_shared)
            T.fill(acc_o, 0)
            T.fill(logsum, 0)
            T.fill(scores_max, -T.infinity(accum_dtype))

            loop_range = (
                T.min(
                    T.ceildiv(seq_kv, block_N),
                    T.ceildiv((bx + 1) * block_M + past_len, block_N),
                )
                if is_causal
                else T.ceildiv(seq_kv, block_N)
            )

            for k in T.Pipelined(loop_range, num_stages=num_stages):
                T.copy(K[bz, by // groups, k * block_N : (k + 1) * block_N, :], K_shared)
                # Mask goes into acc_s *before* GEMM: valid=0, invalid=-inf.
                # T.gemm accumulates, so valid cells become QK^T and masked stay -inf.
                if is_causal:
                    for i, j in T.Parallel(block_M, block_N):
                        q_idx = bx * block_M + i + past_len
                        k_idx = k * block_N + j
                        acc_s[i, j] = T.if_then_else(
                            k_idx >= valid_seq_kv,
                            -T.infinity(acc_s.dtype),
                            T.if_then_else(q_idx >= k_idx, 0, -T.infinity(acc_s.dtype)),
                        )
                else:
                    for i, j in T.Parallel(block_M, block_N):
                        acc_s[i, j] = T.if_then_else(
                            k * block_N + j < valid_seq_kv,
                            0,
                            -T.infinity(acc_s.dtype),
                        )
                T.gemm(Q_shared, K_shared, acc_s, transpose_B=True, policy=T.GemmWarpPolicy.FullRow)

                # Online softmax: rescale previous (max, sum, acc_o) onto the new max.
                T.copy(scores_max, scores_max_prev)
                T.fill(scores_max, -T.infinity(accum_dtype))
                T.reduce_max(acc_s, scores_max, dim=1, clear=False)
                for i in T.Parallel(block_M):
                    scores_max[i] = T.max(scores_max[i], scores_max_prev[i])
                for i in T.Parallel(block_M):
                    scores_scale[i] = T.exp2(scores_max_prev[i] * scale - scores_max[i] * scale)
                for i, j in T.Parallel(block_M, block_N):
                    acc_s[i, j] = T.exp2(acc_s[i, j] * scale - scores_max[i] * scale)
                T.reduce_sum(acc_s, scores_sum, dim=1)
                for i in T.Parallel(block_M):
                    logsum[i] = logsum[i] * scores_scale[i] + scores_sum[i]
                T.copy(acc_s, acc_s_cast)
                for i, j in T.Parallel(block_M, dim):
                    acc_o[i, j] *= scores_scale[i]

                T.copy(V[bz, by // groups, k * block_N : (k + 1) * block_N, :], V_shared)
                T.gemm(acc_s_cast, V_shared, acc_o, policy=T.GemmWarpPolicy.FullRow)

            for i, j in T.Parallel(block_M, dim):
                acc_o[i, j] /= logsum[i]
            T.copy(acc_o, Output[bz, by, bx * block_M : (bx + 1) * block_M, :])

    return main


@functools.lru_cache(maxsize=None)
def compile_flashattn(
    batch: int,
    heads: int,
    seq_q: int,
    seq_kv: int,
    dim: int,
    is_causal: bool,
    valid_seq_q: int,
    valid_seq_kv: int,
    groups: int,
    block_M: int,
    block_N: int,
    num_stages: int,
    threads: int,
):
    return _flashattn_factory(
        batch,
        heads,
        seq_q,
        seq_kv,
        dim,
        is_causal,
        valid_seq_q,
        valid_seq_kv,
        groups,
        block_M,
        block_N,
        num_stages,
        threads,
    )


def estimate_smem(block_M, block_N, dim, num_stages):
    """实测：Pipelined 会把循环里的 K 和 V 都按 stage 加倍，外加约 2KB。

    128x32 / D=128 / stages=2 → 67584，正好是 64KB+2KB。
    """
    stages = max(int(num_stages), 1)
    return FP16_BYTES * dim * (block_M + 2 * stages * block_N) + SMEM_PAD


def fit_flash_config(block_M, block_N, dim, num_stages, threads):
    """选出能塞进 64KB 的最大 MMA tile。D>=128 时优先 128x32。"""
    if dim >= 128:
        block_M = max(int(block_M), 128)
        block_N = min(int(block_N), 32)
        threads = max(int(threads), 256)
    best = None
    for stages in range(max(int(num_stages), 1), 0, -1):
        m = int(block_M)
        while m >= 32:
            n = int(block_N)
            while n >= 16:
                if estimate_smem(m, n, dim, stages) <= C500_SMEM_LIMIT:
                    thr = threads if m >= 128 else min(int(threads), 128)
                    key = (m * n, n, m, stages)
                    if best is None or key > best[0]:
                        best = (key, (m, n, stages, thr))
                n //= 2
            m //= 2
    if best is None:
        raise RuntimeError(
            f"Flash Attention cannot fit C500 64KB smem: dim={dim} "
            f"requested {block_M}x{block_N} stages={num_stages}"
        )
    return best[1]


def tl_flash_attn(
    q: torch.Tensor,
    k: torch.Tensor,
    v: torch.Tensor,
    is_causal: bool = True,
    block_M: int = 64,
    block_N: int = 64,
    num_stages: int = 1,
    threads: int = 128,
):
    """Run Flash Attention. Q/K/V are [B, H, S, D] float16 (K/V heads may be fewer)."""
    if q.dtype != torch.float16 or k.dtype != torch.float16 or v.dtype != torch.float16:
        raise TypeError("tl_flash_attn expects float16 Q/K/V")
    if q.dim() != 4 or k.dim() != 4 or v.dim() != 4:
        raise ValueError("tl_flash_attn expects [B, H, S, D] tensors")
    if k.shape != v.shape:
        raise ValueError("K and V must have the same shape")
    if q.shape[0] != k.shape[0] or q.shape[-1] != k.shape[-1]:
        raise ValueError("Q/K batch and head_dim must match")
    if q.shape[1] % k.shape[1] != 0:
        raise ValueError("num_q_heads must be divisible by num_kv_heads")

    batch, heads, seq_q, dim = q.shape
    _, kv_heads, seq_kv, _ = k.shape
    groups = heads // kv_heads
    if seq_kv < seq_q:
        raise ValueError("seq_kv must be >= seq_q")

    block_M, block_N, num_stages, threads = fit_flash_config(
        block_M, block_N, dim, num_stages, threads
    )

    seq_q_pad = _align_up(seq_q, block_M)
    seq_kv_pad = _align_up(seq_kv, block_N)
    q_p = _pad_seq(q.contiguous(), seq_q, seq_q_pad)
    k_p = _pad_seq(k.contiguous(), seq_kv, seq_kv_pad)
    v_p = _pad_seq(v.contiguous(), seq_kv, seq_kv_pad)

    kernel = compile_flashattn(
        batch,
        heads,
        seq_q_pad,
        seq_kv_pad,
        dim,
        is_causal,
        seq_q,
        seq_kv,
        groups,
        block_M,
        block_N,
        num_stages,
        threads,
    )
    out = kernel(q_p, k_p, v_p)
    return out[:, :, :seq_q, :]


def tl_flash_attn_v1(q, k, v, is_causal=True):
    """Baseline: 64x64 tiles, 1-stage pipeline, 128 threads (2 waves on C500)."""
    return tl_flash_attn(q, k, v, is_causal, block_M=64, block_N=64, num_stages=1, threads=128)


def tl_flash_attn_v2(q, k, v, is_causal=True):
    """Opt A: keep 64x64 tiles, raise pipeline stages to 2 (overlap copy / MMA)."""
    return tl_flash_attn(q, k, v, is_causal, block_M=64, block_N=64, num_stages=2, threads=128)


def tl_flash_attn_v3(q, k, v, is_causal=True):
    """Opt B: 128x128 tiles + 256 threads (fewer KV-loop trips, more MMA per CTA)."""
    return tl_flash_attn(q, k, v, is_causal, block_M=128, block_N=128, num_stages=1, threads=256)


tl_flash_attn_default = tl_flash_attn_v1


def official_flash_attn(q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, is_causal: bool = True):
    """官方 flash_attn。Q/K/V 为 [B, H, S, D]；GQA 时 K/V heads 可以更少。"""
    try:
        from flash_attn import flash_attn_func

        # 官方接口是 [B, S, H, D]
        out = flash_attn_func(
            q.transpose(1, 2),
            k.transpose(1, 2),
            v.transpose(1, 2),
            causal=is_causal,
        )
        return out.transpose(1, 2).contiguous()
    except ImportError:
        return torch.nn.functional.scaled_dot_product_attention(
            q, k, v, is_causal=is_causal
        )


def ref_flash_attn(q: torch.Tensor, k: torch.Tensor, v: torch.Tensor, is_causal: bool = True):
    """对比基准：官方 flash_attn。"""
    return official_flash_attn(q, k, v, is_causal)


def check_flash_attn(out, q, k, v, is_causal=True, atol=1e-2, rtol=1e-2):
    ref = official_flash_attn(q, k, v, is_causal)
    return torch.allclose(out, ref, atol=atol, rtol=rtol)
