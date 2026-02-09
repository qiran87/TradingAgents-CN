#!/bin/bash
# 测试回测启动API

echo "========================================="
echo "测试回测启动API"
echo "========================================="

# 准备测试数据
CURRENT_DATE=$(date +%Y-%m-%d)
START_DATE="2024-11-01"
END_DATE="2024-11-05"
STOCK_CODE="000001.SZ"

echo "股票代码: $STOCK_CODE"
echo "日期范围: $START_DATE 至 $END_DATE"
echo ""

# 调用回测启动API
echo "发送POST请求到 /api/backtest/start ..."
RESPONSE=$(curl -s -X POST "http://localhost:8000/api/backtest/start" \
  -H "Content-Type: application/json" \
  -d "{
    \"stock_code\": \"$STOCK_CODE\",
    \"start_date\": \"$START_DATE\",
    \"end_date\": \"$END_DATE\",
    \"initial_capital\": 100000.0,
    \"strategy_id\": \"dual_ma\",
    \"strategy_params\": {
      \"short_window\": 5,
      \"long_window\": 20
    }
  }")

echo ""
echo "========================================="
echo "API响应:"
echo "========================================="
echo "$RESPONSE" | python3 -m json.tool

# 提取backtest_id
BACKTEST_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('data', {}).get('backtest_id', 'N/A'))" 2>/dev/null)

echo ""
echo "========================================="
echo "回测任务ID: $BACKTEST_ID"
echo "========================================="

if [ "$BACKTEST_ID" != "N/A" ]; then
    echo ""
    echo "等待3秒后查询任务状态..."
    sleep 3

    echo ""
    echo "查询任务状态..."
    curl -s "http://localhost:8000/api/backtest/status?backtest_id=$BACKTEST_ID" | python3 -m json.tool

    echo ""
    echo "再等待5秒后查询任务状态..."
    sleep 5

    echo ""
    echo "最终任务状态:"
    curl -s "http://localhost:8000/api/backtest/status?backtest_id=$BACKTEST_ID" | python3 -m json.tool
else
    echo ""
    echo "❌ 获取backtest_id失败"
fi

echo ""
echo "========================================="
echo "测试完成"
echo "========================================="
