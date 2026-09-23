# AI Agent 对话记录：TileLang + 沐曦 MACA Flash Attention

硬件：MetaX C500，MACA 3.5.3.20，驱动 3.8.30，显存 64 GB  
软件：镜像 `TileLang / 0.1.9 / Python 3.12 / maca`，源码树 `/app/tilelang-metax`（commit `f1ca0fb9`）  
模型：Cursor Grok 4.6  
算子：Flash Attention Forward

---

## Round 1：需求分析

**日期**：2026-09-23  
**使用模型**：Cursor Grok 4.6

**Prompt**

```text
我要在 TileLang + 沐曦 MACA 上实现 flash_attention，对齐 llama.py 的 apply_scaled_dot_product_attention。

目标硬件：MetaX C500 + MXMACA，TileLang 走 source ./setup_env.sh 后的 /app/tilelang-metax。

输入/输出契约：
- 布局：Q, K, V, O : [B, H, S, D]（BHSD）
- dtype：float16 I/O，float32 累加
- GQA：允许 H_q % H_kv == 0，K/V 用 head_q // groups
- 解码：允许 S_kv >= S_q，causal 对角偏移 S_kv - S_q

数学定义：
  O = softmax(QK^T / sqrt(D) + mask) V
  causal：mask[i,j] = 0 当 i + (S_kv - S_q) >= j，否则 -inf

TileLang 版本约束：只使用本树已出现的 API（T.Kernel / T.copy / T.alloc_shared / T.alloc_fragment / T.gemm / T.Pipelined / T.reduce_max / T.reduce_sum / T.exp2 / T.if_then_else / T.GemmWarpPolicy.FullRow）。这些 API 在 /app/tilelang-metax/examples/maca/flash_attention/example_mha_fwd_bhsd.py 中有实机示例，不另发明接口。

请给出 kernel 分解、归约/访存策略、边界条件、数值风险和可验证的验收标准。
验收必须覆盖非对齐 S、极值输入、与 PyTorch reference 的 atol=rtol=1e-2。
不要假设不存在的 API；不确定处请明确标注。
```

**Agent 回复（摘要）**

### 1. Kernel 分解

Flash Attention 不能物化 `[S_q, S_kv]` 的分数矩阵。一个 CTA 固定一块 Q tile `[block_M, D]`，沿 KV 方向扫 `k = 0..ceil(S_kv/block_N)`：

1. `T.copy` Q tile → `Q_shared`（只做一次）
2. 对每个 KV tile：
  - `T.copy` K → `K_shared`
  - 在 fragment `acc_s` 里写入 mask（合法 0 / 非法 `-inf`）
  - `T.gemm(Q_shared, K_shared, acc_s, transpose_B=True, policy=FullRow)` 得到 `S = QK^T`
  - 对该 tile 做 **online softmax**（见下）
  - `T.copy` V → `V_shared`
  - `T.gemm(P_cast, V_shared, acc_o, policy=FullRow)` 累加输出
3. `acc_o /= logsum`，经 `O_shared` 写回

Grid：`(ceildiv(S_q, block_M), H, B)`。列方向的 KV tile 必须留在同一 CTA 内循环，因为 `row_max` / `logsum` / `acc_o` 是跨 tile 状态。

### 2. 归约 / 访存策略

沿用 FlashAttention-2 + task3 online softmax：


m' = \max(m, m_{\mathrm{tile}}),\quad
\alpha = e^{m-m'},\quad
\ell' = \alpha\ell + \sum e^{s-m'},\quad
O' = \alpha O + P_{\mathrm{tile}} V_{\mathrm{tile}}


实现上把 `1/sqrt(D)` 和 `log2(e)` 折进 `scale`，用 `T.exp2(x * scale)` 代替 `T.exp`，和官方 MACA 示例一致。

访存：


| 缓冲                                     | 位置             | 角色                                   |
| -------------------------------------- | -------------- | ------------------------------------ |
| `Q/K/V/O_shared`                       | shared         | 给 `T.gemm` 的 MMA 源/暂存；Q 复用全部 KV tile |
| `acc_s`, `acc_o`                       | fragment / 寄存器 | fp32 分数与输出累加                         |
| `scores_max`, `logsum`, `scores_scale` | fragment       | 行归约状态，不回写 HBM                        |


`policy=FullRow` 是硬约束：softmax 按行归约，一个 warp 必须拥有整行，否则 `T.reduce_max/sum` 要跨 warp。

`T.Pipelined(num_stages=...)` 用来重叠 K/V copy 与 GEMM。`num_stages=0` 关闭流水，`1` 是保守默认，`2` 是后续优化假设。

### 3. 边界条件

- **S 不对齐 `block_M/block_N`**：kernel 内 `T.copy` 切片要求 tensor 界内。主机把 `S_q` pad 到 `block_M` 倍数、`S_kv` pad 到 `block_N` 倍数；mask 仍用原始 `valid_seq_*`，把 pad 列打成 `-inf`，最后 slice 掉 pad 行。
- **causal + decode**：`past_len = valid_seq_kv - valid_seq_q`，循环上界 `min(ceildiv(S_kv,block_N), ceildiv((bx+1)*block_M + past_len, block_N))`，少扫未来 KV tile。
- **GQA**：`K/V` 下标 `by // groups`。不确定点：`by // groups` 在 MACA codegen 上是否始终合法——官方 GQA 示例是 BSHD；BHSD 这条路径需实测。
- **D**：`T.gemm` 走 MMA，要求 `D` 对齐（官方示例 64/128）。本作业固定 `D ∈ {64}` 做验收，**不保证任意 D**。
- **尾块 Q 行**：pad 为零，计算后丢弃，不写回有效输出。

### 4. 数值风险

- 直接 `exp(QK^T/sqrt(D))` 会 overflow。必须 online max；mask 位用 `-T.infinity(fp32)`，避免 `(-inf)-(-inf)` 变 NaN（task3 用 `-1e30` 也是同一原因）。
- `T.gemm` 把 mask 和 `QK^T` **累加**：合法格初值必须是 0，非法格 `-inf`。若 `T.clear` 后再 mask，或 mask 写在 shared 上抢 `T.copy`，会得到错值或竞态（task3 已踩过）。
- fp16 I/O + fp32 acc。`TL_ENABLE_FAST_MATH` 会动 `exp2`，官方示例仍用 `rtol=atol=0.01`。
- 整行被 mask 时 `logsum=0`，`acc_o/logsum` 会 NaN。causal 下每行至少有对角，非 causal 且 `S_kv=0` 视为非法输入，测试不覆盖。

### 5. 不确定 / 不假设的 API

- **不使用** 未在本树 MACA 示例出现的 TMA / `wgmma` / `tcgen05` / warp-specialize。C500 对应通路未验证。
- C500 wave=64（不是 NVIDIA 的 32）。官方 MACA 示例仍用 `threads=128/256`，按 2/4 wave 理解；`threads % 64 == 0`。
- `T.copy` 越界行为未在文档写死，所以用主机 pad，而不是赌 copy 自动 clamp。
- Autotune 装饰器存在，但作业里只做**两个手写假设 + 实测**，不跑全空间搜索。

### 6. 可验证验收标准


| 项        | 标准                                                                        |
| -------- | ------------------------------------------------------------------------- |
| 对齐 shape | `(B,H,S,D) ∈ {(1,1,64,64),(2,4,128,64),(1,8,256,64)}`，causal / non-causal |
| 非对齐 S    | `S ∈ {17,33,65,127}`，`D=64`                                               |
| 解码       | `S_q=16, S_kv=80`                                                         |
| GQA      | `H_q=8, H_kv=2`                                                           |
| 极值       | Q/K 含 `±1000`，输出有限且对齐 reference                                           |
| 误差       | vs `ref_flash_attn`（fp32 中间），`atol=rtol=1e-2`                             |
| 性能       | 同一输入上记录 v1/v2/v3 与 PyTorch 的 ms / TFLOPS；只接受 benchmark 结论                 |


**人工确认**：采纳上述契约。Baseline 定为 `block_M=block_N=64, num_stages=1, threads=128`。不接入 Llama 推理路径（本任务只交付 kernel + 测试 + 记录）。

---

## Round 2：代码与测试

**日期**：2026-09-23  
**使用模型**：Cursor Grok 4.6  
**测试命令**：见 Round 3

**Prompt**

```text
基于以下契约和代码，请生成最小可运行 TileLang kernel 与 PyTorch reference 测试。
要求覆盖非对齐 shape、极值输入和 dtype 误差阈值，并解释每个 TileLang API 的用途。
代码：官方 example_mha_fwd_bhsd.py + 本仓库 task3 online softmax 经验。
```

**Agent 回复**

已生成：

- `assignment/task4/solution.py`：`_flashattn_factory` + `tl_flash_attn` + `ref_flash_attn` + v1/v2/v3
- `assignment/task4/test_flash_attention.py`
- `assignment/task4/benchmark_flash_attention.py`

### TileLang API 用途


| API                                             | 用途                                                           |
| ----------------------------------------------- | ------------------------------------------------------------ |
| `@tilelang.jit(out_idx=[3])`                    | lazy 编译；第 4 个参数 `Output` 由 runtime 分配并返回                     |
| `T.prim_func`                                   | 声明 kernel 入口和 tensor 签名                                      |
| `T.Kernel(grid_x, heads, batch, threads=...)`   | 启动 CTA，绑定 `(bx, by, bz)`                                     |
| `T.ceildiv`                                     | 计算 grid / KV 循环次数                                            |
| `T.alloc_shared`                                | CTA 共享内存，供 `T.gemm` 读 Q/K/V                                  |
| `T.alloc_fragment`                              | 寄存器级 tile，放 `acc_s` / `acc_o` / 行统计                          |
| `T.copy`                                        | 全局 ↔ shared、fragment ↔ fragment 搬移；`T.copy` 后不要再写 shared 越界格 |
| `T.fill` / `T.clear`                            | 初始化累加器和 `-inf` max                                           |
| `T.infinity(dtype)`                             | 类型安全的 inf，给 mask / max 初值                                    |
| `T.if_then_else`                                | 在 fragment 里写 mask，避免 Python `if` 变成错误 IR                    |
| `T.gemm(..., transpose_B=True, policy=FullRow)` | MMA：`acc += A @ B^T`；FullRow 保证行归约不跨 warp                    |
| `T.Pipelined(n, num_stages=s)`                  | KV 循环软件流水；`s=0` 关闭                                           |
| `T.Parallel(M, N)`                              | 元素级并行循环                                                      |
| `T.reduce_max` / `T.reduce_sum`                 | 沿 `dim=1`（block_N）做行归约                                       |
| `T.exp2` / `T.max`                              | online softmax 的缩放与指数                                        |
| `TL_ENABLE_FAST_MATH`                           | 放行 fast `exp2`，与官方示例一致                                       |


### 人工改动

- mask 写成嵌套 `if_then_else`，不调用未确认导出的 `T.And`
- 非对齐 S 用主机 pad + `valid_seq_`* mask，而不是在 `T.copy` 切片里赌 OOB
- v1/v2/v3 分成三个入口，避免把 `ALIGNED` 写进同一个 jit 函数导致两套循环都进 IR（task3 v4 的教训）

---

## Round 3：失败修复

**日期**：2026-09-23  
**使用模型**：Cursor Grok 4.6  
**测试命令**

```bash
cd /data/gollamago
source ./setup_env.sh
cd assignment/task4
python -m pytest -q test_flash_attention.py
```

**Prompt（首次编译失败日志）**

```text
测试失败，错误日志如下：
NameError: name 'q_shape' is not defined
  File "solution.py", line 66, in _flashattn_factory
    @T.prim_func
  File "tilelang/language/eager/builder.py", get_type_hints -> _eval_type
请定位最可能的原因，给出最小修改补丁，并说明如何验证修复没有引入新的越界或精度问题。
```

**Agent 定位**

`solution.py` 顶部的 `from __future__ import annotations` 把 `Q: T.Tensor(q_shape, dtype)` 变成字符串。`T.prim_func` 用 `get_type_hints` 在**模块全局命名空间**求值，外层函数的局部变量 `q_shape` 不存在，于是 `NameError`。官方 `example_mha_fwd_bhsd.py` 没有 future annotations，所以同一写法能过。

**最小补丁**：删除 `from __future__ import annotations`。不改 kernel 本体、不改 mask、不改 pad。

**如何确认没引入越界/精度回归**

1. 对齐 `1x1x64x64` causal：`max_abs=9.766e-04`，有限，`assert_close(atol=rtol=1e-2)`
2. 全量 `pytest`：`18 passed in 41.30s`，覆盖非对齐 S、decode、GQA、极值
3. 非对齐 pad 后 slice 回原 `S`，输出 shape 与输入 Q 一致
4. 极值 `±1000` 输出有限，未出现 `(-inf)-(-inf)` NaN

**结果**：采纳该补丁。编译期还有 `Should support PDL for maca target` warning，不影响正确性，未改代码。

**人工改动**：仅删 future annotations。默认入口保持 `tl_flash_attn_v1`。

---

## Round 4：性能优化

**日期**：2026-09-23  
**使用模型**：Cursor Grok 4.6  
**测试命令**

```bash
python benchmark_flash_attention.py
```

**Prompt**

```text
稳态基准数据如下（v1, MetaX C500, warmup=10, repeat=50, 不含编译）：
v1 64x64 s1 t128 | 1x4x128 causal  0.030ms  0.28 TFLOPS
v1 64x64 s1 t128 | 1x8x256 causal  0.043ms  1.56 TFLOPS
v1 64x64 s1 t128 | 1x8x512 causal  0.076ms  3.54 TFLOPS
v1 64x64 s1 t128 | 1x8x256 nonc.   0.035ms  3.84 TFLOPS
v1 64x64 s1 t128 | 1x2x17  causal  0.082ms  (pad 开销主导)
请提出两个互不相同的优化假设，预测影响的瓶颈，并给出逐项实验设计。
只接受能通过 benchmark 验证的结论。
```

**两个互不相同的假设（先于对照实验提出）**

1. **假设 A（v2）**：`num_stages=1 → 2`，tile 仍 64×64。预测瓶颈是 K/V `T.copy` 与 MMA 无法重叠；双缓冲应隐藏拷贝延迟。风险：shared 加倍、occupancy 下降。
2. **假设 B（v3）**：`block=128×128, threads=256, stages=1`。预测瓶颈是 KV 循环次数和 MMA 利用率；更大 tile 减少 trip count。风险：寄存器/shared 涨导致 spill。

对照：`v1_64x64_s1_t128`。同一脚本，只比较 PASS 配置。加速 > 5% 记有效。编译时间不计。

### 实测表（ms / TFLOPS，相对 v1）


| 配置                 | v1 ms (TFLOPS) | v2 ms (Δ)          | v3 ms (Δ)        |
| ------------------ | -------------- | ------------------ | ---------------- |
| 1x4x128 causal     | 0.030 (0.28)   | 0.028 (**-6.7%**)  | 0.027 (**-10%**) |
| 1x8x256 causal     | 0.043 (1.56)   | 0.039 (**-9.3%**)  | 0.070 (+63%)     |
| 1x8x512 causal     | 0.076 (3.54)   | 0.068 (**-10.5%**) | 0.168 (+121%)    |
| 1x8x1024 causal    | 0.153 (7.04)   | 0.183 (+19.6%)     | 0.401 (+162%)    |
| 1x8x256 non-causal | 0.035 (3.84)   | 0.037 (+5.7%)      | 0.045 (+29%)     |
| 1x2x17 causal      | 0.082          | 0.084 (+2.4%)      | 0.113 (+38%)     |


三档正确性都是 PASS，`max_abs ≤ 1.953e-03`。PyTorch reference 在 S=512/1024 上分别约 0.23 / 0.49 ms，v1 仍快于物化 `S×S` 的 matmul+softmax。

### 结论（只认表）

- **假设 A 部分成立**：S=256/512 causal 有效（约 9–11%）；S=1024 和 non-causal **无效**（变慢）。不能无条件把 `num_stages=2` 设成默认。
- **假设 B 不成立**：除 S=128（单 tile，几乎无 KV 循环）外全面变慢。C500 上 128×128 + 256 threads 的占用上升压过了 trip count 收益；非对齐 S=17 pad 到 128 浪费更明显。
- **最终采纳**：默认 `tl_flash_attn_v1`（64×64 / stage=1 / 128 threads）。v2 仅作为中等 causal 长度的可选配置，不写进默认路径。

**人工改动**：benchmark 增补 S=1024；不改默认 kernel。