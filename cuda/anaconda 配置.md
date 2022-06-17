1.安装Anaconda。

打开命令行输入conda -V检验是否安装及当前conda的版本。

2.conda常用的命令

1）查看安装了哪些包

```text
conda list
```

2)查看当前存在哪些虚拟环境

```text
conda env list 
conda info -e
```

3)检查更新当前conda

```text
conda update conda
```

3.Python创建虚拟环境

```text
conda create -n your_env_name python=x.x
```

anaconda命令创建python版本为x.x，名字为your_env_name的虚拟环境。 **your_env_name文件可以在Anaconda安装目录envs文件下找到** 。

4.激活或者切换虚拟环境

打开命令行，输入python --version检查当前 python 版本。

```text
Linux:  source activate your_env_nam
Windows: activate your_env_name
```

5.对虚拟环境中安装额外的包

```text
conda install -n your_env_name [package]
```

6.关闭虚拟环境(即从当前环境退出返回使用PATH环境中的默认python版本)

```text
deactivate env_name
或者`activate root`切回root环境
Linux下：source deactivate 
```

7.删除虚拟环境

```text
conda remove -n your_env_name --all
```

8.删除环境钟的某个包

```text
conda remove --name $your_env_name  $package_name 
```

9、设置国内镜像

[**Anaconda**](https://link.zhihu.com/?target=http%3A//Anaconda.org)的服务器在国外，安装多个packages时，conda下载的速度经常很慢。清华TUNA镜像源有Anaconda仓库的镜像，将其加入conda的配置即可：

添加Anaconda的TUNA镜像

conda config --add channels [https://**mirrors.tuna.tsinghua.edu.cn**/anaconda/pkgs/free/](https://link.zhihu.com/?target=https%3A//mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/)

TUNA的help中镜像地址加有引号，需要去掉

设置搜索时显示通道地址

conda config --set show_channel_urls yes

10、恢复默认镜像

conda config --remove-key channels
