# TileLang 概念与向量加法实践

参考：[tile-ai/tilelang](https://github.com/tile-ai/tilelang)、[Language Basics](https://tilelang.com/programming_guides/language_basics.html)、[Instructions](https://tilelang.com/programming_guides/instructions.html)。

TileLang（tile-lang）是面向 GPU/加速器 kernel 的 DSL：用接近 Python 的写法描述 **按 tile 分块的计算与数据搬运**，由基于 TVM 的编译器 lowering 成高效设备代码。开发者主要关心「一块数据怎么从全局内存搬进片上、在哪算、怎么写回」，而不是手写 CUDA 线程索引细节。

---

## 一、什么叫 Tile？

**Tile（瓦片）** 是问题空间里切出来的一块子区域，也是一次并行计算处理的基本单位。

以长度为 `N` 的向量为例：选 `BLOCK_N = 1024`，就把整条向量切成若干段

```text
[0, 1024)  [1024, 2048)  ...  [⌊N/BLOCK_N⌋·BLOCK_N, N)
```

每一段就是一个 1-D tile。二维矩阵乘法里常见的是 `BM × BN`、`BM × BK` 这类矩形 tile。

为什么要 tile：

1. **匹配硬件并行**：一个 CUDA/MACA thread block 负责一个（或几个）tile。
2. **匹配片上存储容量**：shared / register 装不下整个张量，只能装小的 tile。
3. **控制访存与计算粒度**：`T.copy`、`T.gemm` 等指令都以 tile 为操作对象。

因此 TileLang 的编程模型可以概括为：

> 把全局问题切成 tile → 每个 block 认领一个 tile → 在该 tile 上做拷贝与计算 → 写回全局。

`BLOCK_N`、`BM`、`BN`、`BK` 这类参数就是 **tile size**（瓦片边长），通常是编译时常量，方便编译器做特化与调度。

---

## 二、内存层次（Memory Scope）

TileLang 显式暴露几层软件可控的存储（见 Language Basics §4）：


| Scope          | 接口                               | 硬件含义                            | 可见范围            |
| -------------- | -------------------------------- | ------------------------------- | --------------- |
| **Global**     | `T.Tensor` / `T.empty`           | 设备全局内存（HBM/DRAM）                | 整个 kernel       |
| **Shared**     | `T.alloc_shared(shape, dtype)`   | 片上共享内存                          | 同一 thread block |
| **Fragment**   | `T.alloc_fragment(shape, dtype)` | 寄存器 tile（block 视角的 register 抽象） | 映射到各线程私有寄存器     |
| **Scalar var** | `T.alloc_var(dtype)`             | 标量寄存器                           | 单线程             |


典型数据路径（GEMM 等算子）：

```text
Global  --T.copy-->  Shared  --计算/再拷贝-->  Fragment  --T.copy-->  Global
```

简单 elementwise（如向量加）也可以跳过 Shared，直接 Global ↔ 隐式寄存器。

---

## 三、核心接口说明

下面只覆盖本作业 `solution.py` 会用到的接口；语义以官方文档为准。

### 3.1 `@tilelang.jit` 与张量声明

```python
@tilelang.jit
def tl_add_1d(A, B, BLOCK_N: int):
    N = T.const("N")                 # 从首次调用的输入形状绑定符号 N
    A: T.Tensor((N,), T.float16)     # 全局输入
    B: T.Tensor((N,), T.float16)
    C = T.empty((N,), T.float16)     # 全局输出；eager 模式下由 runtime 分配并返回
    ...
    return C
```


| 接口                      | 含义                                        |
| ----------------------- | ----------------------------------------- |
| `@tilelang.jit`         | 即时编译。首次调用或 `.compile(...)` 时按参数特化 kernel。 |
| `T.const("N")` / 形状绑定   | 把运行时张量长度变成编译期符号。                          |
| `T.Tensor((N,), dtype)` | 声明已有全局 buffer（函数参数）。                      |
| `T.empty(shape, dtype)` | 声明函数输出张量（常见配合 `out_idx=[-1]`）。            |
| `BLOCK_N: int`          | 外层 Python 参数，作为 **tile size** 烘焙进 TIR。    |


显式编译示例：

```python
k = tl_add_1d.compile(N=n, BLOCK_N=1024)
out = k(a, b)
```

`(N, BLOCK_N)` 变了会重新编译。本环境（MACA）每次编译可能打印 `Should support PDL for maca target`，是后端 lowering 的固定提示，与业务逻辑无关。

### 3.2 `T.Kernel`：启动网格

```python
with T.Kernel(grid_x, threads=...) as bx:
    ...
```


| 参数                      | 含义                                                       |
| ----------------------- | -------------------------------------------------------- |
| `grid_x`（及可选 `grid_y`…） | block 网格大小，对应 `blockIdx`。向量加里常用 `T.ceildiv(N, BLOCK_N)`。 |
| `threads`               | 每 block 线程数（可选；也可由 `T.Parallel` 等推断）。                    |
| `bx`（`by`…）             | block 索引。                                                |


`T.ceildiv(a, b)` = ⌈a/b⌉，保证尾块也有一个 block。

一个 block 通常处理一个 tile：起点 `bx * BLOCK_N`，覆盖 `[bx*BLOCK_N, (bx+1)*BLOCK_N)`。

### 3.3 `T.Parallel`：tile 内并行

```python
for i in T.Parallel(BLOCK_N):
    ...
```

- `T.Parallel(ext0, ext1, ...)`：并行循环，适合 elementwise。
- 编译器把迭代映射到 block 内线程，一般不必手写 `threadIdx`。
- 与 `T.serial`（顺序）、`T.Pipelined`（软件流水）并列，见 Language Basics §3。

尾块保护用 Python `if`：

```python
base_idx = bx * BLOCK_N + i
if base_idx < N:
    ...
```

官方也说明：tile 不能整除问题尺寸时，用谓词 guard；`LegalizeSafeMemoryAccess` 可能再插安全检查。

### 3.4 分配：`T.alloc_shared` / `T.alloc_fragment` / `T.clear`


| 接口                               | 含义                                             |
| -------------------------------- | ---------------------------------------------- |
| `T.alloc_shared(shape, dtype)`   | block 内 shared tile，默认 `shared.dyn`。           |
| `T.alloc_fragment(shape, dtype)` | fragment / register tile（Shared View 下的寄存器抽象）。 |
| `T.clear(buf)`                   | 清零（累加器初始化常用）。                                  |
| `T.fill(buf, value)`             | 填常量。                                           |


向量加若走「分阶段」写法，会用到这三者；直接 Global 写法可以不用。

### 3.5 `T.copy`：按 tile 搬数据

```python
T.copy(src, dst)
```

官方语义（Instructions / Language Basics）：

- 在 **Global / Shared / Fragment** 之间移动 **一整块 tile**。
- 接受完整 buffer、buffer region，或带起点的 `BufferLoad`。
- **extent（拷多长）从参数推断**；一侧缺 extent 时，按另一侧对齐（有限 broadcast）。
- 常见写法：**一侧写起点，一侧是带 shape 的 tile buffer** → 拷贝长度 = 该 buffer 的 shape。

```python
# Global → Shared：从全局起点起，拷 A_shared 那么大的一块
T.copy(A[bx * BLOCK_N], A_shared)

# Fragment → Global：把 fragment 写回全局同一起点
T.copy(C_register, C[bx * BLOCK_N])
```

注意：`A[bx]` 表示起点下标是 `bx`，不是 `bx * BLOCK_N`。多 block 时会错位叠写。

编译器可能把 `T.copy` 降成合并访存、向量 load、`cp.async` 等，但对调用方语义是同步的：语句结束后可安全使用 `dst`。

---

## 四、例子：一维向量加法

任务：`C[i] = A[i] + B[i]`，`float16`，`1 ≤ N ≤ 1M`，必须处理 `N` 不整除 `BLOCK_N` 的尾块。入口：`assignment/task2/solution.py` 的 `tl_add_1d(A, B, BLOCK_N)`。

测试规模：`N ∈ {1, 127, 1024, 100003, 1048576}`。比较 `BLOCK_N = 512` 与 `1024`。

两种写法网格相同，差别只在数据路径。`solution.py` **当前生效的是方法 2**。

### 方法 2（推荐入门）：Global 直接加减

数据路径：`Global →（线程寄存器）→ Global`，不经过 Shared，也不显式 `T.copy`。

```python
with T.Kernel(T.ceildiv(N, BLOCK_N)) as bx:
    for i in T.Parallel(BLOCK_N):
        base_idx = bx * BLOCK_N + i
        if base_idx < N:
            C[base_idx] = A[base_idx] + B[base_idx]
```

对应关系：


| 步骤            | 接口                                |
| ------------- | --------------------------------- |
| 按 tile 开 grid | `T.Kernel(T.ceildiv(N, BLOCK_N))` |
| tile 内并行      | `T.Parallel(BLOCK_N)`             |
| 全局下标          | `bx * BLOCK_N + i`                |
| 尾块            | `if base_idx < N`                 |


这与官方 Language Basics 的最小 Vector Add 示例同一思路：每个线程 load → 加 → store。对没有数据复用的 elementwise，通常足够且更短。

**Benchmark（方法 2）**

环境：MACA / TileLang，`float16`，warmup=10，repeat=100；`atol=rtol=1e-2`。

`BLOCK_N=512`

```text
N        correct  TileLang(us)  PyTorch(us)  max_abs_error
1        PASS     13.56         8.42         0.000e+00
127      PASS     13.91         8.09         0.000e+00
1024     PASS     13.60         8.36         0.000e+00
100003   PASS     13.78         8.71         0.000e+00
1048576  PASS     13.92         8.65         0.000e+00
```

`BLOCK_N=1024`

```text
N        correct  TileLang(us)  PyTorch(us)  max_abs_error
1        PASS     14.16         9.32         0.000e+00
127      PASS     13.66         8.48         0.000e+00
1024     PASS     13.84         8.51         0.000e+00
100003   PASS     13.75         8.55         0.000e+00
1048576  PASS     13.84         8.64         0.000e+00
```

### 方法 1（简要）：Shared + Fragment 分阶段

数据路径：`Global → Shared → Fragment → Global`，用 `T.copy` 整块搬 tile。这是 GEMM 等算子的标准 staging 写法；向量加没有复用，多两次搬运，主要作对比练习。

```python
with T.Kernel(T.ceildiv(N, BLOCK_N)) as bx:
    A_shared = T.alloc_shared(BLOCK_N, T.float16)
    B_shared = T.alloc_shared(BLOCK_N, T.float16)
    C_register = T.alloc_fragment(BLOCK_N, T.float16)
    T.clear(C_register)
    T.copy(A[bx * BLOCK_N], A_shared)
    T.copy(B[bx * BLOCK_N], B_shared)
    for k in T.Parallel(BLOCK_N):
        base_idx = bx * BLOCK_N + k
        if base_idx < N:
            C_register[k] = A_shared[k] + B_shared[k]
    T.copy(C_register, C[bx * BLOCK_N])
```

要点：`T.copy` 的起点必须是 `bx * BLOCK_N`，否则多 block 错位。

**Benchmark（方法 1）**

`BLOCK_N=512`

```text
N        correct  TileLang(us)  PyTorch(us)  max_abs_error
1        PASS     14.75         8.19         0.000e+00
127      PASS     14.65         8.30         0.000e+00
1024     PASS     13.91         8.36         0.000e+00
100003   PASS     13.92         8.67         0.000e+00
1048576  PASS     13.63         8.45         0.000e+00
```

`BLOCK_N=1024`

```text
N        correct  TileLang(us)  PyTorch(us)  max_abs_error
1        PASS     13.74         8.58         0.000e+00
127      PASS     14.04         8.40         0.000e+00
1024     PASS     13.39         8.26         0.000e+00
100003   PASS     14.92         8.62         0.000e+00
1048576  PASS     13.86         8.46         0.000e+00
```

### 结果小结

两种方法、两种 `BLOCK_N` 均正确。耗时约 13–15 μs，彼此接近，且普遍慢于 PyTorch（约 8–9 μs）。访存主导的向量加上，Shared staging 几乎不带来收益；作业也不要求超过 PyTorch。方法 2 更适合本题；方法 1 便于理解后续 GEMM 的 tile 搬运模式。