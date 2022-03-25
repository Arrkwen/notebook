1 编译环境

* make env
* make all

-----需要挂载目录

> 本地的task-management和容器
>
> 本地的mod，方便调试  <---->

2 运行容器

修改Dockerfile

> COPY ./config/tms_config.json/$PROJECT_NAME/

本地make image

3 编写docker-compose.yml

```yml
version: '2'
services:
  task-manager:
    image: 10.151.3.75/rtc/rtc-task-management-service:v0.1.0-master-a192ed9
    ports:
      - '9877:9877'
      - '9878:9878'
      - '19000:19000'
    command: './task-management -config tms_config.json'
    volumes:
      - './tms_config.json:/task-management/tms_config.json'
```

4 配置数据库

    1 安装

    2 配置访问用户

    3 建库，建表

5 修改配置

DatabaseConfig的endpoint一定要指明ip地址

```
{
    "LogLevel": "debug",
    "GRPCEndpoint": "0.0.0.0:9877",
    "HTTPEndpoint": "0.0.0.0:9878",
    "MetricsEndpoint": "0.0.0.0:19000",
    "MaxTaskReportInterval": 60,
    "DatabaseConfig": {
        "Username": "tmadmin",
        "Password": "tm@pswd123",
        "Endpoint": "10.152.205.21:3306",
        "Database": "rtc",
        "UseSSL": false
    }
}
```

6 插入worker_id的位置记录

1. mysql创建:

   - [ ] **需要增加索引吗？**   已经设置主键，有索引的。
   - [X] task_info_table添加字段
2. mysql操作层utils
3. persister.go

   - [X] 持久层的TaskInfo需要增加WorkerId字段
   - [X] 增加更新WorkerID的接口
   - [X] pb 的Task需要添加worker_id字段吗？不需要修改，
   - [ ] TaskInfo<---->结构体成员的数据分布是否需要调整 **？？**
4. mysql.go

   - [X] UpdateTaskInfoOnlyWorkerId 实现更新WorkerID的接口： **service中的taskGet接口应该需要调用**
   - [ ] UpdateTaskInfoAll  是否需要加入workerId字段？？ 暂时不需要
   - [X] ListTaskInfos  增加字段
   - [X] *GetTaskInfo   增加字段*
5. service

   - [X] TaskNew   无任何操作
   - [X] TaskDelete  无任何操作  但是改变了flag可能需要注意一下，在超时任务中需要处理 task.flag = 3
   - [ ] TaskUpdate  同持久层，是否需要更新workerID,应该是不需要的，这个任务更新到底什么意思？目前的任务更新有bug需要重构。
   - [X] TaskGet  增加了debug信息，因为昨天没有响应？是否需要更新WorkerId，不需要，因为实时聚类任务不关心自己的ID。
   - [ ] TaskList  如果需要显示worker_ID,就需要改变Task的结构，增加WorkerId字段。
   - [ ] Report    肯定是需要更新workerID，应该在第一次取数据时更新，还是第一次上报时再更新呢？第一次更新，即使发送过程中client端没有收到task，但是这个task已经写上了他的WorkerId，下次请求时依然只会分配给它。

     1. 下发新任务时需要遍历所有的任务列表，找到未分配的任务进行下发，这儿太耗时，先不关心。
     2. 更新时间有什么作用呢？ 更新任务的时候说明更新时间
     3. 操作数据库，很耗时，是否需要开额外的协程去更新数据库，然后主的执行返回操作。如果写数据库失败，需要记录日志重新去写。
     4. **有bug 任务更新操作，怎么是创建新任务呢，那原来的任务怎么处理？**  会重构的
     5. **任务完成只更新状态，不从数据库删除吗？  任务是不会有完成的，只是增加一个状态**
   - [X] Start
   - [X] handleTimeoutTasks
6. **测试部分**
