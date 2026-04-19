import torch

import torch.nn as nn

class MultiHeadAttention(nn.Module):
    def __init__(self, d_model, num_heads, dropout=0.1): # d_model: 输入的维度， num_heads: 头的数量
        super(MultiHeadAttention, self).__init__()
        
        assert d_model % num_heads == 0
        self.d_model = d_model
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads

        self.q_proj = nn.Linear(d_model, d_model)
        self.k_proj = nn.Linear(d_model, d_model)
        self.v_proj = nn.Linear(d_model, d_model)
        self.o_proj = nn.Linear(d_model, d_model)

        self.dropout = nn.Dropout(dropout)
        self.scale = self.head_dim ** -0.5

    def forward(self, q, k, v, mask=None) -> torch.Tensor:
        B, _, N = q.shape  # [B, L, N] -> [batch_size, sequence_length, d_model]
        q = self.q_proj(q)
        k = self.k_proj(k)
        v = self.v_proj(v)

        q = q.view(B, -1, self.num_heads, self.head_dim).transpose(1, 2)  # [B, -1, N] -> [B, num_heads, -1, head_dim]
        k = k.view(B, -1, self.num_heads, self.head_dim).transpose(1, 2)  # [B, -1, N] -> [B, num_heads, -1, head_dim]
        v = v.view(B, -1, self.num_heads, self.head_dim).transpose(1, 2)  # [B, -1, N] -> [B, num_heads, -1, head_dim]

        attn_weights = torch.matmul(q, k.transpose(-2, -1)) * self.scale
        if mask is not None:
            attn_weights = attn_weights.masked_fill(mask == 0, float("-inf"))

        attn_weights = attn_weights.softmax(dim=-1)
        attn_output = self.dropout(attn_weights)
        attn_output = torch.matmul(attn_weights, v)
        attn_output = attn_output.transpose(1, 2).contiguous().view(B, -1, N)
        attn_output = self.o_proj(attn_output)
        return attn_output


if __name__ == "__main__":
    x = torch.randn(1, 10, 512)
    mha = MultiHeadAttention(d_model=512, num_heads=8)
    output = mha(x)
    print(output.shape)  # [1, 10, 512] 