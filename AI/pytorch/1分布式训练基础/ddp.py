import os
import torch
import torch.distributed as dist
import torch.nn as nn
import torch.optim as optim
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, DistributedSampler
from torchvision.datasets import CIFAR10
from torchvision.transforms import Compose, Normalize, ToTensor
from time import perf_counter

class Timer:
    def __init__(self, label="", is_master=False, log_func=print):
        """
        Timer with logging for tracking durations.
        Args:
            label (str): Description of the timing context.
            is_master (bool): master process, for logging purposes.
            log_func (callable): Logging function, defaults to `print`.
        """
        self.label = label
        self.is_master = is_master
        self.log_func = log_func

    def __enter__(self):
        if self.is_master:
            self.start = perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.is_master:
            self.end = perf_counter()
            self.duration = self.end - self.start
            self.log_func(f"{self.label} took {self.duration:.2f} seconds.")


class DistributedTrainer:
    def __init__(self, rank=None, world_size=None):
        self.rank = int(os.environ["RANK"]) if rank is None else rank  # Rank of the current process
        self.world_size = int(os.environ["WORLD_SIZE"]) if world_size is None else world_size  # Total number of processes
        print(f"World size: {self.world_size}, Rank: {self.rank}")
        self.build_env()

    def is_master(self):
        return self.rank == 0

    def build_env(self):
        self.setup()
        self.build_model()
        self.build_dataloader()

    def setup(self, port=40001):
        dist.init_process_group(backend="nccl")
        torch.cuda.set_device(self.rank)

    def cleanup(self):
        dist.destroy_process_group()

    def build_dataloader(self, batch_size=32):
        self.batch_size = batch_size
        transform = Compose([
            ToTensor(),
            Normalize((0.48145466, 0.4578275, 0.40821073), (0.26862954, 0.26130258, 0.27577711))
            ])
        # train
        train_dataset = CIFAR10(root='./data', train=True, download=True, transform=transform)
        self.sampler = DistributedSampler(train_dataset)
        self.train_dataloader = DataLoader(train_dataset, batch_size=batch_size, sampler=self.sampler)
        # test
        test_dataset = CIFAR10(root='./data', train=False, download=True, transform=transform)
        self.test_dataloader = DataLoader(test_dataset, batch_size=batch_size, sampler=DistributedSampler(test_dataset))


    def build_model(self):
        model = nn.Sequential(
            nn.Flatten(),
            nn.Linear(32 * 32 * 3, 10)
        ).to(self.rank)
        self.model = DDP(model, device_ids=[self.rank])


    def train(self, epochs=5, init_lr=0.0001, save_dir="./checkpoints"):

        criterion = nn.CrossEntropyLoss()
        lr = init_lr * self.world_size * self.batch_size     # word_size越大，iter的次数越少， 因此lr可以和word_size,batch_size等成比例
        optimizer = optim.SGD(self.model.parameters(), lr=lr)

        # 添加学习率调度器
        scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=2, gamma=0.1)

        if self.is_master() and not os.path.exists(save_dir):
            os.makedirs(save_dir)

        with Timer("Total Training", is_master=self.is_master()):
            for epoch in range(epochs):
                with Timer(is_master=self.is_master()):
                    self.sampler.set_epoch(epoch)                # 保证不同进程使用不同的数据顺序
                    self.model.train()                           # 确保模型处于训练模式
                    for inputs, labels in self.train_dataloader:
                        inputs, labels = inputs.to(self.rank), labels.to(self.rank)
                        optimizer.zero_grad()               # 梯度归零，确保当前的梯度计算仅基于当前 batch 的数据。
                        outputs = self.model(inputs)             # 前向传播
                        loss = criterion(outputs, labels)   # 计算损失
                        loss.backward()                     # 根据loss计算每个参数的梯度：.grad
                        optimizer.step()                    # 根据梯度和学习率步长更新参数
                    scheduler.step()                        # 更新学习率
                    acc = self.evaluation()
                    if self.is_master():
                        print(f"Rank {self.rank}, Epoch {epoch}, Loss: {loss.item():.4f}, Acc: {acc:.4f}, LR: {scheduler.get_last_lr()[0]:.4f},", end="")
        
        # 保存模型权重
        if self.is_master():
            checkpoint_path = os.path.join(save_dir, f"model_latest.pth")
            torch.save(self.model.module.state_dict(), checkpoint_path)   # ddp会增加一个额外的module字段，为了保存单卡和多卡的ckpt保存和读取一致
            print(f"Model saved at {checkpoint_path}")

        # 销毁分布式进程组
        self.cleanup()
    
    def evaluation(self):
        self.model.eval()  # 设置模型为评估模式
        total = 0
        correct = 0
        # 禁用梯度计算，节省内存和加速
        with torch.no_grad():
            for inputs, labels in self.test_dataloader:
                inputs, labels = inputs.to(self.rank), labels.to(self.rank)
                outputs = self.model(inputs)  # 前向传播
                _, predicted = torch.max(outputs, 1)  # 获取预测值
                total += labels.size(0)  # 累计总样本数
                correct += (predicted == labels).sum().item()  # 累计正确预测的样本数

        # 使用分布式收集所有进程的结果
        correct_tensor = torch.tensor(correct, device=self.rank)
        total_tensor = torch.tensor(total, device=self.rank)
        dist.reduce(correct_tensor, dst=0, op=dist.ReduceOp.SUM)  # 汇总正确预测数
        dist.reduce(total_tensor, dst=0, op=dist.ReduceOp.SUM)  # 汇总总样本数

        if self.is_master():
            accuracy = correct_tensor.item() / total_tensor.item()  # 计算精度
            return accuracy
        else:
            return None  # 非主进程无需返回精度


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--local_rank", type=int, default=0, help="Local rank passed by torch.distributed.launch")
    parser.add_argument("--world_size", type=int, default=torch.cuda.device_count(), help="Total number of processes")
    args = parser.parse_args()

    trainer = DistributedTrainer(rank=args.local_rank, world_size=args.world_size)
    trainer.train()


if __name__ == "__main__":
    main()
