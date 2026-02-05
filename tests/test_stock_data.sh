#!/bin/bash

###############################################################################
# 股票数据服务测试脚本
#
# 功能：
# 1. 后端API接口测试（4个接口）
# 2. 数据完整性验证
# 3. 错误处理测试
#
# 使用方法：
# chmod +x tests/test_stock_data.sh
# ./tests/test_stock_data.sh
#
# 注意事项：
# - 需要先启动后端服务（./venv/bin/python3 -m app）
# - 需要安装 jq 工具（用于JSON格式化）：brew install jq 或 apt-get install jq
#
###############################################################################

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
BASE_URL="http://localhost:8000"
API_PREFIX="/api/backtest/stock"

# 测试结果统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

###############################################################################
# 工具函数
###############################################################################

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

test_pass() {
    echo -e "${GREEN}✓ $1${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
}

test_fail() {
    echo -e "${RED}✗ $1${NC}"
    echo -e "  期望: $2"
    echo -e "  实际: $3"
    FAILED_TESTS=$((FAILED_TESTS + 1))
}

###############################################################################
# 测试1：API接口测试
###############################################################################

print_header "测试1：股票搜索接口"

result=$(curl -s "${BASE_URL}${API_PREFIX}/search?keyword=000001&limit=5")
success=$(echo "$result" | jq -r '.success')
total=$(echo "$result" | jq -r '.data.total')

[ "$success" == "true" ] && test_pass "1.1 搜索接口返回成功" || test_fail "1.1 搜索接口返回成功" "true" "$success"
[ "$total" -gt 0 ] && test_pass "1.2 返回搜索结果" || test_fail "1.2 返回搜索结果" "> 0" "$total"

TOTAL_TESTS=$((TOTAL_TESTS + 2))

###############################################################################
# 测试2：股票信息接口
###############################################################################

print_header "测试2：股票信息接口"

result=$(curl -s "${BASE_URL}${API_PREFIX}/info?stock_code=000001.SZ")
success=$(echo "$result" | jq -r '.success')
stock_name=$(echo "$result" | jq -r '.data.stock_name')

[ "$success" == "true" ] && test_pass "2.1 股票信息接口返回成功" || test_fail "2.1 股票信息接口返回成功" "true" "$success"
[ "$stock_name" == "平安银行" ] && test_pass "2.2 股票名称正确" || test_fail "2.2 股票名称正确" "平安银行" "$stock_name"

TOTAL_TESTS=$((TOTAL_TESTS + 2))

###############################################################################
# 测试3：数据可用性接口
###############################################################################

print_header "测试3：数据可用性接口"

result=$(curl -s "${BASE_URL}${API_PREFIX}/quotes/check-availability?stock_code=000001.SZ&start_date=2024-01-01&end_date=2024-01-31")
success=$(echo "$result" | jq -r '.success')
coverage=$(echo "$result" | jq -r '.data.coverage')

[ "$success" == "true" ] && test_pass "3.1 数据可用性接口返回成功" || test_fail "3.1 数据可用性接口返回成功" "true" "$success"
[ "$coverage" != "null" ] && test_pass "3.2 返回覆盖率信息" || test_fail "3.2 返回覆盖率信息" "非null" "$coverage"

TOTAL_TESTS=$((TOTAL_TESTS + 2))

###############################################################################
# 测试4：行情数据接口（预期返回404）
###############################################################################

print_header "测试4：行情数据接口"

result=$(curl -s "${BASE_URL}${API_PREFIX}/quotes?stock_code=000001.SZ&start_date=2024-01-01&end_date=2024-01-05")
detail=$(echo "$result" | jq -r '.detail')

# 预期返回404错误，说明错误处理正确
[ "$detail" != "null" ] && test_pass "4.1 行情接口错误处理正确" || test_fail "4.1 行情接口错误处理正确" "返回错误信息" "$detail"

TOTAL_TESTS=$((TOTAL_TESTS + 1))

###############################################################################
# 测试5：搜索功能测试
###############################################################################

print_header "测试5：搜索功能测试"

# 测试按代码搜索
result=$(curl -s "${BASE_URL}${API_PREFIX}/search?keyword=000001")
count1=$(echo "$result" | jq -r '.data.total')
[ "$count1" -gt 0 ] && test_pass "5.1 按代码搜索成功" || test_fail "5.1 按代码搜索成功" "> 0" "$count1"

# 测试按名称搜索（使用URL编码）
result=$(curl -s "${BASE_URL}${API_PREFIX}/search?keyword=%E5%B9%B3%E5%AE%89")
count2=$(echo "$result" | jq -r '.data.total // 0' 2>/dev/null || echo "0")
[ "$count2" -gt 0 ] && test_pass "5.2 按名称搜索成功" || test_fail "5.2 按名称搜索成功" "> 0" "$count2"

TOTAL_TESTS=$((TOTAL_TESTS + 2))

###############################################################################
# 测试总结
###############################################################################

print_header "测试总结"

TOTAL_TESTS=$((TOTAL_TESTS))
echo -e "${BLUE}总测试数: $TOTAL_TESTS${NC}"
echo -e "${GREEN}通过数: $PASSED_TESTS${NC}"
echo -e "${RED}失败数: $FAILED_TESTS${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}🎉 所有测试通过！股票数据服务功能正常。${NC}\n"
    exit 0
else
    echo -e "\n${YELLOW}⚠️  有 $FAILED_TESTS 个测试失败${NC}\n"
    exit 1
fi
