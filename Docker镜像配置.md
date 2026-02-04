# Docker 镜像加速配置指南

## 问题说明

错误信息显示 Docker 无法从 Docker Hub 拉取镜像：
```
failed to resolve reference "docker.io/library/mongo:4.4": context deadline exceeded
```

这是因为 Docker Hub 在国内访问速度慢或被限制。

---

## 🔧 解决方案：配置 Docker 镜像加速器

### 方案一：使用 Docker Desktop 图形界面配置（推荐）

#### 1. 打开 Docker Desktop 设置

1. 点击菜单栏的 Docker 图标
2. 选择 **"Settings"**（或"偏好设置"）
3. 选择左侧菜单的 **"Docker Engine"**

#### 2. 添加镜像加速器配置

在 JSON 配置中添加 `"registry-mirrors"` 配置：

```json
{
  "builder": {
    "gc": {
      "defaultKeepStorage": "20GB",
      "enabled": true
    }
  },
  "experimental": false,
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.nju.edu.cn",
    "https://mirror.ccs.tencentyun.com"
  ]
}
```

#### 3. 应用配置

1. 点击 **"Apply & Restart"** 按钮
2. 等待 Docker 重启完成

#### 4. 验证配置

```bash
docker info | grep -A 10 "Registry Mirrors"
```

应该显示配置的镜像加速器地址。

---

### 方案二：使用命令行手动配置

#### 1. 创建或编辑 Docker 配置文件

```bash
# 创建配置目录（如果不存在）
mkdir -p ~/.docker

# 创建配置文件
cat > ~/.docker/daemon.json <<'EOF'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.nju.edu.cn",
    "https://mirror.ccs.tencentyun.com"
  ]
}
EOF
```

#### 2. 重启 Docker Desktop

1. 点击菜单栏的 Docker 图标
2. 选择 **"Restart Docker Desktop"**

#### 3. 验证配置

```bash
docker info | grep -A 10 "Registry Mirrors"
```

---

## 🚀 配置完成后的操作

### 重新拉取镜像

配置镜像加速器后，重新运行启动脚本：

```bash
cd /Users/qiran/LLM_Proj/LS_Proj/zp_ls/TradingAgents-CN
./start.sh
```

### 或者手动拉取镜像

```bash
# 拉取 MongoDB 镜像
docker pull mongo:4.4

# 拉取 Redis 镜像
docker pull redis:7-alpine

# 启动服务
docker-compose up -d mongodb redis
```

---

## 🔍 其他可用镜像加速器

如果上述镜像源仍然有问题，可以尝试其他镜像源：

### 阿里云镜像加速器
```json
"https://your-id.mirror.aliyuncs.com"
```
*需要注册阿里云账号获取专属地址：https://cr.console.aliyun.com/cn-hangzhou/instances/mirrors*

### 网易云镜像加速器
```json
"https://hub-mirror.c.163.com"
```

### 腾讯云镜像加速器
```json
"https://mirror.ccs.tencentyun.com"
```

### 南京大学镜像加速器
```json
"https://docker.nju.edu.cn"
```

### 中科大镜像加速器
```json
"https://docker.mirrors.ustc.edu.cn"
```

---

## 📝 完整的 daemon.json 配置示例

```json
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.nju.edu.cn",
    "https://mirror.ccs.tencentyun.com",
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com"
  ],
  "dns": ["8.8.8.8", "114.114.114.114"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
```

---

## ⚠️ 常见问题

### 1. 配置后仍然无法拉取镜像

**可能原因：**
- Docker 未正确重启
- 配置文件格式错误（JSON 格式）
- 镜像源暂时不可用

**解决方法：**
```bash
# 检查配置文件语法
cat ~/.docker/daemon.json | python3 -m json.tool

# 查看 Docker 日志
cd ~/Library/Containers/com.docker.docker/Data/log/
tail -f vm/DockerDesktopVM-iso.log
```

### 2. 某些镜像源无法访问

尝试更换其他镜像源，或者组合使用多个镜像源。

### 3. 验证镜像源是否可用

```bash
# 测试镜像源速度
curl -I https://docker.m.daocloud.io/v2/
curl -I https://docker.nju.edu.cn/v2/
```

---

## 🎯 快速修复命令

如果您想快速解决问题，直接复制以下命令：

```bash
# 方法1：使用 DaoCloud 镜像源（推荐）
cat > ~/.docker/daemon.json <<'EOF'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io"
  ]
}
EOF

# 重启 Docker Desktop
osascript -e 'quit app "Docker"'
sleep 5
open -a Docker

echo "⏳ 等待 Docker 启动（约 30 秒）..."
sleep 30

# 验证配置
docker info | grep -A 5 "Registry Mirrors"
```

---

**配置完成后，重新运行启动脚本即可！** 🚀
