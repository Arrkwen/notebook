import torch
import torch.nn as nn


class LayerNormal(nn.Module):
    def __init__(self, eps=1e-6):
        super(LayerNormal, self).__init__()
        self.eps = eps
        self.gamma = nn.Parameter(torch.ones(1))
        self.beta = nn.Parameter(torch.zeros(1))

    def forward(self, x):
        # x [batch_size, sequence_length, d_model]
        mean = x.mean(dim=-1, keepdim=True)
        var = x.var(dim=-1, keepdim=True)
        x_nomal = (x - mean) / torch.sqrt(var + self.eps)
        x = self.gamma * x_nomal + self.beta
        return x


if __name__ == "__main__":
    x = torch.randn(1, 10, 512)
    layer_norm = LayerNormal(eps=1e-6)
    output = layer_norm(x)
    print(output.shape)  # [1, 10, 512]
