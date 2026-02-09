#!/bin/bash
# 重启后端服务脚本
# 用途：快速重启后端服务并清除缓存

set -e  # 遇到错误立即退出

PROJECT_DIR="/Users/qiran/LLM_Proj/LS_Proj/zp_ls/TradingAgents-CN"
cd "$PROJECT_DIR"

echo "=================================="
echo "🔄 重启后端服务"
echo "=================================="
echo ""

# 1. 停止后端进程
echo "📛 [1/5] 停止后端进程..."
BACKEND_PID=$(pgrep -f "python -m app" || true)

if [ -n "$BACKEND_PID" ]; then
    echo "   发现运行中的后端进程 (PID: $BACKEND_PID)"
    kill $BACKEND_PID 2>/dev/null || true
    sleep 2

    # 如果还在运行，强制停止
    if pgrep -f "python -m app" > /dev/null 2>&1; then
        echo "   强制停止进程..."
        pkill -9 -f "python -m app" 2>/dev/null || true
        sleep 1
    fi
    echo "   ✅ 后端进程已停止"
else
    echo "   ℹ️  未发现运行中的后端进程"
fi

# 2. 等待端口释放
echo ""
echo "⏳ [2/5] 等待端口释放..."
sleep 2

if lsof -ti:8000 > /dev/null 2>&1; then
    echo "   ⚠️  端口 8000 仍被占用，强制清理..."
    lsof -ti:8000 | xargs kill -9 2>/dev/null || true
    sleep 1
fi
echo "   ✅ 端口已释放"

# 3. 清除Python缓存
echo ""
echo "🧹 [3/5] 清除Python缓存..."

# 统计缓存
CACHE_COUNT=$(find app -type d -name "__pycache__" 2>/dev/null | wc -l)

if [ "$CACHE_COUNT" -gt 0 ]; then
    echo "   发现 $CACHE_COUNT 个缓存目录"

    # 删除缓存
    find app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
    find app -name "*.pyc" -delete 2>/dev/null

    echo "   ✅ Python缓存已清除"
else
    echo "   ℹ️  未发现缓存文件"
fi

# 4. 验证代码修改
echo ""
echo "🔍 [4/5] 验证关键代码修改..."

MISSING_MODIFICATIONS=0

# 检查 backtest_engine.py
if grep -q "🔍 当前用户信息" app/routers/backtest_engine.py; then
    echo "   ✅ backtest_engine.py 代码已更新"
else
    echo "   ❌ backtest_engine.py 代码未找到修改!"
    MISSING_MODIFICATIONS=1
fi

# 检查 auth_db.py
if grep -q '"sub": token_data.sub' app/routers/auth_db.py; then
    echo "   ✅ auth_db.py 代码已更新"
else
    echo "   ❌ auth_db.py 代码未找到修改!"
    MISSING_MODIFICATIONS=1
fi

if [ $MISSING_MODIFICATIONS -eq 1 ]; then
    echo ""
    echo "⚠️  警告: 代码修改缺失，启动后可能仍有问题!"
    echo "   请确认文件已被正确修改"
fi

# 5. 启动后端
echo ""
echo "🚀 [5/5] 启动后端服务..."
echo "   启动时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 在前台启动，方便查看日志
./venv/bin/python3 -m app
