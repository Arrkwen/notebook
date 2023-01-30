---
参考：https://segmentfault.com/a/1190000039964495
---
### 1. Docker SSH配置

#### 1.1 拉取镜像后，执行：

```
sudo docker run --runtime=nvidia -it -p 8023:22 --ipc=host  --name="torch" -v /home/**:/home/**  torch1.5 /bin/bash
```

其中，
`-p 8023:22`：设置端口映射，将容器tcp22端口转发到主机8023（后续将通过8023端口对容器进行访问），与已占用端口不冲突的情况下可以自由设置；
`--ipc=host`：用于设置主机与容器共享内存；
`-v /home/**/:/home/**/`：将服务器目录与容器目录进行共享，为方便记忆，通常将两个目录名设置为一样；
`torch1.5`：拉取的镜像名称。

#### 1.2 启动并进入容器：

```
sudo docker start torch
sudo docker attach torch
```

#### 1.3 设置容器root 账户密码，用于vscode连接时，输入密码。

```
passwd root
1.输入密码
2.再次输入密码
```

-----------容器安装ssh，如果有不用安装。

#### 1.4 安装openssh:

```
apt update
apt install -y openssh-server
```

#### 1.5 ssh配置：

```
vim /etc/ssh/sshd_config
```

修改SSH配置文件，去掉以下选项的#注释（如找不到对应项，可直接复制到文件中）：

```
Port 22                     #开启22端口
PermitRootLogin yes         #允许root用户使用ssh登录
RSAAuthentication yes       #启用 RSA 认证
PubkeyAuthentication yes    #启用公钥私钥配对认证方式
AuthorizedKeysFile          .ssh/authorized_keys .ssh/authorized_keys2      #公钥文件路径
```

#### 1.6 修改完成后，重新启动ssh服务：

```
service ssh restart
```

#### 1.7 验证端口映射是否正确：

```
sudo docker port [container-ID] 22
```

输出如下，表示配置成功

```
**@master:~$ sudo docker port torch 22
0.0.0.0:8023
```

#### 1.8 设置进入容器后，自动启动ssh服务：

尽管容器内安装了ssh服务，但每次关闭容器重启后，ssh将恢复停止状态，每次进入容器时需要重新启动ssh服务：`service ssh restart`，否则远程连接将失败：
![](https://segmentfault.com/img/bVcRQPh)
在这里，我们可以利用脚本来实现ssh服务的自动启动：

```
vim /root/startup_run.sh
```

写入：

```
#!/bin/bash

LOGTIME=$(date "+%Y-%m-%d %H:%M:%S")
echo "[$LOGTIME] startup run..." >>/root/startup_run.log
service ssh start >>/root/startup_run.log
#service mysql start >>/root/startup_run.log
```

添加文件权限：

```
chmod +x /root/startup_run.sh
```

打开启动文件：

```
vim /root/.bashrc
```

把脚本命令添加到文件末尾：

```
# startup run
if [ -f /root/startup_run.sh ]; then
      /root/startup_run.sh
fi
```

最后，立即生效.bashrc：

```
source ~/.bashrc
```

至此实现了ssh的自动启动，可以退出、重新进入容器后进行ssh连接测试。

### 2 主机

确认是否安装openssh-client

```
scp -v
-bash: scp: command not found
安装
yum -y install openssh-clients
```

开放8023端口

```text
sudo iptables -I INPUT -p tcp --dport 8023 -j ACCEPT
```

### 3. VS-Code配置

#### 3.1 安装Remote Development

打开VS code，打开扩展（ctr+shift+X）查找并安装Remote Development
![](https://segmentfault.com/img/bVcRQNt)

#### 3.2 打开查找栏（ctr+shift+p），输入remote-ssh，选择open Configuration file

![](https://segmentfault.com/img/bVcRQNA)

#### 3.3 进行基础配置：

hostname 为宿主机IP，user 为容器登录账号，端口为容器映射的端口，密码为容器登录账号的密码。

![](https://segmentfault.com/img/bVcRQNE)

#### 3.4 打开远程资源管理器，选择刚才配置好的host进行SSH连接

![](https://segmentfault.com/img/bVcRQNF)

#### 3.5 输入容器root账户密码：

![](https://segmentfault.com/img/bVcRQNH)
连接成功：
![](https://segmentfault.com/img/bVcRQNI)
