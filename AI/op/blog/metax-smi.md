# 沐曦 C500 / mx-smi 笔记

对照官方文档整理：C500 架构、容器如何挂设备、驱动与框架对应关系、代码里如何看用量。

主要参考：

- [曦云系列通用计算 GPU mx-smi 使用手册](https://developer.metax-tech.com/api/client/document/preview/549/C500_mxsmiManual_CN.html#)
- [曦云系列通用计算 GPU 用户指南](https://developer.metax-tech.com/api/client/document/preview/376/C500_UserGuide_CN.html)
- [运行时 API 编程指南 · 编程接口](https://developer.metax-tech.com/api/client/document/preview/693/split_files/%E7%BC%96%E7%A8%8B%E6%8E%A5%E5%8F%A3.html)
- [MXMACA 发布说明 · 版本兼容性](https://developer.metax-tech.com/api/client/document/preview/1281/split_files/%E7%89%88%E6%9C%AC%E5%85%BC%E5%AE%B9%E6%80%A7.html)
- [AI 推理用户手册（MacaRT / ONNX）](https://developer.metax-tech.com/api/client/document/preview/584/C500_AIInferenceUserGuide_CN.html)
- [mcPyTorch 用户指南 · 功能支持](https://developer.metax-tech.com/api/client/document/preview/1327/split_files/%E5%8A%9F%E8%83%BD%E6%94%AF%E6%8C%81.html)

---

## 1. 沐曦 C500 芯片架构

C500 是沐曦「曦云」系列里的通用计算 GPGPU，不是只跑固定算子的 NPU。官方定位：自研 GPGPU 架构 + 多精度混合算力 + 大容量高带宽显存 + MetaXLink 卡间互联 + MXMACA 软件栈。

### 1.1 硬件与指令集

| 项 | 说明 |
| --- | --- |
| 架构 / ISA | 自研 **XCORE 1.0**（编译目标 `xcore1000` 这一代） |
| 计算单元 | 标量、矢量、张量（含 MMA 类矩阵指令） |
| Compute Capability | **10.xx 为 C500 架构族**；C500 为 `10.00`，同族还有 C550=`10.02`、N260=`10.20` |
| 编译 offload | 通用：`--offload-arch=xcore1000`（同 major 可跑）；型号优化：如 C550 用 `xcore1002` |
| 显存 | 64 GB **HBM2e** |
| 主机接口 | PCIe（用户指南建议 AI 训练/推理把 PCIe Max Payload 设为 256） |
| 卡间互联 | **MetaXLink**（沐曦 D2D），`mx-smi topo` / `mx-smi mxlk` 可查 |
| 视频 | 板卡带 **VPU**，`mx-smi --show-usage` 会同时报 GPU / VPU 使用率 |
| 软件栈 | **MXMACA**（MetaX Advanced Compute Architecture），API 层面向 CUDA 生态兼容 |

同一代里的 minor 用来区分变体，不要把 C500 和 C600（CC `15.xx`）混成一代。

### 1.2 与 NVIDIA 对照时怎么理解

公开资料没有把 SM / warp / cache 层级写到和 CUDA 编程手册同级。工程上可以按下面这套对应来记：

```text
XCORE 计算核心  ≈  CUDA SM
标量 / 矢量     ≈  CUDA Core 一类通用计算
张量 / MMA      ≈  Tensor Core
HBM2e           ≈  设备显存
MetaXLink       ≈  NVLink
MXMACA          ≈  CUDA + cuDNN/cuBLAS + 驱动工具链
mx-smi / MXSML  ≈  nvidia-smi / NVML
sGPU            ≈  软件切分（类似 MIG 的产品形态，实现路径不同）
SR-IOV VF       ≈  硬件虚拟化切分
```

mcPyTorch 为了兼容 CUDA 代码，会把 `torch.cuda.get_device_capability()` 报成 `(8, 0)`（模拟 sm_80），**这不等于芯片真实 CC 10.00**。真实代际以运行时 / `mxcc --offload-arch` 为准。

### 1.3 常见规格（公开二手资料，官方手册未逐项给出）

公开渠道常把 C500 分成 **PCIe** 与 **OAM** 两档，数值仅供对照，以板卡 EEPROM / `mx-smi --show-hwinfo` 为准：

| | PCIe | OAM |
| --- | --- | --- |
| FP32 vector / matrix | 约 15 / 30 TFLOPS | 约 18 / 36 TFLOPS |
| TF32 | 约 120 TFLOPS | 约 140 TFLOPS |
| FP16 / BF16 | 约 240 TFLOPS | 约 280 TFLOPS |
| INT8 | 约 480 TOPS | 约 560 TOPS |
| 显存 | 64 GB HBM2e | 64 GB HBM2e |
| TDP | 约 350 W | 约 450 W |
| 互联 | MetaXLink，常见 2/4 卡 | 常见 8 卡全互联 |

---

## 2. 镜像如何挂载设备，是否要指定虚拟显卡

**默认不需要指定虚拟显卡。** 物理卡 + 宿主机内核驱动装好后，容器只挂设备节点即可。虚拟显卡（sGPU / SR-IOV VF）是可选切分能力，只有要用切分时才开。

### 2.1 容器使用 mx-smi（手册原文场景）

驱动装完后 `mx-smi` 在 `/opt/mxdriver/bin/`，并在 `/usr/bin` 建软链。容器里要查卡：

```bash
docker run --device=/dev/dri \
  -v /opt/mxdriver/bin/mx-smi:/opt/mxdriver/bin/mx-smi \
  <IMAGE-ID>
```

说明：

- `--device=/dev/dri`：把沐曦 DRM 设备挂进容器。
- 只挂 `mx-smi` 二进制时，一般只能跑**查询类**命令。
- 要跑设置类命令（升降固件、reset、电源模式、sGPU 等），启动时加 `--privileged=true`。

用户指南里更完整的跑计算镜像写法（推荐）：

```bash
# 使用全部 GPU
docker run -it --device=/dev/mxcd --device=/dev/dri --group-add video \
  cr.metax-tech.com/library/maca-c500:2.0.0 /bin/bash
```

进入后用 `mx-smi -L` 确认容器里能看到卡。

### 2.2 指定物理卡（不是虚拟卡）

驱动会在 `/dev/dri` 下为每张卡建一对 `card*` + `renderD*`。指定某张物理卡时，绑这一对，并始终带上 `/dev/mxcd`：

```bash
docker run -it --device=/dev/mxcd \
  --device=/dev/dri/card1 \
  --device=/dev/dri/renderD128 \
  --group-add video \
  <IMAGE> /bin/bash
```

查对应关系：

```bash
mx-smi -L
mx-smi --show-sysinfo          # 输出 render id / card id
ls -l /dev/dri/by-path | grep 0000:xx:00.0
```

`--show-sysinfo` 示例字段：`GPU#0 MXC500` → `renderD128` + `card1`。

### 2.3 什么时候才要「虚拟显卡」

手册里有两套，**和普通 docker `--device` 不是一回事**：

| 能力 | 是什么 | 怎么开 | 容器怎么挂 |
| --- | --- | --- | --- |
| **物理 GPU（默认）** | Native 设备模型 | 不用开 | `--device=/dev/mxcd --device=/dev/dri` |
| **sGPU（Sliced GPU）** | 软件切分，一父卡最多 16 子设备；**仅非虚拟化模式** | `mx-smi sgpu --enable -i <GPU-ID>`，再 `--create` | `metax-docker run --gpus="[<sgpu:UUID>, ...]"` |
| **SR-IOV VF** | 硬件虚拟化，一张卡切 1/2/4/8 个 VF | 物理机上 `mx-smi vm --enable-vf {1\|2\|4\|8}` | VF 透传到 VM / 容器，不是随便写一个虚拟卡号 |

sGPU 要点：

- 默认关闭；启用、切分、改配额需要 root。
- 创建时可设 `--vram`、`--compute`、`--alias`。
- 子设备在用时不能 disable / remove。
- 调度：Best Effort / Fixed Share / Burst Share。
- **sGPU 与 SR-IOV 虚拟化模式互斥。**

结论：跑训练/算子开发，挂物理 `mxcd` + `dri` 即可，**不要**额外指定虚拟显卡。只有云上要切分显存/算力时，才在宿主机先切 sGPU/VF，再用 `metax-docker --gpus` 或 VF 透传把切出来的实例挂进容器。

---

## 3. 设备 – 驱动 – ONNX – Torch 的对应关系

### 3.1 软件栈（自下而上）

```text
曦云 C500 硬件（XCORE / HBM / MetaXLink）
        │
        ▼
内核驱动 KMD（Driver 包，/opt/mxdriver）
  · 设备节点：/dev/dri/card*、/dev/dri/renderD*、/dev/mxcd
  · 管理库：libmxsml.so
  · 工具：mx-smi
        │
        ▼
用户态 UMD + SDK（MXMACA，/opt/maca）
  · 运行时 mcruntime、编译器 mxcc
  · 库：mcdnn / mcblas / mccl / mcfft ...
        │
        ├──────────────┬────────────────┐
        ▼              ▼                ▼
   mcPyTorch      MacaRT (ONNX)      其它（IREE / JAX / ...）
   torch.cuda*    onnxruntime + MacaEP
```

对应 NVIDIA 的习惯记法：

| 沐曦 | NVIDIA 习惯 |
| --- | --- |
| C500 + MXMACA | GPU + CUDA Toolkit |
| Driver（KMD） | NVIDIA Driver |
| mcruntime | CUDA Runtime |
| mcdnn / mcblas / mccl | cuDNN / cuBLAS / NCCL |
| mcPyTorch | PyTorch CUDA build |
| MacaRT + MacaEP | ONNX Runtime + CUDA EP |
| mx-smi / MXSML / Pymxsml | nvidia-smi / NVML / pynvml |

### 3.2 版本必须成套匹配

发布说明按「Driver + SDK + PyTorch（+ IREE 等）」整包给出，**不要跨代混装**。C500 相关示例如下（数字以当时发布说明为准）：

| Driver | SDK | PyTorch | 备注 |
| --- | --- | --- | --- |
| Metax-Driver 3.8.0.x | SDK 3.8.0.x | Pytorch 3.8.0.x | 较新年份统一编号 |
| Metax-C500-Driver 3.0.0.5 | SDK 3.0.0.8 | Pytorch 3.0.0.3 | C500 3.0 套件 |
| Metax-C500-Driver 2.32.0.6 | SDK 2.32.0.6 | Pytorch 2.32.0.3 | |
| Metax-C500-Driver 2.31.0.6 | SDK 2.31.0.6 | Pytorch 2.31.0.4 | |

ONNX 不在上述同一张表里单独占一列，而是 **MACA-AI / MacaRT** 包：

- 安装：`dpkg -i onnxruntime-maca_*.deb` → `/opt/maca-ai/onnxruntime-maca`
- Python：`onnxruntime_gpu-1.12.0+mc*.whl`（文档示例，实际以包内 wheel 为准）
- 推理时指定 EP：`MACAExecutionProvider` / C++ `AppendExecutionProvider_MACA`
- 设备：`OrtMACAProviderOptions.device_id`（默认 0）

训练路径：C500 → 匹配代际的 Driver + MXMACA SDK → **同代 mcPyTorch**。  
推理路径：同一套 Driver/SDK → **同代 MacaRT** → ONNX + MacaEP。  
PyTorch 导出 ONNX 可用原生 `torch.onnx` 或工具链里的 **MacaConverter**，再交给 MacaRT。

### 3.3 代码里设备从哪来

- **PyTorch**：API 仍写 `cuda`（`torch.cuda.is_available()`、`tensor.to("cuda")`），backend 实际是 MXMACA。
- **ONNX Runtime**：`providers=["MACAExecutionProvider"]`，`device_id` 对应 `mx-smi` 的 GPU#。
- 容器只挂了部分 `card*`/`renderD*` 时，容器内的 GPU# 从 0 重排，以容器里 `mx-smi -L` 为准。

---

## 4. 代码中如何查看设备用量

分三层：**板卡真实占用**（mx-smi / MXSML）、**本进程框架分配器**（PyTorch）、**sGPU 配额内占用**。

### 4.1 命令行（最快）

```bash
mx-smi                              # 默认总览：功耗、显存、温度、使用率、进程、sGPU
mx-smi --show-usage                 # GPU / VPU 使用率（采样周期内）
mx-smi --show-memory                # 板卡显存 + 可访问的系统内存
mx-smi --show-process               # 占用设备的进程
mx-smi --show-temperature --show-board-power --show-usage -l 500
mx-smi dmon --show-temperature --show-board-power -i 0 -c 100
mx-smi sgpu --show-usage            # 子设备使用率（开了 sGPU 时）
mx-smi sgpu --show-memory
```

`dmon` 默认 1000 ms 轮询。写 CSV：`-o file.csv`。指定卡：`-i 0` 或 `-i 0-3`。

### 4.2 Python：Pymxsml（板卡级，对标 pynvml）

手册要求：先装驱动（`libmxsml.so` 在 `/opt/mxdriver/lib`），再装 SDK 自带的 wheel。

```bash
pip3 install /opt/maca/share/mxsml/pymxsml-*.whl
```

枚举设备（官方示例）：

```python
from pymxsml import *

mxSmlInit()  # 任何 API 之前必须先 init；失败会抛 Python 异常

device_num = mxSmlGetDeviceCount()
for i in range(device_num):
    info = mxSmlGetDeviceInfo(i)
    print("device id", i, ", bdf id:", info.bdfId, ", type:", info.deviceName)
```

C 侧同样：`mxSmlInit()` → `mxSmlGetDeviceCount()` → `mxSmlGetDeviceInfo()`。头文件 `/opt/maca/include/mxsml/MxSml.h`。

使用率 / 显存在手册示例里没有写出函数名。要对齐 `mx-smi --show-usage` / `--show-memory`，以本机头文件和 `/opt/maca/share/mxsml/mxsml_demo.py` 为准，不要猜 NVML 同名 API。运行时记得：

```bash
export LD_LIBRARY_PATH=/opt/mxdriver/lib:$LD_LIBRARY_PATH
```

### 4.3 PyTorch：本进程显存（不是整卡 GPU%）

mcPyTorch 兼容 `torch.cuda` 的 Memory management，适合看**当前进程**吃了多少显存：

```python
import torch

assert torch.cuda.is_available()
print("count:", torch.cuda.device_count())
print("name:", torch.cuda.get_device_name(0))

free_b, total_b = torch.cuda.mem_get_info()
print("free/total GB:", free_b / 1024**3, total_b / 1024**3)
print("allocated GB:", torch.cuda.memory_allocated() / 1024**3)
print("reserved GB:", torch.cuda.memory_reserved() / 1024**3)
print(torch.cuda.memory_summary())
```

含义：

- `memory_allocated` / `memory_reserved`：caching allocator 视角，不是 `mx-smi` 的 GPU 利用率。
- 整卡 GPU% / 别人占的显存：用 mx-smi 或 Pymxsml。
- `get_device_capability()` 返回 `(8, 0)` 是兼容层，不要当 C500 的真实 CC。

### 4.4 ONNX / MacaRT

Session 用 `device_id` 选卡；用量监控仍走 mx-smi / MXSML，Runtime 不替代板卡监控。

---

## 5. 实操最短路径

1. 宿主机：`mx-smi` 能列出 C500。
2. 容器：`--device=/dev/mxcd --device=/dev/dri --group-add video`；不必指定虚拟显卡。
3. 框架：Driver / SDK / mcPyTorch / MacaRT 用同一发布代际。
4. 看用量：命令行 `mx-smi --show-usage --show-memory`；Python 板卡用 Pymxsml，本进程用 `torch.cuda.mem_get_info()`。
