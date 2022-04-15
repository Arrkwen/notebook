## json包

`sudo apt-get install libjsoncpp-dev sudo ln -s  /usr/include/jsoncpp/json/  /usr/include/json`

## Yaml包

```
sudo apt-get install libyaml-cpp-dev
```

## opencv包依赖安装

### 1、更新ubuntu上的软件源，不要担心，中端里执行两个命令就行

`命令一：sudo apt-get update`

`命令二：sudo apt-get upgrade`

> 第二个命令可能会出现错误： *sudo apt-get grade Could not get lock /var/lib/dpkg/lock - open (11: Resource.....* [解决方法](https://blog.csdn.net/u011596455/article/details/60322568)

### 2、安装cmake和依赖(用来搭建opencv的)

```
命令一：sudo apt-get install cmake
命令二：sudo apt-get install build-essential libgtk2.0-dev libavcodec-dev libavformat-dev libjpeg62-dev libtiff5-dev libswscale-dev
```

libjasper-dev

```
sudo add-apt-repository “deb http://security.ubuntu.com/ubuntu xenial-security main”
sudo apt update
sudo apt install libjasper1 libjasper-dev
```

### 3 下载opencv并解压，

OpenCV[下载地址](https://opencv.org/releases.html)

### 4、设置cmake参数（别担心，还是继续傻瓜式运行命令）

在解压后文件夹里新建release文件夹，在在终端里进入release文件夹（也可以直接在release文件夹内右键打开Terminal）。

要运行的命令（不要漏掉空格和两点，下面两个命令随便运行一个不报错就行）：

```
sudo cmake -D WITH_TBB=ON -D BUILD_NEW_PYTHON_SUPPORT=ON -D WITH_V4L=ON -D INSTALL_C_EXAMPLES=ON -D INSTALL_PYTHON_EXAMPLES=ON -D BUILD_EXAMPLES=ON -D WITH_QT=ON -D WITH_OPENGL=ON ..
或者直接采用默认
sudo cmake ..

```

### 5、编译opencv(还是只要运行命令)

```
这时终端（Terminal）的路径还是在release文件夹内
sudo make
sudo make install 
```

默认是安装在 `/usr/local/include/opencv4/ `

`/usr/local/share/opencv4/ `

## Eigen

1 下载
`git clone https://gitlab.com/libeigen/eigen.git`
1
2 编译安装

```
cd eigen
mkdir build && cd build
cmake ..
make install
```

该方法默认安装在：
`/usr/local/include/eigen3`    `/usr/local/share/eigen3`


## 6 c++ inlcudePATH

编辑c_cpp_properties.json

```
{
    "configurations": [
        {
            "name": "Linux",
            "includePath": [
                "${workspaceFolder}/**",
                "/usr/local/include/opencv4/**",
                "/usr/local/include/eigen3/**"
            ],
            "defines": [],
            "compilerPath": "/usr/bin/gcc",
            "cStandard": "gnu17",
            "cppStandard": "gnu++17",
            "intelliSenseMode": "linux-gcc-x64"
        }
    ],
    "version": 4
}
```
