参考：https://www.cnblogs.com/cjsblog/p/12256843.html

## gitlab-runner 安装，

注意要和gitlab的版本匹配，通过项目右上角问号->help查看gitlab版本，runner15.0以后的不支持14.8以前的gitlab。

https://docs.gitlab.com/runner/install/linux-repository.html

## gitlab-runner 注册

只有管理员才有shared-runner的url和topken，普通用户一般只能注册group runner或者specific-runner

shared-runner： 同一个gitalb-instance下，所有项目共享，管理员才能实现。

group-runner:      同一个用户组下的所有项目共享

specific-runner： 单独的项目能运行，但可以编辑，关闭lock-specific选项，共享到其它项目。在需要运行的项目下在specific-runner下找到此runner，然后选择：enable for this project。

https://docs.gitlab.com/runner/register/index.html

注册中有一个选择：选择excuter的类型，[参考](https://chengweichen.com/2021/03/gitlab-ci-executor.html)，比较好的方式是使用docker，然后在gitlab-ci.yml中添加image。

## gitlab-runner卸载

yum erase gitlab-runner

## gitlab-runner访问镜像仓库

1 将访问镜像仓库的账号和密码，生成认证密码。

加密

```
# 对比一下登录harbor的用户名:密码 加密后是否和~/.docker/config.json中auth的值对应
echo -n "user:password" | base64

```

解密

```
# xxx为上面加密后的值
echo -n "xxx" | base64 -d

```

2 编辑：~/.docker/config.json，增加仓库地址和访问密码

```

{
	"auths": {
		"harbor.xxx.com": {
			"auth": "xxx"
		}
		"register.xxx.com": {
			"auth": "xxx"
		}
	}
}
```

## gitlab-runner 访问代码仓库

修改runner的网络模式为host

vim /etc/gitlab-runner/config.toml，添加**network_mode = "host"**

```
[runners.docker]
    tls_verify = false
    image = "registry.sensetime.com/cstk/search_engine:ubuntu20.04-amd64-rocm22.10-0.6"
    privileged = false
    disable_entrypoint_overwrite = false
    oom_kill_disable = false
    disable_cache = false
    volumes = ["/cache"]
    shm_size = 0
    network_mode = "host"
```

## gitlab-runner 镜像拉取策略

vim /etc/gitlab-runner/config.toml

pull_policy = "if-not-present"

## gitlab-ci.yml的书写规则

[官网](https://docs.gitlab.com/ee/ci/yaml/)

[菜鸟教程](http://www.ttlsa.com/auto/gitlab-cicd-gitlab-ci-yml-configuration-tasks-detailed/)
