## Dockerfile编写规则

```shell
FROM         baseimage       <指定它妈妈>
MAINTAINER  <NAME>/<EMAIL>   <维护者信息>
RUN         shell命令        <需要在基础镜像上面执行额外的命令>
CMD         shell命令        <打开容器之后需要执行的命令>
WORKDIR     目录             <指定工作目录>
ADD       本地文件 路径        <将网络或本地文件放入镜像内部>
ENV       ENV_ANME = XXX     <指定镜像里面的环境变量>
VOLUME    ['path_dir',]     <镜像数据持久化的目录，默认是和本地/usr/lib/docker/path_dir挂载>
EXPOSE    port1 port2       <镜像暴露的端口>结合-p指定

# 表示注释
```

**比如**

```
dockerfile
FROM centos
LABEL version="1.0" description="centos7" by="测试"
ENV MYPATH /usr/local
WORKDIR $MYPATH

RUN yum -y install java-1.8.0-openjdk
#设置容器时间与宿主机时间同步
RUN /bin/cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && echo 'Asia/Shanghai' >/etc/timezone

EXPOSE 80

CMD echo "------success------OK------"
```

### **FROM**

格式为 FROM `<image>` 或 FROM `<image>`:`<tag>`。
Dockerfile 的第一条指令必须为 FROM 指令。并且，如果在同一个 Dockerfile 中创建多个镜像时，可以使用多个 FROM 指令。

```
# 第一行必须指定基础容器，这里的是tomcat8
FROM tomcat:8
```

### **MAINTAINER**

格式为 MAINTAINER `<name>`，指定维护者信息。

注意：MAINTAINER 指令已经被抛弃，建议使用 LABEL 指令。

```
# 维护者信息(可选)建议用LABEL 指令
MAINTAINER xiaojianjun xiaojianjun@tansun.com.cn
```

**LABEL**

LABEL 指令为镜像添加标签。一个 LABEL 就是一个键值对，也可以一行指定多个键值对。

```
#多行指定信息
LABEL com.example.label-with-value="foo"
LABEL version="1.0"
LABEL description="This text illustrates \that label-values can span multiple lines."

#一行指定多个键值对
LABEL app.version="1.0" app.host='bestxiao.cn' description="这个app产品构建"
```

如果新添加的 LABEL 和已有的 LABEL 同名，则新值会覆盖掉旧值。

### **RUN**

每条 RUN 指令将在当前镜像的基础上执行指定命令，并提交为新的镜像。当命令较长时可以使用 \ 来换行。

```shell
RUN yum -y install java-1.8.0-openjdk 
```

### **CMD**

指定启动容器时执行的命令，每个 Dockerfile 只能有一条 CMD 命令。如果指定了多条 CMD 命令，只有最后一条会被执行。如果用户在启动容器时指定了要运行的命令，则会覆盖掉 CMD 指定的命令。

```
CMD echo "------success------OK------"
```

### **EXPOSE**

告诉 Docker 服务，容器需要暴露的端口号，供互联系统使用。在启动容器时需要通过 -P 参数让 Docker 主机分配一个端口转发到指定的端口。使用 -p 参数则可以具体指定主机上哪个端口映射过来。

```
EXPOSE 22 80 8443 8080
```

### **ENV**

格式为 ENV `<key>` `<value>`。指定一个环境变量，会被后续 RUN 指令使用，并在容器运行时保持。

```
ENV PG_MAJOR 9.3
ENV PG_VERSION 9.3.4
RUN curl -SL http://example.com/postgres-$PG_VERSION.tar.xz | tar -xJC /usr/src/postgress && …
ENV PATH /usr/local/postgres-$PG_MAJOR/bin:$PATH
```

### **ADD**

该命令将复制指定的 `<src>` 到容器中的 `<dest>`。其中 `<src>` 可以是 Dockerfile 所在目录的一个相对路径(文件或目录)；也可以是一个 URL；还可以是一个 tar 文件(自动解压为目录)。

```
ADD <src> <dest>
```

### **COPY**

复制本地主机的 `<src>` (为 Dockerfile 所在目录的相对路径，文件或目录) 为容器中的 `<dest>`。目标路径不存在时，会自动创建。当使用本地目录为源目录时，推荐使用 COPY。

```
COPY <src> <dest>
```

### **ENTRYPOINT**

配置容器启动后执行的命令，并且不可被 docker run 提供的参数覆盖。
每个 Dockerfile 中只能有一个 ENTRYPOINT，当指定多个 ENTRYPOINT 时，只有最后一个生效。

```
ENTRYPOINT [“executable”, “param1”, “param2”]
ENTRYPOINT command param1 param2 (shell 中执行)
```

### **VOLUME**

使用 VOLUME 指令添加多个数据卷，创建一个可以从本地或其他容器挂载的挂载点，一般用来存放数据库和需要保持的数据等。

```
VOLUME ["/data"]
VOLUME ["/data1", "/data2"]
```

### **USER**

指定运行容器时的用户名或 UID，后续的 RUN 也会使用指定用户。当服务不需要管理员权限时，可以通过该命令指定运行用户。并且可以在之前创建所需要的用户

### **WORKDIR**

为后续的 RUN、CMD、ENTRYPOINT 指令配置工作目录。可以使用多个 WORKDIR 指令，后续命令如果参数是相对路径，则会基于之前命令指定的路径。

```
# WORKDIT 后续的 RUN、CMD、ENTRYPOINT 指令配置容器内的工作目录
WORKDIR /path/to/workdir
```

### **ONBUILD**

配置当所创建的镜像作为其他新创建镜像的基础镜像时，所执行的操作指令

```
FROM image-A#automatically run the followingADD ONBUILD ADD . /app/srcONBUILD RUN /usr/local/bin/python-build –dir /app/src
```

如果基于 image-A 创建新的镜像时，新的 Dockerfile 中使用 FROM image-A 指定基础镜像时，会自动执行 ONBUILD

### 构建镜像

>  docker build -f dockerfile_path -t iamge_name:tag save_path
