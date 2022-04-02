## go mod

go buildin package manager.

go mod是go语言内置的包管理工具，集成在go tool中，安装好go就可以使用。

要求: go version >= 1.11

官方文档： [https://tip.golang.org/cmd/go...](https://link.segmentfault.com/?enc=CrfLuYQcY27dcgyer3H7Ug%3D%3D.W%2Fklx%2BxDRX1cMM1zudxNdSVfGsvz3xbxgDreLa0KgHnvzZbYZ9Itl4TpTjnDhuTYM0iqmJ0qCgRJfJGJ8%2BaB9njgP9uZWMtfqzmmeEmZDrY%3D)

### 环境变量

```
# 通过环境变量GOPROXY设置代理
export GOPROXY=https://goproxy.io

# go mod功能开关，默认是auto，在gopath中不启用
# 可设置为on强制启用
export GO111MODULE=on
```

### mod模式

go mod 模式，默认将依赖包下载到$GOROOT/src/pkg/mod目录下

并且，会按照最小版本满足(mvs)来拉去依赖。

### vendor 模式

vendor模式，依赖只从顶层的vendor目录中查找依赖。

但是go mod是不推荐使用vendor目录的，而是直接使用source或cache中的包。但是如果网络不好的时候，也可以使用vendor模式构建，然后在vendor目录下查找依赖

go mod 默认是mod模式，忽略vendor目录。通过flag `-mod=vendor`设置

**全局改变mod的默认方式**

全局的话也可以通过环境变量 `GOFLAGS=-mod=vendor`来设置flag。

**命令行改变**

> go build -mod =vendor -o xxx xxx.go
>
> go build -mod=mod -o xxx xxx.go

### go mod init

初始化

*update：init现在已经做了优化*
`go mod init <module-name>`

---

init报错outside gopath no import comments

```
# 方法一 手动创建go.mod文件， 写入module xxx
echo 'module xxx' > go.mod

# 方法二 main包加入import声明
package main // import "xxx"
```

### go mod download

下载依赖

### go mod tidy

同步依赖包，添加需要的，移除多余的

### go mod vendor

将依赖包放入vendor

### go mod verify

校验下载到mod cache的依赖包，是否被修改

### go mod graph

查看依赖图，就是把go.mod文件内容打印出来

### go mod why [package module]

解释为什么有这个依赖

### go get 下载/升级依赖

go mod不再下载源码进$GOPATH/src

go mod的下载目录在$GOPATH/pkg/mod，并且是文件权限是只读的 `-r--r--r--`

```
# tag必须以v开头 v1.2.3格式
go get -u xxx.com/pkg@2.1.0
```

### go mod edit

#### -replace

让原本依赖的 github.com/repo/pkg 包，实际使用 github.com/your-fork/pkg@v。

```
go mod edit -replace old[@v]=new[@v]

# 如果不是replace本地包，必须带上版本号
go mod edit -replace golang.org/x/crypto=github.com/golang/crypto@v0.0.0-20190621222207-cc06ce4a13d4
```

```
# go.mod
replace golang.org/x/crypto => github.com/golang/crypto v0.0.0-20190621222207-cc06ce4a13d4

replace golang.org/x/crypto v0.0.0-20190621222207-cc06ce4a13d4 => github.com/golang/crypto v0.0.0-20190621222207-cc06ce4a13d4
```

#### -module

改变go.mod 的文件路径

> go mod edit -module go_mod_path

#### -exclude

排除某个module

#### -go

-go=version 指定某一go语言版本

#### -require

指定依赖，覆盖原来的go.mod里的路径

### go.mod & go.sum

go.mod：依赖列表和版本约束。

go.sum：记录module文件hash值，用于安全校验。

### 最佳实践

* go mod不推荐使用vendor，不要将vendor提交到版本控制。
* CICD等场景下载vendor不方便时，使用vendor可能会更好。也可以考虑搭建nexus golang repo。

## go get

> 使用go module之后，go get 拉取依赖的方式就发生了变化

* 下载项目依赖

```text
go get ./...
```

* 拉取最新的版本(优先择取 tag)

```text
go get golang.org/x/text@latest
```

* 拉取 指定分支/master 分支的最新 commit

```text
go get golang.org/x/text@master
```

* 拉取 tag 为 v0.3.2 的 commit

```text
go get golang.org/x/text@v0.3.2
```

* 拉取 hash 为 342b231 的 commit，最终会被转换为 v0.3.2：

```text
go get golang.org/x/text@342b2e
```

* 指定版本拉取，拉取v3版本

```text
go get github.com/smartwalle/alipay/v3
```

* 更新

```text
go get -u
```

## go list

显示可以下载的版本

```text
go list -m -versions github.com/gogf/gf
```

## go clean

1. 清理moudle 缓存

```text
go clean -modcache
```
