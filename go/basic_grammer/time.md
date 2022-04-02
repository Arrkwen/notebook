## 时间

### 获取时间

```go
import (
    "fmt"
    "time"
)

func main() {
    // 获取本地计算机时间
    localTime := time.Now()
    // 2020-08-01 22:08:12.983185 +0800 CST m=+0.000104694
    fmt.Println(localTime)
}
```

Copy

### 时间格式化

```go
import (
    "fmt"
    "time"
)

func main() {
    localTime := time.Now()
    // 2006-01-02 15:04:05 中的时间不可更改
    formatTime := localTime.Format("2006-01-02 15:04:05")
    fmt.Println(formatTime) // 返回：2020-08-01 22:16:03
}
```

Copy

上面是用 `-`做为分隔符，也可以自定义：

```go
func main() {
    localTime := time.Now()
    // 日、月、小时和分秒，如果可去掉 前导的 0
    formatTime := localTime.Format("2006年1月2日 15点04分05秒")
    fmt.Println(formatTime) // 返回：2020年8月1日 22点58分07秒
}
```

Copy

只获取指定部分：

```go
import (
    "fmt"
    "time"
)

func main() {
    localTime := time.Now()

    // 分别返回年月日
    fmt.Println(localTime.Year())
    fmt.Println(localTime.Month())
    fmt.Println(localTime.Day())
    // 返回时分秒
    fmt.Println(localTime.Hour())
    fmt.Println(localTime.Minute())
    fmt.Println(localTime.Second())
    // 返回周
    fmt.Println(localTime.Weekday())
}
```

Copy

## 时区

### 查看时区

```go
import (
    "fmt"
    "time"
)

func main() {
    localTime := time.Now()
    // 返回 CST 28800（时区及 UTC 偏移量）
    fmt.Println(localTime.Zone())
    // 需要 tzdata 支持
    time.LoadLocation("Local")
}
```

Copy

### 指定时区

```go
import (
    "fmt"
    "time"
)

func main() {
    localTime := time.Now()
    // 8*60*60 也可用 int((8 * time.Hour).Seconds()) 表示
    cusZone := time.FixedZone("UTC+8", 8*60*60)
    cusTime := localTime.In(cusZone)
    fmt.Println(cusTime)
}
```

Copy

## 时间戳

### 查看时间戳

```go
import (
    "fmt"
    "time"
)

func main() {
    currTime := time.Now()
    // 秒
    unixTime := currTime.Unix()
    // 纳秒
    unixNanoTime := currTime.UnixNano()
}
```

Copy

上面的示例其实是把当前的时间转为时间戳，也可以把指定的时间转为时间戳：

```go
func main() {
    cusZone := time.FixedZone("UTC+8", 8*60*60)
    // 2020-12-11 10:09:08.000000007 +0800 UTC+8
    timeDate := time.Date(2020, 12, 11, 10, 9, 8, 7, cusZone)
    unixTime := timeDate.Unix() // 返回 1607652548
}
```

Copy

### 时间戳转时间字符串

```go
import (
    "fmt"
    "time"
)

func main() {
    currUnixTime := Time.Now().Unix()
    currTime := Time.Unix(currUnixTime, 0)
    // 2020-08-01 00:11:22 +0800 CST
    fmt.Println(currTime)
}
```

### 时间转换

```go
package main

import (
    "fmt"
    "time"
)

func main() {
    // 获取当前(当地)时间
    t := time.Now()
    // 获取0时区时间
    t = time.Now().UTC()
    fmt.Println(t)
    // 获取当前时间戳
    timestamp := t.Unix()
    fmt.Println(timestamp)
    // 获取时区信息
    name, offset := t.Zone()
    fmt.Println(name, offset)
    // 把时间戳转换为时间
    currenttime := time.Unix(timestamp+int64(offset), 0)
    // 格式化时间
    fmt.Println("Current time : ", currenttime.Format("2006-01-02 15:04:05"))
}
```

## 时间运算

```go
import (
    "fmt"
    "time"
)

func main() {
    currTime := time.Now()
    // 时间相加，可改用负数做减法
    fmt.Println(currTime.Add(time.Second * 10)) // 加 10秒
    fmt.Println(currTime.Add(time.Minute * 10)) // 10分钟
    fmt.Println(currTime.Add(time.Hour * 10))   // 10小时
    fmt.Println(currTime.Add(time.Hour * 24 * 10)) // 10天

    // 日期相加
    fmt.Println(currTime.AddDate(1, 2, 3))

    // 时间相减，结果以小时计
    subTime := currTime.Add(time.Hour * 10).Sub(currTime)
	fmt.Println(subTime) // 返回 10h0m0s
}
```

Copy

参考

* [Golang time.Now() 格式化的问题](https://segmentfault.com/q/1010000010976398/a-1020000010977895)
* [time - The Go Programming Language](https://golang.org/pkg/time/#Time.Format)

## timer


## ticker
