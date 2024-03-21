import torch
import torchvision
from torch.utils.data import DataLoader

# 超参数
n_epochs = 5
batch_size_tran = 64
batch_size_test = 1000
learning_rate = 0.01
momentum = 0.5
log_interval = 10
random_seed = 1
torch.manual_seed(random_seed)
torch.cuda.manual_seed(random_seed)


# 加载数据集
train_loader = DataLoader(dataset=torchvision.datasets.MNIST('./data/',train=True,download=True,
                                                     transform=torchvision.transforms.Compose([
                                                         torchvision.transforms.ToTensor(),
                                                         torchvision.transforms.Normalize((0.1307,),(0.3081))
                                                     ])),
                          batch_size=batch_size_tran,
                          shuffle=True)

test_loader = DataLoader(dataset=torchvision.datasets.MNIST('./data/',train=False,download=True,
                                                     transform=torchvision.transforms.Compose([
                                                         torchvision.transforms.ToTensor(),
                                                         torchvision.transforms.Normalize((0.1307,),(0.3081))
                                                     ])),
                          batch_size=batch_size_test,
                          shuffle=True)

# 打印数据集的shape: data[batch_size,channel,h,w],targets: label
# train_data: [64,1,28,28], train_targets:[64]
# test_data: [1000,1,28,28], test_targets: [1000]
examples = enumerate(test_loader)
batch_idx, (example_data, example_targets) = next(examples)
print(example_targets.shape)
print(example_data.shape)

# 构建网络
import os
import torch.nn.functional as F
import torch.optim as optim
from mnist import MnistNet

# 初始化网络和优化器
net = MnistNet()
optimizer = optim.SGD(net.parameters(),lr=learning_rate,momentum=momentum)

# 构建模型训练和测试代码
train_loss = []
train_counter = []
test_loss = []
test_counter = [i*len(train_loader.dataset) for i in range(n_epochs)]

def train(epoch):
    net.train()
    for batch_idx,(data,label) in enumerate(train_loader):
        optimizer.zero_grad()
        output = net(data)
        loss = F.nll_loss(output,label)
        loss.backward()
        optimizer.step()
        
        # 评测
        if batch_idx % log_interval == 0:
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, batch_idx * len(data), len(train_loader.dataset),
                100. * batch_idx / len(train_loader), loss.item()))
            
            train_loss.append(loss.item())
            train_counter.append(batch_idx*batch_size_tran + ((epoch-1)*len(train_loader.dataset)))
            os.makedirs('./model',exist_ok=True)
            torch.save(net.state_dict(),f'./model/MNIST_epoch{epoch}.pth')
            torch.save(optimizer.state_dict(),f'./model/optimizer_epoch{epoch}.pth')

def test():
    net.eval()
    loss = 0.0
    correct = 0
    with torch.no_grad():
        for data, label in test_loader:
            output = net(data)
            loss += F.nll_loss(output,label,reduction="sum").item()
            pred = output.data.max(1,keepdim=True)[1]
            correct += pred.eq(label.data.view_as(pred)).sum()
        loss /= len(test_loader.dataset)
        test_loss.append(loss)
        print('\nTest set: Avg. loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n'.format(
            loss, correct, len(test_loader.dataset),
            100. * correct / len(test_loader.dataset)))

# 评估模型的性能
for epoch in range(1, n_epochs + 1):
    train(epoch)
    test()

# 保存模型最后一轮的权重，注意这儿还保存了网络结构，目的只是为了netron可视化。
torch.save(net,'./model/MNIST.pth')
torch.save(net.state_dict(),'./model/MNIST.pth')
torch.save(optimizer.state_dict(),f'./model/optimizer.pth')

# 查看训练曲线
import matplotlib.pyplot as plt
fig = plt.figure()
plt.plot(train_counter, train_loss, color='blue')
plt.scatter(test_counter, test_loss, color='red')
plt.legend(['Train Loss', 'Test Loss'], loc='upper right')
plt.xlabel('number of training examples seen')
plt.ylabel('negative log likelihood loss')
plt.savefig('./model/loss_cur.jpeg')


# 图片测试结果
examples = enumerate(test_loader)
batch_idx, (example_data, example_targets) = next(examples)
with torch.no_grad():
    output = net(example_data)
fig = plt.figure()
for i in range(6):
    plt.subplot(2, 3, i + 1)
    plt.tight_layout()
    plt.imshow(example_data[i][0], cmap='gray', interpolation='none')
    plt.title("Prediction: {}".format(output.data.max(1, keepdim=True)[1][i].item()))
    plt.xticks([])
    plt.yticks([])
plt.savefig("./model/image_pred.jpeg")
 
 
# ------------------------根据训练曲线，选择中间的模型参数，继续训练------------------------------ #
 
# continued_network = MnistNet()
# continued_optimizer = optim.SGD(net.parameters(), lr=learning_rate, momentum=momentum)
 
# network_state_dict = torch.load('./model/MNIST.pth')
# continued_network.load_state_dict(network_state_dict)
# optimizer_state_dict = torch.load('./model/optimizer.pth')
# continued_optimizer.load_state_dict(optimizer_state_dict)
 
# # 注意不要注释前面的“for epoch in range(1, n_epochs + 1):”部分，
# # 不然报错：x and y must be the same size
# # 为什么是“4”开始呢，因为n_epochs=3，上面用了[1, n_epochs + 1)
# for i in range(n_epochs + 1, n_epochs + 5):
#     test_counter.append(i*len(train_loader.dataset))
#     train(i)
#     test()
 
# fig = plt.figure()
# plt.plot(train_counter, train_loss, color='blue')
# plt.scatter(test_counter, test_loss, color='red')
# plt.legend(['Train Loss', 'Test Loss'], loc='upper right')
# plt.xlabel('number of training examples seen')
# plt.ylabel('negative log likelihood loss')
# plt.show()