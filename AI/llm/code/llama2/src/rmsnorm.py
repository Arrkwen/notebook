import torch
import torch.nn as nn


class RMSNorm(nn.Module):
    def __init__(self, d_model, eps=1e-6):
        super(RMSNorm, self).__init__()
        self.eps = eps
        self.gamma = nn.Parameter(torch.ones(d_model))

    def forward(self, x):
        # rsqrt 开平方根，再取倒数
        x = x * torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True) + self.eps)
        x = self.gamma * x
        return x


if __name__ == "__main__":
    # 准备参数和输入
    batch_size, seq_len, dim = 1, 1, 4
    torch.manual_seed(42)
    x = torch.randn(batch_size, seq_len, dim, dtype=torch.float32)

    # 初始化并应用 RMSNorm
    norm = RMSNorm(dim)
    output = norm(x)

    # 验证输出形状
    print("--- RMSNorm Test ---")
    print("Input shape:", x.shape)
    print("Input:", x)
    print("Output shape:", output.shape)
    print("Output:", output)
