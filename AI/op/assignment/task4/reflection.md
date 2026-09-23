# AI 辅助算子开发实践笔记

## 1. 算子与环境

- 算子：Flash Attention Forward（causal / non-causal MHA，可选 GQA）
- 契约：`Q,K,V,O = [B, H, S, D] float16`，fp32 累加；`O = softmax(QK^T/sqrt(D)+mask) V`
- 硬件：MetaX C500，MACA 3.5.3.20，驱动 3.8.30，64 GB
- 软件：TileLang `0.1.9+cuda.gitf1ca0fb9`（`/app/tilelang-metax`），PyTorch `2.8.0+metax3.5.3.9`
- 代码：`assignment/task4/solution.py`，测试 `test_flash_attention.py`，基准 `benchmark_flash_attention.py`

## 2. Agent 参与过程

四轮 Prompt 全文见 `prompts.md`。摘要：

1. **需求分析**：给定 BHSD 契约和「只许用本树已出现的 API」。Agent 按 FlashAttention-2 + task3 online softmax 拆 CTA、列出 pad/mask/GQA/数值风险，并标出 TMA/wgmma 等未验证接口。人工确认 baseline = 64×64 / stage=1 / 128 threads。
2. **代码与测试**：Agent 写出 `_flashattn_factory`、主机 pad、`ref_flash_attn`，以及覆盖非对齐 / decode / GQA / 极值的 pytest。每个 TileLang API 在 `prompts.md` Round 2 列表里解释。
3. **失败修复**：首次编译 `NameError: q_shape is not defined`。原因是 `from __future__ import annotations` 让 `T.prim_func` 在模块全局求值注解。最小补丁是删掉这行。随后 `pytest` 18 passed，`max_abs ≤ 2e-3`。
4. **性能优化**：两个事先写好的假设——A 提高 `num_stages`，B 加大 tile。实测 A 只在 S=256/512 causal 上快 9–11%，S=1024 反而慢 20%；B 除 S=128 外全面变慢。默认保持 v1。

人工改动很少：删 future annotations、mask 不用未确认的 `T.And`、benchmark 补 S=1024。没有改公式，也没有把未实测的配置写进默认路径。

## 3. 优势与局限

**优势**

- 代码模板：官方 MACA `example_mha_fwd_bhsd.py` 经 Agent 改成作业风格（pad、GQA、v1/v2/v3 分入口），比从零写 `T.gemm` + online softmax 快。
- 测试补全：非对齐 S、decode、极值、GQA 这些边界 Agent 一次列全，减少漏测。
- 调优思路：两个假设方向不同（流水 vs 切块），方便做成可复现对照，而不是「帮我优化」这种无法验收的请求。

**局限**

- **API 幻觉**：`T.And` 在 TIR 里有、在 `tilelang.language` 导出里不一定有；`from __future__ import annotations` 会让看起来和官方一模一样的 `T.Tensor(q_shape, dtype)` 在 eager builder 里炸。必须对照本机源码，而不是记忆。
- **硬件知识不足**：C500 wave=64、PDL 未实现、128×128 在中等 S 上占用过高，这些无法从 NVIDIA 经验直接外推。Agent 预测「更大 tile 更快」被 benchmark 推翻。
- **数值稳定性**：mask 必须写在 fragment 且用 `-inf` 初值再 `T.gemm` 累加；整行 mask 时 `logsum=0` 仍是隐患。`TL_ENABLE_FAST_MATH` 会动 `exp2`，误差阈值只能按 fp16 的 `1e-2` 验收。
- **性能必须实测**：`num_stages=2` 不是单调收益。S=512 有效、S=1024 有害。没有表就不能改默认。

**后续人工 review 清单**

1. 注解是否被 future annotations / 字符串化，JIT 能否拿到外层局部变量。
2. `T.copy` 之后有没有写 shared 越界格；mask 是否只写 fragment。
3. causal / pad / GQA 的下标是否用 `valid_seq_*` 而不是 padded shape。
4. `T.gemm` 的 `FullRow` 是否还在（改 policy 会破坏行归约）。
5. 每个优化假设必须有独立入口 + 同一 benchmark 行，编译时间单独列。
6. 默认配置只允许「多规模都不变差」的结果进入。
