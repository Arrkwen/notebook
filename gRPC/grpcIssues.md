### 1 grpc.WithInsecure

 is deprecated: use insecure.NewCredentials() instead.

**answer:**

```go
grpc.Dial(":9950", grpc.WithTransportCredentials(insecure.NewCredentials()))
```

### 2 service.mustEmbedUnimplementedXXXServer()

pb.mustEmbedUnimplementedXXXServer 添加到实现接口的结构体中,其中pb是生成_gprc.pb.go的目录

例如：

```
type TMServerstruct {  
persister   persister.PersistHandler  
serverLimit *manager.ServiceLimit   
pb.UnimplementedTaskManagerServiceServer}
```
