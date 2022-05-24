# 从零开始的C++包管理器CONAN上手指南

从 C++ 诞生至今已经走过了几十个年头，如今越来越多的语言诞生在世界上，受到大众追捧；一些同样古老的语言在历经脱胎换骨般的发展后也迎头赶上，变得无所不能。可以看到 C/C++ 所擅长的领域正在被一点点地分割，它们的地盘正在不断地被蚕食。

![TIOBE 2019八月榜单](http://chu-studio.com/posts/2019/assets/tiobe2019%E5%85%AB_1566444389_343.png)

C++ 排名的逐步下降，除了其 Core Language 越来越复杂以外，其生态过于零碎也是一个非常大的问题。

一个非常普遍的现象，C/C++ 项目如果要依赖第三方库，往往有 N 种姿势来完成这个事情：

1. 直接在源码中包裹第三方库的头文件和二进制
2. 把第三方库的源码带入工程中随项目一起编译
3. 依赖系统中安装的组件，而后使用 pkg_config 或 CMake 的 *find* 系函数来查找依赖

其中，方案1不具备可移植性，但依赖非开源组件且无软件包可用时往往只能用这种方法；方案2，普适性比较强，可以针对源码做定制，但是大大增加了源码的大小和构建的耗时；方案3，Windows 下往往不可用，并且需要用户手动准备环境，每次搭建新环境时比较繁琐。

可以看到，光依赖管理就没有一个比较标准的解决方案，并且这些方法各自也都有很大缺陷。这进一步导致社区的撕裂，其结果就是即便是可移植的开源库，如果你想在项目中引用它，也得看看要用什么方法来引入才能对接到你的 Build System 中。

而在其他的流行语言中，包管理器可以说是一个很常态很普遍的东西了，比如 Python 的  *pip* ，JS 的  *npm* ，C# 的 *nuget* 等等。

至于为何会这样，也有一个很大的原因是 C/C++ 本身的定位和历史原因。它能 Target 到众多的平台上，从 X86、X64 到 Arm，从 Windows、Linux 到 MacOS 甚至于嵌入式的系统中。每个平台的特点都不尽相同，甚至于相同平台使用不同编译器构建后能产生不同的 ABI。这使得包管理器的设计远比无需编译的 Python、JS 一流复杂很多。

当然我们也看到像微软在这方面做了尝试，弄出了 vcpkg，笔者没有用过，听说是更贴近 apt 的作用，用来安装全局的依赖。

讲了一通废话，接下来就要请出本文的主角了—— **Conan** 。

Conan 是一个开源的、跨平台的、去中心化的 C++ 包管理器。通过它可以安装、解决构建依赖，更重要的是可以直接集成到 Build System 中使用。同时它也允许你搭建自己的私有仓库，供私有项目使用。具体到细节，当向 Conan 请求安装依赖时，Conan 会拿着编译相关的配置信息去服务器请求是否有对应平台的预构建二进制包，如果有，则直接下载并解压到本地的缓存仓库中，否则，会执行对应的构建脚本，构建出符合当前平台的二进制包。这种方式并无特别之处，但是是可以解决 C++ 平台众多的问题的有效方法。

![Conan工作原理](http://chu-studio.com/posts/2019/assets/20190820004330615_1754915548.png)

本文记录了从零开始上手 Conan 的过程，谨以此文帮助更多 C++ 使用者了解和上手这一现代化的包管理器，从依赖配置的苦海中解脱出来。

## 安装

Conan 基于 Python 编写，故需要在开始前安装好 Python3。然后使用标准的 *pip* 安装即可。

```
pip install conan
```

需要注意的是，Linux 下需要用 *sudo* 安装全局的 pip 包。而 OSX 下也可以使用 *brew* 来安装 Conan。

## 配置

Conan 会在第一次启动时自动配置好默认的 Profile 和 Remote 设置。它的配置以及本地的二进制仓库均存储在用户目录下 `~/.conan/`中（Windows上，是 `%USERPROFILE%\.conan\`）。

其中用户配置文件为 `conan.conf`，通常情况下无需修改，但当需要设置代理时，可以对其进行编辑。

```
[proxies]
http = http://dev-proxy.oa.com:8080
https = http://dev-proxy.oa.com:8080
```

另外，当使用 Artifactory 来搭建私有仓库时，需要启用 `general.revisions_enabled = 1`这个开关。笔者会在下文介绍如何搭建私有仓库，这里不予展开。

而 Profile 则存储在 `profiles`文件夹中，用于设定各种编译环境和选项。默认会创建一个名为 default 的 Profile 供使用。

## 基本概念

### 软件包

Conan 使用这样的格式来描述一个软件包：`名称/版本@用户/渠道`。其中渠道（Channel）用来描述是稳定版（Stable）还是测试版（Testing）等信息，以 boost 为例，我们可以看到这样的包名：

```
boost/1.64.0@conan/stable
boost/1.65.1@conan/stable
boost/1.66.0@conan/stable
boost/1.67.0@conan/stable
boost/1.68.0@conan/stable
boost/1.69.0@conan/stable
boost/1.70.0@conan/stable
```

### 软件包仓库

NodeJS 的包管理器 *npm* 会把依赖存储到工程目录的 `node_modules`文件夹中，此外也能安装全局的包。Python 的包管理器 *pip* 能把包装到用户目录下或者是全局环境中，所以一般配合 *venv* 使之把包装在工程中不污染环境。

相比之下，可能是出于 C++ 的库通常需要依据环境编译，并且大小比较大的考量，默认情况下 Conan 只把包装在用户目录下。一般来说，在开发环境中这点已经足够使用了。但是在配合 CI/CD 的时候，这里就有可能出现竞争。为此，Conan 提供了一个环境变量 `CONAN_USER_HOME`来让用户指定一个 Conan 的工作目录，这样就能起到类似于 Python 的 Virtual Environment 的作用。

上文中，用户目录的软件包仓库被称为本地缓存（Local Cache）；那么同样的，服务器上也有一个软件包的仓库，文档中称为远端（Remote）。

Conan 提供了几个官方和社区的远端供选择，默认的，安装后会自动配置 Conan Center 这个源：

* conan-center: https://bintray.com/conan/conan-center
* conan-transit（废弃）: https://bintray.com/conan/conan-transit
* bincrafters（开源社区源） : https://bintray.com/bincrafters/public-conan
* conan-community（类似测试源，不稳定） : https://bintray.com/conan-community/conan

### 编译环境

通常情况下默认的 Profile 就够用了，故本文不赘述配置 Profile 的过程，如有时间会在未来进行补充。

需要注意的是使用 GCC 作编译器时需要手动开启对 C++11 的 ABI 的支持，否则默认位于兼容模式下，将使用老的 ABI。

```
conan profile new default --detect  # Generates default profile detecting GCC and sets old ABI
conan profile update settings.compiler.libcxx=libstdc++11 default  # Sets libcxx to C++11 ABI
```

## 基本操作

### 1. 搜索软件包

```
conan search boost* -r=conan-center
```

使用上述命令在默认的中心仓库中搜索 boost 软件包。在不指定 `-r`的情况下，默认搜索本地缓存。

### 2. 管理远端

```
# 添加源
conan remote add my-repo http://my-repo.com/xxx

# 或者使用insert来将其作为首个源
conan remote update my-repo http://my-repo.com/xxx --insert=0

# 展示所有源
conan remote list

# 删除一个源
conan remote remove my-repo
```

Conan 的远端是个列表，并有先后顺序，默认在安装软件包的时候会先检查本地缓存，然后依次从软件源中获取软件包。

因此常用源应当使用 `insert`参数使之排到前面。

### 3. 安装依赖与构建

类似于 CMake，Conan 使用一个叫做 `conanfile.txt`的文件来描述工程依赖和导出相关的文件（更进阶的，可以使用 `conanfile.py`来精确控制这个过程）。

以配合 CMake 使用为例，`conanfile.txt`需要这样编写（官方用例）：

```
[requires]
Poco/1.7.8p3@pocoproject/stable

[generators]
cmake
```

这里要提一点，如果有包 A 依赖包 C 的 1.0 版本，包 B 依赖包 C 的 1.2 版本，此时就会出现冲突。通过手动在 Requires 中写入 `C/1.2@xxx/yyy`这样的依赖可以强制提升 C 的版本号为最新，从而解决冲突的问题。

这个 CMake 的 Generator 会在安装依赖后产生一个 `conanbuildinfo.cmake`供 CMake 使用来查找依赖。

那么工程对应的 `cmakefile.txt`会这样编写：

```
project(FoundationTimer)
cmake_minimum_required(VERSION 2.8.12)
add_definitions("-std=c++11")

include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)
conan_basic_setup()

add_executable(timer timer.cpp)
target_link_libraries(timer ${CONAN_LIBS})
```

其中 `${CONAN_LIBS}`就直接标明了所有的第三方依赖，直接链接（Link）上去就大功告成了。

整个安装依赖和构建的具体命令如下：

```
# 假设位于工程目录下
mkdir build  # out of source build
cd build
conan install ..  # 安装依赖和创建cmake导出文件，使用 --profile=xxx 来指定不同的构建环境
cmake ..
cmake --build . --config Release
```

## 进阶

Conan 确实极大的简化了依赖安装的过程，但是具体使用过程中也能发现 Conan 目前的弱点：

* 国内访问中心仓库的速度极慢
* 可选的软件包少，只涵盖知名度高的和常用的软件包

对于这两个缺陷，本文将通过自建软件源和自己编写软件包来解决。

### 1. 自建仓库

Conan 官方提供了一个迷你的服务端来提供仓库的功能，同时也推荐使用 `Artifactory Community Edition for C/C++`来自建仓库。当然，如果是为了开源项目，可以直接在 [Bintray](https://bintray.com/signup/oss) 上申请一个开源项目账号来上传自制软件包而无需自建仓库（但是实在是太慢了）。

本文使用 Artifactory 来自建仓库，因为功能相对完善。Artifactory 支持配置用户和组以及对应的权限，商业版本还支持高可用和分布式。

#### 安装

为了简单起见，本文采取 Docker 镜像的方式安装 Artifactory：

```
sudo docker pull docker.bintray.io/jfrog/artifactory-cpp-ce
```

以官方文档为例，使用下述命令即可创建容器：

```
sudo docker run -d --restart=always --name artifactory -v /data/artifactory:/var/opt/jfrog/artifactory -p 8081:8081 -e EXTRA_JAVA_OPTIONS='-Xms512m -Xmx2g -Xss256k -XX:+UseG1GC' docker.bintray.io/jfrog/artifactory-pro:latest
```

上述命令会暴露在本机的 `8081`端口上，同时挂载数据目录到 `/data/artifactory`目录下。

注意到，Artifactory 默认会以 UserID 1030 运行服务，一定要注意宿主机的数据目录的权限是否满足要求，如果启动时出现 Permission Denied 错误，记得修改目录权限：

```
sudo chown 1030:1030 /data/artifactory
sudo chmod 0755 /data/artifactory
```

你也可以使用 `--user 1234:4321`的方式来指定 Docker 使用哪个用户/组权限来执行容器。

#### 配置

首次访问 `http://localhost:8081`即可打开配置向导。默认的，配置好 Admin 账户的密码，初始化默认的 Conan 仓库配置即可。向导会提示你创建一个 HTTP Proxy，如果网络够好或者只作私仓使用则可以忽略该配置，否则，建议创建一个代理设置来加速访问 Remote 仓库。

Artifactory 提供了三种类型的 Conan 仓库供不同目的使用：

* 本地仓库（Local）：即当前 Artifactory 服务器上存储软件包的仓库；
* 远端仓库（Remote）：即第三方的软件仓库，在本服务器上作为 Proxy 和 Cache 运作；
* 虚拟仓库（Virtual）：作为一个索引中心，能将其他两类仓库整合到一个仓库名下，方便使用。

初始化之后，Artifactory 会创建好一个本地仓库，一个到 Conan Center 的远程仓库和包含上述两个仓库的虚拟仓库。

需要注意的是，默认配置下 Artifactory 是允许匿名访问的，必须在 Admin > Security Configuration 页面中关闭匿名访问才能真正作为私仓使用。

#### 添加到 Conan

在仓库管理页面，点击虚拟仓库 Conan，在右上角点击 Set Me Up 按钮即可显示当前仓库如何在 Conan 中配置并作为一个源。

![Artifactory Set Me Up](http://chu-studio.com/posts/2019/assets/artifactor_1566467205_29569.png)

照着上面写的步骤，即可把自建源加入到 Conan 中：

```
conan remote add <REMOTE> http://localhost:8081/artifactory/api/conan/conan
```

在使用之前，还需要修改你的 `conan.conf`，开启 `revisions_enabled`功能才能正常使用私仓。这是因为 Artifactory 并不支持 Conan v1 的协议，必须开启这一功能使用 v2 协议才能正常使用。

如果你配置了 Remote 仓库，则此时，你可以通过自己的私仓来访问到官方源，同时还可以配置上社区源来同时进行访问（然而社区源使用 v1 协议，导致并不能直接下载其上的包，这种情况下可以先下载社区源的包到本地，再上传到你的私仓上）。尤其在安装过官方仓库的软件包后，Artifactory 会将其缓存到本地，之后就会作为本地的 Cache 加速访问。

更多的配置可以参看官方文档，本文不再赘述。

### 2. 自建软件包

因为很多第三方开源项目没有 Conan 官方的支持，使用这些项目的时候就需要自己来编写 Receipe 来告诉 Conan 如何编译、打包第三方库了。

![Conan打包过程](http://chu-studio.com/posts/2019/assets/conan%E6%89%93%E5%8C%85%E8%BF%87%E7%A8%8B_1566475463_11093.png)

这里以 `bgfx`为例来构造一个 Conan 的二进制包，并提交到我们自建的私仓中。

因为 `bgfx`官方构建方式比较复杂，笔者选取了其 CMake 版本来执行构建。此外 Github 上已经有用户创建过对应的构建脚本了，因此这里可以直接参考别人的写法来进行构建。

使用 `conan new Hello/0.1 -t`可以创建一个 HelloWorld 的空白 Receipe。可以看到呈现出这样的目录结构：

```
conanfile.py
test_package
  CMakeLists.txt
  conanfile.py
  example.cpp
```

其中 `conanfile.py`用来描述构建软件包的编译打包过程，`test_package`存储一个测试用的样例，用来检查是否成功构建了软件包并且是否能正常使用。

以构建 `bgfx`的脚本为例，修改 `conanfile.py`：

```
from conans import ConanFile, CMake
from distutils.dir_util import copy_tree

class BgfxConan(ConanFile):
    name            = "bgfx"
    version         = "20190604.018bbc4"  # 这个地方我乱填的，请遵照SemVer的规范制定版本号
    description     = "Conan package for bgfx."
    url             = "https://github.com/9chu/bgfx-conan"
    license         = "BSD"
    settings        = "arch", "build_type", "compiler", "os"  # 这些选项会被作为包的标识，区分不同的ABI
    generators      = "cmake"
    options         = {"shared": [True, False]}
    default_options = "shared=False"

    def source(self):
        self.run("git clone https://github.com/JoshuaBrookover/bgfx.cmake")
        copy_tree("bgfx.cmake", ".")
        self.run("git reset --hard 018bbc4")
        self.run("git submodule update --init --recursive")

    def build(self):
        cmake          = CMake(self)
        shared_options = "-DBUILD_SHARED_LIBS=ON" if self.options.shared else "-DBUILD_SHARED_LIBS=OFF"
        fixed_options  = "-DBGFX_BUILD_EXAMPLES=OFF"
        tool_options   = "-DBGFX_BUILD_TOOLS=OFF" if self.settings.os == "Emscripten" else ""
        opengl_version = "-DBGFX_OPENGL_VERSION=33"
        self.run("cmake %s %s %s %s %s" % (cmake.command_line, shared_options, fixed_options, tool_options, opengl_version))
        self.run("cmake --build . %s -j8" % cmake.build_config)

    def collect_headers(self, include_folder):
        self.copy("*.h"  , dst="include", src=include_folder)
        self.copy("*.hpp", dst="include", src=include_folder)
        self.copy("*.inl", dst="include", src=include_folder)

    def package(self):
        self.collect_headers("bgfx/include")
        self.collect_headers("bimg/include")
        self.collect_headers("bx/include"  )
        self.copy("*.a"  , dst="lib", keep_path=False)
        self.copy("*.so" , dst="lib", keep_path=False)
        self.copy("*.lib", dst="lib", keep_path=False)
        self.copy("*.dll", dst="bin", keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["bgfxd", "bimgd", "bxd"] if self.settings.build_type == "Debug" else ["bgfx", "bimg", "bx"]
        self.cpp_info.libs.extend(["astc-codec", "astc", "edtaa3", "etc1", "etc2", "iqa", "squish", "nvtt", "pvrtc"])
        if self.settings.os == "Macos":
            self.cpp_info.exelinkflags = ["-framework Cocoa", "-framework QuartzCore", "-framework OpenGL", "-weak_framework Metal"]
        if self.settings.os == "Linux":
            self.cpp_info.libs.extend(["GL", "X11", "pthread", "dl"])
```

可以看到整个脚本分为若干个函数。其中，`source`函数，用于源代码拉取和准备，比如对源码进行一些修改；`build`函数，调用 CMake 进行构建；`package`函数，用于执行打包操作；`package_info`则用于输出构建相关的信息，比如需要链接包中的哪些库文件。

默认的，Conan 以 `lib`、`include`、`bin`等文件夹标识头文件库文件目录，也可以在 `package_info`函数中进行修改。此外，Conan 提供了一系列的驱动包装函数来执行各种第三方工具，以及定制版本号规则、设定依赖等等。具体可以通过查阅官方文档来进一步了解，本文仅作抛砖引玉的目的。

在构建完成后，Conan 会以 Settings 和 Options 的取值 Hash 后为软件包指定一个 package_id，因而不同的构建选项会对应到不同的 Id 上。最终拉取预编译包时就会以这个 Id 作为基准。因此，如果构建一个 Header-Only 的包，则可以去掉这些选项，这样在各个平台上都不需要额外构建即可使用了。

编写完 Receipe 后，就可以执行 Conan 来进行构建了。

```
conan install bgfx/20190604.018bbc4@9chu/stable --build=bgfx
```

构建完成后会自动执行 `test_package`的内容进行测试。最后使用命令上传到我们的私仓：

```
conan upload bgfx/20190604.018bbc4@9chu/stable --all -r=my_local_server
```

然后，我们就能在 Artifactory 中看到我们提交的包了。

![上传结果](http://chu-studio.com/posts/2019/assets/1566478305_22738.png)

### 3. 配合 CMake 实战

上传完自己制作的包，接下来就可以将其作为依赖引入自己的项目之中了。

在这里，推荐使用 Conan 官方提供的 [CMake 脚本](https://github.com/conan-io/cmake-conan)将其引入项目中。

```
cmake_minimum_required(VERSION 3.1)
project(test CXX)

######################################## conan package manager ########################################

# Download automatically, you can also just copy the conan.cmake file
if(NOT EXISTS "${CMAKE_BINARY_DIR}/conan.cmake")
    message(STATUS "Downloading conan.cmake from https://github.com/conan-io/cmake-conan")
    file(DOWNLOAD "https://github.com/conan-io/cmake-conan/raw/v0.14/conan.cmake"
        "${CMAKE_BINARY_DIR}/conan.cmake")
endif()

include(${CMAKE_BINARY_DIR}/conan.cmake)

######################################## dependencies ########################################

conan_cmake_run(
    REQUIRES
        bgfx/20190604.018bbc4@9chu/stable
    BASIC_SETUP CMAKE_TARGETS
    BUILD missing)

######################################## compiler flags ########################################

set(CMAKE_CXX_STANDARD 11)

if(MSVC)
    add_definitions(-D_WIN32_WINNT=0x0600 -D_GNU_SOURCE -D_CRT_SECURE_NO_WARNINGS)
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} /utf-8")
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} /utf-8")
else()
    set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -g -Wall -Wextra -Wno-implicit-fallthrough")
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -g -Wall -Wextra -Wno-implicit-fallthrough")
endif()

######################################## targets ########################################

file(GLOB_RECURSE TEST_SRC ${CMAKE_CURRENT_SOURCE_DIR}/include/*.hpp ${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp)

add_executable(test ${TEST_SRC})
target_include_directories(test PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(test CONAN_PKG::bgfx)
```

通过 `conan_cmake_run` 来直接指定依赖，这样就不需要写 `conanfile.txt` 并且会在 CMake 构建的时候自动把依赖安装上，集成到 CMake 中，非常的方便。

此外，由于使用了 `CMAKE_TARGETS`模式，依赖的指定方法也变成了 `CONAN_PKG::bgfx`的方式，这里可以根据需要自行调整。

## 总结

可以说，Conan 为 C++ 的依赖管理提供了非常好的解决方案。支持私仓，使得我们有机会将它作为私有组件的依赖管理工具。跨平台的特性，使得我们有机会配合 CMake 将环境配置、编译构建一条龙化。对于 C++ 的生态，这也是一件非常有益的事情。
