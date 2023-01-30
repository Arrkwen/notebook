### 关联远程仓库

> 1 git init
>
> 2 git remote add origin 远程仓库地址：    git@github.com：xx/notebook.git
>
> 3 推送到master分支
>
> git add .
>
> git commit -m
>
> git push -u origin master

### 设置git提交规范

为了方便使用，我们避免了过于复杂的规定，格式较为简单且不限制中英文：

```go
<type>(<scope>): <subject>
// 注意冒号 : 后有空格
// 如 feat(miniprogram): 增加了小程序模板消息相关功能
复制代码
```

**scope选填**表示commit的作用范围，如数据层、视图层，也可以是目录名称
**subject必填**用于对commit进行简短的描述
**type必填**表示提交类型，值有以下几种：

* feat - 新功能 feature
* fix - 修复 bug
* docs - 文档注释
* style - 代码格式(不影响代码运行的变动)
* refactor - 重构、优化(既不增加新功能，也不是修复bug)
* perf - 性能优化
* test - 增加测试
* chore - 构建过程或辅助工具的变动
* revert - 回退
* build - 打包

```
bash
查看本机是否安装node?   node -v
安装node : wget https://nodejs.org/dist/latest/node-v17.6.0-linux-x64.tar.xz
解压： tar -xzvf node-v17.6.0-linux-x64.tar.xz
改名：mv node-v17.6.0-linux-x64.tar.xz nodejs
测试版本： cd ./nodejs/bin/&node -v&npm -v
添加环境变量：export PATH=$PATH:xxx/nodejs/bin
测试node -v  可行，输出v17.6.0  测试sudo node -v 不可行
添加sudo权限   ln -s node的完整路径 /usr/local/bin/node
              ln -s npm的完整路径 /usr/local/bin/npm
再次测试sudo npm -v 可行
安装commitizen： $ sudo npm install -g commitizen
在需要执行commit的项目里面执行 commitizen init cz-conventional-changelog --save --save-exact 然后将git commit 替换为 git cz
由于执行了上面的命令，会在当前项目生成node_modules  package.json  package-lock.json三个额外的文件，因此我们需要忽略这些文件，参考下一个链接。

```

[配置git提交忽略文件](https://www.cnblogs.com/kevingrace/p/5690241.html)

增加文件正则表达式到.gitignore中。

网站

https://backlog.com/git-tutorial/cn/intro/intro1_1.html

https://juejin.cn/post/6844903793033756680
