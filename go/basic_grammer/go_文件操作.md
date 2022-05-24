# go I/O库总结

[参考连接](https://mp.weixin.qq.com/s/Rz8ddGV6pq8-z3swiEDpVQ)

在计算机和信息技术领域里 `I/O`这个术语表示输入 / 输出 ( 英语：Input / Output ) ，通常指数据在存储器（内部和外部）或其他周边设备之间的输入和输出，是信息处理系统与外部之间的通信。输入是系统接收的信号或数据，输出则是从其发送的信号或数据。

在Go语言中涉及 `I/O`操作的内置库有很多种，比如：`io`库，`os`库，`ioutil`库，`bufio`库，`bytes`库，`strings`库等等。拥有这么多内置库是好事，但是具体到涉及 `I/O`的场景我们应该选择哪个库呢？

## io.Reader/Writer

Go语言里使用 `io.Reader`和 `io.Writer`两个 interface 来抽象 `I/O`，他们的定义如下。

```
type Reader interface {
 Read(p []byte) (n int, err error)
}

type Writer interface {
 Write(p []byte) (n int, err error)
}
```

`io.Reader` 接口代表一个可以从中读取字节流的实体，而 `io.Writer`则代表一个可以向其写入字节流的实体。

### io.Reader/Writer 常用的几种实现

* net.Conn: 表示网络连接。
* os.Stdin, os.Stdout, os.Stderr: 标准输入、输出和错误。
* os.File: 网络,标准输入输出,文件的流读取。
* strings.Reader: 字符串抽象成 io.Reader 的实现。
* bytes.Reader: []byte抽象成 io.Reader 的实现。
* bytes.Buffer: []byte抽象成 io.Reader 和 io.Writer 的实现。
* bufio.Reader/Writer: 带缓冲的流读取和写入（比如按行读写）。

除了这几种实现外常用的还有 `ioutil`工具库包含了很多IO工具函数，编码相关的内置库 `encoding/base64`、`encoding/binary`等也是通过 io.Reader 和 io.Writer 实现各自的编码功能的。

这些常用实现和工具库与io.Reader和io.Writer间的关系可以用下图表示。

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/z4pQ0O5h0f4Su3aNL1vDWgHXQ2LcA5E7XTxnlibOhNsMjQvDAEtF7h2vwre0HUVXd61iaRTlrLUsInfU3iayfLeWw/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

## 每种I/O库的使用场景

### io库

`io`库属于底层接口定义库。它的作用主要是定义个 `I/O`的基本接口和个基本常量，并解释这些接口的功能。在实际编写代码做 `I/O`操作时，这个库一般只用来调用它的常量和接口定义，比如用 `io.EOF`判断是否已经读取完，用 `io.Reader`做变量的类型声明。

```
// 字节流读取完后，会返回io.EOF这个error
for {
 n, err := r.Read(buf)
 fmt.Println(n, err, buf[:n])
 if err == io.EOF {
  break
 }
}
```

### os 库

`os`库主要是处理操作系统操作的，它作为Go程序和操作系统交互的桥梁。创建文件、打开或者关闭文件、Socket等等这些操作和都是和操作系统挂钩的，所以都通过 `os`库来执行。这个库经常和 `ioutil`，`bufio`等配合使用

### ioutil库

`ioutil`库是一个有工具包，它提供了很多实用的 IO 工具函数，例如 ReadAll、ReadFile、WriteFile、ReadDir。唯一需要注意的是它们都是一次性读取和一次性写入，所以使用时，尤其是把数据从文件里一次性读到内存中时需要注意文件的大小。

读出文件中的所有内容

```
func readByFile() {
  data, err := ioutil.ReadFile( "./file/test.txt")
  if err != nil {
    log.Fatal("err:", err)
    return
  }
  fmt.Println("data", string(data)) 
}
```

将数据一次性写入文件

```
func writeFile() {
  err := ioutil.WriteFile("./file/write_test.txt", []byte("hello world!"), 0644)
  if err != nil {
    panic(err)
    return
  }
}
```

### bufio库

bufio，可以理解为在 `io`库的基础上额外封装加了一个缓存层，它提供了很多按行进行读写的函数，从io库的按字节读写变为按行读写对写代码来说还是方便了不少。

```

func readBigFile(filePath string) error {
  f, err := os.Open(filePath)
  defer f.Close()

  if err != nil {
    log.Fatal(err)
    return err
  }

  buf := bufio.NewReader(f)
  count := 0
  // 循环中打印前100行内容
  for {
    count += 1
    line, err := buf.ReadString('\n')
    line = strings.TrimSpace(line)
    if err != nil {
      return err
    }
    fmt.Println("line", line)

    if count > 100 {
      break
    }
  }
  return nil
}
```

* ReadLine和ReadString方法：buf.ReadLine()，buf.ReadString("\n")都是按行读，只不过ReadLine读出来的是[]byte，后者直接读出了string，最终他们底层调用的都是ReadSlice方法。
* bufio VS ioutil 库：bufio 和 ioutil 库都提供了读写文件的能力。它们之间唯一的区别是 bufio 有一个额外的缓存层。这个优势主要体现在读取大文件的时候。

### bytes 和 strings 库

bytes 和 strings 库里的 bytes.Reader 和string.Reader，它们都实现了 `io.Reader`接口，也都提供了NewReader方法用来从 `[]byte`或者 `string`类型的变量直接构建出相应的Reader实现。

```
r := strings.NewReader("abcde")
// 或者是 bytes.NewReader([]byte("abcde"))
buf := make([]byte, 4)
for {
 n, err := r.Read(buf)
 fmt.Println(n, err, buf[:n])
 if err == io.EOF {
  break
 }
}
```

另一个区别是 bytes 库有Buffer的功能，而 strings 库则没有。

```
var buf bytes.Buffer
fmt.Fprintf(&buf, "Size: %d MB.", 85)
s := buf.String()) // s == "Size: 85 MB."
```

## 总结

关于 `io.Reader`和 `io.Writer`接口，可以简单理解为读源和写源。也就是说，只要实现了 `Reader`中的 `Read`方法，这个东西就可以作为读源，里面可以包含数据，被我们读取。`Writer`也是如此。

以上是我对Go语言里做 `I/O`操作时经常会用到的Go语言内置库在使用场景和每个库要解决的问题上的一些总结，希望能帮大家理清思路，作为参考，在开发任务中需要时正确选择合适的库完成 `I/O`操作。如果文章中的叙述有错误，欢迎留言指正，也欢迎在留言中对文章内容进行探讨和提出建议。

# 文件操作总结

Go官方提供的文件操作标准库分散在 `os`、`ioutil`等多个包中，里面有非常多的方法涵盖了文件操作的所有场景，不过因为我平时开发过程中需要直接操作文件的场景其实并不多，在加上 Go 标准库的文档太难搜索，每次遇到要使用文件函数时都是去 Google 查该怎么用。

最近偶然在查到国外一个人在2015年写的博客，他用常用的文件函数汇总了30多个文件操作场景，包括四大类： **基本操作、读写操作、文件压缩、其他操作** 。每一个文件操作都给了代码示例。写的非常好，强烈推荐你阅读一下，浏览一下它的目录，然后放到收藏夹里，要用到的时候拿出来 Copy and paste then adjust a little bit ! ![图片](https://mmbiz.qpic.cn/mmbiz_png/z4pQ0O5h0f7SpwIICZ9mzWnh0ESmsEtcOkLhnuTAia0QowvaQXHljO7UHoh0pQLWO3IibUPNpoLenq2EbvWkjA5g/640?wx_fmt=png&wxfrom=5&wx_lazy=1&wx_co=1)

关于 Go 的这些 IO 相互之间的差异，以及分别适合什么情况下使用，推荐阅读我以前的文章：[**Go语言的IO库那么多，我该怎么选？**](http://mp.weixin.qq.com/s?__biz=MzUzNTY5MzU2MA==&mid=2247487490&idx=1&sn=c016a569809ea2ef1e02df40ebd9916d&chksm=fa80c195cdf74883b82d89a5244fb53fa6f04e45686a3af4ca20c5787dc495f8d5e68c1e2a27&scene=21#wechat_redirect)

> 原文链接：https://www.devdungeon.com/content/working-files-go
>
> 作者：**NanoDano**
>
> 作者主页：https://www.devdungeon.com/users/nanodano

### 介绍

#### 一切皆文件

UNIX 的一个基础设计就是"万物皆文件"(everything is a file)。我们不必知道操作系统的设备驱动把什么映射给了一个文件描述符，操作系统为设备提供了文件格式的接口。

Go语言中的reader和writer接口也类似。我们只需简单的读写字节，不必知道reader的数据来自哪里，也不必知道writer将数据发送到哪里。你可以在 `/dev`下查看可用的设备，有些可能需要较高的权限才能访问。

### 文件基本操作

#### 创建空文件

```
package main

import (
    "log"
    "os"
)

var (
    newFile *os.File
    err     error
)

func main() {
    newFile, err = os.Create("test.txt")
    if err != nil {
        log.Fatal(err)
    }
    log.Println(newFile)
    newFile.Close()
}
```

#### Truncate裁剪文件

```
package main

import (
    "log"
    "os"
)

func main() {
    // 裁剪一个文件到100个字节。
    // 如果文件本来就少于100个字节，则文件中原始内容得以保留，剩余的字节以null字节填充。
    // 如果文件本来超过100个字节，则超过的字节会被抛弃。
    // 这样我们总是得到精确的100个字节的文件。
    // 传入0则会清空文件。

    err := os.Truncate("test.txt", 100)
    if err != nil {
        log.Fatal(err)
    }
}
```

#### 获取文件信息

1EB=1024PB
1PB=1024TB
1TB=1024GB
1GB=1024MB
1MB=1024KB
1KB=1024B

```
package main

import (
    "fmt"
    "log"
    "os"
)

var (
    fileInfo os.FileInfo
    err      error
)

func main() {
    // 如果文件不存在，则返回错误
    fileInfo, err = os.Stat("test.txt")
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println("File name:", fileInfo.Name())
    fmt.Println("Size in bytes:", fileInfo.Size())
    fmt.Println("Permissions:", fileInfo.Mode())
    fmt.Println("Last modified:", fileInfo.ModTime())
    fmt.Println("Is Directory: ", fileInfo.IsDir())
    fmt.Printf("System interface type: %T\n", fileInfo.Sys())
    fmt.Printf("System info: %+v\n\n", fileInfo.Sys())
}
```

#### 重命名和移动

```
package main

import (
    "log"
    "os"
)

func main() {
    originalPath := "test.txt"
    newPath := "test2.txt"
    err := os.Rename(originalPath, newPath)
    if err != nil {
        log.Fatal(err)
    }
}
```

#### 删除文件

```
package main

import (
    "log"
    "os"
)

func main() {
    err := os.Remove("test.txt")
    if err != nil {
        log.Fatal(err)
    }
}
```

#### 打开和关闭文件

```
package main

import (
    "log"
    "os"
)

func main() {
    // 简单地以只读的方式打开。下面的例子会介绍读写的例子。
    file, err := os.Open("test.txt")
    if err != nil {
        log.Fatal(err)
    }
    file.Close()

    // OpenFile提供更多的选项。
    // 最后一个参数是权限模式permission mode
    // 第二个是打开时的属性    
    file, err = os.OpenFile("test.txt", os.O_APPEND, 0666)
    if err != nil {
        log.Fatal(err)
    }
    file.Close()

    // 下面的属性可以单独使用，也可以组合使用。
    // 组合使用时可以使用 OR 操作设置 OpenFile的第二个参数，例如：
    // os.O_CREATE|os.O_APPEND
    // 或者 os.O_CREATE|os.O_TRUNC|os.O_WRONLY

    // os.O_RDONLY // 只读
    // os.O_WRONLY // 只写
    // os.O_RDWR // 读写
    // os.O_APPEND // 往文件中添建（Append）
    // os.O_CREATE // 如果文件不存在则先创建
    // os.O_TRUNC // 文件打开时裁剪文件
    // os.O_EXCL // 和O_CREATE一起使用，文件不能存在
    // os.O_SYNC // 以同步I/O的方式打开
}
```

#### 检查文件是否存在

```
package main

import (
    "log"
    "os"
)

var (
    fileInfo *os.FileInfo
    err      error
)

func main() {
    // 文件不存在则返回error
    fileInfo, err := os.Stat("test.txt")
    if err != nil {
        if os.IsNotExist(err) {
            log.Fatal("File does not exist.")
        }
    }
    log.Println("File does exist. File information:")
    log.Println(fileInfo)
}
```

#### 检查读写权限

```
package main

import (
    "log"
    "os"
)

func main() {
    // 这个例子测试写权限，如果没有写权限则返回error。
    // 注意文件不存在也会返回error，需要检查error的信息来获取到底是哪个错误导致。
    file, err := os.OpenFile("test.txt", os.O_WRONLY, 0666)
    if err != nil {
        if os.IsPermission(err) {
            log.Println("Error: Write permission denied.")
        }
    }
    file.Close()

    // 测试读权限
    file, err = os.OpenFile("test.txt", os.O_RDONLY, 0666)
    if err != nil {
        if os.IsPermission(err) {
            log.Println("Error: Read permission denied.")
        }
    }
    file.Close()
}
```

#### 改变权限、拥有者、时间戳

```
package main

import (
    "log"
    "os"
    "time"
)

func main() {
    // 使用Linux风格改变文件权限
    err := os.Chmod("test.txt", 0777)
    if err != nil {
        log.Println(err)
    }

    // 改变文件所有者
    err = os.Chown("test.txt", os.Getuid(), os.Getgid())
    if err != nil {
        log.Println(err)
    }

    // 改变时间戳
    twoDaysFromNow := time.Now().Add(48 * time.Hour)
    lastAccessTime := twoDaysFromNow
    lastModifyTime := twoDaysFromNow
    err = os.Chtimes("test.txt", lastAccessTime, lastModifyTime)
    if err != nil {
        log.Println(err)
    }
}
```

#### 创建硬链接和软链接

一个普通的文件是一个指向硬盘的inode的地方。硬链接创建一个新的指针指向同一个地方。只有所有的链接被删除后文件才会被删除。硬链接只在相同的文件系统中才工作。你可以认为一个硬链接是一个正常的链接。

symbolic link，又叫软连接，和硬链接有点不一样，它不直接指向硬盘中的相同的地方，而是通过名字引用其它文件。他们可以指向不同的文件系统中的不同文件。并不是所有的操作系统都支持软链接。

```
package main

import (
    "os"
    "log"
    "fmt"
)

func main() {
    // 创建一个硬链接。
    // 创建后同一个文件内容会有两个文件名，改变一个文件的内容会影响另一个。
    // 删除和重命名不会影响另一个。
    err := os.Link("original.txt", "original_also.txt")
    if err != nil {
        log.Fatal(err)
    }

    fmt.Println("creating sym")
    // Create a symlink
    err = os.Symlink("original.txt", "original_sym.txt")
    if err != nil {
        log.Fatal(err)
    }

    // Lstat返回一个文件的信息，但是当文件是一个软链接时，它返回软链接的信息，而不是引用的文件的信息。
    // Symlink在Windows中不工作。
    fileInfo, err := os.Lstat("original_sym.txt")
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Link info: %+v", fileInfo)

    //改变软链接的拥有者不会影响原始文件。
    err = os.Lchown("original_sym.txt", os.Getuid(), os.Getgid())
    if err != nil {
        log.Fatal(err)
    }
}
```

### 文件读写

#### 复制文件

```
package main

import (
    "os"
    "log"
    "io"
)

func main() {
    // 打开原始文件
    originalFile, err := os.Open("test.txt")
    if err != nil {
        log.Fatal(err)
    }
    defer originalFile.Close()

    // 创建新的文件作为目标文件
    newFile, err := os.Create("test_copy.txt")
    if err != nil {
        log.Fatal(err)
    }
    defer newFile.Close()

    // 从源中复制字节到目标文件
    bytesWritten, err := io.Copy(newFile, originalFile)
    if err != nil {
        log.Fatal(err)
    }
    log.Printf("Copied %d bytes.", bytesWritten)

    // 将文件内容flush到硬盘中
    err = newFile.Sync()
    if err != nil {
        log.Fatal(err)
    }
}
```

#### 跳转到文件指定位置(Seek)

```
package main

import (
    "os"
    "fmt"
    "log"
)

func main() {
    file, _ := os.Open("test.txt")
    defer file.Close()

    // 偏离位置，可以是正数也可以是负数
    var offset int64 = 5

    // 用来计算offset的初始位置
    // 0 = 文件开始位置
    // 1 = 当前位置
    // 2 = 文件结尾处
    var whence int = 0
    newPosition, err := file.Seek(offset, whence)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println("Just moved to 5:", newPosition)

    // 从当前位置回退两个字节
    newPosition, err = file.Seek(-2, 1)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println("Just moved back two:", newPosition)

    // 使用下面的技巧得到当前的位置
    currentPosition, err := file.Seek(0, 1)
    fmt.Println("Current position:", currentPosition)

    // 转到文件开始处
    newPosition, err = file.Seek(0, 0)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println("Position after seeking 0,0:", newPosition)
}
```

#### 写文件

可以使用 `os`包写入一个打开的文件。因为Go可执行包是静态链接的可执行文件，你import的每一个包都会增加你的可执行文件的大小。其它的包如 `io`、｀ioutil｀、｀bufio｀提供了一些方法，但是它们不是必须的。

```
package main

import (
    "os"
    "log"
)

func main() {
    // 可写方式打开文件
    file, err := os.OpenFile(
        "test.txt",
        os.O_WRONLY|os.O_TRUNC|os.O_CREATE,
        0666,
    )
    if err != nil {
        log.Fatal(err)
    }
    defer file.Close()

    // 写字节到文件中
    byteSlice := []byte("Bytes!\n")
    bytesWritten, err := file.Write(byteSlice)
    if err != nil {
        log.Fatal(err)
    }
    log.Printf("Wrote %d bytes.\n", bytesWritten)
}
```

#### 快写文件

`ioutil`包有一个非常有用的方法 `WriteFile()`可以处理创建或者打开文件、写入字节切片和关闭文件一系列的操作。如果你需要简洁快速地写字节切片到文件中，你可以使用它。

```
package main

import (
    "io/ioutil"
    "log"
)

func main() {
    err := ioutil.WriteFile("test.txt", []byte("Hi\n"), 0666)
    if err != nil {
        log.Fatal(err)
    }
}
```

#### 使用缓存写

`bufio`包提供了带缓存功能的writer，所以你可以在写字节到硬盘前使用内存缓存。当你处理很多的数据很有用，因为它可以节省操作硬盘I/O的时间。在其它一些情况下它也很有用，比如你每次写一个字节，把它们攒在内存缓存中，然后一次写入到硬盘中，减少硬盘的磨损以及提升性能。

```
package main

import (
    "log"
    "os"
    "bufio"
)

func main() {
    // 打开文件，只写
    file, err := os.OpenFile("test.txt", os.O_WRONLY, 0666)
    if err != nil {
        log.Fatal(err)
    }
    defer file.Close()

    // 为这个文件创建buffered writer
    bufferedWriter := bufio.NewWriter(file)

    // 写字节到buffer
    bytesWritten, err := bufferedWriter.Write(
        []byte{65, 66, 67},
    )
    if err != nil {
        log.Fatal(err)
    }
    log.Printf("Bytes written: %d\n", bytesWritten)

    // 写字符串到buffer
    // 也可以使用 WriteRune() 和 WriteByte()   
    bytesWritten, err = bufferedWriter.WriteString(
        "Buffered string\n",
    )
    if err != nil {
        log.Fatal(err)
    }
    log.Printf("Bytes written: %d\n", bytesWritten)

    // 检查缓存中的字节数
    unflushedBufferSize := bufferedWriter.Buffered()
    log.Printf("Bytes buffered: %d\n", unflushedBufferSize)

    // 还有多少字节可用（未使用的缓存大小）
    bytesAvailable := bufferedWriter.Available()
    if err != nil {
        log.Fatal(err)
    }
    log.Printf("Available buffer: %d\n", bytesAvailable)

    // 写内存buffer到硬盘
    bufferedWriter.Flush()

    // 丢弃还没有flush的缓存的内容，清除错误并把它的输出传给参数中的writer
    // 当你想将缓存传给另外一个writer时有用
    bufferedWriter.Reset(bufferedWriter)

    bytesAvailable = bufferedWriter.Available()
    if err != nil {
        log.Fatal(err)
    }
    log.Printf("Available buffer: %d\n", bytesAvailable)

    // 重新设置缓存的大小。
    // 第一个参数是缓存应该输出到哪里，这个例子中我们使用相同的writer。
    // 如果我们设置的新的大小小于第一个参数writer的缓存大小， 比如10，我们不会得到一个10字节大小的缓存，
    // 而是writer的原始大小的缓存，默认是4096。
    // 它的功能主要还是为了扩容。
    bufferedWriter = bufio.NewWriterSize(
        bufferedWriter,
        8000,
    )

    // resize后检查缓存的大小
    bytesAvailable = bufferedWriter.Available()
    if err != nil {
        log.Fatal(err)
    }
    log.Printf("Available buffer: %d\n", bytesAvailable)
}
```

#### 读取最多N个字节

`os.File`提供了文件操作的基本功能， 而 `io`、`ioutil`、`bufio`提供了额外的辅助函数。

```
package main

import (
    "os"
    "log"
)

func main() {
    // 打开文件，只读
    file, err := os.Open("test.txt")
    if err != nil {
        log.Fatal(err)
    }
    defer file.Close()

    // 从文件中读取len(b)字节的文件。
    // 返回0字节意味着读取到文件尾了
    // 读取到文件会返回io.EOF的error
    byteSlice := make([]byte, 16)
    bytesRead, err := file.Read(byteSlice)
    if err != nil {
        log.Fatal(err)
    }
    log.Printf("Number of bytes read: %d\n", bytesRead)
    log.Printf("Data read: %s\n", byteSlice)
}
```

#### 读取正好N个字节

```
package main

import (
    "os"
    "log"
    "io"
)

func main() {
    // Open file for reading
    file, err := os.Open("test.txt")
    if err != nil {
        log.Fatal(err)
    }

    // file.Read()可以读取一个小文件到大的byte slice中，
    // 但是io.ReadFull()在文件的字节数小于byte slice字节数的时候会返回错误
    byteSlice := make([]byte, 2)
    numBytesRead, err := io.ReadFull(file, byteSlice)
    if err != nil {
        log.Fatal(err)
    }
    log.Printf("Number of bytes read: %d\n", numBytesRead)
    log.Printf("Data read: %s\n", byteSlice)
}
```

#### 读取至少N个字节

```
package main

import (
    "os"
    "log"
    "io"
)

func main() {
    // 打开文件，只读
    file, err := os.Open("test.txt")
    if err != nil {
        log.Fatal(err)
    }

    byteSlice := make([]byte, 512)
    minBytes := 8
    // io.ReadAtLeast()在不能得到最小的字节的时候会返回错误，但会把已读的文件保留
    numBytesRead, err := io.ReadAtLeast(file, byteSlice, minBytes)
    if err != nil {
        log.Fatal(err)
    }
    log.Printf("Number of bytes read: %d\n", numBytesRead)
    log.Printf("Data read: %s\n", byteSlice)
}
```

#### 读取全部字节

```
package main

import (
    "os"
    "log"
    "fmt"
    "io/ioutil"
)

func main() {
    file, err := os.Open("test.txt")
    if err != nil {
        log.Fatal(err)
    }

    // os.File.Read(), io.ReadFull() 和
    // io.ReadAtLeast() 在读取之前都需要一个固定大小的byte slice。
    // 但ioutil.ReadAll()会读取reader(这个例子中是file)的每一个字节，然后把字节slice返回。
    data, err := ioutil.ReadAll(file)
    if err != nil {
        log.Fatal(err)
    }

    fmt.Printf("Data as hex: %x\n", data)
    fmt.Printf("Data as string: %s\n", data)
    fmt.Println("Number of bytes read:", len(data))
}
```

#### 快读到内存

```
package main

import (
    "log"
    "io/ioutil"
)

func main() {
    // 读取文件到byte slice中
    data, err := ioutil.ReadFile("test.txt")
    if err != nil {
        log.Fatal(err)
    }

    log.Printf("Data read: %s\n", data)
}
```

#### 使用缓存读

有缓存写也有缓存读。缓存reader会把一些内容缓存在内存中。它会提供比 `os.File`和 `io.Reader`更多的函数,缺省的缓存大小是4096，最小缓存是16。

```
package main

import (
    "os"
    "log"
    "bufio"
    "fmt"
)

func main() {
    // 打开文件，创建buffered reader
    file, err := os.Open("test.txt")
    if err != nil {
        log.Fatal(err)
    }
    bufferedReader := bufio.NewReader(file)

    // 得到字节，当前指针不变
    byteSlice := make([]byte, 5)
    byteSlice, err = bufferedReader.Peek(5)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Peeked at 5 bytes: %s\n", byteSlice)

    // 读取，指针同时移动
    numBytesRead, err := bufferedReader.Read(byteSlice)
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Read %d bytes: %s\n", numBytesRead, byteSlice)

    // 读取一个字节, 如果读取不成功会返回Error
    myByte, err := bufferedReader.ReadByte()
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Read 1 byte: %c\n", myByte)     

    // 读取到分隔符，包含分隔符，返回byte slice
    dataBytes, err := bufferedReader.ReadBytes('\n')
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Read bytes: %s\n", dataBytes)           

    // 读取到分隔符，包含分隔符，返回字符串
    dataString, err := bufferedReader.ReadString('\n')
    if err != nil {
        log.Fatal(err)
    }
    fmt.Printf("Read string: %s\n", dataString)     

    //这个例子读取了很多行，所以test.txt应该包含多行文本才不至于出错
}
```

#### 使用 scanner

`Scanner`是 `bufio`包下的类型,在处理文件中以分隔符分隔的文本时很有用。通常我们使用换行符作为分隔符将文件内容分成多行。在CSV文件中，逗号一般作为分隔符。`os.File`文件可以被包装成 `bufio.Scanner`，它就像一个缓存reader。我们会调用 `Scan()`方法去读取下一个分隔符，使用 `Text()`或者 `Bytes()`获取读取的数据。

分隔符可以不是一个简单的字节或者字符，有一个特殊的方法可以实现分隔符的功能，以及将指针移动多少，返回什么数据。如果没有定制的 `SplitFunc`提供，缺省的 `ScanLines`会使用 `newline`字符作为分隔符，其它的分隔函数还包括 `ScanRunes`和 `ScanWords`,皆在 `bufio`包中。

```
// To define your own split function, match this fingerprint
type SplitFunc func(data []byte, atEOF bool) (advance int, token []byte, err error)

// Returning (0, nil, nil) will tell the scanner
// to scan again, but with a bigger buffer because
// it wasn't enough data to reach the delimiter
```

下面的例子中，为一个文件创建了 `bufio.Scanner`，并按照单词逐个读取：

```
package main

import (
    "os"
    "log"
    "fmt"
    "bufio"
)

func main() {
    file, err := os.Open("test.txt")
    if err != nil {
        log.Fatal(err)
    }
    scanner := bufio.NewScanner(file)

    // 缺省的分隔函数是bufio.ScanLines,我们这里使用ScanWords。
    // 也可以定制一个SplitFunc类型的分隔函数
    scanner.Split(bufio.ScanWords)

    // scan下一个token.
    success := scanner.Scan()
    if success == false {
        // 出现错误或者EOF是返回Error
        err = scanner.Err()
        if err == nil {
            log.Println("Scan completed and reached EOF")
        } else {
            log.Fatal(err)
        }
    }

    // 得到数据，Bytes() 或者 Text()
    fmt.Println("First word found:", scanner.Text())

    // 再次调用scanner.Scan()发现下一个token
}
```

### 文件压缩

#### 打包(zip) 文件

```
// This example uses zip but standard library
// also supports tar archives
package main

import (
    "archive/zip"
    "log"
    "os"
)

func main() {
    // 创建一个打包文件
    outFile, err := os.Create("test.zip")
    if err != nil {
        log.Fatal(err)
    }
    defer outFile.Close()

    // 创建zip writer
    zipWriter := zip.NewWriter(outFile)


    // 往打包文件中写文件。
    // 这里我们使用硬编码的内容，你可以遍历一个文件夹，把文件夹下的文件以及它们的内容写入到这个打包文件中。
    var filesToArchive = []struct {
        Name, Body string
    } {
        {"test.txt", "String contents of file"},
        {"test2.txt", "\x61\x62\x63\n"},
    }

    // 下面将要打包的内容写入到打包文件中，依次写入。
    for _, file := range filesToArchive {
            fileWriter, err := zipWriter.Create(file.Name)
            if err != nil {
                    log.Fatal(err)
            }
            _, err = fileWriter.Write([]byte(file.Body))
            if err != nil {
                    log.Fatal(err)
            }
    }

    // 清理
    err = zipWriter.Close()
    if err != nil {
            log.Fatal(err)
    }
}
```

#### 抽取(unzip) 文件

```
// This example uses zip but standard library
// also supports tar archives
package main

import (
    "archive/zip"
    "log"
    "io"
    "os"
    "path/filepath"
)

func main() {
    zipReader, err := zip.OpenReader("test.zip")
    if err != nil {
        log.Fatal(err)
    }
    defer zipReader.Close()

    // 遍历打包文件中的每一文件/文件夹
    for _, file := range zipReader.Reader.File {
        // 打包文件中的文件就像普通的一个文件对象一样
        zippedFile, err := file.Open()
        if err != nil {
            log.Fatal(err)
        }
        defer zippedFile.Close()

        // 指定抽取的文件名。
        // 你可以指定全路径名或者一个前缀，这样可以把它们放在不同的文件夹中。
        // 我们这个例子使用打包文件中相同的文件名。
        targetDir := "./"
        extractedFilePath := filepath.Join(
            targetDir,
            file.Name,
        )

        // 抽取项目或者创建文件夹
        if file.FileInfo().IsDir() {
            // 创建文件夹并设置同样的权限
            log.Println("Creating directory:", extractedFilePath)
            os.MkdirAll(extractedFilePath, file.Mode())
        } else {
            //抽取正常的文件
            log.Println("Extracting file:", file.Name)

            outputFile, err := os.OpenFile(
                extractedFilePath,
                os.O_WRONLY|os.O_CREATE|os.O_TRUNC,
                file.Mode(),
            )
            if err != nil {
                log.Fatal(err)
            }
            defer outputFile.Close()

            // 通过io.Copy简洁地复制文件内容
            _, err = io.Copy(outputFile, zippedFile)
            if err != nil {
                log.Fatal(err)
            }
        }
    }
}
```

#### 压缩文件

```
// 这个例子中使用gzip压缩格式，标准库还支持zlib, bz2, flate, lzw
package main

import (
    "os"
    "compress/gzip"
    "log"
)

func main() {
    outputFile, err := os.Create("test.txt.gz")
    if err != nil {
        log.Fatal(err)
    }

    gzipWriter := gzip.NewWriter(outputFile)
    defer gzipWriter.Close()

    // 当我们写如到gizp writer数据时，它会依次压缩数据并写入到底层的文件中。
    // 我们不必关心它是如何压缩的，还是像普通的writer一样操作即可。
    _, err = gzipWriter.Write([]byte("Gophers rule!\n"))
    if err != nil {
        log.Fatal(err)
    }

    log.Println("Compressed data written to file.")
}
```

#### 解压缩文件

```
// 这个例子中使用gzip压缩格式，标准库还支持zlib, bz2, flate, lzw
package main

import (
    "compress/gzip"
    "log"
    "io"
    "os"
)

func main() {
    // 打开一个gzip文件。
    // 文件是一个reader,但是我们可以使用各种数据源，比如web服务器返回的gzipped内容，
    // 它的内容不是一个文件，而是一个内存流
    gzipFile, err := os.Open("test.txt.gz")
    if err != nil {
        log.Fatal(err)
    }

    gzipReader, err := gzip.NewReader(gzipFile)
    if err != nil {
        log.Fatal(err)
    }
    defer gzipReader.Close()

    // 解压缩到一个writer,它是一个file writer
    outfileWriter, err := os.Create("unzipped.txt")
    if err != nil {
        log.Fatal(err)
    }
    defer outfileWriter.Close()

    // 复制内容
    _, err = io.Copy(outfileWriter, gzipReader)
    if err != nil {
        log.Fatal(err)
    }
}
```

### 文件其它操作

#### 临时文件和目录

`ioutil`提供了两个函数: `TempDir()` 和 `TempFile()`。使用完毕后，调用者负责删除这些临时文件和文件夹。有一点好处就是当你传递一个空字符串作为文件夹名的时候，它会在操作系统的临时文件夹中创建这些项目（/tmp on Linux）。`os.TempDir()`返回当前操作系统的临时文件夹。

```
package main

import (
     "os"
     "io/ioutil"
     "log"
     "fmt"
)

func main() {
     // 在系统临时文件夹中创建一个临时文件夹
     tempDirPath, err := ioutil.TempDir("", "myTempDir")
     if err != nil {
          log.Fatal(err)
     }
     fmt.Println("Temp dir created:", tempDirPath)

     // 在临时文件夹中创建临时文件
     tempFile, err := ioutil.TempFile(tempDirPath, "myTempFile.txt")
     if err != nil {
          log.Fatal(err)
     }
     fmt.Println("Temp file created:", tempFile.Name())

     // ... 做一些操作 ...

     // 关闭文件
     err = tempFile.Close()
     if err != nil {
        log.Fatal(err)
    }

    // 删除我们创建的资源
     err = os.Remove(tempFile.Name())
     if err != nil {
        log.Fatal(err)
    }
     err = os.Remove(tempDirPath)
     if err != nil {
        log.Fatal(err)
    }
}
```

#### 通过HTTP下载文件

```
package main

import (
     "os"
     "io"
     "log"
     "net/http"
)

func main() {
     newFile, err := os.Create("devdungeon.html")
     if err != nil {
          log.Fatal(err)
     }
     defer newFile.Close()

     url := "http://www.devdungeon.com/archive"
     response, err := http.Get(url)
     defer response.Body.Close()

     // 将HTTP response Body中的内容写入到文件
     // Body满足reader接口，因此我们可以使用ioutil.Copy
     numBytesWritten, err := io.Copy(newFile, response.Body)
     if err != nil {
          log.Fatal(err)
     }
     log.Printf("Downloaded %d byte file.\n", numBytesWritten)
}
```

#### 哈希和摘要

```
package main

import (
    "crypto/md5"
    "crypto/sha1"
    "crypto/sha256"
    "crypto/sha512"
    "log"
    "fmt"
    "io/ioutil"
)

func main() {
    // 得到文件内容
    data, err := ioutil.ReadFile("test.txt")
    if err != nil {
        log.Fatal(err)
    }

    // 计算Hash
    fmt.Printf("Md5: %x\n\n", md5.Sum(data))
    fmt.Printf("Sha1: %x\n\n", sha1.Sum(data))
    fmt.Printf("Sha256: %x\n\n", sha256.Sum256(data))
    fmt.Printf("Sha512: %x\n\n", sha512.Sum512(data))
}
```

上面的例子复制整个文件内容到内存中，传递给hash函数。另一个方式是创建一个hash writer, 使用 `Write`、`WriteString`、`Copy`将数据传给它。下面的例子使用 md5 hash,但你可以使用其它的Writer。

```
package main

import (
    "crypto/md5"
    "log"
    "fmt"
    "io"
    "os"
)

func main() {
    file, err := os.Open("test.txt")
    if err != nil {
        log.Fatal(err)
    }
    defer file.Close()

    //创建一个新的hasher,满足writer接口
    hasher := md5.New()
    _, err = io.Copy(hasher, file)
    if err != nil {
        log.Fatal(err)
    }

    // 计算hash并打印结果。
    // 传递 nil 作为参数，因为我们不通参数传递数据，而是通过writer接口。
    sum := hasher.Sum(nil)
    fmt.Printf("Md5 checksum: %x\n", sum)
}
```
