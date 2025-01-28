import os
import torch
import torch.distributed as dist

def setup(rank, world_size):
    os.environ['MASTER_ADDR'] = 'localhost'
    os.environ['MASTER_PORT'] = '12355'
    dist.init_process_group(backend='nccl', rank=rank, world_size=world_size)
    torch.cuda.set_device(rank)

def cleanup():
    dist.destroy_process_group()


# 1. AllReduce
# 所有 GPU 的张量数据会规约（如求和）并广播到所有 GPU。
def allreduce_example(rank, world_size):
    tensor = torch.ones(1).cuda(rank) * (rank + 1)  # 每个 GPU 上初始张量不同
    print(f"Before AllReduce on rank {rank}: {tensor.item()}")
    dist.all_reduce(tensor, op=dist.ReduceOp.SUM)  # 求和规约
    print(f"After AllReduce on rank {rank}: {tensor.item()}")

# 2. Broadcast
# 将一个源 GPU 的张量广播到所有 GPU。
def broadcast_example(rank, world_size):
    tensor = torch.zeros(1).cuda(rank)
    if rank == 0:
        tensor += 10  # 在源 GPU 上初始化张量
    print(f"Before Broadcast on rank {rank}: {tensor.item()}")
    dist.broadcast(tensor, src=0)  # 从 rank 0 广播
    print(f"After Broadcast on rank {rank}: {tensor.item()}")

# 3. Reduce
# 将所有 GPU 的张量规约到一个目标 GPU。
def reduce_example(rank, world_size):
    tensor = torch.ones(1).cuda(rank) * (rank + 1)
    print(f"Before Reduce on rank {rank}: {tensor.item()}")
    dist.reduce(tensor, dst=0, op=dist.ReduceOp.SUM)  # 将张量规约到 rank 0, 其它不变
    print(f"After Reduce on rank {rank}: {tensor.item()}")
    

# 4. AllGather
# 收集所有 GPU 的张量并分发到所有 GPU。
def allgather_example(rank, world_size):
    tensor = torch.ones(1).cuda(rank) * (rank + 1)
    gather_list = [torch.zeros(1).cuda(rank) for _ in range(world_size)]  # 用于存储结果
    print(f"Before AllGather on rank {rank}: {tensor.item()}")
    dist.all_gather(gather_list, tensor)  # 收集所有 GPU 的张量
    print(f"After AllGather on rank {rank}: {', '.join(str(t.item()) for t in gather_list)}")

# 5. ReduceScatter
# 先规约，然后将结果分散到所有 GPU。
def reducescatter_example(rank, world_size):
    input_tensor = torch.arange(rank, rank+world_size).float().cuda(rank)  # 每个 GPU 的数据
    output_tensor = torch.zeros(1).cuda(rank)  # 存储结果
    buffer_list = list(torch.chunk(input_tensor, world_size, dim=0))
    print(f"Before ReduceScatter on rank {rank}: {input_tensor.tolist()}")
    dist.reduce_scatter(output_tensor, buffer_list, op=dist.ReduceOp.SUM)
    print(f"After ReduceScatter on rank {rank}: {output_tensor.item()}")
    

# 6. Send/Recv
# 点对点通信，用于两个 GPU 间传递数据。
def send_recv_example(rank, world_size):
    tensor = torch.ones(1).cuda(rank) * rank
    if rank == 0:
        dist.send(tensor, dst=1)
        print(f"Rank {rank} sent tensor: {tensor.item()}")
    elif rank == 1:
        dist.recv(tensor, src=0)
        print(f"Rank {rank} received tensor: {tensor.item()}")

# 7. AllToAll
# 每个 GPU 向所有其他 GPU 发送和接收数据。
def alltoall_example(rank, world_size):
    send_tensor = torch.arange(world_size).float().cuda(rank) + rank * world_size  # 每个 GPU 数据不同
    recv_tensor = torch.zeros(world_size).float().cuda(rank)  # 存储接收结果
    print(f"Before AllToAll on rank {rank}: {send_tensor.tolist()}")
    dist.all_to_all_single(recv_tensor, send_tensor)  # AllToAll 通信
    print(f"After AllToAll on rank {rank}: {recv_tensor.tolist()}")

import torch.multiprocessing as mp

def run(rank, world_size):
    setup(rank, world_size)

    # 选择一个示例进行测试
    allreduce_example(rank, world_size)
    # broadcast_example(rank, world_size)
    # reduce_example(rank, world_size)
    # allgather_example(rank, world_size)
    # reducescatter_example(rank, world_size)
    # send_recv_example(rank, world_size)
    # alltoall_example(rank, world_size)

    cleanup()

if __name__ == "__main__":
    world_size = 4  # 总 GPU 数
    mp.spawn(run, args=(world_size,), nprocs=world_size, join=True)
