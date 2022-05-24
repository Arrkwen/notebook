# Prometheus + Grafana实现可视化、告警

参考：[陈树义大佬](https://mp.weixin.qq.com/s?__biz=MzA4MjIyNTY0MQ==&mid=2647740094&idx=1&sn=402b974441de0cbf28a15a268c5e3d61&chksm=87ad1e38b0da972e182f77a06bf15b5146017d03a81bd7f3afeabd81dc21bf4dfed4fa059e2d&cur_album_id=1560987127876780034&scene=189#wechat_redirect)

中文文档：https://grafana.com/docs/

Prometheus UI 提供了快速验证 PromQL 以及临时可视化支持的能力，但其可视化能力却比较弱。一般情况下，我们都用 Grafana 来实现对 Prometheus 的可视化实现。

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQJd1epyGYqiceR06sHEzNPsqrFKntQuT31AYwA4WWiaIaQ0AQsB5qmY8g/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

## 什么是 Grafana

Grafana 是一个用来展示各种各样数据的开源软件，在其官网上用这么一段话来说明其作用。

```
Used by thousands of companies to monitor everything from infrastructure, applications, and power plants to beehives.

数以万计的公司用 Grafana 来监控基础设施、应用。
```

从官网上可以看到目前有 Paypal、ebay 等公司已经在使用 Prometheus 了。

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQoWiaGBmcia4WfttWBdtDePyxYPp2lFd9DFBPK5LhQyvkiaSXszQLxu3hA/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

## 快速入门

我们只需要在 Grafana 上配置一个 Prometheus 的数据源。接着我们就可以配置各种图表，Grafana 就会自动去 Prometheus 拉取数据进行展示。

### 安装

https://grafana.com/grafana/download

```
sudo apt-get install -y adduser libfontconfig1
wget https://dl.grafana.com/enterprise/release/grafana-enterprise_8.5.0_amd64.deb
sudo dpkg -i grafana-enterprise_8.5.0_amd64.deb
```

### 安装包细节

* Installs binary to `/usr/sbin/grafana-server`
* Installs Init.d script to `/etc/init.d/grafana-server`
* Creates default file (environment vars) to `/etc/default/grafana-server`
* Installs configuration file to `/etc/grafana/grafana.ini`
* Installs systemd service (if systemd is available) name `grafana-server.service`
* The default configuration sets the log file at `/var/log/grafana/grafana.log`
* The default configuration specifies a SQLite3 db at `/var/lib/grafana/grafana.db`
* Installs HTML/JS/CSS and other Grafana files at `/usr/share/grafana`

### 配置

以下两条命令如果是监控系统就添加，测试就算了

```
### NOT starting on installation, please execute the following statements to configure grafana to start automatically using systemd
 sudo /bin/systemctl daemon-reload
 sudo /bin/systemctl enable grafana-server
```

### 启动服务器

首先我们从 https://grafana.com/grafana/download 下载对应系统的安装包，下载解压后用下面的命令启动：

```
### You can start grafana-server by executing
 sudo /bin/systemctl start grafana-server
```

Grafana 默认使用 3000 端口启动，我们访问：http://localhost:3000 查看对应页面。

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQkDdO7ubRGDqUCvoKRPax427SHiaibvBZDMS7LSB9Pr7DI8JkEh1Zc1Kg/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

默认的账号密码是 admin/admin，登陆进去后是这样的。

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQXx4c2MKun18D6ibQgCcI53kTV7xNsqknVyxIlWsFwUebQjUCo6pqZ4w/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

### 配置数据源

之后我们去设置菜单添加 Prometheus 数据源：

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQYI1Bwc3icCsaYaEjPHXO9PeeicZUiaNtW4HZ2gRowlQe6v5jicgHuU4Wcw/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

打开如下图所示：

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQhvJicGr7XmviaezWhC7xBMxYrapSoWBZGhbFKZ0aTnqpiaSAbnwQm1mBw/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

之后输入对应的名字和 URL 地址即可：注意将Promethus服务开启才行

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQruxuFibkIQLNvb1JMBosE1NANTIyygue4YFmAfdqkaBofQgcG10NIaA/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

这里我们添加了一个名为「Prometheus-1」的数据源，数据获取地址为：http://localhost:9090。

### 配置面板

在 Grafana 中有「Dashboard」和「Panel」的概念，Dashboard 可以理解成「看板」，而 Panel 可以理解成「图表，一个看看板中包含了无数个图表。例如下图就是一个看板（Dashboard）：

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQ5KeCumN7wRzW8Exo0t0W3hReqQ00OwJxYsZm6rib0zgmgSfzuCcx0iaA/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

里面一个个小的图表，就是一个个小的图表（Panel）。

点击「+ 号」-> 「Dashboard」就可以添加一个大面板。

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQWhwnQKtIGoBDMFSYvuF8bXYIQZpPs1tU079GGHQ3SWNnlUnU6Taic0w/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

添加后的面板是空白的，下面我们创建一个图标来显示 CPU 的使用率变化情况。点击右上角的创建图表按钮：

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQY5aY9hdd4icwcib57CKeuibcU7QuJiaUmexqlykYhicIV7JsUuWENXp6vsQ/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

点击创建图表会进入如下界面：

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQjDtufh1Kob0n3TkAO7daPPF4kaxeAPIE6hkyrnTib3ycMQrFKJYqVFA/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

我们设置好数据源、Metrics 数据、图表名称，之后点击右上角的 Apply 按钮即可。保存之后我们就可以在面板中看到机器的 CPU 使用率情况了。

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQOFXITNmzNibtIicDsUk5c60vKV3iciaL3l7KSlVX6ovlibs3A1M7QSv1tDQ/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

### 邮件通道配置

如果我们要使用 Prometheus 进行监控告警，那么 Grafana 也能够实现。

Grafana 的告警渠道有很多，这里我们以邮件告警为例。

**/etc/grafana/grafana.ini** on linux systems

In this config file you can change things like the default admin password, http port, grafana database (sqlite3, mysql, postgres), authentication options (google, github, ldap, auth proxy) along with many other options.

sudo vim /etc/grafana/grafana.ini        ./smtp找到如下位置，进行配置

邮箱地址使用和之参考：https://support.websoft9.com/docs/faq/zh/tech-smtp.html#smtp%E9%85%8D%E7%BD%AE

```
[smtp]
enabled = true
host = smtp.exmail.qq.com:465
user = xxx@qq.com
# If the password contains # or ; you have to wrap it with triple quotes. Ex """#password;"""
password = xxxx
cert_file =
key_file =
skip_verify = false
from_address = xxx@qq.com  //必须与上面的 user 属性一致
from_name = Grafana
ehlo_identity =
```

host 这里是你邮箱所在运营商的 SMTP 服务器。user 属性是发件人的邮箱地址。password 是发件人邮箱的登陆密码。from_address 与 user 属性一样，都是发件人的邮箱地址。from_name 是发件人的显示名称。

tail -f -n 300 /var/log/grafana/grafana.log 查看报错日志

修改完成之后，保存配置文件，之后重启 Grafana。

`sudo systemctl restart grafana-server`

接着通过 Alerting 菜单添加告警渠道。

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQJ5aPKKZjBGQc4BDPCib12IXmE9GorFic1FSjcKB3M3VkM05aTvBlp6GA/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

之后填写「提醒通道」名称、类型，之后点击「Send Test」按钮测试一下。

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQTe5nqnnygwAIKmbZ0RRwiaNy2KyfEdbVnQvGZmI8VmibD1ibLgaIlAyRw/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

正常的话，会收到一封测试邮件，这表明邮件配置已经完成。

此外我们还可以配置 AlertManager、钉钉等其他告警方式，配置的流程都大同小异，这里不再赘述。

### 指标告警配置

配置好邮件发送通道信息后，Grafana 就具备了发送邮件的能力。但是什么时候发送邮件呢？这就需要我们进行指标告警配置了。

我们需要在图表面板设置中设置相关报警信息：

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQ27SqvXxKzCs8N4ZibRApwdj7VTUpLbib2OZ77dhhicmhtiaxxiaHlPlAHQQ/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

这里我配置了 1 分钟内值低于 1，那么就报警，即：1 分钟内挂机了，那么就报警。随后我手动关掉了 NodeExport 节点，过了几分钟我就收到了报警邮件。

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQtaFw0RU9yCwNXwTzb5evcTowufzmX9FwXEl8WWmjicAwHNvVHM4Ve9w/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

***更多关于图表的设置，将在后续文章专门讲述，这里不深入讲解。***

## Grafana 模板中心

对于线上监控来讲，如果我们每个面板都需要自己从零开始，那么就太累了。事实上，我们用到的许多监控信息都是类似的。因此 Grafana 官网 - Dashboards 模块 提供了下载 Dashboard 模板的功能。

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQb11SwqHCHHQL7hbISTSJp7IRnhp6QpS7oka63hMicLQrnvgNcH4Jyug/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

Dashboards 里有许多各种类型的 Dashboard 面板，例如 JVM 监控、MySQL 数据库监控等。你只需找到合适自己的监控面板，之后根据 ID 添加即可。

例如我找到的这个这个面板包含了各种常见的资源监控，例如：CPU、内存等。

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQ8u0vwMcF5q0icc3YlyBL0jmCsP0sYDZkPgkBfC6jiclmAUyn0h6WPicYA/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

你只需要复制它的 ID 并使用 Grafana 的 import 功能导入即可，如下图所示：

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQZqstarHqmFibazx3pome4cpks34mUl8zKLKyWLDIeEIfrFkvGia2rOibA/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

最终的效果如图所示：

![图片](https://mmbiz.qpic.cn/mmbiz_jpg/AVWicyZuuClFicZKZl6mEZYqTpGKOUCvLQnLBN4yy4I7mic8GHmcicVbsdwwJSCgPLma9QQNl9xr4bSzuppEMo2O4w/640?wx_fmt=jpeg&wxfrom=5&wx_lazy=1&wx_co=1)

## 参考资料

* Grafana: The open observability platform | Grafana Labs
* Grafana Dashboards - discover and share dashboards for Grafana. | Grafana Labs
