## docker-compose

参考菜鸟教程

### 安装

下载安装包地址：https://github.com/docker/compose/releases

> wget https://github.com/docker/compose/releases/download/v2.3.3/docker-compose-linux-x86_64

> sudo mv path/docker-compose-linux-x86_64  /usr/local/bin/docker-compose

增加执行权限

> sudo chmod +x docker-compose

添加软连接

> sudo ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose

验证

> docker-compose --version

### 编写docker-compose.yml

#### 宿主机时间和容器时间保持一致

```
volumes:
  - /etc/timezone:/etc/timezone
  - /etc/localtime:/etc/localtime
```

### 启动服务

根据docker-compose.yml文件来启动容器内的应用程序及其相关依赖的服务

> docker-compose up ：以依赖性顺序启动服务
>
> docker-compose up -d: 以后台服务启动
> docker-compose up service_specific ：启动具体的服务及其依赖服务
> docker-compose stop ：按依赖关系顺序停止服务
