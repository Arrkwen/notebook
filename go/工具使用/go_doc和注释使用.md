## 代码添加注释

[参考](https://github.com/OBKoro1/koro1FileHeader/wiki/%E5%AE%89%E8%A3%85%E5%92%8C%E5%BF%AB%E9%80%9F%E4%B8%8A%E6%89%8B)

1 vscode 插件安装 KoroFileHeader

2 ctrl+, --> fileheader  设置json 添加如下

```
    // 文件头部注释
    "fileheader.customMade": {
        "Descripttion":"",
        "version":"",
        "Author":"sueRimn",
        "Date":"Do not edit",
        "LastEditors":"sueRimn",
        "LastEditTime":"Do not Edit"
    },
    //函数注释
    "fileheader.cursorMode": {
        "description":"",
        "param":"",
        "return":""
    }
```

3 在函数上方一行 输入快捷键

`window`：`ctrl+win+t`,`mac`：`ctrl+cmd+t`,`linux`: `ctrl+meta+t`, `Ubuntu`: `ctrl+win+t`

4 函数注释光标移动到下一行，快速添加函数参数描述

`window`: `win+y`, mac: `cmd+y`, linux: `win+y`


## 注释查看

1 安装godoc

`sudo apt install golang-golang-x-tools`

2 godoc -http=:6060

3 打开http://127.0.0.1:6060/  在Packages->thirdparty里面直接搜索自己的包注释
