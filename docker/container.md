### docker从image创建容器

> docker run -it --name xx_name docker_image xx_cmd
> --name 容器名字
> --rm 如果容器已经存在，先自动删除
> -it 获取伪终端，并有输入输出
> -d 以守护进程运行容器，当退出容器时，容器不会挂
> -p port:port 端口映射，可以重复使用-p，以指定多端口
> -v 本地目录：容器目录  目录挂载
> -w 指定打开的工作目录

### docker 容器常用命令

> 退出容器 exit
> 进入容器 docker exec -it dockerID/Name /bin/bash
> 停止容器 docker stop containerID
> 启动容器 docker start containerID
>
> 删除容器 docker container rm dockerID
>
> 查看运行中的容器  docker container ls
>
> 查看所有创建的容器 docker container ls -a
