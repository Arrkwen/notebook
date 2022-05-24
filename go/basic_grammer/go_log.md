# logrus

完全兼容golang的log

## 日志来源

```golang
import (
	log "github.com/sirupsen/logrus"
)

```

## 日志等级

不加任何的args参数，分为七个等级，通过 `log.SetLevel(log.InfoLevel),` 其中Info是默认等级

```
log.Trace("Something very low level.")
log.Debug("Useful debugging information.")
log.Info("Something noteworthy happened!")
log.Warn("You should probably take a look at this.")
log.Error("Something failed but I'm not quitting.")
// Calls os.Exit(1) after logging
log.Fatal("Bye.")
// Calls panic() after logging
log.Panic("I'm bailing.")
```

## 设置日志

### 日志等级

一则可以通过传输传递“trance,debug....panic”等字符串，二则可以通过直接传递等级标志，即日志中return常量，比如log.DebugLevel。

```golang
func ParseLevel(lvl string) (Level, error) {
	switch strings.ToLower(lvl) {
	case "panic":
		return PanicLevel, nil
	case "fatal":
		return FatalLevel, nil
	case "error":
		return ErrorLevel, nil
	case "warn", "warning":
		return WarnLevel, nil
	case "info":
		return InfoLevel, nil
	case "debug":
		return DebugLevel, nil
	case "trace":
		return TraceLevel, nil
	}

	var l Level
	return l, fmt.Errorf("not a valid logrus Level: %q", lvl)
}
```

### 日志输出格式

```golang
// 设置日志格式为json格式,不建议是JSON格式，有点乱
log.SetFormatter(&log.JSONFormatter{})
// 文本模式，这个看情况设置属性
log.SetFormatter(&log.TextFormatter{
		DisableColors: false,   //是否带颜色
		FullTimestamp: true,    //是否带时间
	})

// 设置调用函数，输出会很长
log.SetReportCaller(true)

// 调用日志输出
// 设置将日志输出到标准输出（默认的输出为stderr,标准错误）
// 日志消息输出可以是任意的io.writer类型
log.SetOutput(os.Stdout)

// 输出到文件，参考HOOK

```

常用代码

```golang
func initLog(loglevel string) {
	var logLevel log.Level
	var err error
	if loglevel != "" {
		logLevel, err = log.ParseLevel(loglevel)
		if err != nil {
			logLevel = log.InfoLevel
		}
	} else {
		logLevel = log.InfoLevel
	}
	log.SetLevel(logLevel)
}
```

## 日志的默认使用——不带参数

不携带任何参数

```go
package logrus

import (
	log "github.com/sirupsen/logrus"
)

func LogrusPrint() {
	log.SetLevel(log.TraceLevel)
	log.Trace("Something very low level.")
	log.Debug("Useful debugging information.")
	log.Info("Something noteworthy happened!")
	log.Warn("You should probably take a look at this.")
	log.Error("Something failed but I'm not quitting.")
	// Calls os.Exit(1) after logging
	log.Fatal("Bye.")
	// Calls panic() after logging
	log.Panic("I'm bailing.")
}
```

输出，panic没有输出，因为log之后会产生panic，日志都来不及输出

```
TRAC[0000] Something very low level.                
DEBU[0000] Useful debugging information.            
INFO[0000] Something noteworthy happened!           
WARN[0000] You should probably take a look at this.   
ERRO[0000] Something failed but I'm not quitting.   
FATA[0000] Bye.                                     
exit status 1
```

## 日志使用——携带参数

```go
func LogrusPrintf() {
	log.SetLevel(log.TraceLevel)
	log.Tracef("Something very low level.%s", "I am trancef")
	log.Debugf("Useful debugging information.%s", "I am Debugf")
	log.Infof("Something noteworthy happened!,%s", "I am Infof")
}
```

## 日志使用——WithField

由于上面的%s，日志不够格式化，因此可以通过Fields指定

```go
func LogrusWithFields() {
	log.SetLevel(log.TraceLevel)

	log.WithFields(log.Fields{
		"field": "info",
		"task":  "test info",
	}).Info("test logrus with field")

	// or
	logEntry := log.WithFields(log.Fields{"field": "debug", "task": "test Debug"})
	logEntry.Debug("test logrus With Field")
}

```

输出

```
INFO[0000] test logrus with field                        field=info task="test info"
DEBU[0000] test logrus With Field                        field=debug task="test Debug"
```

## 日志使用——HOOK，日志分割

### 1. 安装依赖库

```
go get github.com/sirupsen/logrus
go get github.com/lestrrat/go-file-rotatelogs
go get github.com/rifflock/lfshook
```

### 2. 添加 hook

```golang
package log

import (
    "github.com/lestrrat/go-file-rotatelogs"
    "github.com/pkg/errors"
    "github.com/rifflock/lfshook"
    log "github.com/sirupsen/logrus"
    "path"
    "time"
)

func init() {
    log.SetLevel(log.InfoLevel)
    log.AddHook(newRotateHook("", "stdout.log", 7*24*time.Hour, 24*time.Hour))
}

func newRotateHook(logPath string, logFileName string, maxAge time.Duration, rotationTime time.Duration) *lfshook.LfsHook {
    baseLogPath := path.Join(logPath, logFileName)

writer, err := rotatelogs.New(
        baseLogPath+".%Y-%m-%d",
        rotatelogs.WithLinkName(baseLogPath),      // 生成软链，指向最新日志文
        rotatelogs.WithMaxAge(maxAge),             // 文件最大保存时间
        rotatelogs.WithRotationTime(rotationTime), // 日志切割时间间隔
    )
    if err != nil {
        log.Errorf("config local file system logger error. %+v", errors.WithStack(err))
    }
    return lfshook.NewHook(lfshook.WriterMap{
        log.DebugLevel: writer, // 为不同级别设置不同的输出目的
        log.InfoLevel:  writer,
        log.WarnLevel:  writer,
        log.ErrorLevel: writer,
        log.FatalLevel: writer,
        log.PanicLevel: writer,
    }, &log.TextFormatter{DisableColors: true, TimestampFormat: "2006-01-02 15:04:05.000"})
}
```
