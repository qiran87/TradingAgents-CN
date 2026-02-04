#!/bin/bash
# TradingAgents-CN 混合部署启动脚本
# 用途：一键启动所有服务（数据库 + 后端 + 前端）

set -e  # 遇到错误立即退出

PROJECT_DIR="/Users/qiran/LLM_Proj/LS_Proj/zp_ls/TradingAgents-CN"

echo "=================================="
echo "🚀 TradingAgents-CN 启动中..."
echo "=================================="

# 1. 检查 Docker 是否运行
echo "📦 [1/5] 检查 Docker 状态..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker Desktop"
    echo "💡 提示：打开 Applications -> Docker.app"
    exit 1
fi
echo "✅ Docker 运行正常"

# 2. 启动数据库服务
echo ""
echo "🗄️  [2/5] 启动数据库服务 (MongoDB + Redis)..."
cd "$PROJECT_DIR"
docker-compose up -d mongodb redis

# 等待数据库启动
echo "⏳ 等待数据库启动..."
sleep 5

# 检查数据库状态
if docker-compose ps | grep -q "Up"; then
    echo "✅ 数据库启动成功"
else
    echo "❌ 数据库启动失败"
    docker-compose logs mongodb redis
    exit 1
fi

# 3. 检查是否已初始化数据库
echo ""
echo "🔧 [3/5] 检查数据库初始化状态..."
if ! docker exec tradingagents-mongodb mongosh --quiet admin --eval "db.getCollectionNames()" | grep -q "users"; then
    echo "⚠️  数据库未初始化，正在执行初始化..."
    source venv/bin/activate
    python scripts/import_config_and_create_user.py --host
    echo "✅ 数据库初始化完成"
else
    echo "✅ 数据库已初始化"
fi

# 4. 启动后端服务
echo ""
echo "⚙️  [4/5] 启动后端服务..."
echo "💡 后端将在新的终端窗口中启动"
echo "   端口: 8000"
echo "   API 文档: http://localhost:8000/docs"

osascript <<EOF
tell application "Terminal"
    do script "cd '$PROJECT_DIR' && source venv/bin/activate && python -m app"
end tell
EOF

# 等待后端启动
echo "⏳ 等待后端服务启动..."
sleep 8

# 检查后端健康状态
if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✅ 后端服务启动成功"
else
    echo "⚠️  后端服务可能未完全启动，请检查终端日志"
fi

# 5. 启动前端服务
echo ""
echo "🎨 [5/5] 启动前端服务..."
echo "💡 前端将在新的终端窗口中启动"
echo "   端口: 3000 或 5173"
echo "   访问地址: http://localhost:3000"

osascript <<EOF
tell application "Terminal"
    do script "cd '$PROJECT_DIR/frontend' && npm run dev"
end tell
EOF

# 等待前端启动
echo "⏳ 等待前端服务启动..."
sleep 5

echo ""
echo "=================================="
echo "🎉 所有服务启动完成！"
echo "=================================="
echo ""
echo "📍 访问地址："
echo "   前端: http://localhost:3000 (或 5173)"
echo "   后端 API 文档: http://localhost:8000/docs"
echo ""
echo "🔐 默认登录信息："
echo "   用户名: admin"
echo "   密码: admin123"
echo ""
echo "📝 查看日志："
echo "   数据库: docker-compose logs -f mongodb redis"
echo "   后端: 查看后端终端窗口"
echo "   前端: 查看前端终端窗口"
echo ""
echo "⚠️  关闭服务请使用: ./stop.sh"
echo ""
