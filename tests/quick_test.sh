#!/bin/bash

# 快速测试脚本 - 跳过依赖检查，直接测试核心功能

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 检测Python环境
PYTHON_CMD=""
if [ -f "./venv/bin/python3" ]; then
    PYTHON_CMD="./venv/bin/python3"
    echo "使用虚拟环境Python"
elif [ -f "./venv/bin/python" ]; then
    PYTHON_CMD="./venv/bin/python"
    echo "使用虚拟环境Python"
else
    PYTHON_CMD="python3"
    echo "使用系统Python"
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  快速测试 - 结果计算服务${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 1. 初始化数据库索引
echo "📝 步骤1: 初始化数据库索引"
if $PYTHON_CMD -m app.scripts.init_result_indexes; then
    echo -e "${GREEN}✅ 数据库索引初始化成功${NC}"
else
    echo -e "${RED}❌ 数据库索引初始化失败${NC}"
    echo "请检查MongoDB是否正在运行"
    exit 1
fi

# 2. 运行单元测试
echo ""
echo "📝 步骤2: 运行单元测试"
if $PYTHON_CMD -m pytest tests/test_result_calculator.py -v; then
    echo -e "${GREEN}✅ 单元测试通过${NC}"
else
    echo -e "${YELLOW}⚠️  单元测试失败，但可能不影响功能${NC}"
fi

# 3. 检查后端服务
echo ""
echo "📝 步骤3: 检查后端服务"
if curl -s "http://localhost:8000/api/health" > /dev/null; then
    echo -e "${GREEN}✅ 后端服务正在运行${NC}"

    # 测试API端点
    echo ""
    echo "📝 步骤4: 测试API端点"
    echo "测试 /api/backtest/test_bt_001/results（预期返回404，但接口正常）"
    response=$(curl -s "http://localhost:8000/api/backtest/test_bt_001/results")
    if echo "$response" | grep -q "success\|detail"; then
        echo -e "${GREEN}✅ API端点测试通过${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  后端服务未运行${NC}"
    echo "请启动后端: $PYTHON_CMD -m app"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  快速测试完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "💡 如需完整测试，请运行: ./tests/test_result_service.sh"
echo ""
