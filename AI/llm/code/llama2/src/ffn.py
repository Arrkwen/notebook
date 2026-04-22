import torch
import torch.nn as nn


class FeedForward(nn.Module):
    def __init__(self, d_model, d_ff, dropout=0.1):
        super(FeedForward, self).__init__()
        self.d_model = d_model
        self.d_ff = d_ff
        self.dropout = nn.Dropout(dropout)
        self.w1 = nn.Linear(d_model, d_ff)
        self.activation = nn.SiLU(inplace=False)
        self.w2 = nn.Linear(d_model, d_ff)
        self.w3 = nn.Linear(d_ff, d_model)

    def forward(self, x):
        x1 = self.w1(x)  # shape (B, L, d_ff)
        x1 = self.activation(x1)  # shape (B, L, d_ff)
        x2 = self.w2(x)  # shape (B, L, d_ff)
        x = x1 * x2  # shape (B, L, d_ff)
        x = self.dropout(x)  # shape (B, L, d_ff)
        x = self.w3(x)  # shape (B, L, d_model)
        return x


if __name__ == "__main__":
    torch.manual_seed(1234)
    x = torch.randn(4, 10, 512)
    ffn = FeedForward(d_model=512, d_ff=2048)
    output = ffn(x)
    print(output.shape)
