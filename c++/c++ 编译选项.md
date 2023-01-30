# **C++ 编译总结**

**编译期间出现： /bin/ld: xxx.so: undefined reference to ，一般是两种错误，第一是链接的库里面确实没有实现对应的函数，第二种是cmake中没有添加对应的lib库依赖，需要添加-lxxx，或者library_include**

**运行期间出现：则需要export LD_LIBRARY_PATH**

## **1 编译选项说明： [参考]([https://www.cnblogs.com/ZhaoxiCheung/p/man-gcc.html](https://www.cnblogs.com/ZhaoxiCheung/p/man-gcc.html))**

## **2 GCC和CLANG 屏蔽编译选项**

### **全局关闭警告**

    根据报错，如果是第三方库的error，需要找到是报错warning的编译选项，然后在Other C Flags里对应的后面添加 -Wno-...就行，比如-Wno-pass-failed，可以屏蔽#prama unroll 无法展开警告

    比如在clang编译器下，-Wpedantic会报警告：warning: must specify at least one argument for '...' parameter of variadic macro [-Wgnu-zero-variadic-macro-arguments]，因此只需要在-Wpedantic 后添加： -Wno-gnu-zero-variadic-macro-arguments，便可以屏蔽此警告

### **局部关闭警告**

**clang <-->hipcc**

**#**pragma**clang diagnostic push**

**#**pragma**clang diagnostic ignored **"-Wunused-variable"

**不需要检查的code**

**#**pragma**clang diagnostic pop**

**gcc**

**#**pragma**GCC diagnostic push**

**#**pragma**GCC diagnostic ignored **"-Wunused-but-set-variable"

**#**pragma**GCC diagnostic ignored **"-Wmaybe-uninitialized"

**#**pragma**GCC diagnostic ignored **"-Wparentheses"

**#**pragma**GCC diagnostic ignored **"-Wunused-variable"

**不需要检查的code**

**#**pragma**GCC diagnostic pop**

## **3 混合编译**

如果一份程序中包含c代码，c++代码，cuda代码，如何混合编译？

## 4 交叉编译

如果一份代码需要编译出不同平台的代码功能，如何实现？

## 5 包依赖
