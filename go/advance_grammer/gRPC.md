# GRPC的实现

[代码仓库](github.com/Arrkwen/Go/userInfo)

## 1 定义pb文件

```protobuf
syntax="proto3";

import "google/api/annotations.proto";                      // 包含google api 支持http调用
import "google/protobuf/timestamp.proto";                   // 
import "protoc-gen-openapiv2/options/annotations.proto";

option go_package="github.com/Arrkwen/userInfo/api";

package xpixel.userInfo;


option (grpc.gateway.protoc_gen_openapiv2.options.openapiv2_swagger) = {
  info: {
    title: "xpixel-userInfo-service"
    version: "v0.1.0"
  }
};

message User{
    string userId = 1;
    string userImage=2;
    string userPhone=3;
    string userPassword=4;
    int32 userType=5;
    google.protobuf.Timestamp register_at=6;
    string userSchool=7;
    string userResearch=8;
    string userGithub=9;
    string userGoogle=10;
}

message SaveUserInfoRequest{
    User user=1;
}

message SaveUserInfoResponse{
    bool isSuccess = 1;
}

service UserService{
    rpc SaveUserInfo(SaveUserInfoRequest) returns (SaveUserInfoResponse){
        option (google.api.http) = {
			post: "/user"
		  	body: "*"
		};
    }
}
```

## 2 安装插件

### 1 下载protoc语言插件

```
go get -u github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-grpc-gateway
go get -u github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-openapiv2
go get -u google.golang.org/protobuf/cmd/protoc-gen-go
go get -u google.golang.org/grpc/cmd/protoc-gen-go-grpc
```

或者

```

go install \
    github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-grpc-gateway \
    github.com/grpc-ecosystem/grpc-gateway/v2/protoc-gen-openapiv2 \
    google.golang.org/protobuf/cmd/protoc-gen-go \
    google.golang.org/grpc/cmd/protoc-gen-go-grpc
```



然后 `$GOBIN`下出现以下可执行文件，$GOBIN=GOPATN/bin$

 protoc-gen-grpc-gateway
protoc-gen-openapiv2
protoc-gen-go
protoc-gen-go-grpc

### 2  下载相关proto 到$GOPATH/src

```
git clone git@github.com:grpc-ecosystem/grpc-gateway.git
git clone git@github.com:protocolbuffers/protobuf.git
git clone git@github.com:googleapis/googleapis.git
```

## 3 生成服务端和客户端代码

新建一个Makefile文件，将如下代码写入，然后执行make gen

```
gen:
	protoc -I ./pb \
		-I ${GOPATH}/src/github.com/googleapis/ \
		-I ${GOPATH}/src/github.com/protobuf/src \
		-I ${GOPATH}/src/github.com/grpc-gateway \
		-I ${GOPATH}/src/ \
		--go_out=./api --go_opt=paths=source_relative \
		--go-grpc_out=./api --go-grpc_opt=paths=source_relative \
		--grpc-gateway_out=./api --grpc-gateway_opt=paths=source_relative \
		--openapiv2_out=./api --openapiv2_opt logtostderr=true \
		./pb/*.proto
```

在./api下面生成了四个文件


## 4 服务端

### 1 声明服务对象，实现服务端接口

1 生成的_grpc.pb.go里面定义了服务端接口，如下

```go
// UserServiceServer is the server API for UserService service.
// All implementations must embed UnimplementedUserServiceServer
// for forward compatibility

type UserServiceServer interface {
	SaveUserInfo(context.Context, *SaveUserInfoRequest) (*SaveUserInfoResponse, error)
	mustEmbedUnimplementedUserServiceServer()
}

```

因此我们需要定义一个结构体对象来实现这个接口。定义如下

```go
type UserInfoManagerServer struct {
	name string
	api.UnimplementedUserServiceServer
}
```

然后使用结构体实现接口UserServiceServer

```go
/*
 * @Author: your name
 * @Date: 2022-04-16 20:01:39
 * @LastEditTime: 2022-04-17 13:42:09
 * @LastEditors: Please set LastEditors
 * @Description: 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
 * @FilePath: /testCode/userInfo/server/service.go
 */
package service

import (
	"context"
	"fmt"
	"reflect"

	"github.com/Arrkwen/Go/userInfo/api"
	"github.com/Arrkwen/Go/userInfo/utils"
)

/**
 * @description: UserManagerrServer is the API for  user information management service
 * @attribute {string} name : server name
 * @attribute {UnimplementedRouteGuideServer}: it must add into the server struct
 */
type UserInfoManagerServer struct {
	name string
	api.UnimplementedUserServiceServer
}

/**
 * @description: New a server
 * @param {utils.ServerConfig} cfg: server configuration
 * @return {*UserInfoManagerServer}: server object pointer
 */
func NewUserInfoManagerServer(cfg *utils.ServerConfig) *UserInfoManagerServer {
	server := &UserInfoManagerServer{name: cfg.ServerName}
	return server
}

/**
 * @description: rpc api:SaveUserInfo:暂时实现是打印请求数据
 * @param {context.Context} ctx：上下文，暂时未使用
 * @param {*api.SaveUserInfoRequest} req: rpc request：请求数据
 * @return {api.SaveUserInfoResponse}rsp: rpc response：响应数据
 */
func (u *UserInfoManagerServer) SaveUserInfo(ctx context.Context, req *api.SaveUserInfoRequest) (*api.SaveUserInfoResponse, error) {
	log.Infof("Saving user info...")
	fmt.Println("%v", req.User)
	return &api.SaveUserInfoResponse{IsSuccess: true}, nil
}
```

### 2 gRPC服务端选项配置

#### 1 配置结构体声明

```
type ServerConfig struct {
	ServerName   string // 服务名
	GPRCEndpoint string // grpc服务端的host:port
	HTTPEndpoint string // HTTP服务的host:port
	TLS          bool   // 是否TLS加密
	CertFilePath string // 加密证书路径
	KeyFilePath  string // 秘钥路径
	MsgSize      int    // gRPC收发包大小限制[4-64]MB
	LogLevel     string // 日志等级：trace,debug,info,warning,error,fatal,panic
}
```

#### 2 配置文件

server_config.json

```
{
    "ServerName":"user info manager Server",
	"GPRCEndpoint": "0.0.0.0:10000",
	"HTTPEndpoint": "0.0.0.0:10001",
	"TLS":          false,
	"CertFilePath": "",
	"KeyFilePath": "",
	"MsgSize":     4,
	"LogLevel": "debug"
}
```

#### 3 配置解析

```go
func loadConfig(configPath string, ptr interface{}) error {
	if ptr == nil {
		return fmt.Errorf("ptr of type(%T) is nil", ptr)
	}
	grpc.WithBlock()

	data, err := ioutil.ReadFile(configPath) // #nosec
	if err != nil {
		return fmt.Errorf("open file(%v) with err %v", configPath, err)
	}

	if err := json.Unmarshal(data, ptr); err != nil {
		return err
	}

	return nil
}

/**
 * @description: 根据配置文件路径解码到对应的结构体
 * @param {string} configPath：配置路径
 * @param {interface{}} ptr：解码对象
 * @return {*}：是否解码成功
 */
func LoadConfig(configPath string, ptr interface{}) error {
	if err := loadConfig(configPath, ptr); err != nil {
		return err
	}
	return nil
}

```

### 3 通过配置初始化服务端选项

当然也不一定非要通过配置的方法，可以直接指定。

```go


import (
	"time"

	log "github.com/sirupsen/logrus"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/examples/data"
	"google.golang.org/grpc/keepalive"
)

/**
 * @description: 初始化gPRC服务端配置选项
 * @param {*ServerConfig} cfg：配置结构体输入
 * @return {*}：服务端配置对象
 */
func ServerOptionGRPC(cfg *ServerConfig) []grpc.ServerOption {
	var opts []grpc.ServerOption
	if cfg.TLS {
		if cfg.CertFilePath == "" {
			cfg.CertFilePath = data.Path("x509/server_cert.pem")
		}
		if cfg.KeyFilePath == "" {
			cfg.KeyFilePath = data.Path("x509/server_key.pem")
		}
		creds, err := credentials.NewServerTLSFromFile(cfg.CertFilePath, cfg.KeyFilePath)
		if err != nil {
			log.Fatalf("Failed to create TLS credentials %v", err)
		}
		opts = []grpc.ServerOption{grpc.Creds(creds)}
	}

	opts = append(opts, grpc.KeepaliveParams(keepalive.ServerParameters{
		Time:    time.Minute,
		Timeout: time.Second * 30,
	}))

	opts = append(opts, grpc.KeepaliveEnforcementPolicy(keepalive.EnforcementPolicy{
		MinTime:             1 * time.Minute,
		PermitWithoutStream: true,
	}))

	const minMsgSize = 4
	const maxMsgSize = 64
	if cfg.MsgSize > maxMsgSize {
		cfg.MsgSize = maxMsgSize
		log.Warnf("gRPC max message size should not be larger than 64MB, actual size: %d, change to 64MB", maxMsgSize)
	}

	if cfg.MsgSize < minMsgSize {
		cfg.MsgSize = minMsgSize
		log.Warnf("gRPC max message size should be larger than 4MB, actual size: %d, change to 4MB", minMsgSize)
	}
	opts = append(opts, grpc.MaxSendMsgSize(cfg.MsgSize*1024*1024))
	opts = append(opts, grpc.MaxRecvMsgSize(cfg.MsgSize*1024*1024))

	return opts
}

```

### 4通过配置初始化服务对象和日志

```go
import (
	"flag"
	"net"
	"os"
	"os/signal"
	"syscall"

	"github.com/Arrkwen/Go/userInfo/api"
	"github.com/Arrkwen/Go/userInfo/service"
	"github.com/Arrkwen/Go/userInfo/utils"
	log "github.com/sirupsen/logrus"
	"google.golang.org/grpc"
)

var (
	configPath = flag.String("config", "config/uims_config.json", "user information managerment server config")
)

/**
 * @description: 初始化日志
 * @param {string} level：trace,debug,info,warning,error,fatal,panic
 * @return {*}
 */
func initLogger(level string) {
	var logLevel log.Level
	var err error
	if level != "" {
		logLevel, err = log.ParseLevel(level)
		if err != nil {
			logLevel = log.InfoLevel
		}
	} else {
		logLevel = log.InfoLevel
	}
	log.SetLevel(logLevel)
}

/**
 * @description: 初始化服务对象
 * @param {*utils.ServerConfig} cfg：服务配置选项
 * @return {*}：返回服务对象指针
 */
func initUIMS(cfg *utils.ServerConfig) *service.UserInfoManagerServer {
	server := service.NewUserInfoManagerServer(cfg)
	return server
}
```

### 5注册，启动，暂停服务

```go
func main() {
	// 加载配置，并初始化服务对象和日志
	flag.Parse()
	cfg := utils.ServerConfig{}
	utils.LoadConfig(*configPath, &cfg)
	initLogger(cfg.LogLevel)
	uims := initUIMS(&cfg)

	// 注册 gprc服务
	listener, err := net.Listen("tcp", cfg.GPRCEndpoint)
	if err != nil {
		log.Fatalf("failed to listen: %v", err)
	}
	grpcOption := utils.ServerOptionGRPC(&cfg)
	grpcServer := grpc.NewServer(grpcOption...)
	api.RegisterUserServiceServer(grpcServer, uims)

	// 启动 grpc 服务
	go func() {
		log.Infof("Server start.....")
		if err := grpcServer.Serve(listener); err != nil {
			log.WithError(err).Fatal("failed to serve grpc service")
		}
	}()

	// 停止 grpc 服务
	sigc := make(chan os.Signal, 1)
	signal.Notify(sigc, os.Interrupt, syscall.SIGINT, syscall.SIGTERM)
	<-sigc
	log.Infof("user info management server existing...")
	grpcServer.GracefulStop()
	log.Infof("user info management server has exited!")
}
```

## 5 客户端

### 1 客户端gprc定义

在_grpc.pb.go 文件中已经生成了所需要的可坏蛋代码接口和实现，所以客户端只需要连接服务端，构造请求数据，发起请求便可

```go
type UserServiceClient interface {
	SaveUserInfo(ctx context.Context, in *SaveUserInfoRequest, opts ...grpc.CallOption) (*SaveUserInfoResponse, error)
}

type userServiceClient struct {
	cc grpc.ClientConnInterface
}

func NewUserServiceClient(cc grpc.ClientConnInterface) UserServiceClient {
	return &userServiceClient{cc}
}

func (c *userServiceClient) SaveUserInfo(ctx context.Context, in *SaveUserInfoRequest, opts ...grpc.CallOption) (*SaveUserInfoResponse, error) {
	out := new(SaveUserInfoResponse)
	err := c.cc.Invoke(ctx, "/xpixel.userInfo.UserService/SaveUserInfo", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}
```

### 2 客户端连接配置选项

#### 1 配置结构体

```
type ClientConfig struct {
	GPRCEndpoint       string // grpc服务端的host:port
	HTTPEndpoint       string // HTTP服务的host:port
	ServerHostOverride string // gRPC服务端域名："xx.xxx.com"
	TLS                bool   // 是否TLS加密
	CaFilePath         string // 证书路径
	LogLevel           string // 日志等级：trace,debug,info,warning,error,fatal,panic
}
```

#### 2配置文件

client_config.json

```
{
	"GPRCEndpoint": "127.0.0.1:10000",
	"HTTPEndpoint": "127.0.0.1:10001",
   	"ServerHostOverride":"",
	"TLS":          false,
	"CaFilePath": "",
	"LogLevel": "debug"
}
```

### 3 初始化客户端配置

```
func ClientOptionsGRPC(cfg *ClientConfig) []grpc.DialOption {
	var opts []grpc.DialOption
	if cfg.TLS {
		if cfg.CaFilePath == "" {
			cfg.CaFilePath = data.Path("x509/ca_cert.pem")
		}
		creds, err := credentials.NewClientTLSFromFile(cfg.CaFilePath, cfg.ServerHostOverride)
		if err != nil {
			log.Fatalf("Failed to create TLS credentials %v", err)
		}
		opts = append(opts, grpc.WithTransportCredentials(creds))
	} else {
		opts = append(opts, grpc.WithTransportCredentials(insecure.NewCredentials()))
	}
	return opts
}

```

### 4 实现服务函数

```
/**
 * @description: 客户端实现保存用户信息
 * @param {api.UserServiceClient} client：grpc stub client
 * @param {*api.User} userInfo: 需要保存的用户信息
 * @return {*}
 */
func SaveUserInfo(client api.UserServiceClient, userInfo *api.User) bool {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	// 发起远端调用
	rsp, err := client.SaveUserInfo(ctx, &api.SaveUserInfoRequest{User: userInfo})
	if err != nil {
		return false
	}
	return rsp.GetIsSuccess()
}
```

### 5连接请求和发起请求

```go
package main

import (
	"context"
	"flag"
	"fmt"

	"time"

	"github.com/Arrkwen/Go/userInfo/api"
	"github.com/Arrkwen/Go/userInfo/utils"
	log "github.com/sirupsen/logrus"
	"google.golang.org/grpc"
	"google.golang.org/protobuf/types/known/timestamppb"
)

var (
	configPath = flag.String("config", "client_config.json", "client configuration")
)

func main() {
	// 加载配置,并初始化日志
	flag.Parse()
	cfg := utils.ClientConfig{}
	err := utils.LoadConfig(*configPath, &cfg)
	if err != nil {
		log.Fatal(err)
	}
	initLogger(cfg.LogLevel)
	log.Infof("connecting : %v", cfg.GPRCEndpoint)

	// 连接服务端
	clientOption := utils.ClientOptionsGRPC(&cfg)
	conn, err := grpc.Dial(cfg.GPRCEndpoint, clientOption...)
	if err != nil {
		log.Fatalf("fail to dial: %v", err)
	}
	defer conn.Close()
	client := api.NewUserServiceClient(conn)
	log.Infof("connect success: %v", client)

	// 构造请求数据
	localTime := time.Now()
	reqData := api.User{
		UserId:           "0",
		UserImage:        "dijia",
		UserPhone:        "155xxxx8388",
		UserPassword:     "*******",
		UserType:         1,
		UserRegisterTime: timestamppb.New(localTime),
		UserSchool:       "USTC",
		UserResearch:     "CV",
		UserGithub:       "github.com/xxx",
		UserGoogle:       "https://scholar.google.com/xxx",
	}
	// 服务调用
	isSuccess := SaveUserInfo(client, &reqData)
	if isSuccess {
		fmt.Println("Save user info success")
	} else {
		fmt.Println("Save user info failed")
	}
}

```
