#!/bin/bash

##############################################################################
# 交易日历服务验证脚本
# 简洁可靠的版本，避免复杂的eval逻辑
##############################################################################

set -e

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8000"

PASS_COUNT=0
FAIL_COUNT=0

test_pass() {
    echo -e "${GREEN}✓ $1${NC}"
    PASS_COUNT=$((PASS_COUNT + 1))
}

test_fail() {
    echo -e "${RED}✗ $1${NC}"
    echo -e "  期望: $2"
    echo -e "  实际: $3"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

##############################################################################
# 测试1：获取交易日列表
##############################################################################
print_header "测试1：获取交易日列表"

result=$(curl -s "${BASE_URL}/api/backtest/trading-days?start_date=2024-01-01&end_date=2024-01-31")
total=$(echo "$result" | jq '.data.total')
first_day=$(echo "$result" | jq -r '.data.trading_days[0]')

[ "$total" -gt 0 ] && test_pass "1.1 返回交易日列表" || test_fail "1.1 返回交易日列表" "> 0" "$total"
[ "$first_day" = "2024-01-01" ] && test_pass "1.2 第一个交易日正确" || test_fail "1.2 第一个交易日正确" "2024-01-01" "$first_day"

##############################################################################
# 测试2：判断是否为交易日
##############################################################################
print_header "测试2：判断是否为交易日"

result=$(curl -s "${BASE_URL}/api/backtest/trading-days/2024-01-15")
is_trading=$(echo "$result" | jq -r '.data.is_trading_day')
weekday=$(echo "$result" | jq '.data.weekday')

[ "$is_trading" = "true" ] && test_pass "2.1 周一是交易日" || test_fail "2.1 周一是交易日" "true" "$is_trading"
[ "$weekday" -eq 1 ] && test_pass "2.2 星期正确" || test_fail "2.2 星期正确" "1" "$weekday"

##############################################################################
# 测试3：周末不是交易日
##############################################################################
print_header "测试3：周末不是交易日"

weekends=("2024-01-06" "2024-01-07" "2024-01-13" "2024-01-14")

for date in "${weekends[@]}"; do
    result=$(curl -s "${BASE_URL}/api/backtest/trading-days/$date")
    is_trading=$(echo "$result" | jq -r '.data.is_trading_day')
    is_weekend=$(echo "$result" | jq -r '.data.is_weekend')
    
    if [ "$is_trading" = "false" ] && [ "$is_weekend" = "true" ]; then
        test_pass "3.${date//2024-} $date 正确标记为非交易日（周末）"
    else
        test_fail "3.${date//2024-} $date 是非交易日" "is_trading=false, is_weekend=true" "is_trading=$is_trading, is_weekend=$is_weekend"
    fi
done

##############################################################################
# 测试4：获取前一个交易日
##############################################################################
print_header "测试4：获取前一个交易日"

result=$(curl -s "${BASE_URL}/api/backtest/trading-days/2024-01-15/previous")
prev_day=$(echo "$result" | jq -r '.data.previous_trading_day')

[ "$prev_day" = "2024-01-12" ] && test_pass "4.1 前一个交易日正确" || test_fail "4.1 前一个交易日正确" "2024-01-12" "$prev_day"

##############################################################################
# 测试5：获取后一个交易日
##############################################################################
print_header "测试5：获取后一个交易日"

result=$(curl -s "${BASE_URL}/api/backtest/trading-days/2024-01-15/next")
next_day=$(echo "$result" | jq -r '.data.next_trading_day')

[ "$next_day" = "2024-01-16" ] && test_pass "5.1 后一个交易日正确" || test_fail "5.1 后一个交易日正确" "2024-01-16" "$next_day"

##############################################################################
# 测试6：获取交易日历信息
##############################################################################
print_header "测试6：获取交易日历信息"

result=$(curl -s "${BASE_URL}/api/backtest/trading-days/info?start_date=2024-01-01&end_date=2024-12-31")
trading_count=$(echo "$result" | jq '.data.trading_days_count')
percentage=$(echo "$result" | jq '.data.trading_day_percentage')

[ "$trading_count" -gt 0 ] && test_pass "6.1 返回交易日统计" || test_fail "6.1 返回交易日统计" "> 0" "$trading_count"
[ $(echo "$percentage > 60" | bc -l) -eq 1 ] && test_pass "6.2 交易日占比合理" || test_fail "6.2 交易日占比合理" "> 60" "$percentage"

##############################################################################
# 测试总结
##############################################################################
print_header "测试总结"

TOTAL_TESTS=$((PASS_COUNT + FAIL_COUNT))
echo -e "${BLUE}总测试数: $TOTAL_TESTS${NC}"
echo -e "${GREEN}通过数: $PASS_COUNT${NC}"
echo -e "${RED}失败数: $FAIL_COUNT${NC}"

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "\n${GREEN}🎉 所有测试通过！交易日历服务功能正常。${NC}\n"
    exit 0
else
    echo -e "\n${YELLOW}⚠️  有 $FAIL_COUNT 个测试失败${NC}\n"
    exit 1
fi
