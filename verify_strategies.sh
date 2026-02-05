#!/bin/bash
# 策略接口验证脚本

echo "======================================"
echo "策略管理接口验证"
echo "======================================"
echo ""

# 检查应用是否运行
if ! lsof -i :8000 > /dev/null 2>&1; then
    echo "❌ 应用未在8000端口运行"
    echo "💡 请先启动应用: ./start.sh"
    exit 1
fi

echo "✅ 应用正在运行"
echo ""

# 检查OpenAPI schema
echo "=== 检查OpenAPI Schema ==="
STRATEGY_COUNT=$(curl -s http://localhost:8000/openapi.json 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
paths = [p for p in data.get('paths', {}).keys() if 'strategies' in p and 'backtest' in p]
print(len(paths))
" 2>/dev/null)

if [ "$STRATEGY_COUNT" -eq "4" ]; then
    echo "✅ 策略路由已加载 (4个接口)"
else
    echo "❌ 策略路由未正确加载 (找到 $STRATEGY_COUNT 个接口)"
fi

echo ""
echo "=== 策略接口列表 ==="
curl -s http://localhost:8000/openapi.json 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
paths = [(p, list(data['paths'][p].keys())) for p in data.get('paths', {}).keys() if 'strategies' in p and 'backtest' in p]
for path, methods in sorted(paths):
    print(f'  {\" \".join(methods).upper():6} {path}')
" 2>/dev/null

echo ""
echo "=== 访问 Swagger 文档 ==="
echo "📍 URL: http://localhost:8000/docs"
echo ""
echo "🔐 重要提示:"
echo "   策略接口需要登录认证才能访问"
echo "   请在 Swagger 文档中点击 'Authorize' 按钮登录"
echo ""
echo "📋 默认登录信息:"
echo "   用户名: admin"
echo "   密码: admin123"
echo ""
echo "登录后，在 'backtest-strategies' 标签下可以看到以下接口:"
echo "   1. GET /api/backtest/strategies - 获取策略列表"
echo "   2. GET /api/backtest/strategies/{strategy_id} - 获取策略详情"
echo "   3. GET /api/backtest/strategies/categories - 获取策略分类"
echo "   4. POST /api/backtest/strategies/{strategy_id}/validate-params - 校验参数"
echo ""
echo "======================================"
