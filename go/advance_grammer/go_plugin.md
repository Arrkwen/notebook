[本文永久链接](https://tonybai.com/2021/07/19/understand-go-plugin) – https://tonybai.com/2021/07/19/understand-go-plugin

要历数Go语言中还有哪些我还没用过的特性，在[Go 1.8版本](https://tonybai.com/2017/02/03/some-changes-in-go-1-8/)中引入的[go plugin](https://pkg.go.dev/plugin@master)算一个。近期想给一个网关类平台设计一个插件系统，于是想起了go plugin^_^。

Go plugin支持将Go包编译为共享库（.so）的形式单独发布，主程序可以在运行时动态加载这些编译为动态共享库文件的go plugin，从中提取导出(exported)变量或函数的符号并在主程序的包中使用。Go plugin的这种特性为Go开发人员提供更多的灵活性，我们可以用之实现支持热插拔的插件系统。

但不得不提到的一个事实是： **go plugin自诞生以来已有4年多了，但它依旧没有被广泛地应用起来** 。究其原因，（我猜）一方面Go自身支持静态编译，可以将应用编译为一个完全不需要依赖操作系统运行时库(一般为libc)的可执行文件，这是Go的优势，而支持go plugin则意味着你只能对主程序进行动态编译，与静态编译的优势相悖；而另外一方面原因占比更大，那就是Go plugin自身有太多的对使用者的约束，这让很多Go开发人员望而却步。

 **只有亲历，才能体会到其中的滋味** 。在这篇文章中，我们就一起来看看go plugin究竟是何许东东，它对使用者究竟有着怎样的约束，我们究竟要不要使用它。

### 1. go plugin的基本使用方法

截至[Go 1.16版本](https://mp.weixin.qq.com/s/UPNn4G_m0zfvJgWxEVl_Tw)，Go官方文档明确说明 **go plugin只支持Linux, FreeBSD和macOS** ，这算是go plugin的第一个约束。在处理器层面，go plugin以支持amd64(x86-64)为主，对arm系列芯片的支持似乎没有明确说明（我翻看各个Go版本release notes也没看到，也许是我漏掉了），但我在华为的泰山服务器(鲲鹏arm64芯片)上使用Go 1.16.2(for arm64)版本构建plugin包以及加载动态共享库.so文件的主程序都顺利通过编译，运行也一切正常。

主程序通过plugin包加载.so并提取.so文件中的符号的过程与C语言应用运行时加载动态链接库并调用库中函数的过程如出一辙。下面我们就来看一个直观的例子。

下面是这个例子的结构布局：

```
// github.com/bigwhite/experiments/tree/master/go-plugin

├── demo1
│   ├── go.mod
│   ├── main.go
│   └── pkg
│       └── pkg1
│           └── pkg1.go
└── demo1-plugins
    ├── Makefile
    ├── go.mod
    └── plugin1.go
```

其中demo1代表主程序工程，demo1-plugins是主程序的plugins工程。下面是插件工程的代码：

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo1-plugins/plugin1.go

package main

import (
    "fmt"
    "log"
)

func init() {
    log.Println("plugin1 init")
}

var V int

func F() {
    fmt.Printf("plugin1: public integer variable V=%d\n", V)
}

type foo struct{}

func (foo) M1() {
    fmt.Println("plugin1: invoke foo.M1")
}

var Foo foo
```

plugin包和普通的Go包没太多区别，只是plugin包有一个约束：其包名必须为 **main** ，我们使用下面命令编译该plugin：

```
$go build -buildmode=plugin -o plugin1.so plugin1.go
```

如果plugin源代码没有放置在main包下面，我们在编译plugin时会遭遇如下编译器错误：

```
-buildmode=plugin requires exactly one main package
```

接下来，我们来看主程序(demo1)：

```
package main

import (
    "fmt"

    "github.com/bigwhite/demo1/pkg/pkg1"
)

func main() {
    err := pkg1.LoadAndInvokeSomethingFromPlugin("../demo1-plugins/plugin1.so")
    if err != nil {
        fmt.Println("LoadAndInvokeSomethingFromPlugin error:", err)
        return
    }
    fmt.Println("LoadAndInvokeSomethingFromPlugin ok")
}
```

下面是主程序demo1工程中的关键代码：

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo1/main.go
package main

import (
    "fmt"

    "github.com/bigwhite/demo1/pkg/pkg1"
)

func main() {
    err := pkg1.LoadAndInvokeSomethingFromPlugin("../demo1-plugins/plugin1.so")
    if err != nil {
        fmt.Println("LoadAndInvokeSomethingFromPlugin error:", err)
        return
    }
    fmt.Println("LoadAndInvokeSomethingFromPlugin ok")
}
```

我们在main函数中调用pkg1包的LoadAndInvokeSomethingFromPlugin函数，该函数会加载main函数传入的go plugin、查找plugin中相应符号并通过这些符号使用plugin中的导出变量、函数等。下面是LoadAndInvokeSomethingFromPlugin函数的实现：

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo1/pkg/pkg1/pkg1.go

package pkg1

import (
    "errors"
    "plugin"
    "log"
)

func init() {
    log.Println("pkg1 init")
}

type MyInterface interface {
    M1()
}

func LoadAndInvokeSomethingFromPlugin(pluginPath string) error {
    p, err := plugin.Open(pluginPath)
    if err != nil {
        return err
    }

    // 导出整型变量
    v, err := p.Lookup("V")
    if err != nil {
        return err
    }
    *v.(*int) = 15

    // 导出函数变量
    f, err := p.Lookup("F")
    if err != nil {
        return err
    }
    f.(func())()

    // 导出自定义类型变量
    f1, err := p.Lookup("Foo")
    if err != nil {
        return err
    }
    i, ok := f1.(MyInterface)
    if !ok {
        return errors.New("f1 does not implement MyInterface")
    }
    i.M1()

    return nil
}
```

在LoadAndInvokeSomethingFromPlugin函数中，我们通过plugin包提供的Plugin类型提供的Lookup方法在加载的.so中查找相应的导出符号，比如上面的V、F和Foo等。Lookup方法返回plugin.Symbol类型，而Symbol类型定义如下：

```
// $GOROOT/src/plugin/plugin.go
type Symbol interface{}
```

我们看到Symbol的底层类型(underlying type)是interface{}，因此它可以承载从plugin中找到的任何类型的变量、函数(得益于[函数是一等公民](https://www.imooc.com/read/87/article/2420))的符号。而plugin中定义的类型则是不能被主程序查找的，通常主程序也不会依赖plugin中定义的类型。

一旦Lookup成功，我们便可以将符号通过类型断言(type assert)获取到其真实类型的实例，通过这些实例(变量或函数)，我们可以调用plugin中实现的逻辑。编译plugin后，运行上述主程序，我们可以看到如下结果：

```
$go run main.go
2021/06/15 10:05:22 pkg1 init
try to LoadAndInvokeSomethingFromPlugin...
2021/06/15 10:05:22 plugin1 init
plugin1: public integer variable V=15
plugin1: invoke foo.M1
LoadAndInvokeSomethingFromPlugin ok
```

那么，主程序是如何知道导出的符号究竟是函数还是变量呢？这取决于主程序插件系统的设计，因为主程序与plugin间必然要有着某种“契约”或“约定”。就像上面主程序定义的MyInterface接口类型，它就是一个主程序与plugin之间的约定，plugin中只要暴露实现了该接口的类型实例，主程序便可以通过MyInterface接口类型实例与其建立关联并调用plugin中的实现 。

### 2. plugin中包的初始化

在上面的例子中我们看到，插件的初始化(plugin1 init)发生在主程序open .so文件时。按照官方文档的说法：“ **当一个插件第一次被open时，plugin中所有不属于主程序的包的init函数将被调用，但一个插件只被初始化一次，而且不能被关闭** ”。

我们来验证一下在主程序中多次加载同一个plugin的情况，这次我们将程序升级为demo2和demo2-plugins：

主程序代码如下：

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo2/main.go

package main

import (
    "fmt"

    "github.com/bigwhite/demo2/pkg/pkg1"
)

func main() {
    fmt.Println("try to LoadPlugin...")
    err := pkg1.LoadPlugin("../demo2-plugins/plugin1.so")
    if err != nil {
        fmt.Println("LoadPlugin error:", err)
        return
    }
    fmt.Println("LoadPlugin ok")
    err = pkg1.LoadPlugin("../demo2-plugins/plugin1.so")
    if err != nil {
        fmt.Println("Re-LoadPlugin error:", err)
        return
    }
    fmt.Println("Re-LoadPlugin ok")
}

package pkg1

import (
    "log"
    "plugin"
)

func init() {
    log.Println("pkg1 init")
}

func LoadPlugin(pluginPath string) error {
    _, err := plugin.Open(pluginPath)
    if err != nil {
        return err
    }
    return nil
}
```

由于仅是验证初始化，我们去掉了查找符号和调用的环节。plugin的代码如下：

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo2-plugins/plugin1.go
package main

import (
    "log"

    _ "github.com/bigwhite/common"
)

func init() {
    log.Println("plugin1 init")
}
```

在demo2的plugin中，我们同样仅保留初始化相关的代码，这里我们在demo2的plugin1中还增加了一个外部依赖：github.com/bigwhite/common。

运行上述代码：

```
$go run main.go
2021/06/15 10:50:47 pkg1 init
try to LoadPlugin...
2021/06/15 10:50:47 common init
2021/06/15 10:50:47 plugin1 init
LoadPlugin ok
Re-LoadPlugin ok
```

通过这个输出结果，我们验证了两点说法：

* 重复加载同一个plugin，不会触发多次plugin包的初始化，上述结果中 **仅输出一次** ：“plugin1 init”；
* plugin中依赖的包，但主程序中没有的包，在加载plugin时，这些包会被初始化，如：“commin init”。

如果主程序也依赖github.com/bigwhite/common包，我们在主程序的main包中增加一行：

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo2/main.go
import (
    "fmt"   

    _ "github.com/bigwhite/common"    // 增加这一行
    "github.com/bigwhite/demo2/pkg/pkg1"
)
```

那么我们再执行demo2，输出如下结果：

```
2021/06/15 11:00:00 common init
2021/06/15 11:00:00 pkg1 init
try to LoadPlugin...
2021/06/15 11:00:00 plugin1 init
LoadPlugin ok
Re-LoadPlugin ok
```

我们看到common包在demo2主程序中已经做了初始化，这样当加载plugin时，common包不会再进行初始化了。

### 3. go plugin的使用约束

开篇我们就提到了，go plugin应用不甚广泛的一个主因是其约束较多，这里我们来看一下究竟go plugin都有哪些约束：

#### 1) 主程序与plugin的共同依赖包的版本必须一致

在上面demo2中，主程序和plugin依赖的github.com/bigwhite/common包是一个本地module，我们在go.mod中使用replace指向本地路径：

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo2/go.mod

module github.com/bigwhite/demo2

replace github.com/bigwhite/common => /Users/tonybai/go/src/github.com/bigwhite/experiments/go-plugin/common

require github.com/bigwhite/common v0.0.0-20180202201655-eb2c6b5be1b6 // 这个版本号是自行“伪造”的

go 1.16
```

如果我clone一份common包，将其放在common1目录下，并在plugin的go.mod中将replace github.com/bigwhite/common语句指向common1目录，我们重新编译主程序和plugin后，运行主程序，我们将得到如下结果：

```
$go run main.go
2021/06/15 14:09:07 common init
2021/06/15 14:09:07 pkg1 init
try to LoadPlugin...
LoadPlugin error: plugin.Open("../demo2-plugins/plugin1"): plugin was built with a different version of package github.com/bigwhite/common
```

我们看到因common的版本不同，plugin加载失败，这是plugin使用的一个约束： **主程序与plugin的共同依赖包的版本必须一致** 。

我们再来看一个主程序与plugin有共同以来包的例子。我们建立demo3，在这个版本中，主程序和plugin都依赖了logrus日志包，但主程序使用的是logrus 1.8.1版本，而plugin使用的是logrus 1.8.0版本，分别编译后，我们运行主程序：

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo3

2021/06/15 14:18:35 pkg1 init
try to LoadPlugin...
LoadPlugin error: plugin.Open("../demo3-plugins/plugin1"): plugin was built with a different version of package github.com/sirupsen/logrus
```

我们看到主程序运行报错，和前面的例子提示一样，都是因为使用了版本不一致的第三方包。要想解决这个问题，我们只需让两者使用的logrus包版本保持一致即可，比如将主程序的logrus从v1.8.1降级为v1.8.0：

```
$go get github.com/sirupsen/logrus@v1.8.0
go get: downgraded github.com/sirupsen/logrus v1.8.1 => v1.8.0
$go run main.go
2021/06/15 14:19:09 pkg1 init
try to LoadPlugin...
2021/06/15 14:19:09 plugin1 init
LoadPlugin ok
```

我们看到降级logrus版本后，主程序便可以正常加载plugin了。

还有一种情况，那就是主程序与plugin使用了同一个module的不同major版本的包，由于major版本不同，虽然是同一module，但实则是两个不同的包，这不会影响主程序对plugin的加载。但问题在于这个被共同依赖的module也会有自己的依赖包，当其不同major版本所依赖的某个包的版本不同时，同样会导致主程序加载plugin出现问题。 比如：主程序依赖go-redis/redis的v6.15.9+incompatible版本，而plugin依赖的是go-redis/redis/v8版本，当我们使用这样的主程序去加载plugin时，我们会遇到如下错误：

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo3

$go run main.go
2021/06/15 14:32:11 pkg1 init
try to LoadPlugin...
LoadPlugin error: plugin.Open("../demo3-plugins/plugin1"): plugin was built with a different version of package golang.org/x/sys/unix
```

我们看到redis版本并未出错，但问题出在redis与redis/v8所依赖的golang.org/x/sys的版本不同， **这种间接依赖的module的版本的不一致同样会导致go plugin加载失败** ，这同样是go plugin的使用约束之一。

#### 2) 如果采用mod=vendor构建，那么主程序和plugin必须基于同一个vendor目录构建

基于vendor构建是[go 1.5版本](https://tonybai.com/2015/07/10/some-changes-in-go-1-5/)引入的特性，[go 1.11版本](https://tonybai.com/2018/11/19/some-changes-in-go-1-11/)引入go module构建模式后，vendor构建的方式得以保留。那么问题来了，如果主程序或plugin采用vendor构建或同时采用vendor构建，那么主程序是否可以正常加载plugin呢？我们来用示例demo4验证一下。(demo4和demo3大同小异，这里就不列出具体代码了）。

首先我们分别为主程序(demo4)和plugin(demo4-plugins)生成vendor目录：

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo4
$go mod vendor

// github.com/bigwhite/experiments/tree/master/go-plugin/demo4-plugins
$go mod vendor
```

我们测试如下三种情况(go 1.16版本默认在有vendor的情况下，优先使用vendor构建。所以要基于mod构建需要显式的传入-mod=mod)：

* 主程序基于mod构建，插件基于vendor构建

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo4-plugins
$go build -mod=vendor -buildmode=plugin -o plugin1.so plugin1.go

// github.com/bigwhite/experiments/tree/master/go-plugin/demo4
$go build -mod=mod -o main.mod main.go

$main.mod
2021/06/15 15:41:21 pkg1 init
try to LoadPlugin...
LoadPlugin error: plugin.Open("../demo4-plugins/plugin1"): plugin was built with a different version of package golang.org/x/sys/unix
```

* 主程序基于vendor构建，插件基于mod构建

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo4-plugins
$go build -mod=mod -buildmode=plugin -o plugin1.so plugin1.go

// github.com/bigwhite/experiments/tree/master/go-plugin/demo4
$go build -mod=vendor -o main.vendor main.go

$./main.vendor
2021/06/15 15:44:15 pkg1 init
try to LoadPlugin...
LoadPlugin error: plugin.Open("../demo4-plugins/plugin1"): plugin was built with a different version of package golang.org/x/sys/unix
```

* 主程序和插件分别基于各自的vendor构建

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo4-plugins
$go build -mod=vendor -buildmode=plugin -o plugin1.so plugin1.go

// github.com/bigwhite/experiments/tree/master/go-plugin/demo4
$go build -mod=vendor -o main.vendor main.go

$./main.vendor
2021/06/15 15:45:11 pkg1 init
try to LoadPlugin...
LoadPlugin error: plugin.Open("../demo4-plugins/plugin1"): plugin was built with a different version of package golang.org/x/sys/unix
```

从上面的测试，我们看到无论是哪一方采用vendor构建，或者双方都基于各自vendor构建，主程序加载plugin都会失败。如何解决这一问题呢？ **让主程序和plugin基于同一个vendor构建** !

我们将plugin1.go拷贝到demo4中，然后分别用vendor构建构建主程序和plugin1.go：

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo4
$go build -mod=vendor -o main.vendor main.go

// github.com/bigwhite/experiments/tree/master/go-plugin/demo4
$go build -mod=vendor -buildmode=plugin -o plugin1.so plugin1.go
```

将编译生成的plugin1.so拷贝到demo4-plugins中，然后运行main.vendor：

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo4
$cp plugin1.so ../demo4-plugins
$main.vendor
2021/06/15 15:48:56 pkg1 init
try to LoadPlugin...
2021/06/15 15:48:56 plugin1 init
LoadPlugin ok
```

我们看到基于同一vendor的主程序与plugin是可以相容的。下面的表格总结了主程序与plugin采用不同构建模式时是否相容：

| 插件构建方式\主程序构建方式 | 基于mod  | 基于自己的vendor |
| --------------------------- | -------- | ---------------- |
| 基于mod                     | 加载成功 | 加载失败         |
| 基于基于自己的vendor        | 加载失败 | 加载失败         |

 **在vendor构建模式下，只有基于同一个vendor目录构建时，plugin才能被主程序加载成功** ！

#### 3) 主程序与plugin使用的编译器版本必须一致

如果我们使用不同版本的Go编译器分别编译主程序以及plugin，那么这两者是否能相容呢？我们还拿demo4来验证一下。我在主机上准备了go 1.16.5和go 1.16两个版本的Go编译器，go 1.16.5是go 1.16的patch维护版本，其区别与go 1.16与go 1.15相比则不是一个量级的，我们用go 1.16编译主程序，用go 1.16.5编译plugin：

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo4-plugins
$go version
go version go1.16.5 darwin/amd64
$go build -buildmode=plugin -o plugin1.so plugin1.go

// github.com/bigwhite/experiments/tree/master/go-plugin/demo4
$go version
go version go1.16 darwin/amd64

$go run main.go
2021/06/15 15:58:44 pkg1 init
try to LoadPlugin...
LoadPlugin error: plugin.Open("../demo4-plugins/plugin1"): plugin was built with a different version of package runtime/internal/sys
```

我们看到即便用patch版本编译，plugin与主程序也是不兼容的。我们将demo4升级到用go 1.16.5版本编译：

```
$go version
go version go1.16.5 darwin/amd64
$go run main.go
2021/06/15 15:59:05 pkg1 init
try to LoadPlugin...
2021/06/15 15:59:05 plugin1 init
LoadPlugin ok
```

我们看到只有主程序与plugin采用完全相同的版本(patch版本也要相同）编译时，它们才是相容的，主程序才能正常加载plugin。

那么操作系统版本是否影响主程序和plugin的相容性呢？这个没有官方说明，我亲测了一下。我在centos 7.6(amd64, go 1.16.5)上构建了demo4-plugin(基于mod=mod），然后将其拷贝到一台ubuntu 18.04(amd64, go1.16.5)的主机上，ubuntu主机上的demo4主程序可以与centos上编译出来的plugin相容。

#### 4) 使用plugin的主程序仅能使用动态链接

Go以静态编译便于分发和部署著称，但 **使用plugin的主程序仅能使用动态链接** 。不信？那我们来挑战一下静态编译demo4中的主程序。

先来看看默认编译的情况：

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo4
$go build main.go
$ldd main
    linux-vdso.so.1 (0x00007ffc05b73000)
    libdl.so.2 => /lib/x86_64-linux-gnu/libdl.so.2 (0x00007f6a9fa3f000)
    libpthread.so.0 => /lib/x86_64-linux-gnu/libpthread.so.0 (0x00007f6a9f820000)
    libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007f6a9f42f000)
    /lib64/ld-linux-x86-64.so.2 (0x00007f6a9fc43000)
```

我们看到默认编译的情况下，demo4主程序被编译为一个需要在运行时动态链接的可执行文件，它依赖诸多linux系统运行时库，比如：libc等。

这一切的原因都是我们在demo4中使用了一些通过cgo实现的标准库，比如plugin包：

```
// $GOROOT/src/plugin/plugin_dlopen.go

// +build linux,cgo darwin,cgo freebsd,cgo

package plugin

/*
#cgo linux LDFLAGS: -ldl
#include <dlfcn.h>
#include <limits.h>
#include <stdlib.h>
#include <stdint.h>

#include <stdio.h>

static uintptr_t pluginOpen(const char* path, char** err) {
    void* h = dlopen(path, RTLD_NOW|RTLD_GLOBAL);
    if (h == NULL) {
        *err = (char*)dlerror();
    }
    return (uintptr_t)h;
}
... ...
*/
```

我们看到plugin_dlopen.go的头部有build指示符，它仅在cgo开启的前提下才会被编译，如果我们去掉cgo，比如利用下面这行命令：

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo4
$ CGO_ENABLED=0 go build main.go
$ ldd main
    not a dynamic executable
```

我们确实编译出一个静态链接的可执行文件，但当我们执行该文件时，我们得到如下结果：

```
$ ./main
2021/06/15 17:01:51 pkg1 init
try to LoadPlugin...
LoadPlugin error: plugin: not implemented
```

我们看到由于cgo被关闭，plugin包的一些函数并没有被编译到最终可执行文件中，于是报了”not implemented”的错误！

在CGO开启的情况下，我们依旧可以让外部链接器使用静态链接，我们再来试一下：

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo4

$ go build -o main-static -ldflags '-linkmode "external" -extldflags "-static"' main.go
# command-line-arguments
/tmp/go-link-638385712/000001.o: In function `pluginOpen':
/usr/local/go/src/plugin/plugin_dlopen.go:19: warning: Using 'dlopen' in statically linked applications requires at runtime the shared libraries from the glibc version used for linking
$ ldd main-static
    not a dynamic executable
```

我们的确得到了一个静态编译的二进制文件，但编译器也给出了warning。

执行这个文件：

```
$ ./main-static
2021/06/15 17:02:35 pkg1 init
try to LoadPlugin...
fatal error: runtime: no plugin module data

goroutine 1 [running]:
runtime.throw(0x5d380a, 0x1e)
    /usr/local/go/src/runtime/panic.go:1117 +0x72 fp=0xc000091b50 sp=0xc000091b20 pc=0x435712
plugin.lastmoduleinit(0xc000076210, 0x1001, 0x1001, 0xc000010040, 0x24db1f0)
    /usr/local/go/src/runtime/plugin.go:20 +0xb50 fp=0xc000091c48 sp=0xc000091b50 pc=0x466750
plugin.open(0x5d284c, 0x18, 0xc0000788f0, 0x0, 0x0)
    /usr/local/go/src/plugin/plugin_dlopen.go:77 +0x4ef fp=0xc000091ec0 sp=0xc000091c48 pc=0x4dad8f
plugin.Open(...)
    /usr/local/go/src/plugin/plugin.go:32
github.com/bigwhite/demo4/pkg/pkg1.LoadPlugin(0x5d284c, 0x1b, 0xc000091f48, 0x1)
    /root/test/go/plugin/demo4/pkg/pkg1/pkg1.go:13 +0x35 fp=0xc000091ef8 sp=0xc000091ec0 pc=0x4dbbb5
main.main()
    /root/test/go/plugin/demo4/main.go:12 +0xa5 fp=0xc000091f88 sp=0xc000091ef8 pc=0x4ee805
runtime.main()
    /usr/local/go/src/runtime/proc.go:225 +0x256 fp=0xc000091fe0 sp=0xc000091f88 pc=0x438196
runtime.goexit()
    /usr/local/go/src/runtime/asm_amd64.s:1371 +0x1 fp=0xc000091fe8 sp=0xc000091fe0 pc=0x46a841
```

warning最终演变为运行时的panic，看来使用plugin的主程序只能编译为动态链接的可执行程序了。目前go项目有多个issue与此有关：

* https://github.com/golang/go/issues/33072
* https://github.com/golang/go/issues/17150
* https://github.com/golang/go/issues/18123

### 4. plugin版本管理

使用动态链接实现插件系统，一个更大的问题就是插件的版本管理问题。

linux上的动态链接库采用soname的方式进行版本管理。soname的关键功能是它提供了兼容性的标准，当要升级系统中的一个库时，并且新库的soname和老库的soname一样，用旧库链接生成的程序使用新库依然能正常运行。这个特性使得在Linux下，升级使得共享库的程序和定位错误变得十分容易。

什么是soname呢？ 在/lib和/usr/lib等集中放置共享库的目录下，你总是会看到诸如下面的情况：

```
2019-12-10 12:28 libfoo.so -> libfoo.so.0.0.0*
2019-12-10 12:28 libfoo.so.0 -> libfoo.so.0.0.0*
2019-12-10 12:28 libfoo.so.0.0.0*
```

关于libfoo.so居然有三个文件入口，其中libfoo.so.0.0.0是真正的共享库文件，而其他两个文件入口则是指向libfoo.so.0.0.0的符号链接。为何会出现这个情况呢？这与共享库的命名惯例和版本管理不无关系。

共享库的惯例中每个共享库都有多个名字属性，包括real name、soname和linker name：

* real name

real name指的是实际包含共享库代码的那个文件的名字(如上面例子中的libfoo.so.0.0.0)，也是在共享库编译命令行中-o后面的那个参数；

* soname

soname则是shared object name的缩写，也是这三个名字中最重要的一个，无论是在编译阶段还是在运行阶段，系统链接器都是通过共享库的soname(如上面例子中的libfoo.so.0)来唯一识别共享库的。即使real name相同但soname不同，也会被链接器认为是两个不同的库。共享库的soname可在编译期间通过传给链接器的参数来指定，如我们可以通过”gcc -shared -Wl,-soname -Wl,libfoo.so.0 -o libfoo.so.0.0.0 libfoo.o”来指定libfoo.so.0.0.0的soname为libfoo.so.0。ldconfig -n directory_with_shared_libraries命令会根据共享库的soname自动生成一个名为soname的符号链接指向real name文件，当然你也可以通过ln命令自己来创建这个符号链接。另外在linux下我们可通过readelf -d查看共享库的soname，ldd输出的ELF文件依赖的共享库列表中显示的也是共享库的soname及所在路径。

* linker name

linker name是编译阶段提供给编译器的名字(如上面例子中的libfoo.so)。如果你构建的共享库的real name是类似于上例中libfoo.so.0.0.0那样的带有版本号的样子，那么你在编译器命令中直接使用-L path -lfoo是无法让链接器找到对应的共享库文件的，除非你为libfoo.so.0.0.0提供了一个linker name(如libfoo.so，一个指向libfoo.so.0.0.0的符号链接)。linker name一般在共享库安装时手工创建。

那么go plugin是否可以用soname的方式来做版本管理呢？基于demo1我们创建demo5，并来做一下试验。

在demo5-plugins中，我们为构建出的.so增加版本信息：

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo5-plugins

$go build -buildmode=plugin -o plugin1.so.1.1 plugin1.go
$ln -s plugin1.so.1.1 plugin1.so.1
$ls -l
lrwxr-xr-x  1 tonybai  staff       14  7 16 05:42 plugin1.so.1@ -> plugin1.so.1.1
-rw-r--r--  1 tonybai  staff  2888408  7 16 05:42 plugin1.so.1.1
```

我们通过ln命令为构建出的plugin1.so.1.1创建了一个符号链接plugin1.so.1，plugin1.so.1作为我们插件的soname传给demo5：

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo5/main.go

func main() {
    fmt.Println("try to LoadAndInvokeSomethingFromPlugin...")
    err := pkg1.LoadAndInvokeSomethingFromPlugin("../demo5-plugins/plugin1.so.1")
    if err != nil {
        fmt.Println("LoadAndInvokeSomethingFromPlugin error:", err)
        return
    }
    fmt.Println("LoadAndInvokeSomethingFromPlugin ok")
}
```

运行demo5：

```
// github.com/bigwhite/experiments/tree/master/go-plugin/demo5

$go run main.go
2021/07/16 05:58:33 pkg1 init
try to LoadAndInvokeSomethingFromPlugin...
2021/07/16 05:58:33 plugin1 init
plugin1: public integer variable V=15
plugin1: invoke foo.M1
LoadAndInvokeSomethingFromPlugin ok
```

我们看到以soname传入的插件被顺利加载并提取符号。

后续如果plugin发生变更，比如打了patch，我们只需要升级plugin为plugin1.so.1.2，然后soname依旧保持不变，主程序也无需变动。

 **注意：如果插件名相同，内容相同，主程序多次加载不会出现问题；但插件名相同，但内容不同，主程序运行时多次load会导致runtime panic，并且是无法恢复的panic。所以务必做好插件的版本管理** 。

### 5. 小结

go plugin是go语言原生提供的一种go插件方案（非go插件方案，可以使用c shared library等）。但经过上面的实验和学习，我们我们看到了plugin使用的诸多约束，这的确给go plugin的推广使用造成的很大障碍，导致目前go plugin应用不甚广泛。

根据上面看到的种种约束，如果要应用go plugin，必须要做到:

* 构建环境一致
* 对第三方包的版本一致。

因此，业内在使用go plugin时多利用builder container（用来构建程序的容器）来保证主程序和plugin使用相同的构建环境。

在go plugin为数不多的用户中，有三个比较知名的开源项目值得后续认真研究：

* [gosh](https://github.com/vladimirvivien/gosh): https://github.com/vladimirvivien/gosh
* [tyk api gateway](https://github.com/TykTechnologies/tyk): https://github.com/TykTechnologies/tyk
* [tidb](https://github.com/pingcap/tidb) : https://github.com/pingcap/tidb

尤其是tidb，还给出了其插件系统使用[go plugin的完整设计方案](https://github.com/pingcap/tidb/blob/master/docs/design/2018-12-10-plugin-framework.md)：https://github.com/pingcap/tidb/blob/master/docs/design/2018-12-10-plugin-framework.md，值得大家细致品读。

本文涉及的所有源码可以在[这里下载](https://github.com/bigwhite/experiments/tree/master/go-plugin/)：https://github.com/bigwhite/experiments/tree/master/go-plugin 。

### 6. 参考资料

* https://golang.org/pkg/plugin/
* https://golang.org/cmd/go/#hdr-Build_modes
* https://golang.org/doc/go1.8
* https://www.reddit.com/r/golang/comments/b6h8qq/is_anyone_actually_using_go_plugins/
* https://medium.com/@alperkose/things-to-avoid-while-using-golang-plugins-f34c0a636e8
* https://medium.com/learning-the-go-programming-language/writing-modular-go-programs-with-plugins-ec46381ee1a9
