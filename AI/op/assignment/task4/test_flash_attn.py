import pytest
import torch

from solution import official_flash_attn, tl_flash_attn, tl_flash_attn_v1

ATOL = 1e-2
RTOL = 1e-2


def _run(q, k, v, is_causal, **kwargs):
    out = tl_flash_attn(q, k, v, is_causal=is_causal, **kwargs)
    ref = official_flash_attn(q, k, v, is_causal=is_causal)
    torch.testing.assert_close(out, ref, atol=ATOL, rtol=RTOL)
    return out, ref


@pytest.mark.parametrize("is_causal", [False, True])
@pytest.mark.parametrize(
    "batch,heads,seq,dim",
    [
        (1, 1, 64, 64),
        (2, 4, 128, 64),
        (1, 8, 256, 64),
    ],
)
def test_aligned_shapes(batch, heads, seq, dim, is_causal):
    q = torch.randn(batch, heads, seq, dim, device="cuda", dtype=torch.float16)
    k = torch.randn_like(q)
    v = torch.randn_like(q)
    _run(q, k, v, is_causal)


@pytest.mark.parametrize("is_causal", [False, True])
@pytest.mark.parametrize("seq", [17, 33, 65, 127])
def test_unaligned_seq(seq, is_causal):
    q = torch.randn(1, 2, seq, 64, device="cuda", dtype=torch.float16)
    k = torch.randn_like(q)
    v = torch.randn_like(q)
    _run(q, k, v, is_causal)


def test_decode_seq_q_lt_seq_kv():
    q = torch.randn(1, 4, 16, 64, device="cuda", dtype=torch.float16)
    k = torch.randn(1, 4, 80, 64, device="cuda", dtype=torch.float16)
    v = torch.randn_like(k)
    _run(q, k, v, is_causal=True)


def test_gqa():
    q = torch.randn(1, 8, 64, 64, device="cuda", dtype=torch.float16)
    k = torch.randn(1, 2, 64, 64, device="cuda", dtype=torch.float16)
    v = torch.randn_like(k)
    _run(q, k, v, is_causal=True)


def test_extreme_values():
    q = torch.tensor(
        [[[[1000.0, -1000.0, 0.0, 1.0] + [0.0] * 60]]],
        device="cuda",
        dtype=torch.float16,
    ).expand(1, 1, 4, 64).contiguous()
    k = q.clone()
    v = torch.randn(1, 1, 4, 64, device="cuda", dtype=torch.float16)
    out, ref = _run(q, k, v, is_causal=True, block_M=64, block_N=64)
    assert torch.isfinite(out).all()
    assert torch.isfinite(ref).all()


def test_v1_entrypoint():
    q = torch.randn(1, 2, 64, 64, device="cuda", dtype=torch.float16)
    k = torch.randn_like(q)
    v = torch.randn_like(q)
    out = tl_flash_attn_v1(q, k, v, is_causal=True)
    ref = official_flash_attn(q, k, v, is_causal=True)
    torch.testing.assert_close(out, ref, atol=ATOL, rtol=RTOL)
