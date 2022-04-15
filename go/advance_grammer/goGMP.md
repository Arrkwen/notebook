参考：

介绍 GMP 的文章有很多了，大家应该也粗浅的知道什么G（goroutine）M（Machine）P（Processsor）。相较于 Java 这样的编程语言，我们经常听到一个线程池的概念。线程池就是提前创建若干个线程，如果有任务需要处理，线程池里的线程就会处理任务，处理完之后线程并不会被销毁，而是等待下一个任务。由于创建和销毁线程都是消耗系统资源的，所以当你想要频繁的创建和销毁线程的时候就可以考虑使用线程池来提升系统的性能。

GMP 的出现可以类比Java中的线程池，当然也有像 [ants](http://github.com/panjf2000/ants) 这样的协程池实现，但是本质上 Golang GMP 就是在很好的完成线程池的角色任务。

## GMP 模型简介

G-M-P分别代表：

* G - Goroutine，Go协程，是参与调度与执行的最小单位
* M - Machine，指的是系统级线程
* P - Processor，指的是逻辑处理器，P关联了的本地可运行G的队列(也称为LRQ)，最多可存放256个G。

GMP调度流程大致如下：

1. 线程M想运行任务就需得获取 P，即与P关联。
2. 然从 P 的本地队列(LRQ)获取 G
3. 若LRQ中没有可运行的G，M 会尝试从全局队列(GRQ)拿一批G放到P的本地队列，
4. 若全局队列也未找到可运行的G时候，M会随机从其他 P 的本地队列偷一半放到自己 P 的本地队列。
5. 拿到可运行的G之后，M 运行 G，G 执行之后，M 会从 P 获取下一个 G，不断重复下去。

![https://img1.kiosk007.top/static/images/go/gc/golang_gmp.png](https://img1.kiosk007.top/static/images/go/gc/golang_gmp.png "https://img1.kiosk007.top/static/images/go/gc/golang_gmp.png")

* **全局队列（Global Queue）** ：存放等待运行的 Goroutine。
* **Goroutine** 在创建后，优先放进本地队列中，本地队列满了之后（本地队列一般大小256），则会把本地队列中一半的G放入全局队列中。
* **Processer** 是可以指定个数，一般可以在程序中使用 `runtime.GOMAXPROCS()` 来设置。
* **Machine(Thread)** 线程想运行任务就得获取P，从P的本地队列获取G，P队列为空的时，M也会尝试从全局队列中获取一批G放入到P的本地队列中，或者从其他的P本地队列中偷一半放入到自己的P的本地队列中。在Go语言本身限制最大是 10000个，可以再 runtime/debug 包中使用 `SetMaxThreads()` 函数来设置。有一个M阻塞会创建一个新的M

> M 与 P 的关系？

**M** 与 **P** 的数量没有绝对关系，一个 **M** 阻塞，**P** 就会去创建或者切换另一个  **M** ，所以，即使 **P** 的默认数量是 1，也有可能会创建很多个 **M** 出来。

> M 与 P 何时被创建？

**P** 在运行时系统会根据事先设定的数量创建

**M** 在没有足够的 **M** 开关联 **P** 并运行其中可运行的**G**时，比如所有的**M** 都发生了阻塞，而 **P** 中还有很多就绪任务，就会寻找空闲的 **M** ，没有空闲的**M**就会创建新的 **M**

> G 与 M 的关系

在 GMP 模型中，经常有听到 `N:1` 、`N:M`、`1:1` 的说法

* **N:1** : N 个协程绑定 1个线程，优点是协程在用户态线程内完成切换，不会陷入到内核态，切换快速。缺点是用不了硬件的多核加速，另外一旦某一个协程阻塞，会导致线程阻塞，其他协程都无法执行。
* **1:1** 即一个协程绑定一个线程，缺点比较明显。协程的创建、删除和切换都由CPU完成，过于昂贵。
* **M:N** : M个协程绑定N个线程，是 `N:1` 和 `1:1` 类型的结合。这对协程调度器要求高，效率越高。

### 调度器的设计策略

* **复用线程** ：避免频繁的创建、销毁线程，尽量复用。

1）work stealing 机制

当本线程无可运行的G时，尝试从其他的线程绑定的P偷取G，而不是销毁线程。

2）hand off 机制

当本线程因为G进行系统调用阻塞时，线程释放绑定的P， **把P转移给其他空闲的线程去执行** ，阻塞的协程会留在阻塞的线程之上。阻塞的协程退出阻塞状态后，会重新加入P本地队列。

* **利用并行** ：通过 GOMAXPROCS 限定P的个数，可以充分利用CPU。
* **抢占式** ：在 coroutine 中要等待一个协程主动让出 CPU 才执行下一个协程，在 Go （高版本）中，一个 goroutine 最多占用 CPU 10ms，防止其他 goroutine 被饿死，这就是 goroutine 不同于 coroutine 的一个地方。
* **全局G队列** ：在新的调度器中依然有全局G队列，当M执行 work stealing 从其他P偷不到G时，他可以从全局G队列中获取G

## 调度器生命周期

要想理解调度器的生命周期，必须得知道 `M0` 和 `G0`这两个概念。

* **M0**

M0 是启动程序后的编号为0的主线程，这个M对应的实例会在全局变量 `runtime.m0`中，M0 负责执行初始化操作和启动第一个G，在之后的M0就和其他的 M 一样了。

* **G0**

G0 是每次启动一个 M 都会创建的第一个 goroutine， G0 仅用于负责调度的G，G0 不指向任何可执行的函数，每个M都会有一个 G0.在调度或系统调用时都会使用G0 的栈空间，全局变量的 G0 是 M0 的 G0 。

**可视化 GMP 过程**

```go
func main() {
	//创建trace文件
	f, err := os.Create("trace.out")
	if err != nil {
		panic(err)
	}

	defer f.Close()

	//启动trace goroutine
	err = trace.Start(f)
	if err != nil {
		panic(err)
	}
	defer trace.Stop()

	//main
	fmt.Println("Hello World")
}

```

运行程序

```bash
$ go run main.go
Hello World
```

|运行结束之后，得到一个 `trace.out` 文件，然后用工具打开

```bash
$ go tool trace trace.out                      
2022/03/27 21:51:23 Parsing trace...
2022/03/27 21:51:23 Splitting trace...
2022/03/27 21:51:23 Opening browser. Trace viewer is listening on http://127.0.0.1:61794
```

![https://img1.kiosk007.top/static/images/go/gc/golang_gmp_trace.jpg](https://img1.kiosk007.top/static/images/go/gc/golang_gmp_trace.jpg "https://img1.kiosk007.top/static/images/go/gc/golang_gmp_trace.jpg")通过浏览器打开 `http://127.0.0.1:61794` 网址，点击 `view trace` 。

点击 Goroutine 可视化的数据条，可以看到一些详细的信息。一共有两个G在运行，一个是特殊的G0，是每个M必须有的一个初始化的G，还有一个G1 是 main goroutine 在一段时间内处于可运行和运行的状态。

## GMP 具体场景

* **场景一：创建G**

一个协程内创建另一个协程，新协程优先在原本协程的本地队列中（局部性）

* **场景二：G执行完毕**

协程G1运行完成后（函数 `goexit`），M上运行的 goroutine 切换 G0 ，G0 负责调度协程的切换（函数：`schedule`）。从P的本地队列取 G2 ，从G0 切换到 G2，并开始运行 G2 协程（函数：`execute`）。实现了线程 `M1` 的复用。

* **场景三：连续创建多个G导致本地队列满**

当一个 Goroutine 中创建了大量的 G 时，会将本地的队列 P 打满，这时需要执行负载均衡策略，会将当前 P1 中的本地队列里的G顺序打乱，并将其P中当前一半的G，还有新创建的G转移到全局队列。

* **场景四：唤醒正在休眠的M**

在创建 G 时，运行的 G 会尝试唤醒其他空闲的 P 和 M 组合去执行。假定 G2 唤醒了 M2，M2 绑定了 P2，并运行 G0，但 P2 本地队列没有 G，M2 此时为 **自旋线程** （没有 G 但为运行状态的线程，不断寻找 G）。

* **场景五：被唤醒的M从全局获取G**

![https://img1.kiosk007.top/static/images/go/gc/golang_gmp_dispatch.jpg](https://img1.kiosk007.top/static/images/go/gc/golang_gmp_dispatch.jpg "https://img1.kiosk007.top/static/images/go/gc/golang_gmp_dispatch.jpg")

M2 尝试从全局队列 取一批 G 放到 P2 的本地队列（函数：`findrunnable()`）。M2 从全局队列取的 G 数量符合下面的公式：

```bash
n = min(len(GQ)/GOMAXPROCS + 1, len(GQ/2))
```

假定我们场景中一共有 4 个 P（GOMAXPROCS 设置为 4，那么我们允许最多就能用 4 个 P 来供 M 使用）。所以 M2 只从能从全局队列取 1 个 G3 移动 P2 本地队列，然后完成从 G0 到 G3 的切换，运行 G3。此时这个线程退出自旋状态。

假设 G2 一直在 M1 上运行，经过 2 轮后，M2 已经把 G7、G4 G9 从全局队列获取到了 P2 的本地队列并完成运行，全局队列和 P2 的本地队列都空了。此时全局队列中没有G，那么M2就需要开始 working stealing （偷取），从其他有G的P拿一半G过来，放到自己的P本地队列里。

* **场景七: 自旋线程的最大限制**

假设 M1 和 M2 都在正常运行 G，M3 和 M4 没有goroutine 可以运行，那么 M3 和 M4 处于  **自旋状态** ，他们会不断的寻找 goroutine。

为什么要让 m3 和 m4 自旋，自旋本质是在运行，线程在运行却没有执行 G，就变成了浪费 CPU. 为什么不销毁现场，来节约 CPU 资源。因为创建和销毁 CPU 也会浪费时间，我们希望当有新 goroutine 创建时，立刻能有 M 运行它，如果销毁再新建就增加了时延，降低了效率。当然也考虑了过多的自旋线程是浪费 CPU，所以系统中最多有 GOMAXPROCS 个自旋的线程，多余的没事做线程会让他们休眠。

* **场景八：G发生阻塞系统调用**

假设在 `N:M` 模型中，假设 M3 处于自旋，还有休眠队列中的 M4 。此时 M1 上的 G4 创建一个 G5 并且 G4 进行了 **阻塞的系统调用** ，M1和P1 立即解绑，如果P1 上有空闲的P列表，P1会立刻唤醒一个M和他绑定。否则P1会加入到空闲的P列表，等待M来获取可用的P。

* **场景九：G发生非阻塞系统调用**

上述场景，假设 G4 创建 G5 进行的是 **非阻塞系统的调用** ，此时的M1和P1解绑，但是M1会记住P1，然后G4进入系统调用的状态，当G4 和 M1 退出系统调用时，会尝试获取P1，如果无法获取，则获取空闲的P，如果依然没有，则4 会被标记为可运行状态，加入到全局队列。M1会因为没有P的绑定变为可休眠状态。

参考：

* [Golang 调度器 GMP 原理与调度全分析](https://learnku.com/articles/41728)

## GODEBUG

得益于 Go 语言优秀的运行时调度系统，即使开发人员没有多线程编程经验，也能很容易地开发并发程序。

调度系统，其中最核心的就是 GMP 的设计，欲深入理解 Go 语言设计的读者都应该看过这些知识。但是，在通过相关博客或者源码学习时，如果不能和实际的代码进行结合，在理解上或许不够深刻。

本文介绍一种方式，即使用 GODEBUG 工具，通过实际运行代码来直观地查看 Go 运行时的调度过程。

## 调度简述

首先，我们先通过程序某时刻的调度快照示意图，通过解析快照状态来简单回顾一下 Go 调度系统。

![图片](https://mmbiz.qpic.cn/mmbiz_png/2EiaKLQksVQL7dru7myziamDqNW6nMq4t4sZB2pPniaan2Kecs9EKmF6NwBUJD5rqCxKB5O2aPEMpZnuPfibO7I2Nw/640?wx_fmt=png&wxfrom=5&wx_lazy=1&wx_co=1)

如上图所示，我们设定了 GOMAXPROCS=2，即 2 个处理器。

当前时刻， P0 和 P1 上正分别挂载着 OS 线程 M1 与 M4，其上分别执行着 G8 和 G17 的代码。P0 的 LRQ（Local Run Queue，本地运行队列）有 3 个 G 在排队等待，而 P1 的 LRQ 已无等待的 G；GRQ （Global Run Queue，全局运行队列）中有 5 个 G 。

网络轮询器 Net Poller 上有一个陷入异步网络调用的 G9；M2 由于 G11 的某种同步系统调用而阻塞；M3 处于空闲状态，时刻准备着当 M1 或 M4 被阻塞时而派上用场。

由于 P1 的 LRQ 已无等待的 G，当 G17 被调度时，它将进行 Wrok Stealing （任务窃取），其窃取源来自于其他处理器 P 的 LRQ（这里是 P1 的 LRQ）、GRQ 和 Net Poller，具体规则见 `<span>runtime.schedule()</span>`函数。

## GODEBUG 工具

启用 GODEBUG 工具非常简单，只需要设置环境变量 GODEBUG 即可。它可以让 Go 程序在运行过程中输出调试信息，能够根据参数配置直观地看到调度器或垃圾回收等详细信息。

GODEBUG 的详细描述介绍可见源码 `<span>runtime/extern.go</span>`文件。

本文我们关心的调试内容是调度器，因此我们只使用 GODEBUG 的两个参数 schedtrace 与 scheddetail。

* schedtrace=n：设置运行时在每 n 毫秒输出一行调度器的概要信息。
* scheddetail: 输出更详细的调度信息。

##### 示例代码

我们使用的示例代码如下

```
package main

import (
 "sync"
)

var wg sync.WaitGroup

func main() {
 for i := 0; i < 20; i++ {
  wg.Add(1)
  go work(&wg)
 }
 wg.Wait()
}

func work(wg *sync.WaitGroup) {
 var counter int
 for i := 0; i < 1e10; i++ {
  counter++
 }
 wg.Done()
}
```

代码比较简单，我们启动 20 个 CPU 密集型的 G 任务，它们受到 WaitGroup 的限制。当所有计算任务的 G 完成了各自的累加工作，程序才会结束执行。

##### schedtrace 调度概要输出

下面，我们设定 GODEBUG=schedtrace=1000，这意味着 1s 输出一次程序的调度概要情况。

```
 $ go build -o demo main.go
 $ GOMAXPROCS=4 GODEBUG=schedtrace=1000 ./demo
SCHED 0ms: gomaxprocs=4 idleprocs=3 threads=2 spinningthreads=0 idlethreads=0 runqueue=0 [0 0 0 0]
SCHED 1003ms: gomaxprocs=4 idleprocs=0 threads=5 spinningthreads=0 idlethreads=0 runqueue=14 [1 0 1 0]
SCHED 2012ms: gomaxprocs=4 idleprocs=0 threads=5 spinningthreads=0 idlethreads=0 runqueue=10 [2 1 2 1]
SCHED 3018ms: gomaxprocs=4 idleprocs=0 threads=5 spinningthreads=0 idlethreads=0 runqueue=12 [0 0 0 4]
SCHED 4029ms: gomaxprocs=4 idleprocs=0 threads=5 spinningthreads=0 idlethreads=0 runqueue=15 [0 0 1 0]
SCHED 5031ms: gomaxprocs=4 idleprocs=0 threads=5 spinningthreads=0 idlethreads=0 runqueue=9 [1 2 2 2]
SCHED 6035ms: gomaxprocs=4 idleprocs=0 threads=5 spinningthreads=0 idlethreads=0 runqueue=15 [0 1 0 0]
SCHED 7044ms: gomaxprocs=4 idleprocs=0 threads=5 spinningthreads=0 idlethreads=0 runqueue=8 [1 2 3 2]
SCHED 8054ms: gomaxprocs=4 idleprocs=0 threads=5 spinningthreads=0 idlethreads=0 runqueue=12 [0 0 4 0]
SCHED 9055ms: gomaxprocs=4 idleprocs=0 threads=5 spinningthreads=0 idlethreads=0 runqueue=6 [3 2 3 2]
SCHED 10063ms: gomaxprocs=4 idleprocs=0 threads=5 spinningthreads=0 idlethreads=0 runqueue=11 [1 2 1 1]
SCHED 11072ms: gomaxprocs=4 idleprocs=0 threads=5 spinningthreads=0 idlethreads=0 runqueue=6 [3 2 3 2]
...
```

其中，

* SCHED：代表程序启动到输出当前行时的运行时间，这个输出间隔受到 schedtrace 值影响。
* gomaxprocs：GOMAXPROCS 值，这里我们设定了其为 4。
* idleprocs：空闲的 P 数量。
* threads：运行时管理的线程数。
* spinningthreads：自旋线程，处于”自旋“状态的线程数（避免频繁的线程创建与销毁）。
* idlethreads：空闲线程数。
* runqueue：全局队列 GRQ 中的 G 数量。
* [2 1 2 1]：代表 4 个 P 的本地队列 LRQ 中 G 数量分别是 2、1、2、1 。

##### scheddetail 调度详细输出

当我们想要查看更详细的调度信息时，需要增加 scheddetail 参数。

```
$ GOMAXPROCS=4 GODEBUG=schedtrace=1000,scheddetail=1 ./demo
SCHED 0ms: gomaxprocs=4 idleprocs=2 threads=3 spinningthreads=1 idlethreads=0 runqueue=0 gcwaiting=0 nmidlelocked=0 stopwait=0 sysmonwait=0
  P0: status=1 schedtick=0 syscalltick=0 m=0 runqsize=0 gfreecnt=0 timerslen=0
  P1: status=1 schedtick=0 syscalltick=0 m=2 runqsize=0 gfreecnt=0 timerslen=0
  P2: status=0 schedtick=0 syscalltick=0 m=-1 runqsize=0 gfreecnt=0 timerslen=0
  P3: status=0 schedtick=0 syscalltick=0 m=-1 runqsize=0 gfreecnt=0 timerslen=0
  M2: p=1 curg=-1 mallocing=0 throwing=0 preemptoff= locks=2 dying=0 spinning=false blocked=false lockedg=-1
  M1: p=-1 curg=-1 mallocing=0 throwing=0 preemptoff= locks=2 dying=0 spinning=false blocked=false lockedg=-1
  M0: p=0 curg=-1 mallocing=0 throwing=0 preemptoff= locks=1 dying=0 spinning=false blocked=false lockedg=1
  G1: status=1() m=-1 lockedm=0
  G2: status=1() m=-1 lockedm=-1
  G3: status=1() m=-1 lockedm=-1
SCHED 1000ms: gomaxprocs=4 idleprocs=0 threads=5 spinningthreads=0 idlethreads=0 runqueue=15 gcwaiting=0 nmidlelocked=0 stopwait=0 sysmonwait=0
  P0: status=1 schedtick=45 syscalltick=0 m=2 runqsize=0 gfreecnt=0 timerslen=0
  P1: status=1 schedtick=46 syscalltick=0 m=3 runqsize=0 gfreecnt=0 timerslen=0
  P2: status=1 schedtick=45 syscalltick=0 m=4 runqsize=1 gfreecnt=0 timerslen=0
  P3: status=1 schedtick=45 syscalltick=0 m=0 runqsize=0 gfreecnt=0 timerslen=0
  M4: p=2 curg=-1 mallocing=0 throwing=0 preemptoff= locks=1 dying=0 spinning=false blocked=false lockedg=-1
  M3: p=1 curg=-1 mallocing=0 throwing=0 preemptoff= locks=1 dying=0 spinning=false blocked=false lockedg=-1
  M2: p=0 curg=40 mallocing=0 throwing=0 preemptoff= locks=0 dying=0 spinning=false blocked=false lockedg=-1
  M1: p=-1 curg=-1 mallocing=0 throwing=0 preemptoff= locks=2 dying=0 spinning=false blocked=false lockedg=-1
  M0: p=3 curg=-1 mallocing=0 throwing=0 preemptoff= locks=1 dying=0 spinning=false blocked=false lockedg=-1
  G1: status=4(semacquire) m=-1 lockedm=-1
  G2: status=4(force gc (idle)) m=-1 lockedm=-1
  G3: status=4(GC sweep wait) m=-1 lockedm=-1
  G17: status=4(GC scavenge wait) m=-1 lockedm=-1
  G33: status=1() m=-1 lockedm=-1
  G34: status=1() m=-1 lockedm=-1
  G35: status=1() m=-1 lockedm=-1
  G36: status=1() m=-1 lockedm=-1
  G37: status=1() m=-1 lockedm=-1
  G38: status=1() m=-1 lockedm=-1
  G39: status=1() m=-1 lockedm=-1
  G40: status=2() m=2 lockedm=-1
  G41: status=1() m=-1 lockedm=-1
  G42: status=1() m=-1 lockedm=-1
  G43: status=1() m=-1 lockedm=-1
  G44: status=1() m=-1 lockedm=-1
  G45: status=1() m=-1 lockedm=-1
  G46: status=1() m=-1 lockedm=-1
  G47: status=1() m=-1 lockedm=-1
  G48: status=1() m=-1 lockedm=-1
  G49: status=1() m=-1 lockedm=-1
  G50: status=1() m=-1 lockedm=-1
  G51: status=1() m=-1 lockedm=-1
  G52: status=1() m=-1 lockedm=-1
...
```

当增加了 scheddetail 参数后，其输出信息不仅包含了 SCHED 的一行概览信息，还增加了 GPM 三个实体状况的详细描述。

###### P

* status：P 的运行状态，其详细分类与描述可查看源码 `<span>runtime/runtime2.go</span>` 的代码。

![图片](https://mmbiz.qpic.cn/mmbiz_png/2EiaKLQksVQL7dru7myziamDqNW6nMq4t4dXqSzoAia9SqL5mtiakzbxvpycB4yyRqKsXiaJQM2P0r1Iibia2UDnaltNw/640?wx_fmt=png&wxfrom=5&wx_lazy=1&wx_co=1)

* schedtick：随着每次调度行为累加，代表 P 的调度次数。
* syscalltick：随着每次系统调用行为累加，代表 P 的系统调用次数。
* m: 绑定的 M 编号，例如在 SCHED 1000ms 时，P0 的 m=2，而 M2 的 p=0。
* runqsize：LRQ 的 G 数量。
* gfreecnt：状态为 Gdead 的数量，即 status = 6。
* timerslen：timer 的数量。

###### M

* p：绑定的 P 编号。
* curg：当前正在 M 上执行代码的 G 编号。
* mallocing：是否正存在分配内存操作。
* throwing：是否有抛出异常。
* preemptoff：如果 preemptoff != ""，则保持 curg 在这个 M 上运行。
* locks：M 的 locks 数量。
* dying：M 的 dying 值，其存在 0、1、2 和其他值四种处理情况。
* spinning：是否处于自选状态。
* blocked：是否处于阻塞状态。
* lockedg：与 G 的 lockedm 相对应，它们的类型是 uintptr，记录不被垃圾收集器跟踪的 M 与绕过写屏障的 G。

###### G

* status: 同 P 的状态类似，其详细分类与描述同样可查看源码 `<span>runtime/runtime2.go</span>` 的代码；if status==Gwaiting ，即 status 的值为 4 时，其括号内还会输出具体的等待原因。
* m：绑定的 M 编号，如果其值为 -1，代表无绑定。
* lockedm：与 M 中的 lockedg 对应。

##### 可视化调度快照

明白了上述各项指标的含义之后。为了绘图简单，我们将 GOMAXPROCS 设定为2，并选取第 1 秒的输出内容进行可视化分析。

```
$ GOMAXPROCS=2 GODEBUG=schedtrace=1000,scheddetail=1 ./demo
...
SCHED 1004ms: gomaxprocs=2 idleprocs=0 threads=4 spinningthreads=0 idlethreads=1 runqueue=10 gcwaiting=0 nmidlelocked=0 stopwait=0 sysmonwait=0
  P0: status=1 schedtick=45 syscalltick=0 m=3 runqsize=4 gfreecnt=0 timerslen=0
  P1: status=1 schedtick=48 syscalltick=0 m=0 runqsize=4 gfreecnt=0 timerslen=0
  M3: p=0 curg=24 mallocing=0 throwing=0 preemptoff= locks=0 dying=0 spinning=false blocked=false lockedg=-1
  M2: p=-1 curg=-1 mallocing=0 throwing=0 preemptoff= locks=0 dying=0 spinning=false blocked=true lockedg=-1
  M1: p=-1 curg=-1 mallocing=0 throwing=0 preemptoff= locks=2 dying=0 spinning=false blocked=false lockedg=-1
  M0: p=1 curg=34 mallocing=0 throwing=0 preemptoff= locks=0 dying=0 spinning=false blocked=false lockedg=-1
  G1: status=4(semacquire) m=-1 lockedm=-1
  G2: status=4(force gc (idle)) m=-1 lockedm=-1
  G3: status=4(GC sweep wait) m=-1 lockedm=-1
  G4: status=4(GC scavenge wait) m=-1 lockedm=-1
  G17: status=1() m=-1 lockedm=-1
  G18: status=1() m=-1 lockedm=-1
  G19: status=1() m=-1 lockedm=-1
  G20: status=1() m=-1 lockedm=-1
  G21: status=1() m=-1 lockedm=-1
  G22: status=1() m=-1 lockedm=-1
  G23: status=1() m=-1 lockedm=-1
  G24: status=2() m=3 lockedm=-1
  G25: status=1() m=-1 lockedm=-1
  G26: status=1() m=-1 lockedm=-1
  G27: status=1() m=-1 lockedm=-1
  G28: status=1() m=-1 lockedm=-1
  G29: status=1() m=-1 lockedm=-1
  G30: status=1() m=-1 lockedm=-1
  G31: status=1() m=-1 lockedm=-1
  G32: status=1() m=-1 lockedm=-1
  G33: status=1() m=-1 lockedm=-1
  G34: status=2() m=0 lockedm=-1
  G35: status=1() m=-1 lockedm=-1
  G36: status=1() m=-1 lockedm=-1
...
```

该时刻的调度情况快照图示如下

![图片](https://mmbiz.qpic.cn/mmbiz_png/2EiaKLQksVQL7dru7myziamDqNW6nMq4t4lOFgoBV6VPwlflqTEe6BzX2na98e9TzWCPjdbg35NbsN3DlcpHZ2lA/640?wx_fmt=png&wxfrom=5&wx_lazy=1&wx_co=1)

我们可以根据详细信息获取到 P、M、G 的具体运行情况。但需要注意的是，有一点我们不能确定，就是各个 P 的 LRQ 与 GRQ 是哪些具体的 G 在队列中等待，但这并不妨碍大局（因此，上图中的 LRQ 和 GRQ 可能并不是实际的 G 编号）。

## 总结

本文介绍了通过增加环境变量 GODEBUG ，我们可以在不做任何代码改变或增加额外的插件情况下，方便地查看 Go 程序的调度情况。

读者若想更直观地理解 Go 语言的 GMP 和调度系统，不妨一试 。

[参考文章](https://mp.weixin.qq.com/s/dVKMLaDaY65cu7qZsn1g_w)
