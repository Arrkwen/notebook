# add_executer和add_library的区别

ADD_EXECUTABLE()用来构建可执行程序，ADD_LIBRARY()来构建静态库或者动态库

```
ADD_LIBRARY(libname [SHARED|STATIC|MODULE] [EXCLUDE_FROM_ALL]
```

* libname代表要生成的静态库或者动态库的名字，名字前不用带lib 系统会自动加上。比如要生成libmath库名，写math就好
* [SHARED|STATIC|MODULE] 分别表示构建动态库(一般.so结尾,mac os 系统为.dyld)、(.a)静态库、动态库(mac os 系统为.so,如果不支持 则当做SHARED看待)；默认参数为STATIC
* EXCLUDE_FROM_ALL 意思是这个库不会被默认构建，除非有其他的组件依赖或者手工构建

# 单独构建静态库

```
ADD_LIBRARY(math ${SRC_LIST})
```

# 单独构建动态库

```
ADD_LIBRARY(math SHARED ${SRC_LIST})
```

# 同时构建静态库和动态库

使用指令实现 SET_TARGET_PROPERTIES(target1 target2 ... PROPERTIES prop1 value1 prop2 value2 ...)

1、它可以指定构建静态库目标的最终库名

2、它可以指定构建动态库目标的版本号

```
# 指定生成目标 目标名字随便写；${SRC_LIST}代表前面定义的源文件列表变量
ADD_LIBRARY(math SHARED ${SRC_LIST})
# 指定动态库具体版本号，VERSION，SOVERSION说明API主版本号。
SET_TARGET_PROPERTIES(math PROPERTIES VERSION 1.2 SOVERSION 1)

# 指定静态库名,区别于动态库名，然后再通过set_target_proprties修改
ADD_LIBRARY(math_static STATIC ${SRC_LIST})
# 改变最终生成的静态库的名字
SET_TARGET_PROPERTIES(math_static PROPERTIES OUTPUT_NAME math)

```

[参考](https://www.jianshu.com/p/07faa990147d)
