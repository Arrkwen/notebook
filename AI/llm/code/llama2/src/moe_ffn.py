import torch
import torch.nn as nn
import torch.nn.functional as F
from ffn import FeedForward


class MoEFFN(nn.Module):
    def __init__(self, d_model, d_ff, n_experts, topk=2, dropout=0.1):
        super(MoEFFN, self).__init__()
        self.n_experts = n_experts
        self.topk = topk

        self.router = nn.Linear(d_model, n_experts, bias=False)
        self.dropout = nn.Dropout(dropout)
        self.experts = nn.ModuleList(
            [FeedForward(d_model, d_ff) for _ in range(n_experts)])

    def forward(self, x):
        # 由于router只是对token进行分配，因此需要对token进行扩展，因此合并batch和seq_len维度
        B, L, D = x.shape
        x_flat = x.view(B*L, D)
        # shape (B*L, n_experts)
        router_logits = self.router(x_flat)
        topk_prob, topk_indices = torch.topk(
            router_logits, k=self.topk, dim=-1)    # shape (B*L, topk)
        topk_prob = F.softmax(topk_prob, dim=-1)   # 对选中的topk 归一化权重

        # 由于每个expert都可能被分配任务，因此按照专家分配任务，利于并行计算(暂时使用循环代替)
        outputs = torch.zeros_like(x_flat)
        for i in range(self.n_experts):
            # 找出当前专家被分配到的任务
            token_idx, k_idx = torch.where(topk_indices == i)
            if len(token_idx) == 0:
                continue
            # 获取当前专家被分配到的任务的输入
            expert_output = self.experts[i](x_flat[token_idx])
            expert_output = expert_output * \
                topk_prob[token_idx, k_idx].unsqueeze(-1)
            # 将当前专家的输出加权累加到输出中，在dim=0上累加，相当于将token_idx的索引对应的输出加上expert_output
            outputs.index_add_(0, token_idx, expert_output)
        outputs = self.dropout(outputs)
        outputs = outputs.view(B, L, D)
        return outputs


if __name__ == "__main__":
    torch.manual_seed(1234)
    x = torch.randn(4, 10, 512)
    moe_ffn = MoEFFN(d_model=512, d_ff=256, n_experts=8, topk=2)
    output = moe_ffn(x)
    print(output.shape)
