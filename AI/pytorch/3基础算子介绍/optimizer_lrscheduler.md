
## 1 **optimizer和scheduler的区别和联系**

**什么是优化器？** 优化器(例如梯度下降法)是在深度学习反向传播过程中，指引损失函数（目标函数）的各个参数往正确的方向更新合适的大小，使得更新后的各个参数让损失函数（目标函数）值不断逼近全局最小。

使用梯度下降进行优化，是几乎所有优化器的核心思想。当我们更新参数时，有两个方面是我们最关心的：

* 首先是优化方向，决定“前进的方向是否正确”，在优化器中反映为**梯度或动量**。
* 其次是步长，决定“每一步迈多远”，在优化器中反映为**学习率**

optimizer是指定 **使用哪个优化器** ，scheduler是 **对优化器的学习率进行调整** 。optimizer.step() 用于更新模型参数，而scheduler.step()是对lr进行调整， optimizer.step()通常用在每个mini-batch之中，而scheduler.step()通常用在epoch里面，但是不绝对的，可以根据具体的需求来做。一般情况下，学习率会随着训练的步骤增加而逐渐减小。

```
model = [Parameter(torch.randn(2, 2, requires_grad=True))]
optimizer = SGD(model, 0.1)
scheduler = ExponentialLR(optimizer, gamma=0.9)

for epoch in range(20):
    for input, target in dataset:
        optimizer.zero_grad()
        output = model(input)
        loss = loss_fn(output, target)
        loss.backward()
        optimizer.step()
    scheduler.step()
```

## 2 optimizer的原理和种类

原理参考[paddle文档](https://paddlepedia.readthedocs.io/en/latest/tutorials/deep_learning/optimizers/gd.html)

代码接口pytorch[官方文档optimize](https://pytorch.org/docs/1.13/optim.html)

## **3.常用scheduler的种类**

pytorch有torch.optim.lr_scheduler模块提供了一些根据epoch训练次数来调整学习率（learning rate）的方法。一般情况下我们会设置随着epoch的增大而逐渐减小学习率从而达到更好的训练效果。学习率的调整应该放在optimizer更新之后，下面是一个参考伪代码：

```
scheduler = ...
for epoch in range(100):
     train(...)
     validate(...)
     scheduler.step()
```

本文介绍的调整学习率的函数都是基于epoch大小变化进行调整的。

### 3.1torch.optim.lr_scheduler.LambdaLR

class torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda, last_epoch=-1)

学习率的更新公式为：  new_l r=λ× initial_l r

 new_l r 是得到的新的学习率，  initial_l r 是初始的学习率，λ是通过参数lr_lambda和epoch得到的。

* optimizer （Optimizer）：要更改学习率的优化器；
* lr_lambda（function or list）：根据epoch计算λ的函数；或者是一个list的这样的function，分别计算各个parameter groups的学习率更新用到的λ；
* last_epoch （int）：最后一个epoch的index，如果是训练了很多个epoch后中断了，继续训练，这个值就等于加载的模型的epoch。默认为-1表示从头开始训练，即从epoch=1开始。

```
import torch
import torch.nn as nn
from torch.optim.lr_scheduler import LambdaLR

initial_lr = 0.1
net_1 = model()

optimizer_1 = torch.optim.Adam(net_1.parameters(), lr = initial_lr)
scheduler_1 = LambdaLR(optimizer_1, lr_lambda=lambda epoch: 1/(epoch+1))

print("初始化的学习率：", optimizer_1.defaults['lr'])

for epoch in range(1, 11):
    # train
    optimizer_1.zero_grad()
    optimizer_1.step()
    print("第%d个epoch的学习率：%f" % (epoch, optimizer_1.param_groups[0]['lr']))
    scheduler_1.step()

初始化的学习率： 0.1
第1个epoch的学习率：0.100000
第2个epoch的学习率：0.050000
第3个epoch的学习率：0.033333
第4个epoch的学习率：0.025000
第5个epoch的学习率：0.020000
第6个epoch的学习率：0.016667
第7个epoch的学习率：0.014286
第8个epoch的学习率：0.012500
第9个epoch的学习率：0.011111
第10个epoch的学习率：0.010000
```

### 3.2 torch.optim.lr_scheduler.StepLR

```
class torch.optim.lr_scheduler.StepLR(optimizer, step_size, gamma=0.1, last_epoch=-1)
```

学习率的更新公式为：  new_l r= initial_l r×γepoch // step_size

参数：

* optimizer （Optimizer）：要更改学习率的优化器；
* step_size（int）：每训练step_size个epoch，更新一次参数；
* gamma（float）：更新lr的乘法因子；
* last_epoch （int）：最后一个epoch的index，如果是训练了很多个epoch后中断了，继续训练，这个值就等于加载的模型的epoch。默认为-1表示从头开始训练，即从epoch=1开始。

```
import torch
import torch.nn as nn
from torch.optim.lr_scheduler import StepLR

initial_lr = 0.1
net_1 = model()

optimizer_1 = torch.optim.Adam(net_1.parameters(), lr = initial_lr)
scheduler_1 = StepLR(optimizer_1, step_size=3, gamma=0.1)

print("初始化的学习率：", optimizer_1.defaults['lr'])

for epoch in range(1, 11):
    # train
    optimizer_1.zero_grad()
    optimizer_1.step()
    print("第%d个epoch的学习率：%f" % (epoch, optimizer_1.param_groups[0]['lr']))
    scheduler_1.step()

初始化的学习率： 0.1
第1个epoch的学习率：0.100000
第2个epoch的学习率：0.100000
第3个epoch的学习率：0.100000
第4个epoch的学习率：0.010000
第5个epoch的学习率：0.010000
第6个epoch的学习率：0.010000
第7个epoch的学习率：0.001000
第8个epoch的学习率：0.001000
第9个epoch的学习率：0.001000
第10个epoch的学习率：0.000100
```

### 3.3 torch.optim.lr_scheduler.MultiStepLR

```
class torch.optim.lr_scheduler.MultiStepLR(optimizer, milestones, gamma=0.1, last_epoch=-1)
```

学习率的更新公式为： new−lr= initial_lr ×γbisect_right ( milestones,epoch )

参数：

* optimizer （Optimizer）：要更改学习率的优化器；
* milestones（list）：递增的list，存放要更新lr的epoch；
* gamma（float）：更新lr的乘法因子；
* last_epoch （int）：最后一个epoch的index，如果是训练了很多个epoch后中断了，继续训练，这个值就等于加载的模型的epoch。默认为-1表示从头开始训练，即从epoch=1开始。

```
import torch
import torch.nn as nn
from torch.optim.lr_scheduler import MultiStepLR

initial_lr = 0.1
net_1 = model()

optimizer_1 = torch.optim.Adam(net_1.parameters(), lr = initial_lr)
scheduler_1 = MultiStepLR(optimizer_1, milestones=[3, 7], gamma=0.1)

print("初始化的学习率：", optimizer_1.defaults['lr'])

for epoch in range(1, 11):
    # train
    optimizer_1.zero_grad()
    optimizer_1.step()
    print("第%d个epoch的学习率：%f" % (epoch, optimizer_1.param_groups[0]['lr']))
    scheduler_1.step()

初始化的学习率： 0.1
第1个epoch的学习率：0.100000
第2个epoch的学习率：0.100000
第3个epoch的学习率：0.100000
第4个epoch的学习率：0.010000
第5个epoch的学习率：0.010000
第6个epoch的学习率：0.010000
第7个epoch的学习率：0.010000
第8个epoch的学习率：0.001000
第9个epoch的学习率：0.001000
第10个epoch的学习率：0.001000
```

### 3.4 torch.optim.lr_scheduler.ExponentialLR

```
class torch.optim.lr_scheduler.ExponentialLR(optimizer, gamma, last_epoch=-1)
```

学习率的更新公式为： new−lr= initial_l r×γepoch

参数：

* optimizer （Optimizer）：要更改学习率的优化器；
* gamma（float）：更新lr的乘法因子；
* last_epoch （int）：最后一个epoch的index，如果是训练了很多个epoch后中断了，继续训练，这个值就等于加载的模型的epoch。默认为-1表示从头开始训练，即从epoch=1开始。

```
import torch
import torch.nn as nn
from torch.optim.lr_scheduler import ExponentialLR

initial_lr = 0.1
net_1 = model()

optimizer_1 = torch.optim.Adam(net_1.parameters(), lr = initial_lr)
scheduler_1 = ExponentialLR(optimizer_1, gamma=0.1)

print("初始化的学习率：", optimizer_1.defaults['lr'])

for epoch in range(1, 11):
    # train
    optimizer_1.zero_grad()
    optimizer_1.step()
    print("第%d个epoch的学习率：%f" % (epoch, optimizer_1.param_groups[0]['lr']))
    scheduler_1.step()

初始化的学习率： 0.1
第1个epoch的学习率：0.100000
第2个epoch的学习率：0.010000
第3个epoch的学习率：0.001000
第4个epoch的学习率：0.000100
第5个epoch的学习率：0.000010
第6个epoch的学习率：0.000001
第7个epoch的学习率：0.000000
第8个epoch的学习率：0.000000
第9个epoch的学习率：0.000000
第10个epoch的学习率：0.000000
```

参考文档：

https://blog.csdn.net/weixin_43977640/article/details/109686618

https://zhuanlan.zhihu.com/p/344294796
