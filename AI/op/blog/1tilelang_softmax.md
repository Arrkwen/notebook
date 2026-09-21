# TileLang Softmax 实现说明

本文整理了 Softmax 算子本身、任务三的实现需求、错误写法的问题、正确切分方式、分 tile 数值例子、硬件资源（block / 寄存器），以及四个实现：`v1` 三趟扫描、`v2` online、`v3` 一行一 block、`v4` 按 M 选 threads + 整除无分支。测试入口是 `tl_softmax = tl_softmax_v4`。对应文件：`assignment/task3/solution.py`。参考：[Online Softmax by Hand](https://dev.to/lewis_won/online-softmax-by-hand-4h13)。

## 0. Softmax 算子说明

Softmax 把一组实数映射成一组非负、且和为 1 的概率分布。输入越大，对应分量越大；常用在分类头、Attention 的分数归一化等场景。

### 0.1 一维定义

对长度为 $M$ 的向量 $\mathbf{x} = (x_0, x_1, \ldots, x_{M-1})$：

$$
\mathrm{softmax}(x)*j = \frac{e^{x_j}}{\sum*{k=0}^{M-1} e^{x_k}}
$$

性质：

- $\mathrm{softmax}(x)_j \ge 0$
- $\sum_j \mathrm{softmax}(x)_j = 1$
- 对任意常数 $c$，有 $\mathrm{softmax}(\mathbf{x} + c) = \mathrm{softmax}(\mathbf{x})$（平移不变）

### 0.2 数值稳定形式

直接算 $e^{x_j}$ 时，若某个 $x_j$ 很大（如 $1000$），会 float 上溢变成 `inf`。利用平移不变性，先减去行内最大值：

$$
m = \max_k x_k, \qquad
\mathrm{softmax}(x)*j = \frac{e^{x_j - m}}{\sum*{k=0}^{M-1} e^{x_k - m}}
$$

这样 $x_j - m \le 0$，指数落在 $(0, 1]$，避免上溢；分子分母同乘 $e^{-m}$，结果与原始定义相同。

### 0.3 二维按行 Softmax

对矩阵 $A \in \mathbb{R}^{N \times M}$，**每一行独立**做 Softmax（等价于 PyTorch 的 `torch.softmax(A, dim=1)`）：

$$
B_{i,j} = \frac{\exp\bigl(A_{i,j} - \max_k A_{i,k}\bigr)}{\sum_k \exp\bigl(A_{i,k} - \max_k A_{i,k}\bigr)}
$$

实现上可以拆成三步（算法 1 的三次 Pass），也可以把前两步合成 online 更新（算法 2）：

1. **求最大值**：$m_i = \max_j A_{i,j}$
2. **求指数和**：$s_i = \sum_j \exp(A_{i,j} - m_i)$
3. **归一化写回**：$B_{i,j} = \exp(A_{i,j} - m_i) / s_i$

当 $M$ 很大、单次装不下整行时，列方向要分 tile；但 $m_i$、$s_i$ 是**整行**归约结果，必须在同一 thread block 内跨 tile 累积——这是后面切分设计的核心约束。

## 1. 任务目标

对二维矩阵按行做数值稳定 Softmax，即上一节的 $B_{i,j}$ 公式。


| 项目   | 约定                                                                            |
| ---- | ----------------------------------------------------------------------------- |
| 输入   | `A: [N, M] float32`                                                           |
| 输出   | 同 shape / dtype                                                               |
| 归约方向 | 最后一维（列方向 /`dim=1`）                                                            |
| 接口   | `tl_softmax_v1` / `v2` / `v3` / `v4`；测试入口 `tl_softmax = tl_softmax_v4` |
| 测试规模 | `(1,1)`、`(3,7)`、`(16,256)`、`(17,513)`、`(64,4096)`，以及极值行 `[-1000, 0, 1000, 1]` |


运行：

```bash
cd /data/gollamago
source ./setup_env.sh
cd assignment/task3
python -m pytest -q test_softmax.py
python benchmark_softmax.py
```

## 2. 初版实现的问题

初版思路是「每个 tile 求局部 max，再得到全局 max」。方向对，但下面几处会直接算错或无法编译出正确归约。会话开始时的错误版本如下（只写到求 tile 局部 max，没有 `exp` / 求和 / 写回）：

```python
import tilelang
import tilelang.language as T

@tilelang.jit
def tl_softmax(A, BLOCK_N: int, BLOCK_M: int):
    N, M = T.const("N, M")
    A: T.Tensor((N, M), T.float32)
    B = T.empty((N, M), T.float32)

    # 初版本，求最大值
    with T.Kernel(T.ceildiv(N, BLOCK_N), T.ceildiv(M, BLOCK_M)) as (bx, by):
        A_shared = T.alloc_shared((BLOCK_N, BLOCK_M), T.float32)
        B_fragment = T.alloc_fragment((BLOCK_N, BLOCK_M), T.float32)
        Temp_max_fragment = T.alloc_fragment((BLOCK_N,), T.float32)
        Temp_sum_fragment = T.alloc_fragment((BLOCK_N,), T.float32)
        T.clear(B_fragment)
        T.clear(Temp_max_fragment)
        T.clear(Temp_sum_fragment)
        T.copy(A[bx * BLOCK_N, by * BLOCK_M], A_shared)
        for (i, j) in T.parallize(BLOCK_N, BLOCK_M):
            if i >= N or j >= M:
                A_shared[i, j] = -float("inf")
            Temp_max_fragment[i] = T.max(Temp_max_fragment[i], A_shared[i, j])
```

对照后面几小节：grid 用了 `(bx, by)` 把列也切开；`T.clear` 把 max 初值变成 0；`T.parallize` 拼写错误且对同一行并发写 max；`if i >= N or j >= M` 使用错误块内下标；`T.copy` 之后直接改 `A_shared` 越界格。

### 2.1 Grid 同时切了列（最关键）

原写法类似：

```python
with T.Kernel(T.ceildiv(N, BLOCK_N), T.ceildiv(M, BLOCK_M)) as (bx, by):
```

Softmax 必须沿整行归约。列一旦分给不同 thread block：

- 每个 block 只能看到自己那 `BLOCK_M` 列的局部最大值
- block 之间没有共享 fragment，也没有同步手段
- 「把各 tile 的 max 合成行 max」在单 kernel 内做不到（除非 atomic 或拆成多个 kernel）

正确做法：**grid 只按行切**；列方向的 tile 用同一个 block 里的 `ko` 循环扫完，这样 `row_max` / `row_sum` 才能跨 tile 累积。`M=4096, BLOCK_M=256` 时就是每个 block 循环 16 次。

### 2.2 最大值初值写成了 0

`T.clear(Temp_max_fragment)` 把 max 初始化成 0。整行都是负数时，max 会被错成 0。求最大值必须用负无穷一类的初值。实现里用有限值 `NEG_INF = -1e30`，避免后面出现 `(-inf) - (-inf) = NaN`。

### 2.3 用 Parallel 手写 max 有写竞争

```python
for (i, j) in T.parallize(BLOCK_N, BLOCK_M):
    Temp_max_fragment[i] = T.max(Temp_max_fragment[i], A_shared[i, j])
```

`T.Parallel(BLOCK_N, BLOCK_M)` 里同一行的多个 `j` 会同时读写 `Temp_max_fragment[i]`，这是数据竞争，不是归约。应使用：

```python
T.reduce_max(tile_fragment, tile_reduce, dim=1, clear=True)
```

### 2.4 边界判断写反，且用了块内下标

`if i >= N or j >= M` 有两处错：

- `i`、`j` 是 tile 内偏移，要和全局下标比：`bx * BLOCK_N + i < N`

正确条件：`bx * BLOCK_N + i < N and ko * BLOCK_M + j < M`。`(1,1)`、`(3,7)`、`(17,513)` 等尾块大部分是 padding，这个判断必须有。

### 2.5 异步拷贝之后改 `A_shared`：缺少同步，还会污染后续 pass

初版在 `T.copy` 之后直接改 shared 里的越界格子：

```python
T.copy(A[bx * BLOCK_N, by * BLOCK_M], A_shared)
for (i, j) in T.parallize(BLOCK_N, BLOCK_M):
    if 越界:
        A_shared[i, j] = -float("inf")
    Temp_max_fragment[i] = T.max(Temp_max_fragment[i], A_shared[i, j])
```

**不要这样做。** 越界屏蔽应放在拷进 fragment 的那一步，而不是写回 `A_shared`。

#### 和异步拷贝抢同一块内存

`T.copy` 从全局内存搬到 shared memory，编译后通常是异步 DMA / `cp.async`，不是「这条语句执行完，数据一定已经在 `A_shared` 里」。正确顺序是：发出拷贝 → barrier（等拷贝完成）→ 再读 `A_shared`。

TileLang 在 `T.copy` 后面接 `T.Parallel` **读** `A_shared` 时，一般会自己插 barrier。但如果你在 copy 刚结束、barrier 之前就去 **写** `A_shared` 的越界格，可能出现：

- 拷贝还没写完，你先写成了 `-inf`，随后 DMA 又把未定义数据盖回来
- 或者你和 DMA 同时写同一块 shared，结果不确定

#### 污染后续 pass

`A_shared` 在 Pass 1 / 2 / 3 复用同一块缓冲，存的应是 **A 的原始 tile**，不是「已经屏蔽过的中间结果」。越界位置在不同 pass 需要不同填充：


| Pass    | 越界该填什么       | 原因                                                                           |
| ------- | ------------ | ---------------------------------------------------------------------------- |
| 1 求 max | `NEG_INF`    | 不能把垃圾值当成更大的 max                                                              |
| 2 求和    | `0`          | 若 shared 里已经是`-inf`，后面 `exp(A_shared - row_max)` 可能变成 `NaN`（`-inf - (-inf)`） |
| 3 写回    | 根本不该改 shared | 只对有效下标算`exp / sum`                                                           |


如果 Pass 1 已经把 `A_shared` 越界格改成 `-inf`：尾块那些格子本来就不会从 `A` 拷到合法数据，shared 里可能一直留着 `-inf`，后面两趟用 `A_shared` 做 `exp(x - row_max)` 就会把 `-inf` 带进计算。等于把「屏蔽」写进了原始输入缓冲，后面三趟对 `A_shared` 的假设就坏了。

#### 正确做法：屏蔽发生在 fragment

```python
T.copy(A[bx * BLOCK_N, ko * BLOCK_M], A_shared)
for i, j in T.Parallel(BLOCK_N, BLOCK_M):
    tile_fragment[i, j] = NEG_INF          # Pass 2 这里改成 0.0
    if bx * BLOCK_N + i < N and ko * BLOCK_M + j < M:
        tile_fragment[i, j] = A_shared[i, j]
```

- `A_shared`：只当只读的原始 tile 缓存，`T.copy` 写完后不再改它
- `tile_fragment`：计算用的工作区，越界在这里屏蔽。它在寄存器上，和 DMA 目标不是同一块内存，不存在和 `T.copy` 抢写；每个 pass 也可以用不同的填充值

**一句话：** `A_shared` 保持「从 A 拷来的原样」；「这个格子算不算进 max/sum」只在 fragment 里处理。

## 3. 正确的并行切分

```
一次 tl_softmax(...) 调用
        │
        │  只 launch 一次 GPU kernel
        ▼
T.Kernel(ceildiv(N, BLOCK_N), threads=128)
        │
        ├── bx = 0  thread block：行 [0, BLOCK_N)
        ├── bx = 1  thread block：行 [BLOCK_N, 2*BLOCK_N)
        └── ...
                │
                └── 每个 block 内部：
                      for ko in range(ceildiv(M, BLOCK_M)):
                          处理列 [ko*BLOCK_M, (ko+1)*BLOCK_M)
```

容易混的两个词：


| 词                       | 含义                           |
| ----------------------- | ---------------------------- |
| **kernel**              | 一次 GPU 函数启动；整张`A` 一次算完       |
| **thread block / `bx`** | 这次启动里的并行工作单元；每块包住`BLOCK_N` 行 |


切分后的行块分配到的是 **同一次启动里的不同 thread block**，不是多个独立 kernel。不同 `bx` 可以同时跑在不同 AP/SM 上，但都是同一套 kernel 程序的不同实例。它们不共享 `row_max` / `row_sum`。

列上的两个 tile **不会**分到不同 block；它们是同一个 `bx` 里 `ko=0, ko=1, ...` 顺序扫过去的。

## 4. 分 tile 数值例子

取 `A` 为 3×5，`BLOCK_N=2`，`BLOCK_M=3`：

```
           col:  0  1  2 | 3  4 (5)
    A = row0 [   1  2  3 | 4  5     ]
        row1 [   5  4  3 | 2  1     ]
        ---------------------------
        row2 [   0  1  0 | 1  0     ]
       (row3)  越界补齐
```

- grid = `ceildiv(3, 2) = 2`：`bx=0` 管 row0~row1，`bx=1` 管 row2（外加越界的 row3）
- 列方向 `num_tiles = ceildiv(5, 3) = 2`，由 `ko` 在 block 内循环

下面只跟踪 `bx=0`（row0、row1）。

### Pass 1：行最大值

越界列填 `NEG_INF`，避免污染 max。


| 迭代     | `tile_fragment`                      | `tile_reduce` | 累积后的`row_max` |
| ------ | ------------------------------------ | ------------- | ------------- |
| `ko=0` | `[[1, 2, 3], [5, 4, 3]]`             | `[3, 5]`      | `[3, 5]`      |
| `ko=1` | `[[4, 5, NEG_INF], [2, 1, NEG_INF]]` | `[5, 2]`      | `[5, 5]`      |


### Pass 2：`exp(x - row_max)` 求和

`row_max = [5, 5]`。越界位填 **0**（不是 `NEG_INF`），否则会污染 sum。


| 迭代     | `tile_fragment`（示意）                       | `tile_reduce`    | 累积后的`row_sum`    |
| ------ | ----------------------------------------- | ---------------- | ---------------- |
| `ko=0` | `[[e^-4, e^-3, e^-2], [e^0, e^-1, e^-2]]` | `[0.203, 1.503]` | `[0.203, 1.503]` |
| `ko=1` | `[[e^-1, e^0, 0], [e^-3, e^-4, 0]]`       | `[1.368, 0.068]` | `[1.571, 1.571]` |


两行数值相同，是因为这个例子里 row0 和 row1 互为逆序。

### Pass 3：归一化写回

```
B[0, :] = [e^-4, e^-3, e^-2, e^-1, e^0] / 1.571
        ≈ [0.012, 0.032, 0.086, 0.234, 0.636]
```

五项之和为 1。`bx=1` 的越界行 row3 会保持 `row_max=NEG_INF`、`row_sum=0`，但边界判断挡住写回，不会出现 `0/0`。

## 5. Kernel 结构（三趟扫描）

每个 thread block 持有：


| 缓冲              | 分配                                 | 作用                              |
| --------------- | ---------------------------------- | ------------------------------- |
| `A_shared`      | `alloc_shared(BLOCK_N, BLOCK_M)`   | 当前列 tile，从全局内存拷入                |
| `tile_fragment` | `alloc_fragment(BLOCK_N, BLOCK_M)` | 当前 tile 的计算值（max 用原值，sum 用 exp） |
| `tile_reduce`   | `alloc_fragment(BLOCK_N,)`         | 当前 tile 沿列归约结果                  |
| `row_max`       | `alloc_fragment(BLOCK_N,)`         | 跨`ko` 累积的整行最大值                  |
| `row_sum`       | `alloc_fragment(BLOCK_N,)`         | 跨`ko` 累积的整行 exp 和               |


流程：

1. `row_max` 填 `NEG_INF`，`row_sum` 清零。
2. **Pass 1**：拷 tile → 越界填 `NEG_INF` → `reduce_max(dim=1)` → `row_max = max(row_max, tile_reduce)`。
3. **Pass 2**：拷 tile → 有效位置 `exp(x - row_max)`，越界填 0 → `reduce_sum(dim=1)` → `row_sum += tile_reduce`。
4. **Pass 3**：拷 tile → 有效位置写 `exp(x - row_max) / row_sum`。

三趟都复用同一块 `A_shared`；TileLang 会在 `copy` 与计算之间插入 barrier。算法 1 读全局 `A` 三遍、写 `B` 一遍。`M` 很大时可用算法 2 的 online softmax 把前两趟合成一遍，见第 8 节。

## 6. 硬件资源：block 排队与寄存器

课程环境是沐曦 **曦云 C500**。计算核心叫 **AP / XCORE**，角色接近 NVIDIA SM。

### 6.1 行很多、`BLOCK_N` 很小：会排队，但不会失败

`ceildiv(N, BLOCK_N)` 只决定 grid 里有多少个 block。AP 数量固定，每个 AP 同时能驻留的 block 还受线程数、shared memory、寄存器限制。

两层排队都是正常调度：

1. **整卡**：grid 有上万个 block 时，AP 同时只能跑一部分，其余在硬件队列里等；某个 AP 上的 block 结束，调度器立刻塞下一个。
2. **单个 AP**：即使还有空闲计算单元，寄存器 / smem / 线程槽满了也不能再多驻留，occupancy 下降。

只要不超过 `maxGridSize`，launch 不会因为 block 多而失败。`BLOCK_N` 太小的真正代价通常是每个 block 太瘦、启动开销占比高；列方向 `ko` 仍要扫完整行 `M`。

### 6.2 `BLOCK_N` / `BLOCK_M` 很大：寄存器是编译期配额

`T.alloc_fragment` **不是**运行时向芯片 `malloc` 寄存器。JIT 时编译器把 fragment 映射到每线程寄存器，必要时 spill 到 local memory。运行时不会「寄存器用完再排队等下一批寄存器」。


| 压力             | 结果                                                   |
| -------------- | ---------------------------------------------------- |
| 用量偏大，但仍低于每线程上限 | occupancy 下降，每个 AP 同时少驻留几个 block                     |
| 再大             | spill 到 local memory，能跑但变慢                           |
| 超过每线程硬上限       | **编译失败或 launch 失败**（类似 too many resources requested） |


寄存器上限卡的是 **单个 block / 每线程**，不是「全芯片寄存器用完」。行很多只增加 block 个数，不增加单个 block 的寄存器。危险的是把 `BLOCK_N × BLOCK_M` 的 fragment 面积撑得太大。

粗算当前默认 tile（`BLOCK_N=16, BLOCK_M=256, threads=128`）：`tile_fragment` 有 `16×256=4096` 个 float32，是整个 block 一份，摊到 128 线程大约每线程 32 个寄存器，再加上 `row_max` / `row_sum` / 临时量，离每线程上限还很远。

### 6.3 沐曦 C500 寄存器规模

官方白皮书没有把「整卡寄存器总容量」写成单一营销数字。可编程侧可通过 `mcGetDeviceProperties` 读 `regsPerBlock`（文档示例标成 Registers per MP）、`sharedMemPerBlock`、`waveSize` 等。

社区调优文章里比较一致的 C500 数字（非官方白皮书逐字引用，上机以设备属性为准）：


| 项目                    | 约数                              |
| --------------------- | ------------------------------- |
| 每个 AP 的 register file | ≈ 512 KB（约 131072 个 32-bit 寄存器） |
| 每个 AP 的 shared memory | ≈ 64 KB                         |
| wave size             | 64                              |
| 每线程寄存器上限              | 255                             |


512 KB 是 **一个 AP 上所有驻留 wave 共用** 的寄存器堆，不是整卡一份，也不是每个 block 独享。例如 128 线程、每线程 64 个 32-bit 寄存器时，一个 block 大约 32 KB；理论上一个 AP 能同时塞十几个这样的 block，再被 smem 和线程槽一起卡住。

C600 公开资料更少，不要把 512 KB 直接套过去。

## 7. 算法 1：三趟扫描（`tl_softmax_v1`）

完整代码见 `solution.py` 中的 `tl_softmax_v1`。核心骨架如下：

```python
NEG_INF = -1e30

@tilelang.jit
def tl_softmax(A, BLOCK_N: int, BLOCK_M: int):
    N, M = T.const("N, M")
    A: T.Tensor((N, M), T.float32)
    B = T.empty((N, M), T.float32)

    with T.Kernel(T.ceildiv(N, BLOCK_N), threads=128) as bx:
        A_shared = T.alloc_shared((BLOCK_N, BLOCK_M), T.float32)
        tile_fragment = T.alloc_fragment((BLOCK_N, BLOCK_M), T.float32)
        tile_reduce = T.alloc_fragment((BLOCK_N,), T.float32)
        row_max = T.alloc_fragment((BLOCK_N,), T.float32)
        row_sum = T.alloc_fragment((BLOCK_N,), T.float32)

        T.fill(row_max, NEG_INF)
        T.clear(row_sum)
        num_tiles = T.ceildiv(M, BLOCK_M)

        for ko in range(num_tiles):          # Pass 1: 行 max
            T.copy(A[bx * BLOCK_N, ko * BLOCK_M], A_shared)
            for i, j in T.Parallel(BLOCK_N, BLOCK_M):
                tile_fragment[i, j] = NEG_INF
                if bx * BLOCK_N + i < N and ko * BLOCK_M + j < M:
                    tile_fragment[i, j] = A_shared[i, j]
            T.reduce_max(tile_fragment, tile_reduce, dim=1, clear=True) # tile内每行求最大值
            for i in T.Parallel(BLOCK_N):
                row_max[i] = T.max(row_max[i], tile_reduce[i])

        for ko in range(num_tiles):          # Pass 2: 行 sum
            T.copy(A[bx * BLOCK_N, ko * BLOCK_M], A_shared)
            for i, j in T.Parallel(BLOCK_N, BLOCK_M):
                tile_fragment[i, j] = 0.0
                if bx * BLOCK_N + i < N and ko * BLOCK_M + j < M:
                    tile_fragment[i, j] = T.exp(A_shared[i, j] - row_max[i])
            T.reduce_sum(tile_fragment, tile_reduce, dim=1, clear=True)
            for i in T.Parallel(BLOCK_N):
                row_sum[i] += tile_reduce[i]

        for ko in range(num_tiles):          # Pass 3: 写回
            T.copy(A[bx * BLOCK_N, ko * BLOCK_M], A_shared)
            for i, j in T.Parallel(BLOCK_N, BLOCK_M):
                if bx * BLOCK_N + i < N and ko * BLOCK_M + j < M:
                    B[bx * BLOCK_N + i, ko * BLOCK_M + j] = (
                        T.exp(A_shared[i, j] - row_max[i]) / row_sum[i]
                    )

    return B
```

测试默认 `BLOCK_N=16, BLOCK_M=256`。极值用例用 `BLOCK_N=1, BLOCK_M=4`，覆盖「一个 block 一行、列方向正好铺满」的情况。

- **Pass 1**：只读全局 `A` → `A_shared` → `tile_fragment`；`row_max` 只在片上累积，不写 `B`。
- **Pass 2**：再扫一遍全局 `A`，读片上 `row_max`，把 `row_sum` 累在 fragment 里，仍然不写 `B`。
- **Pass 3**：第三遍读 `A`，结合 `row_max` / `row_sum`，**唯一一次**写全局 `B`；`A_shared` 保持只读。

三次循环加起来就是：全局内存读 `A` 三遍、写 `B` 一遍；中间归约状态不落 HBM。

## 8. 算法 2：Online Softmax（`tl_softmax_v2`）

算法 1 必须先得到**整行** `row_max`，才能用同一个基准去算 `exp(x - row_max)`。所以 max 和 sum 是两次独立扫 `A`。

Online softmax 的观察是：当前累计的和总是相对于**当前已知的 max**。后面遇到更大的 `tile_max` 时，不必重读旧 tile，只要把旧和乘上缩放因子，换到新基准上：

$$
m' = \max(m, m_{\text{tile}}), \qquad
s' = s \cdot e^{m - m'} + \sum_{j \in \text{tile}} e^{x_j - m'}
$$

第一项把「旧数据在旧 max 下的和」改写成「旧数据在新 max 下的和」；第二项是当前 tile 在新 max 下的和。两者可加。

必须先用旧的 $m$ 算 $e^{m-m'}$，再把 $m$ 覆盖成 $m'$。若先写 `row_max` 再缩放，旧基准就丢了。

切分方式与算法 1 相同：grid 只切行，列 tile 在 block 内循环。`row_max` / `row_sum` 仍是片上 running 状态。

错误写法（v2 初稿）是：先 `row_max = max(row_max, tile_max)`，再 `row_sum += sum(exp(x - row_max))`。当前 tile 的 exp 基准是对的，但**旧的 row_sum 还停在旧 max 上**，两个和不能直接加。

### 8.1 与算法 1 的 IO 对比


|         | 算法 1（v1）            | 算法 2（v2）            |
| ------- | ------------------- | ------------------- |
| 读全局 `A` | 3 遍（max / sum / 写回） | 2 遍（online 累积 / 写回） |
| 写全局 `B` | 1 遍                 | 1 遍                 |
| 片上状态    | `row_max`、`row_sum` | 同样，但 sum 会随 max 重缩放 |


写回仍然要再读一遍 `A`：online 过程只留下每行两个标量，没有把每个 $e^{x_j-m}$ 存下来。

### 8.2 同一 3×5 例子（只跟踪 row0）

tiles 为 `[1, 2, 3] | [4, 5]`。

`ko=0`：

- `tile_max = 3`，`new_max = max(-1e30, 3) = 3`
- `row_sum *= exp(-1e30 - 3) ≈ 0`
- `row_sum += exp(-2)+exp(-1)+exp(0) ≈ 1.503`
- `row_max = 3`

`ko=1`：

- `tile_max = 5`，`new_max = max(3, 5) = 5`
- `row_sum *= exp(3 - 5) = 1.503 * e^{-2} ≈ 0.203`
- `row_sum += exp(-1)+exp(0) ≈ 1.368` → `1.571`
- `row_max = 5`

与算法 1 最终的 `row_max=5`、`row_sum≈1.571` 一致。写回仍是：

```
B[0, :] = [e^-4, e^-3, e^-2, e^-1, e^0] / 1.571
        ≈ [0.012, 0.032, 0.086, 0.234, 0.636]
```

### 8.3 每个 tile 内的步骤

1. `T.copy` → `A_shared`（只读，不改越界格）
2. 越界填 `NEG_INF`，拷进 `tile_fragment`，`reduce_max(dim=1, clear=True)` 得到 `tile_max`
3. `new_max = max(row_max, tile_max)`；`row_sum *= exp(row_max - new_max)`；再 `row_max = new_max`
4. 越界填 `0`，有效位 `exp(x - row_max)`，`reduce_sum(dim=1, clear=True)`
5. `row_sum += tile_reduce`

扫完所有 `ko` 后，再扫一遍 `A` 写 `B[i,j] = exp(A[i,j] - row_max[i]) / row_sum[i]`。

初值：`row_max = NEG_INF`，`row_sum = 0`。第一个 tile 的 scale `exp(NEG_INF - tile_max)` 下溢成 0，旧和保持 0，行为正确。

### 8.4 代码骨架

```python
@tilelang.jit
def tl_softmax_v2(A, BLOCK_N: int, BLOCK_M: int):
    N, M = T.const("N, M")
    A: T.Tensor((N, M), T.float32)
    B = T.empty((N, M), T.float32)

    with T.Kernel(T.ceildiv(N, BLOCK_N), threads=128) as bx:
        A_shared = T.alloc_shared((BLOCK_N, BLOCK_M), T.float32)
        tile_fragment = T.alloc_fragment((BLOCK_N, BLOCK_M), T.float32)
        tile_reduce = T.alloc_fragment((BLOCK_N,), T.float32)
        row_max = T.alloc_fragment((BLOCK_N,), T.float32)
        row_sum = T.alloc_fragment((BLOCK_N,), T.float32)

        T.fill(row_max, NEG_INF)
        T.clear(row_sum)
        num_tiles = T.ceildiv(M, BLOCK_M)

        for ko in range(num_tiles):          # Pass 1: online 累积
            T.copy(A[bx * BLOCK_N, ko * BLOCK_M], A_shared)
            for i, j in T.Parallel(BLOCK_N, BLOCK_M):
                tile_fragment[i, j] = NEG_INF
                if bx * BLOCK_N + i < N and ko * BLOCK_M + j < M:
                    tile_fragment[i, j] = A_shared[i, j]
            T.reduce_max(tile_fragment, tile_reduce, dim=1, clear=True)
            for i in T.Parallel(BLOCK_N):
                new_max = T.max(row_max[i], tile_reduce[i])
                row_sum[i] *= T.exp(row_max[i] - new_max)
                row_max[i] = new_max
            for i, j in T.Parallel(BLOCK_N, BLOCK_M):
                tile_fragment[i, j] = 0.0
                if bx * BLOCK_N + i < N and ko * BLOCK_M + j < M:
                    tile_fragment[i, j] = T.exp(A_shared[i, j] - row_max[i])
            T.reduce_sum(tile_fragment, tile_reduce, dim=1, clear=True)
            for i in T.Parallel(BLOCK_N):
                row_sum[i] += tile_reduce[i]

        for ko in range(num_tiles):          # Pass 2: 写回
            T.copy(A[bx * BLOCK_N, ko * BLOCK_M], A_shared)
            for i, j in T.Parallel(BLOCK_N, BLOCK_M):
                if bx * BLOCK_N + i < N and ko * BLOCK_M + j < M:
                    B[bx * BLOCK_N + i, ko * BLOCK_M + j] = (
                        T.exp(A_shared[i, j] - row_max[i]) / row_sum[i]
                    )

    return B

tl_softmax = tl_softmax_v2
```

测试默认 `BLOCK_N=16, BLOCK_M=256`。极值用例用 `BLOCK_N=1, BLOCK_M=4`。历史入口曾指向 v2；当前 `tl_softmax` 指向 v4。

### 8.5 相对 v1：作业规模上看不到 online 的加速

完整数字以 **第 12 节** 那一次公平对比为准（CUDA Event、warmup 80、repeat 400、三次取中位数）。这里只保留结论：

1. **多数作业 case 只有 1 个列 tile**（`M ≤ 256`）。Online 省的是少扫一遍多个 tile；一块时和 v1 的 Pass1+Pass2 差不多。
2. **小矩阵是启动开销，不是带宽。** `64×4096` 约 1MB，v1/v2 都在 150 us 左右，PyTorch 约 13 us。
3. **v2 每个 tile 多一次 scale。** 公平对比里，即便 `4096×32768`（128 个 tile），v2/v1 仍约 **0.98**，几乎持平。早先「大矩阵 v2 快 40%」是不同次测量、不同 warmup 混出来的，不能当结论。
4. **`(17,513)` 上 v1/v2 都约 1.7 ms**，是 `BLOCK_N=16` 尾块 padding 的实现问题，不是 online 公式更慢。v3 一行一 block 后降到约 17 us。

要超过 v1，必须改调度（v3）和访存特化（v4），而不是再减一趟公式。

即便 v2 把读 `A` 从三遍减到两遍，多数规模仍慢于 `torch.softmax`。下一节用有效带宽说明原因。

## 9. 算法 3：调度与访存优化（`tl_softmax_v3`）

v2 相对 v1 已经把读 `A` 从三遍减到两遍。再慢于 PyTorch，就不是「少一趟公式」能解决的，而是 **CTA 太少、多绕一层 shared、热循环里分支太多**。v3 公式仍是 online softmax，改的是并行切分和数据路径。

### 9.1 先用有效带宽判断瓶颈

假设 online softmax 的 HBM 事务是「读 A 两遍 + 写 B 一遍」，共 `3 * N * M * 4` 字节。用实测耗时除过去，得到 **有效带宽**：

```python
# 有效带宽（GB/s）= 字节数 / 耗时(us) / 1e3
# 3 = 读 A 两遍 + 写 B 一遍
def effective_gbps(n, m, us, passes=3):
    nbytes = n * m * 4 * passes
    return nbytes / us / 1e3
```

C500 的 HBM 峰值大约 1.8 TB/s。用第 12 节同一组耗时计算 v2 / PyTorch 的有效带宽：

| N | M | 数据量 | v2 有效带宽 | PyTorch | 含义 |
|---|---|---|---|---|---|
| 64 | 4096 | 1 MB | **21 GB/s** | 246 GB/s | GPU 几乎空转，不是带宽墙 |
| 1024 | 4096 | 17 MB | 304 | 1542 | v2 仍偏空；PT 已近峰值（或实际少于 3 次 HBM） |
| 4096 | 4096 | 67 MB | 771 | 2026 | CTA 变多，v2 带宽起来，但仍慢于 PT |
| 1024 | 16384 | 67 MB | 310 | 1028 | 同样 67 MB，行少列长 → v2 沿 M 串行 |
| 4096 | 32768 | 537 MB | 798 | 1095 | 进入带宽区，实现细节拉开差距 |

对照代码就能对上号：

```python
# v2：grid 只按 BLOCK_N=16 切行
with T.Kernel(T.ceildiv(N, BLOCK_N), threads=128) as bx:
```

- `N=64` → **4 个 thread block**。几十个 AP 只跑 4 个 CTA，有效带宽约 21 GB/s 是必然的。
- 每个 block 还要把 16 行的整段 `M` **串行**扫完。同样 67 MB，`4096×4096`（256 个 CTA）v2 到 771 GB/s，`1024×16384`（64 个 CTA）只有 310 GB/s。
- 每个 tile 还是 `HBM → A_shared → fragment`，多一次片上搬运和 barrier。

因此优化顺序不是再改公式，而是：

1. **先喂饱 GPU**（一行一个 block）
2. **去掉没有复用的 shared**
3. **少做热循环里的废指令**（第二次边界判断、逐元素除法）

这三条都不增加 HBM 趟数，只提高「同样 3 次访存能跑多满」。测量脚本见第 12 节。

### 9.2 四条具体改动，以及为什么是这四条

**（1）一行一个 block：`T.Kernel(N)`**

```python
with T.Kernel(N, threads=128) as row:
```

`N=64` 时 CTA 从 4 变成 64，对应 9.1 表里约 21 GB/s 那一档。PyTorch last-dim softmax 也是「一行一路」，小 `N` 才能铺开。`BLOCK_N` 仍留在接口里，v3 不用它，只为测试/benchmark 继续传 `BLOCK_N=16`。

**（2）去掉 `A_shared`，HBM 直接进 fragment**

softmax 没有 GEMM 那种 `A` 被同一行多列复用、需要 smem 广播的模式。`T.copy` 进 shared 再搬进寄存器，等于多一轮搬运和 barrier。v3 写成：

```python
chunk[j] = A[row, ko * BLOCK_M + j]   # HBM -> 寄存器
```

**（3）max 之后不重读 A，越界用 `NEG_INF` 自然变成 0**

v2 每个 tile 读两次 `A_shared`：一次给 max，一次给 exp。v3 把原值留在 `chunk` 里就地 `exp`：

```python
for j in T.Parallel(BLOCK_M):
    chunk[j] = T.exp(chunk[j] - row_max[0])
```

越界格在载入时已是 `NEG_INF`，`exp(NEG_INF - row_max)` 下溢成 0，**这一轮不必再写 `if j < M`**。HBM 仍是读 A 两遍（写回还要再读），省的是片上第二次遍历和分支。

**（4）循环外算 `1/row_sum`，写回用乘法**

除法比乘法贵。`inv_sum[0] = 1.0 / row_sum[0]` 提到 Pass 2 外面，每元素一次 `mul`。

刻意没做、以后才值得做的：显式 `float4` 向量 load、整除尺寸的无边界特化、按 `M` 自动选 `threads`。那些是带宽已经上千 GB/s 之后的细节；作业规模上 CTA 数量差两个数量级，先改并行切分。

### 9.3 数据路径

```
Pass 1（每个 row 一个 block，串行扫 ko）
  A[row, tile]  --HBM-->  chunk[BLOCK_M]     越界填 NEG_INF
                  reduce_max(dim=0)
                  row_sum *= exp(old_max - new_max)
                  chunk = exp(chunk - row_max)   就地，不再读 A
                  reduce_sum(dim=0)
                  row_sum += tile_sum

Pass 2
  inv_sum = 1 / row_sum
  A[row, tile]  --HBM-->  exp(x - row_max) * inv_sum  --HBM-->  B
```

`reduce_*` 的 `dim=0`：v3 的 fragment 是一维 `(BLOCK_M,)`，沿这个长度归约到标量。v1/v2 是二维 `(BLOCK_N, BLOCK_M)`，沿列归约所以是 `dim=1`。

### 9.4 代码骨架

```python
@tilelang.jit
def tl_softmax_v3(A, BLOCK_N: int, BLOCK_M: int):
    N, M = T.const("N, M")
    A: T.Tensor((N, M), T.float32)
    B = T.empty((N, M), T.float32)

    with T.Kernel(N, threads=128) as row:
        chunk = T.alloc_fragment((BLOCK_M,), T.float32)
        chunk_reduce = T.alloc_fragment((1,), T.float32)
        row_max = T.alloc_fragment((1,), T.float32)
        row_sum = T.alloc_fragment((1,), T.float32)
        new_max = T.alloc_fragment((1,), T.float32)
        inv_sum = T.alloc_fragment((1,), T.float32)

        T.fill(row_max, NEG_INF)
        T.clear(row_sum)
        num_tiles = T.ceildiv(M, BLOCK_M)

        for ko in range(num_tiles):
            for j in T.Parallel(BLOCK_M):
                chunk[j] = NEG_INF
                if ko * BLOCK_M + j < M:
                    chunk[j] = A[row, ko * BLOCK_M + j]
            T.reduce_max(chunk, chunk_reduce, dim=0, clear=True)
            new_max[0] = T.max(row_max[0], chunk_reduce[0])
            row_sum[0] *= T.exp(row_max[0] - new_max[0])
            row_max[0] = new_max[0]
            for j in T.Parallel(BLOCK_M):
                chunk[j] = T.exp(chunk[j] - row_max[0])
            T.reduce_sum(chunk, chunk_reduce, dim=0, clear=True)
            row_sum[0] += chunk_reduce[0]

        inv_sum[0] = 1.0 / row_sum[0]
        for ko in range(num_tiles):
            for j in T.Parallel(BLOCK_M):
                if ko * BLOCK_M + j < M:
                    B[row, ko * BLOCK_M + j] = (
                        T.exp(A[row, ko * BLOCK_M + j] - row_max[0]) * inv_sum[0]
                    )

    return B

tl_softmax = tl_softmax_v3
```

### 9.5 和 v1/v2 相比改了什么

数字见第 12 节。读法：

- `(17,513)`：v1/v2 约 1.7 ms → v3 约 17 us。`BLOCK_N=16` 包 17 行时第二个 block 几乎全是 padding。
- `(64,4096)` / `(64,8192)`：v2 约 150/297 us → v3 约 29/56 us。CTA 从 4 变成 64。
- 中等规模仍慢于 PT，见 v4。大矩阵上 v3 已经接近或超过 v2 很多，但 `1024×16384` 上要到 v4 才稳定快过 PyTorch。

## 11. 算法 4：按 M 特化（`tl_softmax_v4`）

v3 在中等规模仍慢于 PyTorch，公式已经是 online，差在三件事：

1. `threads=128` 写死，短行浪费、长行 tile 偏小
2. 即使 `M` 能被 `BLOCK_M` 整除，热循环仍有 `if j < M`
3. 有分支的 load 很难被编译成 `float4`

v4 不改 online 公式，只做 **编译期分流**。

### 11.1 为什么是「两个 kernel」而不是 `if ALIGNED`

第一次实现把 aligned / tail 写在同一个 `@tilelang.jit` 函数里，用 `if ALIGNED:` 切换。`ALIGNED` 是 jit 参数，会被降成 TIR 运行时条件，**两个循环都会进 IR**。结果 `row_sum` 累了两遍，输出大约是正确答案的一半。

所以 Python 里选 kernel：

```python
kernel = _tl_softmax_v4_aligned if aligned else _tl_softmax_v4_tail
```

### 11.2 为什么不手写 `T.vectorized(4)`

`T.Parallel(BLOCK_M//4)` 套 `T.vectorized(4)`，下标是 `j*4+v`，layout 推断要求 affine scale=1，直接 InternalError。

可行做法：aligned kernel 里 **连续、无 if** 地 `chunk[j] = A[row, ko*BLOCK_M+j]`，让 `VectorizeLoop` 自己发宽向量。向量宽度的「选择」体现在：只对 `M>=4` 且整除的形状启用这条路径（`vec=4` 记录在 config 里）。

### 11.3 `_pick_v4_config(M, BLOCK_M)`

```python
def _pick_v4_config(m, block_m_hint):
    vec = 4 if m >= 4 else 1
    threads = 64 if m < 128 else 128   # 256 会撑寄存器、occupancy 下降，实测更慢
    block_m = ...
    # M>=4096 时优先 1024/512 等能整除 M 的大 tile，减少 ko 循环
    aligned = 1 if m % block_m == 0 else 0
```

| M | 选出的 (BLOCK_M, threads, aligned, vec) | 含义 |
|---|---|---|
| 1 | (256, 64, 0, 1) | 太短，tail kernel，64 线程 |
| 7 / 513 | (256, 64/128, 0, 4) | 不能整除，tail + 边界 if |
| 256 | (256, 128, 1, 4) | 一行一 tile，无分支 |
| 4096 / 16384 / 32768 | **(1024, 128, 1, 4)** | 大 tile + 无分支；threads 保持 128 |

`THREADS=256` 在中等规模上比 128 更慢，因为每个 CTA 寄存器更多，AP 上同时驻留的 block 变少。自动选 threads 不是越大越好。

数字见第 12 节：`1024×4096` 上 v4/PT 约 1.30；`1024×16384` 与 `4096×32768` 上 v4 已快过 PyTorch（v4/PT 约 0.78~0.79）。

## 12. 公平对比（最终一次）

此前各节的耗时来自不同次运行（warmup/repeat 不同、有的把首次 JIT 算进去、GPU 忙闲不同），所以同一版本数字对不上。下面是 **同一进程、同一输入种子、先全部编译并做正确性检查、再计时** 的一次结果。

方法：

- 设备：MetaX C500；`BLOCK_N=16, BLOCK_M=256`（v4 内部会按 M 重选 tile/threads）
- 计时：`torch.cuda.Event`，不含编译
- warmup 80 次，repeat 400 次；每个 kernel 连跑 3 轮取 **中位数**（微秒）
- 正确性：`atol=rtol=2e-3` 对齐 `torch.softmax`
- 有效带宽：`3 * N * M * 4 / us / 1e3` GB/s（按读 A 两遍 + 写 B 一遍估；若实测超过 HBM 峰值，说明实际不到 3 次或命中缓存）

```python
import statistics
import torch
from solution import tl_softmax_v1, tl_softmax_v2, tl_softmax_v3, tl_softmax_v4

def timed_cuda(fn, warmup=80, repeat=400):
    for _ in range(warmup):
        fn()
    torch.cuda.synchronize()
    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)
    start.record()
    for _ in range(repeat):
        fn()
    end.record()
    torch.cuda.synchronize()
    return start.elapsed_time(end) * 1000.0 / repeat  # us

def median3(fn):
    return statistics.median(timed_cuda(fn) for _ in range(3))
```

| N | M | v1 (us) | v2 (us) | v3 (us) | **v4 (us)** | PyTorch | v2/v1 | v3/v2 | v4/v3 | v4/pt | v4 GB/s | PT GB/s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 21.82 | 11.36 | 11.45 | 11.32 | 7.54 | 0.52 | 1.01 | 0.99 | 1.50 | — | — |
| 3 | 7 | 16.12 | 15.14 | 11.50 | 11.16 | 7.09 | 0.94 | 0.76 | 0.97 | 1.57 | — | — |
| 16 | 256 | 13.37 | 13.53 | 11.32 | 11.14 | 7.05 | 1.01 | 0.84 | 0.98 | 1.58 | 4.4 | 7.0 |
| 17 | 513 | 1697.77 | 1684.85 | 17.37 | 16.39 | 11.31 | 0.99 | **0.01** | 0.94 | 1.45 | 6.4 | 9.2 |
| 64 | 4096 | 145.91 | 150.30 | 29.44 | **14.37** | 12.79 | 1.03 | 0.20 | 0.49 | 1.12 | 219 | 246 |
| 256 | 4096 | 155.73 | 156.50 | 36.52 | 19.32 | 14.74 | 1.00 | 0.23 | 0.53 | 1.31 | 651 | 854 |
| 1024 | 4096 | 165.14 | 165.48 | 62.28 | **42.42** | 32.64 | 1.00 | 0.38 | 0.68 | 1.30 | 1187 | 1542 |
| 4096 | 4096 | 266.90 | 261.26 | 182.78 | 147.57 | 99.37 | 0.98 | 0.70 | 0.81 | 1.48 | 1364 | 2026 |
| 64 | 8192 | 289.23 | 297.49 | 55.60 | 25.86 | 12.45 | 1.03 | 0.19 | 0.47 | 2.08 | 243 | 506 |
| 1024 | 16384 | 659.31 | 649.56 | 234.82 | **155.40** | 195.76 | 0.99 | 0.36 | 0.66 | **0.79** | 1296 | 1028 |
| 4096 | 32768 | 2058.69 | 2019.15 | 1422.27 | **1143.00** | 1470.97 | 0.98 | 0.70 | 0.80 | **0.78** | 1409 | 1095 |

怎么读这一张表：

- **v2 ≈ v1**（大矩阵 v2/v1 ≈ 0.98~1.03）。online 在公平测量下几乎没有稳定加速。
- **v3 是主升档**：一行一 block。`(17,513)` 从 1.7 ms 到 17 us；`N=64` 时大约快 5 倍。
- **v4 再削中等/大对齐矩阵**：大 tile + 无分支。`1024×4096` 为 PT 的 1.30 倍；列更长时 **快过 PyTorch**。
- 作业五组仍略慢于 PT，差在 launch 常数（都是十几微秒量级）。

## 13. 要点回顾

1. 按行 Softmax 的归约状态必须留在 **同一个 thread block** 里，因此 **grid 只切行，列 tile 用循环**。
2. 一次调用仍是 **一个 kernel**；多出来的是 thread block，不是多个 kernel。
3. 最大值用 `reduce_max` + `NEG_INF` 初值；求和用 `reduce_sum` + 越界填 0。
4. 边界一律用全局下标判断，尾块测试才过得去。
5. 算法 1 读 `A` 三遍；算法 2（online）在 max 更新时用 `exp(old_max - new_max)` 重缩放 `row_sum`，读 `A` 两遍。二者写 `B` 都只要一遍。
6. 作业规模上 v2 几乎不加速（公平对比里大矩阵 v2/v1 仍约 0.98）。真正拉开的是 v3 的 CTA 数量和 v4 的无分支大 tile。
7. 有效带宽 = `3*N*M*4 / 耗时`。远低于 HBM 峰值说明 CTA 太少或沿 M 串行。数字以第 12 节那一次测量为准。
8. v3：grid=`N`、去掉 shared、就地 exp。`(17,513)` 从约 1.7 ms 降到约 17 us。
9. v4：按 M 选 tile/threads；整除走独立 aligned kernel。`1024×16384` 起可快过 PyTorch。不要把 aligned/tail 写进同一个 jit `if`。
10. block 太多只会在 AP 上排队；fragment 太大先掉 occupancy、再 spill、再编译/launch 失败。C500 每个 AP 寄存器堆大约 512 KB，每线程大约最多 255 个寄存器。

