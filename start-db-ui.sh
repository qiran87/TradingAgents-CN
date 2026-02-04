#!/bin/bash
# 启动数据库管理界面工具

echo "=================================="
echo "🔍 启动数据库管理界面"
echo "=================================="

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker Desktop"
    exit 1
fi

echo ""
echo "请选择要启动的管理界面："
echo "1) Mongo Express (MongoDB Web 界面)"
echo "2) Redis Commander (Redis Web 界面)"
echo "3) 全部启动"
echo "4) 全部停止"
echo ""
read -p "请输入选项 (1-4): " choice

case $choice in
    1)
        echo ""
        echo "🚀 启动 Mongo Express..."
        docker-compose up -d mongo-express
        echo ""
        echo "✅ Mongo Express 已启动"
        echo ""
        echo "📍 访问地址: http://localhost:8082"
        echo "🔐 用户名: admin"
        echo "🔑 密码: tradingagents123"
        ;;

    2)
        echo ""
        echo "🚀 启动 Redis Commander..."
        docker-compose up -d redis-commander
        echo ""
        echo "✅ Redis Commander 已启动"
        echo ""
        echo "📍 访问地址: http://localhost:8081"
        echo "🔑 已自动连接到本地 Redis"
        ;;

    3)
        echo ""
        echo "🚀 启动所有管理界面..."
        docker-compose up -d mongo-express redis-commander
        echo ""
        echo "✅ 所有管理界面已启动"
        echo ""
        echo "📍 Mongo Express:  http://localhost:8082"
        echo "   用户名: admin"
        echo "   密码: tradingagents123"
        echo ""
        echo "📍 Redis Commander: http://localhost:8081"
        ;;

    4)
        echo ""
        echo "🛑 停止所有管理界面..."
        docker-compose stop mongo-express redis-commander
        echo ""
        echo "✅ 所有管理界面已停止"
        ;;

    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

echo ""
echo "💡 提示："
echo "   - 查看日志: docker-compose logs -f mongo-express redis-commander"
echo "   - 访问文档: cat 数据库查看指南.md"
echo ""
