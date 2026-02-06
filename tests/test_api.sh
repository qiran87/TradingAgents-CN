#!/bin/bash
# 简单的API测试脚本，用于调试

echo "=========================================="
echo "   API测试脚本"
echo "=========================================="
echo ""

# 1. 测试健康检查
echo "[1] 测试健康检查..."
curl -s "http://localhost:8000/api/health" | jq .
echo ""

# 2. 测试启动回测
echo "[2] 测试启动回测..."
response=$(curl -s -X POST "http://localhost:8000/api/backtest/start" \
    -H "Content-Type: application/json" \
    -d '{
        "stock_code": "000001.SZ",
        "start_date": "2023-12-01",
        "end_date": "2023-12-05",
        "initial_capital": 100000.0,
        "strategy_id": "dual_ma",
        "strategy_params": {}
    }')

echo "$response" | jq .
echo ""

# 3. 提取backtest_id
backtest_id=$(echo "$response" | jq -r '.data.backtest_id // .data.backtestId // empty')
echo "提取的任务ID: $backtest_id"
echo ""

if [ -z "$backtest_id" ] || [ "$backtest_id" == "null" ]; then
    echo "❌ 无法获取任务ID"
    exit 1
fi

echo "✓ 任务ID获取成功"
echo ""

# 4. 等待3秒
echo "[3] 等待任务创建..."
sleep 3
echo ""

# 5. 测试获取状态
echo "[4] 测试获取状态..."
curl -s "http://localhost:8000/api/backtest/$backtest_id/current-state" | jq .
echo ""

echo "=========================================="
echo "   测试完成"
echo "=========================================="
