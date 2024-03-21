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

import time 
loop = 20
t0 = time.time()
for i in range(loop):
    ort_output = ort_session.run(['output'], ort_inputs)[0]
t1 = time.time()
print(f"ort run time:{(t1-t0)/loop} ms")