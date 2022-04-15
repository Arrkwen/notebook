<!--
 * @Descripttion: 
 * @version: 
 * @Author: xiaokun
 * @Date: 2022-04-14 15:11:04
 * @LastEditors: xiaokun
 * @LastEditTime: 2022-04-14 15:16:03
-->

# 静态代码检查工具golangci-lint

[参考官网](https://golangci-lint.run/usage/configuration/)，[参考博文](https://kiosk007.top/post/golang-%E9%9D%99%E6%80%81%E4%BB%A3%E7%A0%81%E5%88%86%E6%9E%90%E5%B7%A5%E5%85%B7/)

## 1 安装

```
curl -sSfL https://raw.githubusercontent.com/golangci/golangci-lint/master/install.sh | sh -s -- -b $(go env GOPATH)/bin v1.45.2
```

## 2 测试

`golangci-lint --version`

## 3 使用

### 检查所有文件

``golangci-lint run``

It's an equivalent of executing:

``golangci-lint run ./...``

### 检查单个目录或者单个文件

You can choose which directories and files to analyze:

``golangci-lint run dir1 dir2/... dir3/file1.go``

Directories are NOT analyzed recursively. To analyze them recursively append `/...` to their path.

GolangCI-Lint can be used with zero configuration. By default the following linters are enabled:

### 指定一个linter

Pass `-E/--enable` to enable linter and `-D/--disable`to disable:

只使用errcheck
golangci-lint run --disable-all -E errcheck

## 4 修改配置

在项目根目录下面创建文件，写入配置选项，golangci-lint会自动查找该配置文件，不用指定路径。

* `.golangci.yml`

```
linters:
  # Disable all linters.
  # Default: false
  disable-all: true
  # Enable specific linter
  # https://golangci-lint.run/usage/linters/#enabled-by-default-linters
  enable:
    - asciicheck
    - bidichk
    - bodyclose
    - contextcheck
    - cyclop
    - deadcode
    - depguard
    - dogsled
    - dupl
    - durationcheck
    - errcheck
    - errname
    - errorlint
    - exhaustive
    - exhaustivestruct
    - exportloopref
    - forbidigo
    - forcetypeassert
    - funlen
    - gci
    - gochecknoglobals
    - gochecknoinits
    - gocognit
    - goconst
    - gocritic
    - gocyclo
    - godot
    - godox
    - goerr113
    - gofmt
    - gofumpt
    - goheader
    - goimports
    - golint
    - gomnd
    - gomoddirectives
    - gomodguard
    - goprintffuncname
    - gosec
    - gosimple
    - govet
    - ifshort
    - importas
    - ineffassign
    - interfacer
    - ireturn
    - lll
    - makezero
    - maligned
    - misspell
    - nakedret
    - nestif
    - nilerr
    - nilnil
    - nlreturn
    - noctx
    - nolintlint
    - paralleltest
    - prealloc
    - predeclared
    - promlinter
    - revive
    - rowserrcheck
    - scopelint
    - sqlclosecheck
    - staticcheck
    - structcheck
    - stylecheck
    - tagliatelle
    - tenv
    - testpackage
    - thelper
    - tparallel
    - typecheck
    - unconvert
    - unparam
    - unused
    - varcheck
    - varnamelen
    - wastedassign
    - whitespace
    - wrapcheck
    - wsl
  # Enable all available linters.
  # Default: false
  enable-all: true
  # Disable specific linter
  # https://golangci-lint.run/usage/linters/#disabled-by-default-linters--e--enable
  disable:
    - asciicheck
    - bidichk
    - bodyclose
    - contextcheck
    - cyclop
    - deadcode
    - depguard
    - dogsled
    - dupl
    - durationcheck
    - errcheck
    - errname
    - errorlint
    - exhaustive
    - exhaustivestruct
    - exportloopref
    - forbidigo
    - forcetypeassert
    - funlen
    - gci
    - gochecknoglobals
    - gochecknoinits
    - gocognit
    - goconst
    - gocritic
    - gocyclo
    - godot
    - godox
    - goerr113
    - gofmt
    - gofumpt
    - goheader
    - goimports
    - golint
    - gomnd
    - gomoddirectives
    - gomodguard
    - goprintffuncname
    - gosec
    - gosimple
    - govet
    - ifshort
    - importas
    - ineffassign
    - interfacer
    - ireturn
    - lll
    - makezero
    - maligned
    - misspell
    - nakedret
    - nestif
    - nilerr
    - nilnil
    - nlreturn
    - noctx
    - nolintlint
    - paralleltest
    - prealloc
    - predeclared
    - promlinter
    - revive
    - rowserrcheck
    - scopelint
    - sqlclosecheck
    - staticcheck
    - structcheck
    - stylecheck
    - tagliatelle
    - tenv
    - testpackage
    - thelper
    - tparallel
    - typecheck
    - unconvert
    - unparam
    - unused
    - varcheck
    - varnamelen
    - wastedassign
    - whitespace
    - wrapcheck
    - wsl
  # Enable presets.
  # https://golangci-lint.run/usage/linters
  presets:
    - bugs
    - comment
    - complexity
    - error
    - format
    - import
    - metalinter
    - module
    - performance
    - sql
    - style
    - test
    - unused
  # Run only fast linters from enabled linters set (first run won't be fast)
  # Default: false
  fast: true
```
