### 关联远程仓库

> 1 git init
>
> 2 git remote add origin 远程仓库地址：    git@github.com：xx/notebook.git
>
> 3 推送到master分支
>
>    git add .
>
>    git commit -m
>
>    git push -u origin master

### 设置git提交规范

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
