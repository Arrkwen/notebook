# NineToothed 概念与向量加法实践

参考：[NineToothed Documentation](https://ninetoothed.org/)、[The Basics](https://ninetoothed.org/basics.html)、[InfiniTensor/ninetoothed](https://github.com/InfiniTensor/ninetoothed)。本作业入口是 `assignment/task2/ninetoothed_add.py`。

NineToothed 是建立在 [Triton](https://github.com/triton-lang/triton) 上的 DSL：保留 Triton 的编译与并行模型，但用更高层的 **张量元编程（Tensor-Oriented Metaprogramming, TOM）** 描述分块，让开发者不必手写指针、mask、`program_id` 等细节。

官方定位（[ninetoothed.org](https://ninetoothed.org/)）：

> A domain-specific language (DSL) based on Triton, offering higher-level abstractions. Through its tensor-oriented metaprogramming (TOM) model, it empowers developers to write high-performance compute kernels intuitively, without the need to manage low-level details like pointer arithmetic or memory access.

---

## 一、设计意图

GPU kernel 难写的往往不是「每个元素做什么」，而是 **数据怎么切、谁和谁对齐、哪个 program 负责哪一块**。Triton 已经比 CUDA 高一层，但仍要自己算 offset / mask。NineToothed 把这件事拆成两段（**Arrange-and-Apply**）：

| 阶段 | 职责 | 何时发生 |
|---|---|---|
| **Arrangement（排列）** | 对符号张量做编译期元操作：`tile` / `expand` / `squeeze` / `permute` 等，决定分块与多参数之间的对应关系 | 编译期 |
| **Application（施加）** | 描述 **一个 program 拿到的那一块 tile** 上做什么，如 `output = lhs + rhs`、`ntl.dot` | 运行时（每个 program） |

编译器规则（[Basics：Arrange-and-Apply](https://ninetoothed.org/basics.html)）：

1. 按 **排列后最外层张量的 shape** 启动 program。
2. 把 **次外层张量**（也就是每一块 tile）映射到这些 program。
3. 多个参数排列完成后，**最外层 shape 必须一致**，否则无法一对一映射（矩阵乘要用 `expand` 把 A 的行块、B 的列块对齐到 C 的块网格）。

因此 NineToothed 的意图可以概括成：

> 用符号张量在编译期把问题切成层级 tile，用 arrangement 对齐多输入，用 application 写块上的算法；编译器负责 launch 与访存，底层仍走 Triton。

和 TileLang 的对比（概念层，不是性能承诺）：

| | NineToothed | TileLang |
|---|---|---|
| 底座 | Triton | TVM TIR |
| 分块怎么写 | `tensor.tile(...)` 得到嵌套符号张量 | `T.Kernel` + `T.Parallel` / `T.copy` 的 tile 起点 |
| 计算怎么写 | application 里对 **块** 做 `+` / `ntl.dot` | kernel 里对 **下标或 fragment** 赋值 |
| 调优 | `block_size(lower, upper)` 作为 meta-parameter | `BLOCK_N` 等编译期常量，可另开 autotune |

---

## 二、符号、符号张量与 Tile

### 2.1 Symbol

`Symbol` 类似符号计算里的变量：本身不存数，只表示名字或表达式，可参与 `BLOCK_SIZE_M * BLOCK_SIZE_N` 这类编译期运算。

`ninetoothed.block_size(lower_bound, upper_bound)` 会生成一个 **meta-parameter**：不手写具体值时，由编译器在范围内自动搜索（autotune）。调试时可直接写死整数，例如 `BLOCK_SIZE = 1024`。

### 2.2 Symbolic Tensor

`Tensor(ndim)` / `Tensor(shape=...)` 创建的是 **符号张量**：`shape`、`strides` 里是符号，不是真实数据。`Tensor(1)` 表示一维向量模板，`Tensor(2)` 表示矩阵模板。真正的 `torch.Tensor` 只在调用 kernel 时传入。

### 2.3 什么叫 Tile（在九齿里）

`x.tile((BLOCK_SIZE,))` 把一维 `x` 切成两层：

- **外层**：有多少个块，shape ≈ `ceildiv(N, BLOCK_SIZE)`（默认向上取整，覆盖尾块）。
- **内层（`dtype.shape`）**：每个块的长度 `BLOCK_SIZE`。

官方数值例子：长度为 16、`BLOCK_SIZE=2` 时，外层 8 个 program，每个 program 拿到长度 2 的一块。`application` 的参数是 **这一块**，不是整条向量。

尾块：`tile` 默认 `(size + tile - 1) // tile`，最后一个 program 对应不足一块的元素；访存 mask 由编译器插入，作业要求的尾块保护包含在 arrangement 里，不必在 application 里写 `if i < N`。

`tile` 还可指定 `strides`、`dilation`、`floor_mode`。矩阵乘会再 `tile((1, -1))`、`expand`、`squeeze`，得到三层以上的层级张量；**只有最外层用于 launch**，更内层可在 application 里索引、循环。

---

## 三、重要接口

下面覆盖本作业实际用到的，以及读懂官方向量加 / 矩阵乘所需的接口。签名以安装包与 [Python API](https://ninetoothed.org/) 为准。

### 3.1 `Tensor`

```python
from ninetoothed import Tensor

Tensor(1)                    # 一维符号张量（向量加）
Tensor(2)                    # 二维符号张量（矩阵乘）
Tensor(shape=(4, 8))         # 编译期已知形状（文档示例）
```

| 成员 / 方法 | 含义 |
|---|---|
| `shape` | 当前层形状（符号或整数） |
| `dtype` | 嵌套时，内层仍是 `Tensor`，故 `tiled.dtype.shape` 是 tile 大小 |
| `tile(tile_shape, strides=None, dilation=None, floor_mode=False)` | 切成层级张量；`tile_size == -1` 表示该维整维作为一块 |
| `expand` / `squeeze` / `permute` | 对齐多输入最外层 shape、去掉大小为 1 的维 |

### 3.2 `block_size` 与 `Symbol`

```python
BLOCK_SIZE = ninetoothed.block_size(lower_bound=256, upper_bound=8192)
# 或调试：
BLOCK_SIZE = 1024
```

| 接口 | 含义 |
|---|---|
| `Symbol(name)` | 普通符号 |
| `block_size(lower_bound, upper_bound)` | 作为 meta-parameter 的块大小，供 autotune |

作业里：`NINETOOTHED_AUTOTUNE=1` 时用 `block_size(256, 8192)`，否则固定 `1024`。

### 3.3 `arrangement` / `application` / `make`

```python
def arrangement(lhs, rhs, output):
    return (
        lhs.tile((BLOCK_SIZE,)),
        rhs.tile((BLOCK_SIZE,)),
        output.tile((BLOCK_SIZE,)),
    )

def application(lhs, rhs, output):
    output = lhs + rhs   # 写的是「当前 program 的那一块」

kernel = ninetoothed.make(
    arrangement,
    application,
    (Tensor(1), Tensor(1), Tensor(1)),
)
```

| 接口 | 含义 |
|---|---|
| `arrangement(*tensors)` | 返回与参数一一对应的排列结果；最外层 shape 必须对齐 |
| `application(...)` | 块上的计算。`output = lhs + rhs` 会写入对应 tile，不是 Python 局部变量丢掉结果 |
| `ninetoothed.make(arrangement, application, tensors, caller="torch", kernel_name=..., num_warps=..., num_stages=..., max_num_configs=...)` | 把两段拼成可调用 kernel；默认走 `jit` 生成 Triton 并给 PyTorch 调用 |

`make` 会用 `arrangement(*tensors)` 的结果给 `application` 做类型标注，再交给 JIT。`caller="torch"` 得到 Python 可调用对象；`caller` 也可走 AOT。

### 3.4 调用约定

官方向量加调用（与作业包装一致）：

```python
z = torch.empty_like(x)
kernel(x, y, z)
```

kernel **不负责分配输出**。`nt_add_1d` 里的 `torch.empty_like` 是 host 包装，计时时会算进延迟；下面对比 `BLOCK_SIZE` 的表格用的是 **预先分配 output 再反复 launch**，更接近 kernel 本身。

### 3.5 Application 里常用计算（向量加用不到，矩阵乘会用）

| 接口 | 含义 |
|---|---|
| `ntl.zeros(shape, dtype=...)` | 块上累加器 |
| `ntl.dot(a, b)` | 小块矩阵乘 |
| `input[k]` / `range(input.shape[0])` | 层级张量的索引与迭代 |

向量加的 application 只有一行 `output = lhs + rhs`，因为每个 program 已经只看到对齐好的一维 tile。

---

## 四、例子：一维向量加法

任务：`output[i] = lhs[i] + rhs[i]`，`float16`，处理尾块。默认 `BLOCK_SIZE = 1024`。测试 `size=98432`；benchmark 长度为 `2^18` … `2^27`。

```python
def arrangement(lhs, rhs, output):
    lhs_tile = lhs.tile((BLOCK_SIZE,))
    rhs_tile = rhs.tile((BLOCK_SIZE,))
    output_tile = output.tile((BLOCK_SIZE,))
    return lhs_tile, rhs_tile, output_tile

def application(lhs, rhs, output):
    output = lhs + rhs
```

对应关系：

| 步骤 | 九齿里是谁做的 |
|---|---|
| 按 `BLOCK_SIZE` 切块、尾块 ceildiv | `tile((BLOCK_SIZE,))` |
| 三个向量块网格对齐 | 三次同样的 `tile`，最外层 shape 相同 |
| 每个 program 逐元素加 | `application` 里的 `+`（编译成 Triton load/add/store） |
| launch 多少个 program | 外层长度 `ceildiv(N, BLOCK_SIZE)` |

`solution.py` 里 TileLang 要自己写 `bx * BLOCK_N + i` 和 `if base_idx < N`；九齿把这两步收进 `tile` + 编译器。

---

## 五、不同 `BLOCK_SIZE` 的加法结果

环境：MACA，`float16`，`triton.testing.do_bench`，单位微秒。output 预分配。正确性：`torch.allclose` 全部 PASS。PyTorch 列为同一 `size` 下 `torch.add` 的一次测量，便于对照。

| size | BS=256 | BS=512 | BS=1024（作业默认） | BS=4096 | BS=8192 | PyTorch |
|---:|---:|---:|---:|---:|---:|---:|
| 262144 | 34.68 | 29.64 | 30.67 | 30.21 | 30.44 | 33.89 |
| 524288 | 40.86 | 39.43 | 35.79 | 34.83 | 34.85 | 35.69 |
| 1048576 | 58.24 | 44.02 | 34.12 | 31.34 | 33.13 | 37.78 |
| 2097152 | 78.69 | 55.76 | 50.47 | 40.96 | 47.26 | 40.65 |
| 4194304 | 129.54 | 80.95 | 52.65 | 43.78 | 44.06 | 49.00 |
| 8388608 | 216.76 | 121.98 | 75.49 | 60.78 | 60.75 | 60.46 |
| 16777216 | 405.47 | 211.81 | 124.79 | 95.83 | 94.27 | 93.46 |
| 33554432 | 769.05 | 394.19 | 211.91 | 166.01 | 163.01 | 161.71 |
| 67108864 | 1498.38 | 755.86 | 391.83 | 297.63 | 296.21 | 295.21 |
| 134217728 | 2937.04 | 1467.15 | 759.01 | **565.25** | 569.01 | 559.18 |

读表：

1. **小 N**（≤2^18）几种 block 都在 ~30 μs，和 PyTorch 差不多，主要是 launch / 框架开销。
2. **大 N** 是显存带宽问题。`BLOCK_SIZE=256` 在 `2^27` 上约 **2937 μs**，默认 **1024** 约 **759 μs**，**4096/8192** 约 **565 μs**，已贴近 PyTorch **559 μs**。
3. 作业默认 1024 在大向量上大约慢 PyTorch **35%**；把 tile 提到 4096 后缺口基本消失。autotune 上界若停在 1024，搜不到这条更快的配置。
4. 同一规模下 TileLang（`benchmark_add.py`，`BLOCK_N=1024`）在 `2^27` 约 **542 μs**，与 PyTorch 几乎重合。九齿默认 1024 更慢，是 Triton 生成配置（tile / warp）没吃满带宽，不是 `lhs + rhs` 写错。

`nt_add_1d` 每次 `empty_like` 再 launch，终端里的包装耗时会略高于上表（大 N 上常见 ~780 μs vs kernel ~760 μs）。对比 block size 时应用同一套计时方式。

---

## 六、开发体验（对照作业要求）

九齿向量加的心智负担很低：`arrangement` 三次 `tile`，`application` 一行加法，尾块由 `tile` 的 ceildiv 处理。和 TileLang 相比，不必写 `T.Kernel`、全局下标和 `T.copy` 起点。代价是性能细节（`BLOCK_SIZE`、`num_warps`）藏在 meta-parameter 和 Triton 后端里；默认 1024 在大向量上明显慢于 PyTorch / TileLang，加大 block 或打开并放宽 autotune 后可以追平带宽。对作业来说，正确性优先，默认 1024 可以交差；若要讲清分块，应同时给出 256 与 4096 的对比。
