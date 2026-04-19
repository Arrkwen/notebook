import torch
import math

import torch.nn as nn


class PositionalEncoding(nn.Module):
    """
    正弦位置编码
    Transformer 论文中使用固定公式计算位置编码，不涉及可学习参数。
    PE(pos, 2i) = sin(pos / 10000^(2i/d_model))
    PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))
    """
    def __init__(self, d_model, max_len=10):
        super(PositionalEncoding, self).__init__()
        self.d_model = d_model
        self.max_len = max_len
        self.encoding = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * -(math.log(10000.0) / d_model))
        self.encoding[:, 0::2] = torch.sin(position * div_term)
        self.encoding[:, 1::2] = torch.cos(position * div_term)
        self.encoding = self.encoding.unsqueeze(0).repeat(1, 1, 1)
        self.encoding = nn.Parameter(self.encoding, requires_grad=False)

    def forward(self, x):
        # x [batch_size, sequence_length, d_model]
        return x + self.encoding[:, :x.shape[1], :]


def visualize_positional_encoding(encoding, seq_len=10):
    import matplotlib.pyplot as plt
    plt.figure(figsize=(10, 5))
    encoding = encoding.transpose(1,2)
    plt.imshow(encoding[0][:, :seq_len], aspect='auto', origin='lower')
    plt.colorbar()
    plt.title('Positional Encoding')
    plt.savefig('positional_encoding.png')
    plt.close()


if __name__ == "__main__":
    x = torch.randn(1, 2, 12)
    positional_encoding = PositionalEncoding(d_model=12)
    output = positional_encoding(x)
    print(output.shape)  # [1, 2, 12]

    visualize_positional_encoding(positional_encoding.encoding, x.shape[1])