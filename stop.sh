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

# 3. 等待进程完全结束并清除Python缓存
echo ""
echo "⏳ [3/4] 等待进程完全结束..."
sleep 3

# 确认进程已停止
REMAINING_BACKEND=$(pgrep -f "python -m app" || true)
REMAINING_FRONTEND=$(pgrep -f "npm run dev" || true)

if [ -n "$REMAINING_BACKEND" ] || [ -n "$REMAINING_FRONTEND" ]; then
    echo "⚠️  发现残留进程，强制停止..."
    pkill -9 -f "python -m app" 2>/dev/null || true
    pkill -9 -f "npm run dev" 2>/dev/null || true
    sleep 2
fi

echo "✅ 所有进程已完全结束"

# 4. 清除Python缓存
echo ""
echo "🧹 [4/4] 清除Python缓存..."

# 统计缓存数量
CACHE_DIRS=$(find "$PROJECT_DIR/app" -type d -name "__pycache__" 2>/dev/null | wc -l)
CACHE_FILES=$(find "$PROJECT_DIR/app" -name "*.pyc" 2>/dev/null | wc -l)

if [ "$CACHE_DIRS" -gt 0 ] || [ "$CACHE_FILES" -gt 0 ]; then
    echo "   发现 $CACHE_DIRS 个缓存目录和 $CACHE_FILES 个缓存文件"

    # 删除缓存目录和文件
    find "$PROJECT_DIR/app" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
    find "$PROJECT_DIR/app" -name "*.pyc" -delete 2>/dev/null

    # 验证清除结果
    REMAINING_DIRS=$(find "$PROJECT_DIR/app" -type d -name "__pycache__" 2>/dev/null | wc -l)
    REMAINING_FILES=$(find "$PROJECT_DIR/app" -name "*.pyc" 2>/dev/null | wc -l)

    if [ "$REMAINING_DIRS" -eq 0 ] && [ "$REMAINING_FILES" -eq 0 ]; then
        echo "✅ Python缓存已彻底清除"
    else
        echo "⚠️  部分缓存未能清除: $REMAINING_DIRS 个目录, $REMAINING_FILES 个文件"
    fi
else
    echo "ℹ️  未发现Python缓存文件"
fi

# 5. 清理端口占用提示
echo ""
echo "🔍 [5/5] 检查端口占用..."
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
echo "   - Python缓存已清除，确保代码修改生效"
echo "   - 数据库服务可能仍在运行（保留数据以便下次快速启动）"
echo "   - 完全停止数据库: docker-compose stop mongodb redis"
echo "   - 重新启动所有服务: ./start.sh"
echo ""
