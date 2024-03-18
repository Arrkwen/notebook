# Conan

Conan安装和远程仓库关联

1 安装

```
pip install conan
```

2 添加远程仓库

```
conan remote add conan_lib http://conan.conan_lib.com/artifactory/api/conan/conan_lib
```

3 添加用户

```
conan user -p <password> -r conan_lib <username>
```

## conan 创建包

1 编译包，将其安装到install目录下，我们以编译faiss的gpu包为例：

```
1 拉取代码
git clone https://github.com/facebookresearch/faiss.git

cd faiss

mkdir build && cd build

cmake -DCMAKE_INSTALL_PREFIX=../install \
      -DFAISS_ENABLE_PYTHON=OFF \
      -DBUILD_TESTING=OFF \
      -DBUILD_SHARED_LIBS=ON \
      -DCMAKE_BUILD_TYPE=Release \
      -DFAISS_OPT_LEVEL=avx2 \
      -DFAISS_ENABLE_GPU=ON \
      -DCUDAToolkit_ROOT=/usr/local/cuda \
      -DCMAKE_CUDA_ARCHITECTURES="75;" \
      ..

make -j48 faiss
make -j48 install

cd -

```

2 准备conanfile.py文本，在里面描述包的信息以及需要打包的代码路径

```
from conans import ConanFile, AutoToolsBuildEnvironment
from conans.model.version import Version

class FaissConan(ConanFile):
    name = "faiss"
    version = "1.7.2.6"
    license = "MIT License"
    url = "https://github.com/facebookresearch/faiss"
    description = "Facebook AI Similarity Searching"
    settings = "os", "os_target", "arch_target", "compiler"
    options = {"device": ["None", "CUDA8.0", "CUDA10.0", "CUDA11.0"]}
    default_options = {"device": "None"}

    def package(self):
        self.copy("*", dst="", src="install", symlinks=True)

    def package_id(self):
        self.info.requires.clear()
        v = Version(str(self.settings.compiler.version))
        if self.settings.compiler == "gcc" and (v >= "5.0"):
            self.info.settings.compiler.version = "5 and later"
    def configure(self):
        del self.settings.compiler.cppstd
        del self.settings.compiler.libcxx

```

2 准备分发的平台信息faiss.profile

```
[settings]
arch=Linux
arch_build=Linux
arch_target=Linux
build_type=Release
compiler=gcc
compiler.version=7.5
os=x86_64
os_build=x86_64
os_target=x86_64
[options]
device=CUDA11.0
[build_requires]
[env]

```

3 打包

```
conan export-pkg . conan_lib/stable -pr=./build/faiss.profile
```

4 上传包

```
conan upload faiss/1.7.2.6@conan_lib/stable -r conan_lib --all --con
firm
```

## conan 搜索包

```
搜索包的所有版本信息
conan search faiss --table table.html -r conan_lib

搜索某一个版本的所有信息
conan search faiss/1.7.2.6@conan_lib/stable --table table.html -r conan_lib
```

## conan 拉取包

拉取单个包

```
conan install faiss/1.7.2.6@conan_lib/stable -pr=faiss.profile
```

批量拉包，需要编写conanfile.py，添加build_requirments函数

```
from conans import ConanFile
from conans.model.version import Version


class ConanEaxample(ConanFile):
    name = "ConanEaxample"
    version = "1.0.0"
    settings = "os", "arch", "compiler", "build_type"
    options = {"device": ["None", "CUDA11.0", "CUDA12.0"]}
    default_options = {"device": "None"}
    description = """conan example"""
    url = "http://github.com/xxx"
    license = "xxx"
    author = "xxx"
    generators = "cmake"

    def package(self):
        self.copy("*", dst="", src="install", symlinks=True)

    def package_id(self):
        self.info.requires.clear()
        v = Version(str(self.settings.compiler.version))
        if self.settings.compiler == "gcc" and (v >= "5"):
            self.info.settings.compiler.version = "5 and later"

    def imports(self):
        self.copy("*", "deps/include", src="include")
        self.copy("*", "deps/lib", src="lib")

    def configure(self):
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd
        self.options["kestrel"].device = self.options.device
        self.options["kestrel_nart"].device = self.options.device
        if self.options.device != "S100ACC":
            self.options["faiss"].device = self.options.device
        if self.options.device == "ROCM":
            self.options["faiss"].device = "ROCM"
        if self.options.device == "enflame":
            self.options["faiss"].device = "None"
        self.options["openacl"].device = self.options.device

    def build_requirements(self):
        self.build_requires("benchmark/1.5.2@kestrel/stable")
        self.build_requires("gtest/1.8.1@kestrel/stable")
        self.build_requires("Eigen/3.3.5@kestrel/stable")
        self.build_requires("pybind11/2.5.0@conan_lib/stable")
        self.build_requires("hnswlib/0.4.0.2@conan_lib/stable")
        self.build_requires("spdlog/1.10.0@conan_lib/stable")
        self.build_requires("cpp-httplib/0.7.18@conan_lib/stable")
        self.build_requires("bearssl/2.0.0@kestrel/stable")

        self.build_requires(
            "xxx/{}@kestrel/stable".format(self.xxx_version))

        # Faiss
        if self.options.device == "Cambricon":
            self.build_requires("mlufaiss/v1.6.3.3@conan_lib/stable")
        elif self.options.device == "ROCM":
            self.build_requires("faiss/1.7.2.7@conan_lib/stable")
        else:
            self.build_requires("faiss/1.7.2.6@conan_lib/stable")
```

```
conan install . -pr=faiss.profile
```

或者将所有包相关的依赖写到一个文件里面，类似如下，命名为conanfile.txt

```
[requires]
lib1/2.4.0@conan_lib1/stable
nart/2.4.0@/conan_lib2stable
senu/2.6.0@conan_lib1/stable
encoder/2.6.0@conan_lib1/stable

[options]
lib1:device=CUDA11.0
nart:device=CUDA11.0
senu:device=None
encoder:device=None

[imports]
lib, * -> ./deps/lib @ excludes=static
```

下载

```
conan install conanfile.txt -pr=faiss.profile
```
