## 安装静态编译检查工具

ubuntu-dockerfile

```
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update --yes &&  apt-get install --no-install-recommends --yes \
    pciutils\
    build-essential \
    ca-certificates \
    openssl \
    libssl-dev \
    libxml2 \
    openssh-client \
    openssh-server \
    gfortran \
    net-tools \
    iputils-ping \
    git \
    git-lfs \
    valgrind \
    vim \
    curl \
    wget \
    gdb \
    tzdata \
    clang-format-10 \
    clang-tidy-10 \
    libx11-6 \
    && apt-get clean --yes && apt-get autoclean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/

ENV LANG C.UTF-8
ENV TZ Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone  && dpkg-reconfigure --frontend noninteractive tzdata

# git config
RUN git config --global lfs.url "https://lfs.sensetime.com/" \
    && git config --global credential.helper store

# cmake
ARG CMAKE_PKG=cmake-3.18.6-Linux-x86_64.sh
RUN mkdir /build && cd /build \
    && wget -q --show-progress --progress=bar:force:noscroll --no-check-certificate https://cmake.org/files/v3.18/${CMAKE_PKG} \
    && bash ${CMAKE_PKG} --skip-license --prefix=/usr/local  \
    && rm -rf /build

# miniconda and python
ARG CONDA_PKG=Miniconda3-py37_4.11.0-Linux-x86_64.sh
RUN mkdir /build && cd /build \
    && wget -q --show-progress --progress=bar:force:noscroll --no-check-certificate https://repo.anaconda.com/miniconda/${CONDA_PKG} \
    && bash ${CONDA_PKG} -b -p /opt/miniconda3 \
    && /opt/miniconda3/bin/conda install -y numpy matplotlib pandas requests \
    && /opt/miniconda3/bin/conda install -y -c conda-forge conan gcovr \
    && rm -rf /build
ENV PATH /opt/miniconda3/bin:${PATH}

# conan setup
RUN /opt/miniconda3/bin/conan remote remove conancenter \
    && /opt/miniconda3/bin/conan remote add kestrel http://conan.kestrel.sensetime.com/artifactory/api/conan/kestrel \
    && /opt/miniconda3/bin/conan remote add cstk http://conan.kestrel.sensetime.com/artifactory/api/conan/cstk

# openblas
ARG OPENBLAS_VERSION=0.3.20
RUN mkdir /build && cd /build \
    && wget -q --show-progress --progress=bar:force:noscroll --no-check-certificate https://github.com/xianyi/OpenBLAS/archive/refs/tags/v${OPENBLAS_VERSION}.tar.gz \
    && tar xzvf v${OPENBLAS_VERSION}.tar.gz >/dev/null 2>&1 \
    && cd OpenBLAS-${OPENBLAS_VERSION} \
    && make NUM_THREADS=32 USE_OPENMP=1 TARGET=HASWELL BINARY=64 -j 16 >/dev/null 2>&1 \
    && make PREFIX=/usr/local install >/dev/null 2>&1  \
    && rm -rf /build

# golang
RUN mkdir /build && cd /build \
    && export GO_PKG=go1.15.15.linux-amd64.tar.gz \
    && wget -q --show-progress --progress=bar:force:noscroll --no-check-certificate https://golang.google.cn/dl/${GO_PKG} \
    && rm -rf /usr/local/go && tar -C /usr/local -xzf ${GO_PKG} \
    && export PATH=/usr/local/go/bin:${PATH} \
    && go env -w GOPROXY=https://goproxy.cn,direct \
    && rm -rf /build
ENV PATH /usr/local/go/bin:${PATH}
ENV OMP_NUM_THREADS 8

RUN ldconfig

CMD [ "/bin/bash" ]

```

centos-dockerfile

```
FROM centos:7.6-dtk22.04.1-py37

RUN mv /etc/localtime /etc/localtime.bak && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

#openssl
RUN mkdir ~/openssl && cd ~/openssl \
    && rm -rf /etc/ssl \
    && rm -rf /usr/bin/openssl \
    && rm -rf /usr/include/openssl \
    && wget -q --no-cookie  --no-check-certificate https://github.com/openssl/openssl/archive/refs/tags/OpenSSL_1_1_1s.tar.gz \
    && tar -xf OpenSSL_1_1_1s.tar.gz \
    && cd openssl-OpenSSL_1_1_1s \
    && ./config \
    && make -j32 && make install \
    && ln -s /usr/local/bin/openssl /usr/bin/openssl \
    && ln -s /usr/local/include/openssl /usr/include/openssl \
    && rm -rf ~/openssl


RUN yum install  -y \
    pciutils\
    build-essential \
    ca-certificates \
    libssl-dev \
    libxml2 \
    net-tools \
    iputils-ping \
    git \
    git-lfs \
    valgrind \
    curl \
    wget \
    gdb \
    tzdata \
    libx11-6 \
    vim \
    && yum remove all

# git config
RUN git config --global lfs.url "https://lfs.sensetime.com/" \
    && git config --global credential.helper store

# cmake
ARG CMAKE_PKG=cmake-3.18.6-Linux-x86_64.sh
RUN mkdir /build && cd /build \
    && wget -q --no-check-certificate https://cmake.org/files/v3.18/${CMAKE_PKG} \
    && bash ${CMAKE_PKG} --skip-license --prefix=/usr/local  \
    && rm -rf /build

COPY CMakeCXXCompiler.cmake.in /usr/local/share/cmake-3.18/Modules/CMakeCXXCompiler.cmake.in

# miniconda and python
ARG CONDA_PKG=Miniconda3-py37_4.11.0-Linux-x86_64.sh
RUN mkdir /build && cd /build \
    && wget -q --no-check-certificate https://repo.anaconda.com/miniconda/${CONDA_PKG} \
    && bash ${CONDA_PKG} -b -p /opt/miniconda3 \
    && /opt/miniconda3/bin/conda install -y numpy matplotlib pandas requests \
    && /opt/miniconda3/bin/conda install -y -c conda-forge conan gcovr \
    && rm -rf /build
ENV PATH /opt/miniconda3/bin:${PATH}

# conan setup
RUN /opt/miniconda3/bin/conan remote remove conancenter \
    && /opt/miniconda3/bin/conan remote add kestrel http://conan.kestrel.sensetime.com/artifactory/api/conan/kestrel \
    && /opt/miniconda3/bin/conan remote add cstk http://conan.kestrel.sensetime.com/artifactory/api/conan/cstk

# openblas
ARG OPENBLAS_VERSION=0.3.20
RUN mkdir /build && cd /build \
    && wget -q --no-check-certificate https://github.com/xianyi/OpenBLAS/archive/refs/tags/v${OPENBLAS_VERSION}.tar.gz \
    && tar xzvf v${OPENBLAS_VERSION}.tar.gz >/dev/null 2>&1 \
    && cd OpenBLAS-${OPENBLAS_VERSION} \
    && make NUM_THREADS=32 USE_OPENMP=1 TARGET=HASWELL BINARY=64 -j 16 >/dev/null 2>&1 \
    && make PREFIX=/usr/local install >/dev/null 2>&1  \
    && rm -rf /build

# golang
RUN mkdir /build && cd /build \
    && export GO_PKG=go1.15.15.linux-amd64.tar.gz \
    && wget -q --no-check-certificate https://golang.google.cn/dl/${GO_PKG} \
    && rm -rf /usr/local/go && tar -C /usr/local -xzf ${GO_PKG} \
    && export PATH=/usr/local/go/bin:${PATH} \
    && go env -w GOPROXY=https://goproxy.cn,direct \
    && rm -rf /build
ENV PATH /usr/local/go/bin:${PATH}
ENV OMP_NUM_THREADS 8

# lapack
 ARG LAPACK_VERSION=3.9.1
 RUN mkdir /lapack && cd lapack \
    && wget -q --no-check-certificate https://github.com/Reference-LAPACK/lapack/archive/refs/tags/v${LAPACK_VERSION}.tar.gz \
    && tar xzvf v${LAPACK_VERSION}.tar.gz >/dev/null 2>&1 \
    && cd lapack-${LAPACK_VERSION} \
    && mkdir build && cd build \
    && CC=hipcc CXX=hipcc cmake -DCBLAS=ON -DLAPACKE=ON -DCMAKE_BUILD_TYPE=RELEASE -DBUILD_SHARED_LIBS=ON -DCMAKE_INSTALL_PREFIX=/usr/local .. \
    && make -j4 &&make install \
    && rm -rf /lapack
```
