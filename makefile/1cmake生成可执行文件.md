# 构建可执行文件

```
# CMake 最低版本号要求
cmake_minimum_required (VERSION 3.16)
# 项目信息 名字随便写
project (sample1)
message(STATUS "This is BINARY dir " ${sample1_BINARY_DIR})
message(STATUS "This is SOURCE dir " ${sample1_SOURCE_DIR})

# 定义源文件列表
set(SRC_LIST main.cpp)

# 设置可执行文件的输出路径，PROJECT_BINARY_DIR是内建变量，一般是make目录
set(EXECUTABLE_OUTPUT_PATH ${PROJECT_BINARY_DIR}/bin)

# 指定生成目标 目标名字随便写，和project指定的名字没有必然联系；${SRC_LIST}代表前面定义的源文件列表变量
add_executable(${PROJECT_NAME} ${SRC_LIST})

# 指定安装目录，会在cmake_install_prefix目录下创建lib,将可执行文件保存到lib目录下。
install(TARGETS ${PROJECT_NAME} DESTINATION lib)
```
