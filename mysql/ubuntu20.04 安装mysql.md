## 安装MySQL

### 先决条件

确保您以具有sudo特权的用户身份登录。

### 在Ubuntu上安装MySQL

在撰写本文时，Ubuntu存储库中可用的MySQL的最新版本是MySQL 8.0。要安装它，请运行以下命令：

```markup
sudo apt update
sudo apt install mysql-server
```

安装完成后，MySQL服务将自动启动。要验证MySQL服务器正在运行，请输入：

```markup
sudo systemctl status mysql
```

输出应显示该服务已启用并正在运行：

```markup
● mysql.service - MySQL Community Server
 Loaded: loaded (/lib/systemd/system/mysql.service; enabled; vendor preset: enabled)
 Active: active (running) since Tue 2020-04-28 20:59:52 UTC; 10min ago
 Main PID: 8617 (mysqld)
 Status: "Server is operational"
 ...
```

### 保护MySQL

MySQL安装随附一个名为的脚本 `mysql_secure_installation`，可让您轻松提高数据库服务器的安全性。

调用不带参数的脚本：

```markup
sudo mysql_secure_installation
```

系统将要求您配置 `VALIDATE PASSWORD PLUGIN`用来测试MySQL用户密码强度并提高安全性的密码：

```markup
Securing the MySQL server deployment.

Connecting to MySQL using a blank password.

VALIDATE PASSWORD COMPONENT can be used to test passwords
and improve security. It checks the strength of password
and allows the users to set only those passwords which are
secure enough. Would you like to setup VALIDATE PASSWORD component?

Press y|Y for Yes, any other key for No: y
```

密码验证策略分为三个级别：低，中和强。按下 `y`如果你想设置的验证密码插件或任何其他键移动到下一个步骤：

//测试数据就选择低，关键的还是要做好密码保护

```markup
There are three levels of password validation policy:

LOW Length >= 8
MEDIUM Length >= 8, numeric, mixed case, and special characters
STRONG Length >= 8, numeric, mixed case, special characters and dictionary file

Please enter 0 = LOW, 1 = MEDIUM and 2 = STRONG: 2
```

在下一个提示符下，将要求您设置MySQL root用户的密码：

```markup
Please set the password for root here.

New password: 

Re-enter new password: 
```

如果您设置了验证密码插件，该脚本将向您显示新密码的强度。键入 `y`以确认密码：

```markup
Estimated strength of the password: 50 
Do you wish to continue with the password provided?(Press y|Y for Yes, any other key for No) : y
```

接下来，将要求您删除匿名用户，限制root用户对本地计算机的访问，删除测试数据库并重新加载特权表。您应该回答 `y`所有问题。

### 验证安装是否成功

```
mysql -V
```

### root登录

> sudo mysql

### 创建用户

本机访问用户

> CREATE USER 'admin'@'localhost' IDENTIFIED BY 'pswd';

远程访问用户

> CREATE USER 'kalacloud-remote'@'%' IDENTIFIED WITH mysql_native_password BY 'password';

#### 查看用户

> SELECT user, host FROM mysql.user;

#### 删除MySQL用户帐户

要删除用户帐户，请使用以下命令：

```markup
DROP USER IF EXISTS 'database_user'@'localhost';
```

输出：

```markup
Query OK, 0 rows affected, 1 warning (0.00 sec)
```

#### 修改账户密码策略

查看相关密码设置规则

> SHOW VARIABLES LIKE 'validate_password%'
>
> +-----------------------------------------------+-------------------+
> | Variable_name                                |       Value       |
> +-----------------------------------------------+-------------------+
> | validate_password.dictionary_file          |               |
> | validate_password.length                      |      8       |
> | validate_password.mixed_case_count   |      1       |
> | validate_password.number_count         |      1       |
> | validate_password.policy                       |   LOW    |
> | validate_password.special_char_count   |      1      |
> +------------------------------------------------------+--------- --+

修改每一项

> set global validate_password.policy=0;  //1 2   LOW MIDUM STRONG

#### 向MySQL用户帐户授予权限

可以向用户帐户授予多种类型的特权。您可以在此处找到MySQL支持的特权的完整列表。

根据自己的需要，给你用于远程访问的账号赋予权限。下面的例子是给账号全局权限，包括创建（`CREATE`）、修改（`ALTER`）、删除（`DROP`） 数据库、表、用户，任意表的插入（`INSERT`）、更新（`UPDATE`）、删除（`DELETE`）操作权限。可以使用 `SELECT` 查询数据，使用 `REFERENCES` 建立外键关系权限，以及使用 `RELOAD` 权限执行 `FLUSH` 操作的权限。当然，你也可以根据自己都需求，对账号权限进行调整。

千万不要授权所有权利，即使用如下命令！！！！！！

要授予对特定数据库用户帐户的所有特权，请使用以下命令：

```markup
GRANT ALL PRIVILEGES ON database_name.* TO 'database_user'@'localhost';
```

要授予对所有数据库用户帐户的所有特权，请使用以下命令：

```markup
GRANT ALL PRIVILEGES ON *.* TO 'database_user'@'localhost';
```

要对数据库中的特定表授予用户帐户的所有特权，请使用以下命令：

```markup
GRANT ALL PRIVILEGES ON database_name.table_name TO 'database_user'@'localhost';
```

**如果要仅授予特定数据库类型的用户帐户特定特权，请执行以下操作：**

```markup
GRANT SELECT, INSERT, DELETE ON database_name.* TO database_user@'localhost';
```

#### 从MySQL用户帐户撤消权限

如果您需要撤消一个用户帐户的一个或多个特权或所有特权，则语法几乎与授予它相同。例如，如果要撤消特定数据库上用户帐户的所有特权，请使用以下命令：

```markup
REVOKE ALL PRIVILEGES ON database_name.* TO 'database_user'@'localhost';
```

#### 显示MySQL用户帐户权限

查找授予特定MySQL用户帐户类型的特权：

```markup
SHOW GRANTS FOR 'database_user'@'localhost';
```

输出：

```markup
+---------------------------------------------------------------------------+
| Grants for database_user@localhost |
+---------------------------------------------------------------------------+
| GRANT USAGE ON *.* TO 'database_user'@'localhost' |
| GRANT ALL PRIVILEGES ON `database_name`.* TO 'database_user'@'localhost' |
+---------------------------------------------------------------------------+
2 rows in set (0.00 sec)
```

### 远程访问账户设置

参考：https://kalacloud.com/blog/how-to-allow-remote-access-to-mysql/

#### 开启 MySQL 远程连接权限步骤

1. 编辑 MySQL 配置文件
2. 配置服务器内置防火墙
3. 配置阿里云/腾讯云等安全组允许外网连接
4. 多种方式远程连接 MySQL

#### 1.编辑 MySQL 配置文件

在默认情况下，MySQL 数据库仅监听本地连接。如果想让外网远程连接到数据库，我们需要修改配置文件，让 MySQL 可以监听远程固定 ip 或者监听所有远程 ip。

首先打开 `mysqld.cnf` 配置文件。

```bash
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf
```

找到 bind - address 这一行，如下图所示。

[![mysqld](https://kalacloud.com/static/2e2920bb039ba4b3a7a7b1e57992d731/be796/01-mysqld.jpg "mysqld")](https://kalacloud.com/static/2e2920bb039ba4b3a7a7b1e57992d731/6ed34/01-mysqld.jpg)

默认情况下， bind - address 的值为 127.0.0.1 ，所以只能监听本地连接。我们需要将这个值改为远程连接 ip 可访问，可使用通配符 ip 地址 `*`， `::`， `0.0.0.0` ，当然也可以是单独的固定 ip，这样就仅允许指定 ip 连接，更加安全。

[![mysqld-bind-address](https://kalacloud.com/static/823469868183d856d686d3fbb45e8059/be796/02-mysqld-bind-address.jpg "mysqld-bind-address")](https://kalacloud.com/static/823469868183d856d686d3fbb45e8059/6ed34/02-mysqld-bind-address.jpg)

提示：在某些 MySQL 版本的配置文件中，没有 bind - address 这一行，这种情况下，在合适的位置加上就可以了。

 **提示：** 在某些 MySQL 版本的配置文件中，没有 bind - address 这一行，这种情况下，在合适的位置加上就可以了。

更改后，保存并退出编辑器（使用 CTRL+X 保存并退出 nano 编辑器。）

然后重启 MySQL 服务，使刚刚编辑的 `mysqld.cnf` 文件生效：

```bash
sudo systemctl restart mysql
```

如果你想用现有账号来作为远程登录账号的话，那么需要重新配置这个账号，好让它有远程访问的权限。我们使用 root 账号来登录 mysql 进行设置。

```bash
sudo mysql
```

如果你开启了 root 密码验证，那么使用这个命令来登录

```bash
mysql -u root -p
```

将用做远程登录的账号 host 改为任意主机（%）或者是固定主机 ip 。可以使用 `RENAME USER` 命令来实现：

```bash
mysql> RENAME USER 'kalacloud'@'localhost' TO 'kalacloud'@'%';
```

[![rename-user](https://kalacloud.com/static/9f4bc871f60735d8bf8448407d6a78a8/be796/03-rename-user.jpg "rename-user")](https://kalacloud.com/static/9f4bc871f60735d8bf8448407d6a78a8/dcec8/03-rename-user.jpg)

当然你也可以创建一个新账号专门用于远程登录，可以使用这个命令创建账号：

```bash
CREATE USER 'kalacloud-remote'@'%' IDENTIFIED WITH mysql_native_password BY 'password';
```

接着，根据自己的需要，给你用于远程访问的账号赋予权限。下面的例子是给账号全局权限，包括创建（`CREATE`）、修改（`ALTER`）、删除（`DROP`） 数据库、表、用户，任意表的插入（`INSERT`）、更新（`UPDATE`）、删除（`DELETE`）操作权限。可以使用 `SELECT` 查询数据，使用 `REFERENCES` 建立外键关系权限，以及使用 `RELOAD` 权限执行 `FLUSH` 操作的权限。当然，你也可以根据自己都需求，对账号权限进行调整。

```bash
GRANT CREATE, ALTER, DROP, INSERT, UPDATE, DELETE, SELECT, REFERENCES, RELOAD on *.* TO 'kalacloud-remote'@'%' WITH GRANT OPTION;
```

最后，运行 `FLUSH PRIVILEGES` 命令，刷新 MySQL 的系统权限相关表，更新缓存。

```bash
mysql> FLUSH PRIVILEGES;
```

全部完成，现在退出 MySQL：

```bash
mysql> exit
```

#### 2.配置服务器内置防火墙

MySQL 默认端口为 3306 ，我们需要告诉防火墙，允许 3306 端口通讯。

如果你仅希望某一台服务器可远程访问数据库，则可以使用以下命令授权某一台（ip）服务器访问。

```bash
sudo ufw allow from remote_IP_address to any port 3306
```

当然，你也可以允许任意计算机远程访问数据库。

```bash
sudo ufw allow 3306
```

到这里，让 MySQL 允许远程连接在服务器的部分就全部设置完成了。但仍然有很多同学依然无法远程访问，卡在这里。这种情况，大多数是因为你没有配置 **云服务的防火墙** 。也就是说，除了服务器内置的防火墙外，还有云服务的防火墙需要被开启，接着我们讲讲阿里云 / 腾讯云配置 MySQL 远程连接的步骤 。

#### 3.置配阿里云 / 腾讯云等云服务 MySQL 允许远程访问

如果你的数据库 / 服务器 host 在云服务中，那么开启 MySQL 允许远程访问的配置步骤前边都一样，只是在最后，我们还需要在云服务的[安全组](https://help.aliyun.com/document_detail/25471.html?spm=5176.100241.0.0.IneJPl)里，添加一条规则，允许 3306 端口连接。很多同学卡在这里了，一定要注意。

[![aliyun](https://kalacloud.com/static/caf4b2020b284723e1b1eb48c52e6e47/be796/06-aliyun.jpg "aliyun")](https://kalacloud.com/static/caf4b2020b284723e1b1eb48c52e6e47/57a9c/06-aliyun.jpg)

阿里云服务器实例中的防火墙设置

腾讯云与阿里云类似，也是在安全组里设置。如果你使用的是腾讯云纯 MySQL 数据库，那么可以在实例详情中找到开启外网的选项。如果还无法连接，也可查阅 [无法连接实例](https://cloud.tencent.com/document/product/236/44754#.E5.AE.89.E5.85.A8.E7.BB.84.E9.85.8D.E7.BD.AE.E6.9C.89.E8.AF.AF) 的手册文档。

[![tencent-cloud](https://kalacloud.com/static/ee714f69a71ab95aa1c27fe46d4aec83/be796/07-tencent-cloud.jpg "tencent-cloud")](https://kalacloud.com/static/ee714f69a71ab95aa1c27fe46d4aec83/0afc5/07-tencent-cloud.jpg)

腾讯云 MySQL 开启外网连接方式

#### 4.远程连接到 MySQL 数据库

##### （1）使用命令行远程访问 MySQL 数据库

```bash
~: mysql -u username -h mysql_server_ip -p
```

[![remote-mysql.jpg](https://kalacloud.com/static/2e5eb747e21714e7ef69366b36fef11c/be796/08-remote-mysql.jpg "remote-mysql.jpg")](https://kalacloud.com/static/2e5eb747e21714e7ef69366b36fef11c/6fffd/08-remote-mysql.jpg)

使用命令行访问远程 MySQL 数据库

 **特别注意 ** ：如果你的 MySQL 服务端口不是默认的 3306 ，那么指定端口登录，只要在命令后面增加 -P XXXX 即可。即将以上命令：mysql -u root -p 改为 mysql -u root -p -P [指定端口] 即可，注意指定端口的字母 P 为大写。

##### （2）使用 Sequel Ace 等本地软件远程连接 MySQL 数据库

[![remote-mysql-sequel-Ace.](https://kalacloud.com/static/464afe7007486b9da365bf444c5cbc3e/be796/09-remote-mysql-sequel-pro.jpg "remote-mysql-sequel-Ace.")](https://kalacloud.com/static/464afe7007486b9da365bf444c5cbc3e/11438/09-remote-mysql-sequel-pro.jpg)

使用 Sequel Ace 等数据库操作软件远程访问 MySQL 数据库。

Sequel Pro、Workbench 等本地软件并不支持 `caching_sha2_plugin` 插件认证方式，你可使用本教程前文所述的方法，将远程登录账号改为密码认证方式或新建一个使用密码认证的新账号用于远程登录。

## 卸载

> sudo apt-get autoremove --purge mysql-server
>
> sudo apt-get remove mysql-common
>
> sudo rm -rf /etc/mysql/  /var/lib/mysql

#### 清理残留数据

> dpkg -l |grep ^rc|awk '{print $2}' |sudo xargs dpkg -P
>
> sudo apt autoremove
>
> sudo apt autoclean
