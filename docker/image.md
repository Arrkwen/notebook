### docker image导出导入

1 切换一个机器去pull

> docker image pull osrm/osrm-backend

2 打包image

> docker save -o osrm.tar osrm/osrm-backend   NAME:VERSION

3 远程传送到目标机器

> scp -P 1022 file developer@10.211.19.15:/media/nvme2n1p1/xiaokun/
>
> scp file user@ip:dir   scp 默认是22端口

4解包image

> docker load -i osrm.tar

### docker image 常用命令

> 查看image: docker image ls
>
> 删除image   docker image rm imageID/imageName
