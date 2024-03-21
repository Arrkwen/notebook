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


# 启动onnx runtime 会话
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

import torch
import torchvision

class Model(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.conv1 = torch.nn.Conv2d(3, 18, 3)
        self.conv2 = torchvision.ops.DeformConv2d(3, 3, 3)

    def forward(self, x):
        return self.conv2(x, self.conv1(x))