## ubuntu完全卸载CUDA

```python
sudo apt-get autoremove --purge remove nvidia* cuda*

sudo rm -rf /usr/local/cuda*
```

如果遇到，无法下载的问题

Unable to correct missing packages.

E: Failed to fetch http://cn.archive.ubuntu.com/ubuntu/pool/universe/f/freeglut/freeglut3_2.8.1-3_amd64.deb  Connection failed [IP: 91.189.91.39 80]
E: Failed to fetch http://cn.archive.ubuntu.com/ubuntu/pool/universe/f/freeglut/freeglut3-dev_2.8.1-3_amd64.deb  Connection failed [IP: 91.189.91.39 80]

更新软件源,software & upate页面的download from

![](http://confluence.sensetime.com/download/attachments/414178875/image2022-6-6_17-30-37.png?version=1&modificationDate=1654507837977&api=v2 "肖坤 &gt; 文件中转 &gt; image2022-6-6_17-30-37.png")

Cuda 安装 参考官网安装指南：

https://developer.nvidia.com/cuda-downloads?target_os=Linux&target_arch=x86_64&Distribution=Ubuntu&target_version=20.04&target_type=deb_local
