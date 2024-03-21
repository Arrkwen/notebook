## 初识模型部署

对于深度学习模型来说，模型部署指让训练好的模型在特定环境中高效运行是AI应用的最后一公里。因为开发语言，底层推理引擎之间的不统一，因此需要中间表示来串联，完成模型的快速部署。即产生了如下的部署流程。该流程有两个优势：模型训练阶段可以使用不同的训练框架进行模型训练，不用关心底层的运行逻辑；模型部署阶段，可以通过中间表示的网络优化+推理引擎的算子优化实现模型推理加速。

![pipeline](https://user-images.githubusercontent.com/4560679/156556619-3da7a572-876b-4909-b26f-04e81190c546.png)

## torch.onnx.export导出原理介绍

以下讲解参考自：[mmdeploy](https://mmdeploy.readthedocs.io/zh-cn/latest/tutorial/03_pytorch2onnx.html)， 经过测试后，torch 1.x版本的结果和如下讲解一致，但是2.2.x后 trace和script输出到onnx可视化结果完全是一样的，2.0和21没有测试，应该是2.x之后到改动，因此以下讲解都是基于1.11.0的torch版本。

[TorchScript](https://pytorch.org/docs/stable/jit.html) 是一种序列化和优化 PyTorch 模型的格式，在优化过程中，一个 `torch.nn.Module`模型会被转换成 TorchScript 的 `torch.jit.ScriptModule`模型。现在， TorchScript 也被常当成一种中间表示使用。[OpenMMLab的文章](https://zhuanlan.zhihu.com/p/486914187)中对 TorchScript 有详细的介绍，这里介绍 TorchScript 仅用于说明 PyTorch 模型转 ONNX的原理。 `torch.onnx.export`中需要的模型实际上是一个 `torch.jit.ScriptModule`。而要把普通 PyTorch 模型转一个这样的 TorchScript 模型，有跟踪（trace）和脚本化（script）两种导出计算图的方法。如果给 `torch.onnx.export`传入了一个普通 PyTorch 模型(`torch.nn.Module`)，那么这个模型会默认使用跟踪的方法导出。这一过程如下图所示：

![image](https://user-images.githubusercontent.com/47652064/163531613-9eb3c851-933e-4b0d-913a-bf92ac36e80b.png)

跟踪法只能通过实际运行一遍模型的方法导出模型的静态图，即无法识别出模型中的控制流（如循环）；脚本化则能通过解析模型来正确记录所有的控制流。我们以下面这段代码为例来看一看这两种转换方法的区别：

```python
import torch

class Model(torch.nn.Module):
    def __init__(self, n):
        super().__init__()
        self.n = n
        self.conv = torch.nn.Conv2d(3, 3, 3)

    def forward(self, x):
        for i in range(self.n):
            x = self.conv(x)
        return x



models = [Model(2), Model(3)]
model_names = ['model_2', 'model_3']

for model, model_name in zip(models, model_names):
    dummy_input = torch.rand(1, 3, 10, 10)
    dummy_output = model(dummy_input)
    model_trace = torch.jit.trace(model, dummy_input)
    model_script = torch.jit.script(model)

    # 跟踪法与直接 torch.onnx.export(model, ...)等价
    torch.onnx.export(model_trace, dummy_input, f'{model_name}_trace.onnx',example_outputs=dummy_output)
    # 脚本化必须先调用 torch.jit.sciprt
    torch.onnx.export(model_script, dummy_input, f'{model_name}_script.onnx',example_outputs=dummy_output)
```

在这段代码里，定义了一个带循环的模型，模型通过参数 `n`来控制输入张量被卷积的次数。之后，各创建了一个 `n=2`和 `n=3`的模型。把这两个模型分别用跟踪和脚本化的方法进行导出。 值得一提的是，由于这里的两个模型（`model_trace`, `model_scrip`)是 TorchScript 模型，`export`函数已经不需要再运行一遍模型了。（如果模型是用跟踪法得到的，那么在执行 `torch.jit.trace`的时候就运行过一遍了；而用脚本化导出时，模型不需要实际运行）参数中的 `dummy_input`和 `dummy_output`仅仅是为了获取输入和输出张量的类型和形状。 运行上面的代码，我们把得到的4个 onnx 文件用 [netron](https://github.com/lutzroeder/Netron?tab=readme-ov-file)可视化：

![image](https://user-images.githubusercontent.com/47652064/163531637-994ffa0a-847d-4c0d-a9e3-0ecd78c9a3aa.png)

首先看跟踪法得到的 ONNX 模型结构。可以看出来，对于不同的 `n`,ONNX 模型的结构是不一样的。

![image](https://user-images.githubusercontent.com/47652064/163531659-b06e5df2-6e18-462e-82ff-b16d95b9765c.png)

而用脚本化的话，最终的 ONNX 模型用 `Loop` 节点来表示循环。这样哪怕对于不同的 `n`，ONNX 模型也有同样的结构。 由于推理引擎对静态图的支持更好，通常我们在模型部署时不需要显式地把 PyTorch 模型转成 TorchScript 模型，直接把 PyTorch 模型用 `torch.onnx.export` 跟踪导出即可。了解这部分的知识主要是为了在模型转换报错时能够更好地定位问题是否发生在 PyTorch 转 TorchScript 阶段。

## torch.onnx.export接口详解

参考的是torch 1.11.0的版本，其它版本自行根据接口说明调整，该函数详细的 API 文档可参考 [torch.onnx ‒ PyTorch 1.11.0 documentation](https://pytorch.org/docs/stable/onnx.html#functions)

```python
def export(model, args, f, export_params=True, verbose=False, training=TrainingMode.EVAL,
           input_names=None, output_names=None, aten=False, export_raw_ir=False,
           operator_export_type=None, opset_version=None, _retain_param_name=True,
           do_constant_folding=True, example_outputs=None, strip_doc_string=True,
           dynamic_axes=None, keep_initializers_as_inputs=None, custom_opsets=None,
           enable_onnx_checker=True, use_external_data_format=False):
```

前三个必选参数为模型、模型输入、导出的 onnx 文件名，我们对这几个参数已经很熟悉了。我们来着重看一下后面的一些常用可选参数。

#### args

模型forward函数的参数输入，因为只是将计算图转化为静态图，不用关心数据正确性，因此一般使用随机数构造。只接受元组，张量，或者字典，其中蟑螂和字典都会转为元组输入。

```python
# 张量形式，其中张量x会被默认转换为(x,)
class Model(torch.nn.Module):
      def forward(self, x):
          ...
          return x

model=Model()
x = torch.randn(2,3)
torch.onnx.export(model, x, 'test.onnx')

# 元组形式
class Model(torch.nn.Module):
      def forward(self, k, x):
          ...
          return x

model = Model()
k = torch.randn(2, 3)
x = torch.randn(2, 3)
torch.onnx.export(model, (k,x), 'test.onnx')

# 具名字典形式
class Model(torch.nn.Module):
      def forward(self, k, x):
          ...
          return x

model = Model()
k = torch.randn(2, 3)
x = {torch.tensor(1.): torch.randn(2, 3)}
torch.onnx.export(model, (k, x, {}), 'test.onnx')
```

#### export_params

模型中是否存储模型权重。一般中间表示包含两大类信息：模型结构和模型权重，这两类信息可以在同一个文件里存储，也可以分文件存储。ONNX 是用同一个文件表示记录模型的结构和权重的。 我们部署时一般都默认这个参数为 True。如果 onnx 文件是用来在不同框架间传递模型（比如 PyTorch 到 Tensorflow）而不是用于部署，则可以令这个参数为 False。

#### input_names, output_names

设置输入和输出张量的名称。如果不设置的话，会自动分配一些简单的名字（如数字）。 ONNX 模型的每个输入和输出张量都有一个名字。很多推理引擎在运行 ONNX 文件时，都需要以“名称-张量值”的数据对来输入数据，并根据输出张量的名称来获取输出数据。在进行跟张量有关的设置（比如添加动态维度）时，也需要知道张量的名字。 在实际的部署流水线中，我们都需要设置输入和输出张量的名称，并保证 ONNX 和推理引擎中使用同一套名称。

#### dynamic_axes

指定输入输出张量的哪些维度是动态的。 为了追求效率，ONNX 默认所有参与运算的张量都是静态的（张量的形状不发生改变）。但在实际应用中，我们又希望模型的输入张量是动态的，尤其是本来就没有形状限制的全卷积模型。因此，我们需要显式地指明输入输出张量的哪几个维度的大小是可变的。 我们来看一个 `dynamic_axes`的设置例子：

```
import torch

class Model(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.conv = torch.nn.Conv2d(3, 3, 3)

    def forward(self, x):
        x = self.conv(x)
        return x


model = Model()
dummy_input = torch.rand(1, 3, 10, 10)
model_names = ['model_static.onnx',
'model_dynamic_0.onnx',
'model_dynamic_23.onnx']

dynamic_axes_0 = {
    'in' : [0],
    'out' : [0]
}
dynamic_axes_23 = {
    'in' : [2, 3],
    'out' : [2, 3]
}

torch.onnx.export(model, dummy_input, model_names[0],
input_names=['in'], output_names=['out'])
torch.onnx.export(model, dummy_input, model_names[1],
input_names=['in'], output_names=['out'], dynamic_axes=dynamic_axes_0)
torch.onnx.export(model, dummy_input, model_names[2],
input_names=['in'], output_names=['out'], dynamic_axes=dynamic_axes_23)
```

首先，我们导出3个 ONNX 模型，分别为没有动态维度、第0维动态、第2第3维动态的模型。 在这份代码里，我们是用列表的方式表示动态维度，例如：

```
dynamic_axes_0 = {
    'in' : [0],
    'out' : [0]
}
```

由于 ONNX 要求每个动态维度都有一个名字，这样写的话会引出一条 UserWarning，警告我们通过列表的方式设置动态维度的话系统会自动为它们分配名字。一种显式添加动态维度名字的方法如下：

```python
dynamic_axes_0 = {
    'in' : {0: 'batch'},
    'out' : {0: 'batch'}
}
```

由于在这份代码里我们没有更多的对动态维度的操作，因此简单地用列表指定动态维度即可。 之后，我们用下面的代码来看一看动态维度的作用：

```
import onnxruntime
import numpy as np

origin_tensor = np.random.rand(1, 3, 10, 10).astype(np.float32)
mult_batch_tensor = np.random.rand(2, 3, 10, 10).astype(np.float32)
big_tensor = np.random.rand(1, 3, 20, 20).astype(np.float32)

inputs = [origin_tensor, mult_batch_tensor, big_tensor]
exceptions = dict()

for model_name in model_names:
    for i, input in enumerate(inputs):
        try:
            ort_session = onnxruntime.InferenceSession(model_name)
            ort_inputs = {'in': input}
            ort_session.run(['out'], ort_inputs)
        except Exception as e:
            exceptions[(i, model_name)] = e
            print(f'Input[{i}] on model {model_name} error.')
        else:
            print(f'Input[{i}] on model {model_name} succeed.')
```

我们在模型导出计算图时用的是一个形状为 `（1，3，10，10)`的张量。现在，我们来尝试以形状分别是 `(1,3,10,10),(2,3,10,10),(1,3,20,20)`为输入，用ONNX Runtime运行一下这几个模型，看看哪些情况下会报错，并保存对应的报错信息。得到的输出信息应该如下：

```
Input[0] on model model_static.onnx succeed.
Input[1] on model model_static.onnx error.
Input[2] on model model_static.onnx error.
Input[0] on model model_dynamic_0.onnx succeed.
Input[1] on model model_dynamic_0.onnx succeed.
Input[2] on model model_dynamic_0.onnx error.
Input[0] on model model_dynamic_23.onnx succeed.
Input[1] on model model_dynamic_23.onnx error.
Input[2] on model model_dynamic_23.onnx succeed.
```

可以看出，形状相同的 `(1,3,10,10)`的输入在所有模型上都没有出错。而对于batch（第0维）或者长宽（第2、3维）不同的输入，只有在设置了对应的动态维度后才不会出错。我们可以错误信息中找出是哪些维度出了问题。比如我们可以用以下代码查看 `input[1]在 model_static.onnx`中的报错信息：

```
print(exceptions[(1, 'model_static.onnx')])

# output
# [ONNXRuntimeError] : 2 : INVALID_ARGUMENT : Got invalid dimensions for input: in for the following indices index: 0 Got: 2 Expected: 1 Please fix either the inputs or the model.
```

这段报错告诉我们名字叫 `in`的输入的第0维不匹配。本来该维的长度应该为1，但我们的输入是2。实际部署中，如果我们碰到了类似的报错，就可以通过设置动态维度来解决问题。

### do_constant_folding

常量折叠，一些node的输入输出都是常量，就会被默认折叠，这里面可能会有一些坑，暂时留个todo吧，后续再找个example 补充一下，之前是有遇到

### opset_version

转换时参考哪个 ONNX 算子集版本，不同的pytorch版本默认的opset_version不一样，下面进行详细介绍

## PyTorch 对 ONNX 的算子支持

在确保 `torch.onnx.export()`的调用方法无误后，PyTorch 转 ONNX 时最容易出现的问题就是算子不兼容了。这里我们会介绍如何判断某个 PyTorch 算子在 ONNX 中是否兼容，以助大家在碰到报错时能更好地把错误归类。而具体添加算子的方法我们会在之后的文章里介绍。 在转换普通的 `torch.nn.Module`模型时，PyTorch 一方面会用跟踪法执行前向推理，把遇到的算子整合成计算图；另一方面，PyTorch 还会把遇到的每个算子翻译成 ONNX 中定义的算子。在这个翻译过程中，可能会碰到以下情况：

* 该算子可以一对一地翻译成一个 ONNX 算子。
* 该算子在 ONNX 中没有直接对应的算子，会翻译成一至多个 ONNX 算子。
* 该算子没有定义翻译成 ONNX 的规则，报错。

那么，该如何查看 PyTorch 算子与 ONNX 算子的对应情况呢？由于 PyTorch 算子是向 ONNX 对齐的，这里我们先看一下 ONNX 算子的定义情况，再看一下 PyTorch 定义的算子映射关系。

### ONNX 算子文档

ONNX 算子的定义情况，都可以在官方的[算子文档](https://github.com/onnx/onnx/blob/main/docs/Operators.md)中查看。这份文档十分重要，我们碰到任何和 ONNX 算子有关的问题都得来”请教“这份文档。

![image](https://user-images.githubusercontent.com/47652064/163531682-306991b9-1ffe-49fe-8aee-be27b618b096.png)

这份文档中最重要的开头的这个算子变更表格。表格的第一列是算子名，第二列是该算子发生变动的算子集版本号，也就是我们之前在 `torch.onnx.export`中提到的 `opset_version`表示的算子集版本号。通过查看算子第一次发生变动的版本号，我们可以知道某个算子是从哪个版本开始支持的；通过查看某算子小于等于 `opset_version`的第一个改动记录，我们可以知道当前算子集版本中该算子的定义规则。

![image](https://user-images.githubusercontent.com/47652064/163531690-2d70e6d2-728b-4f7f-8f5a-efaaf620ff02.png)

通过点击表格中的链接，我们可以查看某个算子的输入、输出参数规定及使用示例。比如上图是Relu在 ONNX 中的定义规则，这份定义表明 Relu 应该有一个输入和一个输入，输入输出的类型相同，均为 tensor。

### PyTorch 对 ONNX 算子的映射

在 PyTorch 中，和 ONNX 有关的定义全部放在 [torch.onnx 目录](https://github.com/pytorch/pytorch/tree/main/torch/onnx)中，如下图所示：

![image](https://user-images.githubusercontent.com/47652064/163531700-ddf994e5-6989-483c-a1a3-f1b50dfd84f0.png)

其中，`symbloic_opset{n}.py`（符号表文件）即表示 PyTorch 在支持第 n 版 ONNX 算子集时新加入的内容。我们之前讲过， bicubic 插值是在第 11 个版本开始支持的。我们以它为例来看看如何查找算子的映射情况。 首先，使用搜索功能，在 `torch/onnx`文件夹搜索”bicubic”，可以发现这个这个插值在第 11 个版本的定义文件中：

![image](https://user-images.githubusercontent.com/47652064/163531714-7cf9b784-5b7f-4438-ba01-8cff4c7c9ddc.png)

之后，我们按照代码的调用逻辑，逐步跳转直到最底层的 ONNX 映射函数：

```
upsample_bicubic2d = _interpolate("upsample_bicubic2d", 4, "cubic")

->

def _interpolate(name, dim, interpolate_mode):
    return sym_help._interpolate_helper(name, dim, interpolate_mode)

->

def _interpolate_helper(name, dim, interpolate_mode):
    def symbolic_fn(g, input, output_size, *args):
        ...

    return symbolic_fn
```

最后，在 `symbolic_fn`中，我们可以看到插值算子是怎么样被映射成多个 ONNX 算子的。其中，每一个 `g.op`就是一个 ONNX 的定义。比如其中的 `Resize`算子就是这样写的：

```
    return g.op("Resize",
                input,
                empty_roi,
                empty_scales,
                output_size,
                coordinate_transformation_mode_s=coordinate_transformation_mode,
                cubic_coeff_a_f=-0.75,  # only valid when mode="cubic"
                mode_s=interpolate_mode,  # nearest, linear, or cubic
                nearest_mode_s="floor")  # only valid when mode="nearest"
```

通过在前面提到的 ONNX 算子文档中查找 [Resize 算子的定义](https://github.com/onnx/onnx/blob/main/docs/Operators.md#resize)，我们就可以知道这每一个参数的含义了。用类似的方法，我们可以去查询其他 ONNX 算子的参数含义，进而知道 PyTorch 中的参数是怎样一步一步传入到每个 ONNX 算子中的。 掌握了如何查询 PyTorch 映射到 ONNX 的关系后，我们在实际应用时就可以在 `torch.onnx.export()`的 `opset_version`中先预设一个版本号，碰到了问题就去对应的 PyTorch 符号表文件里去查。如果某算子确实不存在，或者算子的映射关系不满足我们的要求，我们就可能得用其他的算子绕过去，或者自定义算子了。

按照1自定义CNN网络结构实战吧。
