文章参考：  [pytorch 实现MNIST手写数字识别](https://zhuanlan.zhihu.com/p/137571225)， [MMDeploy 模型部署第一张](https://mmdeploy.readthedocs.io/zh-cn/latest/tutorial/01_introduction_to_model_deployment.html)

## 手写数字识别

### 1 训练模型

参考mnist.py，我们定义了如下CNN的网络结构，并且运行mnist.py，我们得到了MNIST.pth的网络模型

```python
class MnistNet(nn.Module):
    def __init__(self):
        super(MnistNet,self).__init__()
  
        self.conv1 = nn.Conv2d(1,10,kernel_size=5)
        self.conv2 = nn.Conv2d(10,20,kernel_size=5)
        self.conv2_drop = nn.Dropout2d()
        self.fc1 = nn.Linear(320,50)
        self.fc2 = nn.Linear(50,10)
  
    def forward(self,x):
        x = F.relu(F.max_pool2d(self.conv1(x),2))
        x = F.relu(F.max_pool2d(self.conv2_drop(self.conv2(x)),2))
        x = x.view(-1,320)
        x = F.relu(self.fc1(x))
        x = F.dropout(x,training=self.training)
        x = F.relu(self.fc2(x))
        return F.log_softmax(x,dim=1)
```

接下来我们尝试将MNIST.pth模型转换为onnx，并测试转换前和转换后的正确性和速度对比。

### 2 测试torch模型

我们先使用如下代码和图片测试上面训练的模型

```python
# 导入相关库
import cv2
import numpy as np
import torch
from mnist import MnistNet

device = "cpu"

# load 模型
model = MnistNet().to(device)
network_state_dict = torch.load('./model/MNIST.pth')
model.load_state_dict(network_state_dict)

# load 测试图片
img_path = "./images/3.jpeg"
image_rgb = cv2.imread(img_path)
# 将RGB图像转换为灰度图像
image_gray = cv2.cvtColor(image_rgb, cv2.COLOR_BGR2GRAY)
# 调整灰度图像的大小为[28, 28]
image_resized = cv2.resize(image_gray, (28, 28))
# 将数据转为mnist数据集的格式
image_modified = np.where(image_resized > 100, 0, 255)
cv2.imwrite("./images/3_gray.jpeg",image_modified)
# 转换为[batch,1,h,w]
img_tensor = torch.from_numpy(image_modified.astype(np.float32)).unsqueeze(dim=0).unsqueeze(dim=0).to(device)

# 预测
model.eval()
output = model(img_tensor)
pred = output.data.max(1)[1].detach().numpy()[0]
print("pred:", pred)
```

### 3 导出onnx模型

```
# 安装 ONNX Runtime, ONNX
pip install onnxruntime onnx
```

```
# 导出batch_size = 1的情况

import torch
x = torch.randn(1,1,28,28)
from mnist import MnistNet

model_path = './model/MNIST.pth'
onnx_path = './model/MNIST.onnx'

# load 模型
model = MnistNet()
network_state_dict = torch.load(model_path)
model.load_state_dict(network_state_dict)

# 导出为onnx模型
with torch.no_grad():
    torch.onnx.export(
        model,
        x,
        onnx_path,
        input_names=["input"],
        output_names=["output"]
    )

# 检查导出是否正确
import onnx
onnx_model = onnx.load(onnx_path)
try:
    onnx.checker.check_model(onnx_model)
except Exception:
    print("Model incorrect")
else:
    print("Model correct")

```

**torch.onnx.export** 是 PyTorch 自带的把模型转换成 ONNX 格式的函数。让我们先看一下前三个必选参数：前三个参数分别是要转换的模型、模型的任意一组输入、导出的 ONNX 文件的文件名。转换模型时，需要原模型和输出文件名是很容易理解的，但为什么需要为模型提供一组输入呢？这就涉及到 ONNX 转换的原理了。从 PyTorch 的模型到 ONNX 的模型，本质上是一种语言上的翻译。直觉上的想法是像编译器一样彻底解析原模型的代码，记录所有控制流。但ONNX 记录通常是不考虑控制流的静态图（即如果源代码有多重控制流，但是静态图只会根据一组输入，转换具体的执行流），因此，PyTorch 提供了一种叫做追踪（trace）的模型转换方法：给定一组输入，再实际执行一遍模型，即把这组输入对应的计算图记录下来，保存为 ONNX 格式。**export** 函数用的就是追踪导出方法，需要给任意一组输入，让模型跑起来。

```
torch.onnx.export 接口的参数介绍： todo

```

接下来可视化转换后的网络模型，对比一下code的网络结构

1 先按照官网安装[netron](https://github.com/lutzroeder/Netron?tab=readme-ov-file)

```
pip install netron
```

2 可视化网络，结果是符合网络结构的。

```
netron ./model/MNIST.onnx
```

### 4 运行onnx模型

```
import cv2
import numpy as np
import onnxruntime

onnx_path = './model/MNIST.onnx'

# 启动onnx runtime 会话
ort_session = onnxruntime.InferenceSession(onnx_path)

# 加载测试图片
img_path = "./images/3_gray.jpeg"
image_rgb = cv2.imread(img_path)
# gray img
image_gray = cv2.cvtColor(image_rgb, cv2.COLOR_BGR2GRAY).astype(np.float32)
# [batch,1,28,28] ort 的输入只能是numpy数组
image_gray = np.expand_dims(image_gray,axis=0)
img_input = np.expand_dims(image_gray,axis=0)

ort_inputs = {'input': img_input}
ort_output = ort_session.run(['output'], ort_inputs)[0]
pred = np.argmax(ort_output[0])
print("ort pred:",pred)
```

这段代码中，除去数据读取预处理操作外，和 ONNX Runtime 相关的代码只有三行。让我们简单解析一下这三行代码。**onnxruntime.InferenceSession** 用于获取一个 ONNX Runtime 推理器，其参数是用于推理的 ONNX 模型文件。推理器的 run 方法用于模型推理，其第一个参数为输出张量名的列表，第二个参数为输入值的字典。其中输入值字典的 key 为张量名，value 为 numpy 类型的张量值。输入输出张量的名称需要和 **torch.onnx.export** 中设置的输入输出名对应。

### 5 torch  vs onnx 运行时间对比

|       | time(ms) |
| ----- | -------- |
| torch | 0.000527 |
| onnx  | 0.000107 |

### 6 TODO事项

1. onnx导出如何支持动态batch? 即动态的input接口
2. onnx导出如何自定义算子？MNIST的算子，onnx or onnxruntime都支持，但遇到未支持的算子，如何解决？
3. onnx导出模型如何支持其它推理引擎(除了onnxruntime，比如TensorRT)

### 7  动态batch支持

参考1torch导出onnx的基础介绍中，关于torch.onnx.export的接口参数详解中的 `dynamic_axes` 接口说明，我们将batch设置为动态轴，完整代码参考mnist_exportt.py

```
# 支持动态batch， 在输入和输出节点上指明动态轴，并给动态轴显示指明名称
dynamic_axes_0 = {
    'input' : {0: 'batch'},
    'output' : {0: 'batch'}
}

onnx_batch_path = './model/MNIST_BATCH.onnx'
with torch.no_grad():
    torch.onnx.export(
        model,
        x,
        onnx_batch_path,
        input_names=["input"],
        output_names=["output"],
        dyn
```

精度测试，是否对齐torch的结果

```python
import torch
import torchvision
import onnxruntime
import numpy as np
from torch.utils.data import DataLoader
import torch.nn.functional as F

# load 模型，启动会话
onnx_path = "./model/MNIST_BATCH.onnx"
ort_session = onnxruntime.InferenceSession(onnx_path)


# load 数据
batch_size_test = 10
test_loader = DataLoader(dataset=torchvision.datasets.MNIST('./data/',train=False,download=True,
                                                     transform=torchvision.transforms.Compose([
                                                         torchvision.transforms.ToTensor(),
                                                         torchvision.transforms.Normalize((0.1307,),(0.3081))
                                                     ])),
                          batch_size=batch_size_test,
                          shuffle=True)


# 精度测试
correct = 0
with torch.no_grad():
    for data, label in test_loader:
        ort_inputs = {"input":data.numpy()}
        ort_output = ort_session.run(['output'], ort_inputs)[0]
        pred = torch.tensor(np.argmax(ort_output,axis=1))
        correct += pred.eq(label.data.view_as(pred)).sum()
    print('\nTest set: Avg. Accuracy: {}/{} ({:.0f}%)\n'.format(
        correct, len(test_loader.dataset),
        100. * correct / len(test_loader.dataset)))

```
