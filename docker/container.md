## docker从image创建容器

> docker run -it --name xx_name docker_image xx_cmd
> --name 容器名字
> --rm 如果容器已经存在，先自动删除
> -it 获取伪终端，并有输入输出
> -d 以守护进程运行容器，当退出容器时，容器不会挂
> -p port:port 端口映射，可以重复使用-p，以指定多端口
> -v 本地目录：容器目录  目录挂载
> -w 指定打开的工作目录

## docker 容器常用命令

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

## 容器无法访问宿主机mysql

### 1宿主机mysql要允许远程访问！！！

### 2打开防火墙

> iptables -A INPUT -p tcp -i docker0 --dport 3306 -j ACCEPT

MySQL 默认端口为 3306 ，我们需要告诉防火墙，允许 3306 端口通讯。

如果你仅希望某一台服务器可远程访问数据库，则可以使用以下命令授权某一台（ip）服务器访问。

```bash
sudo ufw allow from remote_IP_address to any port 3306
```

当然，你也可以允许任意计算机远程访问数据库。

```bash
sudo ufw allow 3306
```

### 3 配置数据库访问地址

endpoint 一定不能是127.0.01:3306呀！！！！！

```
    "DatabaseConfig": {
        "Username": "tmadmin",
        "Password": "tm@pswd123",
        "Endpoint": "宿主机ip:3306",
        "Database": "rtc",
        "UseSSL": false
    }
```
