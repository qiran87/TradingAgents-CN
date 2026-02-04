#!/bin/bash
# Docker Desktop 重启脚本

echo "🔄 正在重启 Docker Desktop..."

# 退出 Docker Desktop
osascript -e 'quit app "Docker"' 2>/dev/null || true

# 等待 Docker 完全退出
echo "⏳ 等待 Docker 退出..."
sleep 5

# 重新启动 Docker Desktop
echo "🚀 启动 Docker Desktop..."
open -a Docker

# 等待 Docker 启动
echo "⏳ 等待 Docker 引擎启动（约 30 秒）..."
for i in {1..30}; do
    if docker info > /dev/null 2>&1; then
        echo "✅ Docker 启动成功！"
        break
    fi
    echo "   等待中... ($i/30)"
    sleep 1
done

# 验证镜像加速器配置
echo ""
echo "🔍 验证镜像加速器配置："
docker info | grep -A 5 "Registry Mirrors"

echo ""
echo "✅ 配置完成！现在可以运行 ./start.sh 启动服务了"
