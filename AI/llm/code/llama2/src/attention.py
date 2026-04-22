import torch
import torch.nn as nn
from .rope import repeat_kv, apply_rotary_emb, precompute_freqs_cis


class GroupQueryAttention(nn.Module):
    def __init__(self,
                 d_model,
                 n_heads,
                 n_kv_heads,
                 max_batch_size=1024,
                 max_seq_len=2048,
                 dropout=0.1):
        super(GroupQueryAttention, self).__init__()
        self.d_model = d_model
        self.n_heads = n_heads
        self.n_kv_heads = n_kv_heads
        assert d_model % n_heads == 0, "d_model must be divisible by n_heads"
        assert d_model % n_kv_heads == 0, "d_model must be divisible by n_kv_heads"
        self.head_dim = d_model // n_heads
        self.dropout = nn.Dropout(dropout)
        self.scale = self.head_dim ** -0.5

        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, n_kv_heads * self.head_dim)
        self.v_proj = nn.Linear(d_model, n_kv_heads * self.head_dim)
        self.o_proj = nn.Linear(d_model, d_model)

        self.register_buffer("cache_k",
                             torch.zeros(
                                 max_batch_size,
                                 max_seq_len,
                                 n_kv_heads,
                                 self.head_dim
                             ),
                             persistent=False)  # 不保存到磁盘，只在内存中保存
        self.register_buffer("cache_v",
                             torch.zeros(
                                 max_batch_size,
                                 max_seq_len,
                                 n_kv_heads,
                                 self.head_dim
                             ),
                             persistent=False)

    def forward(self, x, start_pos, freqs_cis, mask=None):
        B, L, D = x.shape
        q = self.q_proj(x)
        k = self.k_proj(x)
        v = self.v_proj(x)

        q = q.view(B, -1, self.n_heads, self.head_dim)
        k = k.view(B, -1, self.n_kv_heads, self.head_dim)
        v = v.view(B, -1, self.n_kv_heads, self.head_dim)

        # 应用相对位置编码
        q, k = apply_rotary_emb(q, k, freqs_cis)

        self.cache_k = self.cache_k.to(q)
        self.cache_v = self.cache_v.to(q)

        # kv cache
        if self.cache_k is not None and start_pos > 0:
            self.cache_k[:B, :start_pos] = k
            self.cache_v[:B, :start_pos] = v
            k = self.cache_k[:B, :start_pos + L]
            v = self.cache_v[:B, :start_pos + L]

        # shape (B, L, n_heads, head_dim)
        k = repeat_kv(k, self.n_heads // self.n_kv_heads)
        # shape (B, L, n_heads, head_dim)
        v = repeat_kv(v, self.n_heads // self.n_kv_heads)

        q = q.transpose(1, 2)
        k = k.transpose(1, 2)
        v = v.transpose(1, 2)

        attn_weights = torch.matmul(q, k.transpose(-2, -1)) * self.scale

        if mask is not None:
            attn_weights = attn_weights + mask

        attn_weights = attn_weights.softmax(dim=-1)
        attn_weights = self.dropout(attn_weights)
        attn_output = torch.matmul(attn_weights, v)

        attn_output = attn_output.transpose(
            1, 2).contiguous().view(B, -1, D)
        attn_output = self.o_proj(attn_output)
        return attn_output


if __name__ == "__main__":
    torch.manual_seed(1234)
    x = torch.randn(4, 10, 512)
    gqa = GroupQueryAttention(d_model=512, n_heads=8,
                              n_kv_heads=4, max_batch_size=32, max_seq_len=10)
    freqs_cis = precompute_freqs_cis(gqa.head_dim, 10)
    output = gqa(x, 0, freqs_cis)
    print(output.shape)
