#!/bin/bash
# TradingAgents-CN 混合部署停止脚本
# 用途：一键停止所有服务

PROJECT_DIR="/Users/qiran/LLM_Proj/LS_Proj/zp_ls/TradingAgents-CN"

echo "=================================="
echo "🛑 TradingAgents-CN 停止中..."
echo "=================================="

# 1. 停止前端和后端进程
echo ""
echo "🔍 [1/3] 查找并停止应用进程..."

# 查找并停止前端进程
FRONTEND_PIDS=$(pgrep -f "npm run dev" || true)
if [ -n "$FRONTEND_PIDS" ]; then
    echo "🎨 停止前端服务 (PID: $FRONTEND_PIDS)..."
    kill $FRONTEND_PIDS 2>/dev/null || true
    sleep 2
    # 强制停止（如果还在运行）
    pkill -9 -f "npm run dev" 2>/dev/null || true
    echo "✅ 前端服务已停止"
else
    echo "ℹ️  未发现运行中的前端服务"
fi

# 查找并停止后端进程
BACKEND_PIDS=$(pgrep -f "python -m app" || true)
if [ -n "$BACKEND_PIDS" ]; then
    echo "⚙️  停止后端服务 (PID: $BACKEND_PIDS)..."
    kill $BACKEND_PIDS 2>/dev/null || true
    sleep 2
    # 强制停止（如果还在运行）
    pkill -9 -f "python -m app" 2>/dev/null || true
    echo "✅ 后端服务已停止"
else
    echo "ℹ️  未发现运行中的后端服务"
fi

# 2. 停止数据库服务
echo ""
echo "🗄️  [2/3] 停止数据库服务..."
cd "$PROJECT_DIR"

# 询问是否停止数据库
read -p "是否同时停止数据库服务 (MongoDB + Redis)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "⏹️  停止 MongoDB 和 Redis..."
    docker-compose stop mongodb redis
    echo "✅ 数据库服务已停止"
else
    echo "ℹ️  数据库服务保持运行"
    echo "   如需停止，请运行: docker-compose stop mongodb redis"
fi

# 3. 清理端口占用提示
echo ""
echo "🔍 [3/3] 检查端口占用..."
PORTS_IN_USE=""

if lsof -ti:8000 > /dev/null 2>&1; then
    PORTS_IN_USE="$PORTS_IN_USE 8000(后端)"
fi

if lsof -ti:3000 > /dev/null 2>&1 || lsof -ti:5173 > /dev/null 2>&1; then
    PORTS_IN_USE="$PORTS_IN_USE 3000/5173(前端)"
fi

if [ -n "$PORTS_IN_USE" ]; then
    echo "⚠️  以下端口仍被占用:$PORTS_IN_USE"
    echo "   如需清理，请运行: lsof -ti:<端口> | xargs kill -9"
else
    echo "✅ 所有端口已释放"
fi

echo ""
echo "=================================="
echo "✅ 停止完成！"
echo "=================================="
echo ""
echo "💡 提示："
echo "   - 数据库服务可能仍在运行（保留数据以便下次快速启动）"
echo "   - 完全停止数据库: docker-compose stop mongodb redis"
echo "   - 重新启动所有服务: ./start.sh"
echo ""
