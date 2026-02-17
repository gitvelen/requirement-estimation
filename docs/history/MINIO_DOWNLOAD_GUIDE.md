# MinIO镜像下载指南

## 问题
Docker Hub连接超时，无法直接下载MinIO镜像

## 解决方案

### 方案1：使用国内镜像加速器（推荐）

#### 1.1 配置Docker镜像加速

```bash
# 创建或编辑Docker配置文件
sudo tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://mirror.ccs.tencentyun.com",
    "https://mirror.baidubce.com"
  ],
  "max-concurrent-downloads": 10
}
