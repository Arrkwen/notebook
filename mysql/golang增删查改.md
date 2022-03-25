https://meilihao.github.io/go-database-sql-tutorial_zh-CN/accessing.html

### sql.DB

sql.DB 通过数据库驱动为我们提供管理底层数据库连接的打开和关闭操作.

sql.DB 为我们管理数据库连接池
需要注意的是，sql.DB表示操作数据库的抽象访问接口,而非一个数据库连接对象;它可以根据driver打开关闭数据库连接，管理连接池。正在使用的连接被标记为繁忙，用完后回到连接池等待下次使用。所以，如果你没有把连接释放回连接池，会导致过多连接使系统资源耗尽。

https://studygolang.com/articles/12509


### Prepared Statement

sql.Stmt支持预备表达式，可以用来优化SQL查询提高性能，减少SQL注入的风险, DB.Prepare()和Tx.Prepare()都提供了对于预备表达式的支持。

预处理的流程:
step1. 将sql分为2部分.命令部分和数据部分.
step2. 首先将命令部分发送给mysql服务器,mysql进行预处理.(如生成AST)
step3. 然后将数据部分发送给mysql服务器,mysql进行占位符替换.
step4. mysql服务器执行sql语句,把执行结果发送给客户端.

预处理的优势:
1.因为发送命令后,在mysql服务器端,就会将AST生成好,所以不需要对每一次值的更换都重新生成一次AST.对同样的数据不同的SQL来讲,只需生成1次AST,并缓存起来即可.
2.避免SQL注入.因为mysql知道再次发送过来的内容为”数据”,因此不会将这些数据解析为SQL,避免了SQL注入.

需要注意的点:
使用预处理进行查询操作时,不仅在defer时需要关闭结果,而且还要关闭命令句柄,否则同样会占用连接,导致阻塞.

### 事务

事务(transaction)

* transaction, err := Db.Begin() 开启事务
* transaction.Exec() 执行事务
* transaction.Commit() 提交事务
* transaction.Rollback() 回滚事务

A. 事务的应用场景
　　1. 同时更新多个表
　　2. 同时更新多行数据
B. 事务的ACID
　　1. 原子性
　　2. 一致性
　　3. 隔离性
　　4. 持久性

需要注意的点:

1. 执行失败要回滚
2. 提交失败要回滚

```go
package main

import (
    _ "github.com/go-sql-driver/mysql"
    "database/sql"
    "fmt"
)


func Transaction(db *sql.DB) {

    // 开启事务
    tx, err := db.Begin()

    if err != nil {
        panic(err)
    }

    result, err := tx.Exec("insert into user(name, age)values(?,?)", "Jack", 98)
    if err != nil {
        // 失败回滚
        tx.Rollback()
        panic(err)
    }
  
    fmt.Println("result", result)

    exec, err := tx.Exec("update user set name=?, age=? where id=?", "Jack", 98, 1)
    if err != nil {
        // 失败回滚
        tx.Rollback()
        panic(err)
    }
    fmt.Println("exec", exec)

    // 提交事务
    err = tx.Commit()
  
    if err != nil {
        // 失败回滚
        tx.Rollback()
        panic(err)
    }
}

func main() {

    dns := "root:123456@tcp(172.16.65.200:3306)/golang"
    db, err := sql.Open("mysql", dns)
    if err != nil {
        panic(err)
    }

    err = db.Ping()
    if err != nil {
        panic(err)
    }

    Transaction(db)
}
```

### MySQL只是插入记录，需要使用事务或者锁吗？

锁：insert操作一般不像delete/update，有时候需要先锁定行(forupdate)做检查，这时候有一个显式加锁的过程，insert很少这么去锁定数据，如果需要检查一般也是用insert on duplicate update直接进行pk/uk更新就好了，所以很少有锁的逻辑在insert场景里

事务：如果要保证数据的一致性，事务是必开的，比如说库存场景，已售+1，库存必然要-1，否则一定会产生销量和库存数据对不上的问题，比如业务逻辑是：库存-1，添加一条销售记录，肯定是要开启事务，但是开启事务的确会有一定的性能损耗，所以一般也是如果事务逻辑相对简单，还是业务保证数据幂等就好
