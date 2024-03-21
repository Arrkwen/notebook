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

import time 
loop = 20
t0 = time.time()
for i in range(loop):
    output = model(img_tensor)
t1 = time.time()
print(f"ort run time:{(t1-t0)/loop} ms")