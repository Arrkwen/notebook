### 安装路径

TEXDIR (the main TeX directory):
     /usr/local/texlive/2021
   TEXMFLOCAL (directory for site-wide local files):
     /usr/local/texlive/texmf-local
   TEXMFSYSVAR (directory for variable and automatically generated data):
     /usr/local/texlive/2021/texmf-var
   TEXMFSYSCONFIG (directory for local config):
     /usr/local/texlive/2021/texmf-config
   TEXMFVAR (personal directory for variable and automatically generated data):
     ~/.texlive2021/texmf-var
   TEXMFCONFIG (personal directory for local config):
     ~/.texlive2021/texmf-config
   TEXMFHOME (directory for user-specific files):
     ~/texmf

## ubuntu安装latex2021

### 1 下载镜像

> texlive2021.iso [清华源](https://mirrors.tuna.tsinghua.edu.cn/CTAN/systems/texlive/Images/)

### 2 解压

> sudo mount -o loop texlive2021.iso /mnt

### 3 安装

> cd /mnt/
> sudo ./install-tl
> 支持默认路径安装 选择 I

时间稍长

### 4 卸载镜像文件

> cd ..
> sudo umount /mnt

### 5 设置环境变量

> export PATH=/usr/local/texlive/2021/bin/x86_64-linux:$PATH
> export PATH=/usr/local/texlive/2021/texmf-dist/scripts/latexindent:$PATH
> export MANPATH=/usr/local/texlive/2021/texmf-dist/doc/man:$MANPATH
> export INFOPATH=/usr/local/texlive/2021/texmf-dist/doc/info:$INFOPATH

### 6 字体设置

6.1 拷贝tex的字体到系统字体库

> sudo cp /usr/local/texlive/2021/texmf-var/fonts/conf/texlive-fontconfig.conf /etc/fonts/conf.d/09-texlive.conf

6.2 安装win字体

> sudo apt update
> sudo apt install ttf-mscorefonts-installer

选择ok yes

6.3 刷新字体

> sudo mkfontscale
> sudo mkfontdir
> sudo fc-cache  -fsv

7 vscode 插件

> latex workshop
