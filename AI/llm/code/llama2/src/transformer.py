import torch
import torch.nn as nn

from .attention import GroupQueryAttention
from .ffn import FeedForward
from .rmsnorm import RMSNorm
from .rope import precompute_freqs_cis


class TransformerBlock(nn.Module):
    def __init__(self, layer_id, d_model, d_ff, n_heads, n_kv_heads, max_batch_size=1024, max_seq_len=2048, dropout=0.1):
        super(TransformerBlock, self).__init__()
        self.layer_id = layer_id
        self.attention = GroupQueryAttention(d_model, n_heads, n_kv_heads,
                                             max_batch_size, max_seq_len, dropout)
        self.ffn = FeedForward(d_model, d_ff, dropout)
        self.attention_norm = RMSNorm(d_model)
        self.ffn_norm = RMSNorm(d_model, eps=1e-5)

    def forward(self, x, start_pos, freqs_cis, mask=None):
        x = x + self.attention(self.attention_norm(x),
                               start_pos, freqs_cis, mask)
        x = x + self.ffn(self.ffn_norm(x))
        return x


class Llama2Transformer(nn.Module):
    def __init__(self,
                 d_model,
                 d_ff,
                 n_heads,
                 n_kv_heads,
                 n_layers,
                 vocab_size,
                 max_batch_size=1024,
                 max_seq_len=2048,
                 dropout=0.1):
        super(Llama2Transformer, self).__init__()
        self.d_model = d_model
        self.d_ff = d_ff
        self.n_heads = n_heads
        self.n_kv_heads = n_kv_heads
        self.n_layers = n_layers
        self.max_batch_size = max_batch_size

        self.token_embedding = nn.Embedding(vocab_size, d_model)
        self.blocks = nn.ModuleList([TransformerBlock(
            layer_id=i, d_model=d_model, d_ff=d_ff, n_heads=n_heads, n_kv_heads=n_kv_heads,
            max_batch_size=max_batch_size, max_seq_len=max_seq_len, dropout=dropout) for i in range(n_layers)])
        self.norm = RMSNorm(d_model, eps=1e-5)
        self.output_layer = nn.Linear(d_model, vocab_size, bias=False)
        self.init_params()

        # 预计算频率,register_buffer不会保存到磁盘，只在内存中保存，*2是工程余量，避免位置超出范围
        self.register_buffer("freqs_cis", precompute_freqs_cis(
            d_model//n_heads, max_seq_len*2), persistent=False)

    def init_params(self):
        for p in self.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)

    def forward(self, tokens: torch.Tensor, start_pos: int):
        B, L = tokens.shape
        x = self.token_embedding(tokens)
        freqs_cis = self.freqs_cis[start_pos:start_pos + L]

        mask = None
        if L > 1:
            mask = torch.full((L, L), float("-inf"), device=tokens.device)
            mask = torch.triu(mask, diagonal=1)
            mask = torch.hstack(
                [torch.zeros((L, start_pos), device=tokens.device, dtype=x.dtype), mask])

        for block in self.blocks:
            x = block(x, start_pos, freqs_cis, mask)
        x = self.norm(x)
        logits = self.output_layer(x)
        return logits


if __name__ == "__main__":
    torch.manual_seed(1234)
    x = torch.randn(4, 10, 512)
    transformer_block = TransformerBlock(
        d_model=512, d_ff=2048, n_heads=8, n_kv_heads=4, max_batch_size=32, max_seq_len=10)
    freqs_cis = precompute_freqs_cis(transformer_block.attention.head_dim, 10)
    output = transformer_block(x, 0, freqs_cis)
    print(output.shape)
