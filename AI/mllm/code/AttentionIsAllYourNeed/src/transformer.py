import torch
import torch.nn as nn
import math

from .attention import MultiHeadAttention
from .ffn import FeedForward
from .pos import PositionalEncoding
from .normal import LayerNormal


class EncoderLayer(nn.Module):
    def __init__(self, d_model, num_heads, dropout=0.1, ffn_hidden_dim=2048):
        super().__init__()
        self.attention = MultiHeadAttention(d_model, num_heads, dropout)
        self.attention_norm = LayerNormal(d_model)
        self.ffn = FeedForward(d_model, ffn_hidden_dim, dropout)
        self.ffn_norm = LayerNormal(d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, mask=None):
        x_ = x
        x = self.attention(x, x, x, mask)
        x = self.attention_norm(self.dropout(x) + x_)
        x_ = x
        x = self.ffn(x)
        x = self.ffn_norm(self.dropout(x) + x_)
        return x


class DecoderLayer(nn.Module):
    def __init__(self, d_model, num_heads, dropout=0.1, ffn_hidden_dim=2048):
        super().__init__()
        self.attention = MultiHeadAttention(d_model, num_heads, dropout)
        self.cross_attention = MultiHeadAttention(d_model, num_heads, dropout)
        self.attention_norm = LayerNormal(d_model)
        self.cross_attention_norm = LayerNormal(d_model)
        self.ffn = FeedForward(d_model, ffn_hidden_dim, dropout)
        self.ffn_norm = LayerNormal(d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x, enc_output, src_mask=None, tgt_mask=None):
        x_ = x
        x = self.attention(x, x, x, tgt_mask)
        x = self.attention_norm(self.dropout(x) + x_)
        x_ = x
        x = self.cross_attention(x, enc_output, enc_output, src_mask)
        x = self.cross_attention_norm(self.dropout(x) + x_)
        x_ = x
        x = self.ffn(x)
        x = self.ffn_norm(self.dropout(x) + x_)
        return x


class Transformer(nn.Module):
    def __init__(self,
                 src_vocab_size,
                 tgt_vocab_size,
                 d_model,
                 num_heads,
                 num_encoder_layers,
                 num_decoder_layers,
                 max_len,
                 dropout=0.1,
                 ffn_hidden_dim=2048):
        super().__init__()
        self.src_embedding = nn.Embedding(src_vocab_size, d_model)
        self.tgt_embedding = nn.Embedding(tgt_vocab_size, d_model)
        self.d_model = d_model
        self.pos_encoding = PositionalEncoding(d_model, max_len)
        self.encoder = nn.ModuleList([EncoderLayer(d_model, num_heads, dropout, ffn_hidden_dim) for _ in range(num_encoder_layers)])
        self.decoder = nn.ModuleList([DecoderLayer(d_model, num_heads, dropout, ffn_hidden_dim) for _ in range(num_decoder_layers)])
        self.dropout = nn.Dropout(dropout)
        self.output_layer = nn.Linear(d_model, tgt_vocab_size)
        
        self.init_params()

    def init_params(self):
        for p in self.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)

    def generate_mask(self, src, tgt):
        # src [batch_size, seq_len]
        # src_mask [batch_size, 1, 1, seq_len]
        # pad mask
        src_mask = (src != 0).unsqueeze(1).unsqueeze(2)
        # tgt [batch_size, seq_len]
        # tgt_mask [batch_size, 1, seq_len, seq_len]
        # pad + casual mask
        tgt_len = tgt.size(1)
        tgt_pad_mask = (tgt != 0).unsqueeze(1).unsqueeze(2)  # [batch_size, 1, 1, seq_len]
        tgt_causal_mask = torch.tril(torch.ones((tgt_len, tgt_len), device=tgt.device)).bool()  # [seq_len, seq_len]
        tgt_mask = tgt_pad_mask & tgt_causal_mask.unsqueeze(0)  # [batch_size, 1, seq_len, seq_len]
        return src_mask, tgt_mask

    def encode(self, src, src_mask):
        x = self.src_embedding(src) * math.sqrt(self.d_model)
        x = self.pos_encoding(x)
        self.dropout(x)
        for encoder_layer in self.encoder:
            x = encoder_layer(x, src_mask)
        return x

    def decode(self, tgt, enc_output, src_mask, tgt_mask):
        x = self.tgt_embedding(tgt) * math.sqrt(self.d_model)
        x = self.pos_encoding(x)
        for decoder_layer in self.decoder:
            x = decoder_layer(x, enc_output, src_mask, tgt_mask)
        return x

    def forward(self, src, tgt):
        src_mask, tgt_mask = self.generate_mask(src, tgt)
        enc_output = self.encode(src, src_mask)
        dec_output = self.decode(tgt, enc_output, src_mask, tgt_mask)
        return self.output_layer(dec_output)
