cmake对大小写不敏感，但是最好统一为大写。

# 1 添加头文件目录**INCLUDE_DIRECTORIES**

**语法：**

```
include_directories([AFTER|BEFORE] [SYSTEM] dir1 [dir2 ...])
```

它相当于g++选项中的-I参数的作用，也相当于环境变量中增加路径到CPLUS_INCLUDE_PATH变量的作用。

# 2 添加需要链接的库文件目录**LINK_DIRECTORIES**

**语法：**

```
link_directories(directory1 directory2 ...)
```

它相当于g++命令的-L选项的作用，也相当于环境变量中增加LD_LIBRARY_PATH的路径的作用。

# 3 查找库所在目录**FIND_LIBRARY**

link_directories相当于你已清楚需要链接的动态库所在的目录，但是如果某个库是系统的第三方库，但是你不知道在哪里，则可以使用find_libraries

**语法：**

```
find_library (<VAR> name1 [path1 path2 ...])
```

例子如下：

```
FIND_LIBRARY(RUNTIME_LIB rt /usr/lib  /usr/local/lib NO_DEFAULT_PATH)
```

cmake会在目录中查找，如果所有目录中都没有，值RUNTIME_LIB就会被赋为NO_DEFAULT_PATH

# 4 设置要链接的库文件的名称TARGET_LINK_LIBRARIES

**语法：**

```
target_link_libraries(<target> [item1 [item2 [...]]]
                      [[debug|optimized|general] <item>] ...)
```

它相当于g++命令的-l选项的作用

```
# 以下写法都可以： 
target_link_libraries(myProject comm)       # 连接libhello.so库，默认优先链接动态库
target_link_libraries(myProject libcomm.a)  # 显示指定链接静态库
target_link_libraries(myProject libcomm.so) # 显示指定链接动态库

# 再如：
target_link_libraries(myProject libcomm.so)　　#这些库名写法都可以。
target_link_libraries(myProject comm)
target_link_libraries(myProject -lcomm)
```

# 5 代码

```
./sample7
    |
    +--- CMakeLists.txt
    |
    +--- build/
    +--- src/
            +--- CMakeLists.txt
            +--- main.cpp
    +--- 3rdlib/
          +--- libMath.a
          +--- libmath.so
          +--- Math.h
```

sample7下的cmakelist.txt

```
# CMake 最低版本号要求
cmake_minimum_required (VERSION 2.8)

if(POLICY CMP0042)
  cmake_policy(SET CMP0042 NEW)  # CMake 3.0+ (2.8.12): MacOS "@rpath" in target's install name
endif()

# 项目工程名
project (sample7)
message(STATUS "root This is BINARY dir " ${PROJECT_BINARY_DIR})
message(STATUS "root This is SOURCE dir " ${PROJECT_SOURCE_DIR})

# 添加子目录
ADD_SUBDIRECTORY(src)
```

src目录下的Cmakelist.txt

```
# 打印信息
message(STATUS "src This is BINARY dir " ${PROJECT_BINARY_DIR})
message(STATUS "src This is SOURCE dir " ${PROJECT_SOURCE_DIR})

# 定义工程根目录; CMAKE_SOURCE_DIR为内建变量，表示工程根目录的CMakeLists.txt文件路径
SET(ROOT_DIR ${CMAKE_SOURCE_DIR})

# 指定头文件搜索路径，INCLUDE_DIRECTORIES相当于g++的-I参数
INCLUDE_DIRECTORIES(${ROOT_DIR}/3rdlib)

# 指定引用的外部库的搜索路径，LINK_DIRECTORIES相当于g++的-L参数
LINK_DIRECTORIES(${ROOT_DIR}/3rdlib)

# 指定可执行文件存放目录
SET(EXECUTABLE_OUTPUT_PATH ${PROJECT_BINARY_DIR}/bin)

# 构建可执行程序
ADD_EXECUTABLE(sample7 main.cpp)
# 链接静态库，TARGET_LINK_LIBRARIES相当于g++的-l参数
TARGET_LINK_LIBRARIES(sample7 libmath.a)
# 链接动态库
# TARGET_LINK_LIBRARIES(sample7 libmath.so)
# 会自动搜索：优先链接libmath.so，如果没有链接静态库。
# TARGET_LINK_LIBRARIES(sample7 math)
```

参考： https://www.jianshu.com/p/37fbe3dd202b
