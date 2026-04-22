import torch


def precompute_freqs_cis(dim: int, max_seq_len: int = 4, theta: float = 10000.0):
    # 1 计算频率: 1/theta^(2i/dim): shape (dim // 2)
    freqs = 1.0 / (theta ** (torch.arange(0, dim, 2)
                             [: (dim // 2)].float() / dim))
    # 2 计算相位(幅度角): 角频率 * 位置(t) : shape (max_seq_len, dim // 2)
    freqs = torch.outer(torch.arange(max_seq_len, device=freqs.device),
                        freqs).float()  # torch.outer 计算两个向量的外积
    # 3 使用极坐标表示: 模长为1，相位为幅度角，即将vector的每个分量映射到复平面上，长度都为1，但是具备不同的角度
    freqs_cis = torch.polar(torch.ones_like(freqs), freqs)
    return freqs_cis


# 保留max_seq_len和head_dim，其他维度都为1(batch_size, n_heads)
def reshape_for_broadcast(freqs_cis: torch.Tensor, x: torch.Tensor) -> torch.Tensor:
    ndim = x.ndim
    shape = [d if i == 1 or i == ndim -
             1 else 1 for i, d in enumerate(x.shape)]
    return freqs_cis.view(*shape)


def apply_rotary_emb(xq: torch.Tensor,
                     xk: torch.Tensor,
                     freqs_cis: torch.Tensor) -> torch.Tensor:
    # 对最后一个纬度：head_dim进行拆分，相邻的两个向量拆成实部和虚部
    # shape (batch_size, seq_len, n_heads, head_dim // 2)
    xq_ = torch.view_as_complex(xq.float().reshape(*xq.shape[:-1], -1, 2))
    xk_ = torch.view_as_complex(xk.float().reshape(*xk.shape[:-1], -1, 2))

    # 保留max_seq_len和head_dim，其他维度都为1(batch_size, n_heads)
    freqs_q_cis = reshape_for_broadcast(freqs_cis, xq_)
    freqs_k_cis = reshape_for_broadcast(freqs_cis, xk_)

    # view_as_real: 将复数转换为实数，shape (batch_size, seq_len, n_heads, head_dim // 2, 2)
    # flatten: 将最后一个纬度展平，shape (batch_size, seq_len, n_heads, head_dim)
    xq_ = torch.view_as_real(xq_ * freqs_q_cis).flatten(3)
    xk_ = torch.view_as_real(xk_ * freqs_k_cis).flatten(3)
    return xq_.type(xq.dtype), xk_.type(xk.dtype)


def repeat_kv(x: torch.Tensor, n_rep: int) -> torch.Tensor:
    batch_size, seq_len, n_kv_heads, head_dim = x.shape
    if n_rep == 1:
        return x

    return (x[:, :, :, None, :]
            .expand(batch_size, seq_len, n_kv_heads, n_rep, head_dim)
            .reshape(batch_size, seq_len, n_kv_heads*n_rep, head_dim))


if __name__ == "__main__":
    torch.manual_seed(1234)
    freqs_cis = precompute_freqs_cis(8)
    print(freqs_cis)

    xq = torch.randn(2, 4, 2, 8)
    xk = torch.randn(2, 4, 2, 8)
    xq, xk = apply_rotary_emb(xq, xk, freqs_cis)
    print(f"xq.shape: {xq.shape}")
    print(f"xk.shape: {xk.shape}")
