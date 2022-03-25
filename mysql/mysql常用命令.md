## MySQL常用命令

官网：https://dev.mysql.com/doc/refman/8.0/en/char.html

### 获取偶数的方法

select * from pos_info_report_tmp_20110712 r
where mod(r.id,2) = 0;

获取奇数的方法
select * from pos_info_report_tmp_20110712 r
where mod(r.id,2) = 1;

MySQL查看用户状态，root用户下：
select host,user from mysql.user;
创建用户：
CREATE USER 'jdbc'@'localhost'  IDENTIFIED BY 'jdbc'; #本地登录
CREATE USER 'jdbc'@'%'  IDENTIFIED BY 'jdbc'; #远程登录
更改用户密码：
set password for jdbc@localhost = password('jdbc');
切换到root用户创建数据库springtest：
create database springtest DEFAULT CHARSET utf8 COLLATE utf8_general_ci;
授权jdbc用户拥有所有数据库的所有权限：
grant all privileges on *.* to 'jdbc'@'localhost' identified by 'jdbc';
grant all privileges on *.* to 'jdbc'@'%' identified by 'jdbc';
flush privileges; #刷新系统权限表

#创建数据库
create database mbook DEFAULT CHARSET utf8 COLLATE utf8_general_ci;
create database recruitmentwebsite DEFAULT CHARSET utf8 COLLATE utf8_general_ci;

#sftp上传文件 本地 -- 目标
put /home/hao/Desktop/recruitmentwebsite.sql /usr/local/java/
#下载文件
get /var/www/fuyatao/index.php  /home/fuyatao/

#修改数据库编码
alter database db_dorm CHARACTER SET GBK COLLATE gbk_chinese_ci;

#授权ssh用户拥有mbook数据库 远程和本地链接 的 所有权限：
grant all privileges on `mbook`.* to 'ssh'@'localhost' identified by 'ssh';
grant all privileges on `mbook`.* to 'ssh'@'%' identified by 'ssh';

#授予用户在所有数据库上的所有权限
grant all privileges on *.* to 'ssh'@'localhost' identified by 'ssh';
grant all privileges on *.* to 'ssh'@'%' identified by 'ssh';

#执行sql脚本,可以有2种方法:在命令行下(未连接数据库),输入 ：
mysql -h localhost -u root -proot < /itoffer_new.sql

#在命令行下(已连接某个账户，且选择了use database或者创建了数据库,此时的提示符为 mysql> ),输入：
source /itoffer_new.sql

#创建表
create table login(
id int(10) auto_increment not null primary key,
name varchar(50),
password varchar(50),
role varchar(50) DEFAULT 'False'
);

#插入数据
insert into login values('1','a','a','True');
insert into login values('2','观海先生','a','True');
insert into login values('3','衣知世','a','True');
insert into login values('4','田松石','a','False');

#修改某一条数据
update student set sex='男' where id=4;

#删除数据
delete from student where id=5;

select * from login where name=a and password=a

#数据库备份语句
mysqldump -ussh -pssh --all-databases > /backup/mbook_$(date +%Y%m%d%H%M%S).sql
mysqldump -ussh -pssh --all-databases | gzip > /backup/mbook_$(date +%Y%m%d%H%M%S).sql.gz
#定时清理备份文件命令
find /backup/mbook -name $mbook"*.sql.gz" -type f -mmin +1 -exec rm -rf {} \; > /dev/null 2>&1
find /backup/mbook -name $mbook"*.sql" -type f -mmin +1 -exec rm -rf {} \; > /dev/null 2>&1

### 登陆mysql

> shell>mysql [-h host] -u user -p [-D database]
> Enter password:

-h 指定的是远程主机，登陆本地数据库可以不用

-D 用于指定登陆之后选择的数据库，如果没有指定数据库，则不进行数据库选择。

### 退出mysql

> mysql>quit

不加分号

### 创建数据库

> mysql>create database database_name;

### 删除数据库

> mysql>drop database database_name;

### 使用数据库

> mysql>use database_name;

每次使用某个数据库前必须明确选择使用它，也既是使用use命令。

### mysql的数据类型

mysql主要有三类数据类型：数值类型、时间&日期类型、字符串类型。

#### 数值类型

- **int**，正常整型数值，分为signed和unsigned，范围分别是 -2147483648 到 2147483647 和 0 到
  4294967295
- **tinyint**，超小整型数值，分为signed和unsigned，范围分别是 -128 到 128 和 0 到 255
- **smallint**，小型整型数值，分为signed和unsigned，范围分别是 -32768 到 32768 和 0 到 65535
- **mediumint**，中等整型数值，分为signed和unsigned，范围分别是 -8388608 到 8388608 和 0 到
  16777215
- **bignit**，大号整型数值，分为signed和unsigned，范围分别是 -9223372036854775808 到 9223372036854775808和 0 到 18446744073709551615
- **float(m, d)**，浮点型数值，不能为unsigned。可以设定显示总长度m位数字和d位小数。默认情况下分别是10和2
- **double(m,d)**，双精度浮点型数值，不能为unsigned。可以设定显示总长度m位数字和d位小数。默认情况下分别是16和4。
- **decimal(m,d)**，一种未包装的小数，不能为unsigned。每一位小数都对应一个字节，需要明确定义总长度m位数字和d位小数。numeric和decimal是同义词。

#### 时间&日期类型

- **date**，yyyy-mm-dd格式，范围从1000-01-01到9999-12-31
- **datetime**，yyyy-mm-dd hh:mm:ss格式，范围从1000-01-01 00:00:00到9999-12-31
  23:59:59
- **timestamp**，范围从1970年1月1日0点0分0秒到2037年的某个时间，格式类似datetime，但是没有连字符。例如1973年12月30日15点30分0秒对应19731230153000（yyyymmddhhmmss）
- **time**，hh:mm:ss格式存储。
- **year(m)**，2位或4位格式。指定2位时，例如year(2)，能够存储1970年到2069年（70-69）。指定4位时，能够存储1901年到2155年，默认4位长度。

#### 字符串类型

- char(m)，固定长度字符串，长度从1到255，左对齐右填充，默认长度为1
- varchar(m)，变长字符串，长度从1到255，定义式必须指定一个长度。从版本5.03及其以后，最大长度能到65535。长度小于等于255时，额外用一个字节存储长度值，长度超过255时，额外用2个字节存储长度值。

`声明CHAR(4)` and `VARCHAR(4)在内存中的字节存储数，超过4时，会截断。但如果开启strict SQL mode,超出的数据不会插入成功。`

| 值          | char(4)  | 存储需求 | varchar(4) | 存储要求 |
| ----------- | -------- | -------- | ---------- | -------- |
| ”          | ’ ‘    | 4字节    | ”         | 1字节    |
| ‘ab’      | ‘ab ‘  | 4字节    | ‘ab’     | 3字节    |
| ‘abcd’    | ‘abcd’ | 4字节    | ‘abcd’   | 5字节    |
| ‘abcdefg’ | ‘abcd’ | 4字节    | ‘abcd’   | 5字节    |

- blob和text，最大存储65535个字节。blob将数据当作二进制数组存储，可以保存图片、声音等数据；text依然将数据当作字符存储。无需为blob和text指定长度。
- tinyblob和tinytext，最大存储255个字节，其余特性和blob/text一致
- mediumblob和mediumtext，最大存储16777215个字节，其余特性和blob/text一致
- longblob和longtext，最大存储4294967295个字节，其余特性和blob/text一致
- enum，枚举类型，枚举最多可以有65535个元素，枚举型字段中除列举字符串之外，可以为NULL，若插入非法字符串，将用空(”)字符串代替

### 创建表格

> mysql>create table table_name (cloumn_name colume_type, colunm_name colunm_type ...);

列项除了有数据类型，还可以添加一些别的属性，例如 not null, auto_increment, default等。还可以指定主键，设置数据库引擎，设置字符集等。例如：

```mysql
mysql>create table hotel (
        -> `id` int unsinged not null auto_increment,
        -> `default test` int default 0,
        -> `num` char(4) not null,
        -> `price` varchar(5) not null,
        -> `position` varchar(30) not null,
        -> `describe` text,
        -> `available` enum('y', 'n'),
        -> primary key(`id`)
);
```

有几点需要注意：

- ` 叫反引号，号是Esc下面的那个按键。在mysql语句中，如果创建表格时候表格的名字或属性字段跟系统关键字重名，或者名字中间包括空白字符，可以利用反引号把名字括起来，mysql只保留反引号内的内容。同时要注意，用其他引号括起来都不对，因为mysql会认为引号是字段的起始字符，这不符合命名规则。
- text类型不能有默认值。需要默认值的可以在字段后面用 default 注明。
- 利用 primary key(column_name, column) 来设置主键，多个列项之间用逗号隔开。

### 删除表格：

> mysql>drop table table_name;

如果为了保证即使没有表存在，也不至于语句出错，可以使用下面的命令：

> mysql>drop table if exists table_name;

参考

https://blog.csdn.net/xiangyubobo/article/details/46544733
http://www.tutorialspoint.com/mysql/mysql-data-types.htm
https://dev.mysql.com/doc/refman/5.0/en/char.html
https://dev.mysql.com/doc/refman/5.0/en/blob.html
https://dev.mysql.com/doc/refman/5.0/en/enum.html


## Mysql执行脚本创建数据库

> mysql -h localhost -u tmadmin -ptm@pswd123 < xx.sql
