## 下载和安装

### 1 下载

下载地址：[https://github.com/google/protobuf/releases](https://links.jianshu.com/go?to=https%3A%2F%2Fgithub.com%2Fgoogle%2Fprotobuf%2Freleases)，下拉找到最新版本的Assets

下载适合操作系统的压缩包：`protoc-3.20.0-linux-x86_64.zip`

### 2 解压

`unzip protoc-3.20.0-linux-x86_64.zip` 会生成三个文件

`bin`,`inclue`,`readme.txt`

### 3 添加环境变量

将bin目录添加到环境变量，或者移动到 `$GOPATH/bin目录下`

### 4 验证

> protoc --version

### 5 安装语言生成插件

> **go get -u github.com/golang/protobuf/protoc-gen-go**
>
> go get -u google.golang.org/grpc   //grpc包

确保protoc-gen-go也在环境目录下

## proto编译引用外部包问题

在 `test.proto`文件中引用了一个外部包:

<pre highlighted="true"><div data-tips="复制代码" class="esa-clipboard-button" data-clipboard-target="#copy_target_0">Copy </div><code class="hljs language-cpp" id="copy_target_0">import "google/api/annotations.proto";
</code></pre>

当使用命令编译的时候提示找不到包：

<pre highlighted="true"><div data-tips="复制代码" class="esa-clipboard-button" data-clipboard-target="#copy_target_1">Copy </div><code class="hljs language-cmake" id="copy_target_1"><table class="hljs-ln"><tbody><tr><td class="hljs-ln-line hljs-ln-numbers" data-line-number="1"><div class="hljs-ln-n" data-line-number="1"></div></td><td class="hljs-ln-line hljs-ln-code" data-line-number="1"># protoc --go_out=plugins=grpc:. ./test.proto</td></tr><tr><td class="hljs-ln-line hljs-ln-numbers" data-line-number="2"><div class="hljs-ln-n" data-line-number="2"></div></td><td class="hljs-ln-line hljs-ln-code" data-line-number="2">google/api/annotations.proto: File not found.</td></tr><tr><td class="hljs-ln-line hljs-ln-numbers" data-line-number="3"><div class="hljs-ln-n" data-line-number="3"></div></td><td class="hljs-ln-line hljs-ln-code" data-line-number="3">test.proto:5:1: Import "google/api/annotations.proto" was not found or had errors.</td></tr></tbody></table></code></pre>

解决：

去github上将对应的包下载下来放在 `$GOPATH/src`下，例如这里缺失 `google/api`。

去[gooogleapis](https://github.com/googleapis/googleapis/tree/master/google)将项目下载下来，并将整个项目放到 `$GOPATH/src`，此时的完整路径应该是:

<pre highlighted="true"><div data-tips="复制代码" class="esa-clipboard-button" data-clipboard-target="#copy_target_2">Copy </div><code class="hljs language-bash" id="copy_target_2">$GOPATH/src/google/api/annotations.proto
</code></pre>

这才完成了第一步，如果这时候你去直接执行protoc编译命令，依旧会得到上面的报错信息，protoc并没有成功的获取到外部proto文件。

为了解决问题，首先了解下protoc中import的两条规则：

1. import 不允许使用相对路径；
2. import 导入路径应该从根开始的绝对路径；

这个**根开始的绝对路径**指的是 `$GOPATH/src`开始的路径，这个需要先了解。

假设此时的目录结构为:

<pre highlighted="true"><div data-tips="复制代码" class="esa-clipboard-button" data-clipboard-target="#copy_target_3">Copy </div><code class="hljs language-lua" id="copy_target_3"><table class="hljs-ln"><tbody><tr><td class="hljs-ln-line hljs-ln-numbers" data-line-number="1"><div class="hljs-ln-n" data-line-number="1"></div></td><td class="hljs-ln-line hljs-ln-code" data-line-number="1">src</td></tr><tr><td class="hljs-ln-line hljs-ln-numbers" data-line-number="2"><div class="hljs-ln-n" data-line-number="2"></div></td><td class="hljs-ln-line hljs-ln-code" data-line-number="2">-- google</td></tr><tr><td class="hljs-ln-line hljs-ln-numbers" data-line-number="3"><div class="hljs-ln-n" data-line-number="3"></div></td><td class="hljs-ln-line hljs-ln-code" data-line-number="3">  -- api</td></tr><tr><td class="hljs-ln-line hljs-ln-numbers" data-line-number="4"><div class="hljs-ln-n" data-line-number="4"></div></td><td class="hljs-ln-line hljs-ln-code" data-line-number="4">  	-- annotations.proto</td></tr><tr><td class="hljs-ln-line hljs-ln-numbers" data-line-number="5"><div class="hljs-ln-n" data-line-number="5"></div></td><td class="hljs-ln-line hljs-ln-code" data-line-number="5">-- test</td></tr><tr><td class="hljs-ln-line hljs-ln-numbers" data-line-number="6"><div class="hljs-ln-n" data-line-number="6"></div></td><td class="hljs-ln-line hljs-ln-code" data-line-number="6">  -- test.proto</td></tr></tbody></table></code></pre>

`test.proto`中引用了 `google/api/annotations.proto`，此时我们命令的执行位置为：

<pre highlighted="true"><div data-tips="复制代码" class="esa-clipboard-button" data-clipboard-target="#copy_target_4">Copy </div><code class="hljs language-bash" id="copy_target_4">src/test
</code></pre>

执行的命令为：

<pre highlighted="true"><div data-tips="复制代码" class="esa-clipboard-button" data-clipboard-target="#copy_target_5">Copy </div><code class="hljs language-bash" id="copy_target_5">protoc --go_out=plugins=grpc:. ./test.proto
</code></pre>

protoc有一个参数 `-I`，表示引入文件的目录路径，这里有 **坑** 。

`-I`参数简单来说，就是如果多个proto文件之间有互相依赖，生成某个proto文件时，需要import其他几个proto文件，这时候就要用 `-I`来指定搜索目录。如果没有指定 `-I`参数，则在当前目录进行搜索。

例如这里的 `import "google/api/annotations.proto";`，这里的这个路径，其实是从 `$GOPATH/src`开始的路径。

也就是说，首先要用 `-I`参数将引入包的路径设置到 `$GOPATH/src`目录下，即

<pre highlighted="true"><div data-tips="复制代码" class="esa-clipboard-button" data-clipboard-target="#copy_target_6">Copy </div><code class="hljs language-css" id="copy_target_6">protoc -I ../
</code></pre>

完整命令:

<pre highlighted="true"><div data-tips="复制代码" class="esa-clipboard-button" data-clipboard-target="#copy_target_7">Copy </div><code class="hljs language-shell" id="copy_target_7"><table class="hljs-ln"><tbody><tr><td class="hljs-ln-line hljs-ln-numbers" data-line-number="1"><div class="hljs-ln-n" data-line-number="1"></div></td><td class="hljs-ln-line hljs-ln-code" data-line-number="1"># <span class="language-bash">pwd</span></td></tr><tr><td class="hljs-ln-line hljs-ln-numbers" data-line-number="2"><div class="hljs-ln-n" data-line-number="2"></div></td><td class="hljs-ln-line hljs-ln-code" data-line-number="2">.../src/test</td></tr><tr><td class="hljs-ln-line hljs-ln-numbers" data-line-number="3"><div class="hljs-ln-n" data-line-number="3"></div></td><td class="hljs-ln-line hljs-ln-code" data-line-number="3"># <span class="language-bash">protoc -I ../ -I ./ --go_out=plugins=grpc:. ./test.proto</span></td></tr></tbody></table></code></pre>

每个 `-I`参数都引入一个目录，proto文件中引入了几个外部proto文件理论来说就需要多少个 `-I`（同一目录的可以一次性引入），再加上待编译的proto也需要引入，所以上面这里就用了两个 `-I`来引入目录文件。

推荐使用 `$GOPATH/src`的方式来引入，简单直观不容易出错：

<pre highlighted="true"><div data-tips="复制代码" class="esa-clipboard-button" data-clipboard-target="#copy_target_8">Copy </div><code class="language-bash hljs" id="copy_target_8"><table class="hljs-ln"><tbody><tr><td class="hljs-ln-line hljs-ln-numbers" data-line-number="1"><div class="hljs-ln-n" data-line-number="1"></div></td><td class="hljs-ln-line hljs-ln-code" data-line-number="1">protoc -I ./ \</td></tr><tr><td class="hljs-ln-line hljs-ln-numbers" data-line-number="2"><div class="hljs-ln-n" data-line-number="2"></div></td><td class="hljs-ln-line hljs-ln-code" data-line-number="2">	-I $GOPATH/src \</td></tr><tr><td class="hljs-ln-line hljs-ln-numbers" data-line-number="3"><div class="hljs-ln-n" data-line-number="3"></div></td><td class="hljs-ln-line hljs-ln-code" data-line-number="3">	-I $GOPATH/src/google/api \</td></tr><tr><td class="hljs-ln-line hljs-ln-numbers" data-line-number="4"><div class="hljs-ln-n" data-line-number="4"></div></td><td class="hljs-ln-line hljs-ln-code" data-line-number="4">	--go_out=plugins=grpc:. ./xxx.proto</td></tr></tbody></table></code></pre>

### google-protobuf

git clone git@github.com:protocolbuffers/protobuf.git

### grpc-gatway

https://github.com/grpc-ecosystem/grpc-gateway

### googleapis

https://github.com/googleapis/googleapis

protoc参数解释


## protoc 参数含义

```
$protoc --proto_path=./proto \
	--proto_path=$GOPATH/src/github.com/protobuf/src/google/protobuf/
   --go_out=./api --go_opt=paths=source_relative \
  --go-grpc_out=./api --go-grpc_opt=paths=source_relative \
  --grpc-gateway_out=./api --grpc-gateway_opt=paths=source_relative \
  ./proto/helloworld/hello_world.proto
```

### --proto_path or -I

其中 `--proto_path=./proto`用于指定 直接编译的proto文件目录和import 文件路径（默认为{$pwd}），即前面引入的 `google/api/annotations.proto`文件的位置。

如果用 `-I`,也是可以的只是不需要=

> protoc -I  .                                           // 包含当前目录
>     -I $GOPATH/src                               //  其他目录
>     -I $GOPATH/src/google/api \

### --go_out

语言插件，即proto_gen_go，指定生成的文件 `xxx.pb.go` 输出目录

### --go-grpc_out

用于指定生成的文件 `xxx_grpc.pb.go` 输出目录

### --grpc-gateway_out

用于指定生成的文件 `xxx.pb.gw.go` 输出目录

### --go_opt

这儿的可选性也可以不用，也可以直接接在插件语言后 比如 --go_out=plugins=xx,paths=xx。但为了层次分明，建议如此

用于指定可选项，有两个选择 plugins和paths,参数之间使用 `逗号,`隔开，然后使用 `冒号:结尾`

例如：`--go_opt=plugins=grpc,paths=import:.` 。 

#### plugins

`plugins`参数有不带grpc和带grpc两种（应该还有其它的，目前知道的有这两种），两者的区别如下，带grpc的会多一些跟gRPC相关的代码，实现gRPC通信。

#### paths

paths 参数有两个选项，`import` 和 `source_relative` 。建议使用`paths=source_relative`

默认为 `import` ，将生成的代码放到proto文件中指定的go_package目录下

 `source_relative` 如果没有指定输出目录，将生成的代码放到proto文件相同的目录下，如果目录已存在则不用创建 。

#### 安装语言插件

```
go get -u github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-grpc-gateway
go get -u github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-openapiv2
go get -u google.golang.org/protobuf/cmd/protoc-gen-go
go get -u google.golang.org/grpc/cmd/protoc-gen-go-grpc
```

然后 `$GOBIN`下出现以下可执行文件，$GOBIN=GOPATN/bin$

* `protoc-gen-grpc-gateway`
* `protoc-gen-openapiv2`
* `protoc-gen-go`
* `protoc-gen-go-grpc`
