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
        dynamic_axes=dynamic_axes_0
    )
onnx_batch_model = onnx.load(onnx_batch_path)
try:
    onnx.checker.check_model(onnx_batch_model)
except Exception:
    print("Model batch incorrect")
else:
    print("Model batch correct")