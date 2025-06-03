# 现在展示的结果是text_feat的结果比image_feat的结果更好，那我们先使用网络结构学习text_feat
# 原来的网络结构

import torch
import clip
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F

import torchvision.transforms as transforms
from torch.utils.data import DataLoader
from torchvision.datasets import Caltech101
from PIL import Image

def load_image(image_path):
    img = Image.open(image_path)
    if img.mode != "RGB":
        img = img.convert("RGB")  # caltech101数据集中存在灰度图片，统一转换成 RGB
    return img

class ConvertToRGB:
    def __call__(self, img):
        return img.convert("RGB") if img.mode != "RGB" else img

transform = transforms.Compose([
    ConvertToRGB(),  
    transforms.Resize((224, 224)),  
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
])


# 加载数据集
data="/media/nvme1n1p1/users/xiaokun1/notebook/AI/pytorch/2网络结构/data"
trainset = Caltech101(root=data, download=True, transform=transform)
testset = Caltech101(root=data, download=True, transform=transform)

# 生成 DataLoader
trainloader = DataLoader(trainset, batch_size=32, shuffle=True,num_workers=2)
testloader = DataLoader(testset, batch_size=32, shuffle=False,num_workers=2)

# 获取类别数
num_classes = len(trainset.categories)
print(f"Caltech-101 共有 {num_classes} 个类别")


device = "cuda" if torch.cuda.is_available() else "cpu"
vit_B16="/media/nvme1n1p1/users/xiaokun1/notebook/AI/mllm/code/clip/model/ViT-B-16.pt"
model, preprocess = clip.load(vit_B16, device=device)

categories = []
for i in range(101):
    categories.append(testset.categories[i])
print(categories)
# testset.categories[testset.y[index]]

# 测试文本feature的精度
text_template = [f"a photo of {x}" for x in categories]
text = clip.tokenize(text_template).to(device)

with torch.no_grad():
    text_features = model.encode_text(text)
    text_features = F.normalize(text_features, dim=-1)

class CosineSimilarityLoss(nn.Module):
    def __init__(self, margin=0.0):
        super(CosineSimilarityLoss, self).__init__()
        # self.margin = margin  # 可选的 margin（用于负样本）

    def forward(self, prediction, target):
        """
        :param prediction: 预测的特征（生成图像的特征）
        :param target: 目标图像的特征
        :return: Cosine 相似度损失
        """
        # 计算 Cosine 相似度
        cosine_sim = F.cosine_similarity(prediction, target)
        loss = 1 - cosine_sim.mean()  # 计算 1 - cosine_similarity 作为损失
        return loss


class AlexNet(nn.Module):
    def __init__(self) -> None:
        super(AlexNet).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=11, stride=4, padding=2),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
            nn.Conv2d(64, 192, kernel_size=5, padding=2),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
            nn.Conv2d(192, 384, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(384, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(256, 256, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=3, stride=2),
        )
        self.avgpool = nn.AdaptiveAvgPool2d((2, 1))
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.avgpool(x)
        x = torch.flatten(x, 1)
        return x

new_model = AlexNet()
# x = torch.rand((1,3,224,224),dtype=torch.float32)
# output = new_model(x)


# 将模型移动到GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
new_model = new_model.to(device)

# 定义损失函数和优化器
init_lr = 0.01
num_epochs = 200
criterion = CosineSimilarityLoss()
optimizer = optim.SGD(new_model.parameters(), lr=init_lr, momentum=0.9, weight_decay=0.001)
lr_scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=num_epochs, eta_min=0)
# 训练模型

for epoch in range(num_epochs):
    new_model.train()
    running_loss = 0.0
    for inputs, labels in trainloader:
        labels = text_features[labels]
        inputs, labels = inputs.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = new_model(inputs)
        # outputs = F.normalize(outputs, dim=-1)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item()
    lr_scheduler.step()
    print(f"Epoch {epoch+1}, Loss: {running_loss/len(trainloader)}")


torch.save(new_model, "clip_class_model.pth")
# new_model = torch.load("/media/nvme1n1p1/users/xiaokun1/notebook/AI/pytorch/2网络结构/clip_class_model.pth")
# 评估新模型的评测能力
def evaluate_model(model, testloader, device):
    model.eval()  # 设置为评估模式
    correct = 0
    total = 0

    with torch.no_grad():  # 禁用梯度计算，加快推理速度
        for inputs, labels in testloader:
            inputs, labels = inputs.to(device), labels.to(device)
            image_features = model(inputs)
            image_features = F.normalize(image_features, dim=-1)
            scores = image_features @ text_features.type(image_features.type()).T
            _, predicted = torch.max(scores, 1)  # 取最大概率的类别
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    accuracy = 100 * correct / total
    print(f"模型在测试集上的准确率: {accuracy:.2f}%")
    return accuracy

# 调用测试函数
evaluate_model(new_model, testloader, device)