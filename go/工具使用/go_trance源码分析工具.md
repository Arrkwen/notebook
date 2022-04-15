# 源码分析工具functrance的使用

作用： 输出函数调用链条，如下格式：

## 1 安装

`go install github.com/bigwhite/functrace/cmd/gen@latest`

## 2 安装测试

```
$ gen -h
[gen -h]
gen [-w] xxx.go
  -w	write result to (source) file instead of stdout
```

## 3 源码分析

### 1 单文件源代码 `testGmp.go`

```go
/*
 * @Descripttion:
 * @version:
 * @Author: xiaokun
 * @Date: 2022-04-13 20:20:51
 * @LastEditors: xiaokun
 * @LastEditTime: 2022-04-13 20:23:04
 */

package main

import (
	"sync"
)

var wg sync.WaitGroup

func main() {
	for i := 0; i < 2; i++ {
		wg.Add(1)
		go work(&wg)
	}
	wg.Wait()
}

func work(wg *sync.WaitGroup) {
	cnt := 0
	Add(cnt)
	wg.Done()
}

func Add(n int) {
	for i := 0; i < 1e10; i++ {
		n++
	}
}



```



### 2插入functrace

`gen -w testGmp.go`

会在每一个函数之前增加 `defer functrace.Trace()()`

### 3下载functrace

`go get github.com/bigwhite/functrace`

### 4 编译源代码

`go build -o main -tags trace testGmp.go`

### 5执行可执行程序main

./main 输出如下

```
g[01]:  ->main.main
g[07]:  ->main.work
g[07]:          ->main.Add
g[06]:  ->main.work
g[06]:          ->main.Add
g[06]:          <-main.Add
g[06]:  <-main.work
g[07]:          <-main.Add
g[07]:  <-main.work
g[01]:  <-main.main
```


### 6 批量增加修改文件

1 下载代码

`git@github.com:bigwhite/functrace.git`

2 将functrace/scripts/batch_add_trace.sh 拷贝到上面gnet目录下并执行下面命令：

`bash batch_add_trace.sh`


## 可视化Go代码调用关系--go-callvis

[更多参考](https://github.com/ofabry/go-callvis)

### 1 安装

`go get -u github.com/ofabry/go-callvis`

### 2 使用

go-callvis `<target package>`

### 3 查看

HTTP server is listening on [http://localhost:7878/](http://localhost:7878/) by default, use option `-http="ADDR:PORT"` to change HTTP server address.
