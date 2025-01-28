# 单机单卡
# CUDA_VISIBLE_DEVICES=1 python -m torch.distributed.launch --nproc_per_node=1 ddp.py

# 单机双卡
# CUDA_VISIBLE_DEVICES=1,2 python -m torch.distributed.launch --nproc_per_node=2 ddp.py

# 单机四卡
# CUDA_VISIBLE_DEVICES=1,2,3,4 python -m torch.distributed.launch --nproc_per_node=4 ddp.py

# 单机八卡
# python -m torch.distributed.launch --nproc_per_node=8 ddp.py

# 多机多卡:
# python -m torch.distributed.launch
#         --nnodes=${nnodes} \                  # 总节点数量
#         --node_rank=0  \                      # 第一个节点
#         --nproc_per_node=8 \                  # 每个节点的卡数(进程数量)
#         --master_addr=${master_addr} \        # 主节点ip地址
#         --master_port 12355 \                 # 主节点通信端口
#         ddp.py

# 多机多卡: 
# python -m torch.distributed.launch
#         --nnodes=${nnodes} \
#         --node_rank=1  \                      # 第二个节点
#         --nproc_per_node=8 \
#         --master_addr=${master_addr} \
#         --master_port 12355 \
#         ddp.py