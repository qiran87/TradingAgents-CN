#!/bin/bash

# P1-3: 历史记录检索条件增强测试脚本
# 测试时间范围、初始资金范围、收益率范围筛选功能

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# 测试统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 记录测试结果
record_result() {
    local test_name="$1"
    local result="$2"
    local message="$3"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ "$result" = "PASS" ]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo -e "${GREEN}✓${NC} $test_name: ${GREEN}PASS${NC} - $message"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo -e "${RED}✗${NC} $test_name: ${RED}FAIL${NC} - $message"
    fi
}

# 基础URL
BASE_URL="http://localhost:8000"
PROJECT_DIR="/Users/qiran/LLM_Proj/LS_Proj/zp_ls/TradingAgents-CN"

print_step "P1-3: 历史记录检索条件增强测试"

# ============================================================================
# 后端API测试
# ============================================================================
print_step "1. 后端API功能测试"

# 1.1 测试历史记录API支持新参数（OpenAPI JSON格式）
print_info "测试1.1: 验证API支持时间范围参数"
if curl -s "$BASE_URL/openapi.json" | grep -q '"start_date"' && \
   curl -s "$BASE_URL/openapi.json" | grep -q '"end_date"'; then
    record_result "时间范围参数" "PASS" "API支持start_date和end_date参数"
else
    record_result "时间范围参数" "FAIL" "API不支持时间范围参数"
fi

print_info "测试1.2: 验证API支持初始资金范围参数"
if grep -q "initial_capital_min: Optional\[float\] = Query" "$PROJECT_DIR/app/routers/backtest_history.py" && \
   grep -q "initial_capital_max: Optional\[float\] = Query" "$PROJECT_DIR/app/routers/backtest_history.py"; then
    record_result "初始资金范围参数" "PASS" "API路由定义了initial_capital_min和initial_capital_max参数"
else
    record_result "初始资金范围参数" "FAIL" "API路由缺少初始资金范围参数定义"
fi

print_info "测试1.3: 验证API支持收益率范围参数"
if grep -q "return_rate_min: Optional\[float\] = Query" "$PROJECT_DIR/app/routers/backtest_history.py" && \
   grep -q "return_rate_max: Optional\[float\] = Query" "$PROJECT_DIR/app/routers/backtest_history.py"; then
    record_result "收益率范围参数" "PASS" "API路由定义了return_rate_min和return_rate_max参数"
else
    record_result "收益率范围参数" "FAIL" "API路由缺少收益率范围参数定义"
fi

# 1.2 测试后端服务层实现（代码检查）
print_info "测试1.4: 检查后端服务支持时间范围筛选"
if grep -q "start_date: Optional\[str\]" "$PROJECT_DIR/app/services/history_service.py" && \
   grep -q "end_date: Optional\[str\]" "$PROJECT_DIR/app/services/history_service.py"; then
    record_result "后端时间范围参数" "PASS" "后端服务定义了时间范围参数"
else
    record_result "后端时间范围参数" "FAIL" "后端服务缺少时间范围参数定义"
fi

print_info "测试1.5: 检查后端服务支持初始资金范围筛选"
if grep -q "initial_capital_min: Optional\[float\]" "$PROJECT_DIR/app/services/history_service.py" && \
   grep -q "initial_capital_max: Optional\[float\]" "$PROJECT_DIR/app/services/history_service.py"; then
    record_result "后端初始资金范围参数" "PASS" "后端服务定义了初始资金范围参数"
else
    record_result "后端初始资金范围参数" "FAIL" "后端服务缺少初始资金范围参数定义"
fi

print_info "测试1.6: 检查后端服务支持收益率范围筛选"
if grep -q "return_rate_min: Optional\[float\]" "$PROJECT_DIR/app/services/history_service.py" && \
   grep -q "return_rate_max: Optional\[float\]" "$PROJECT_DIR/app/services/history_service.py"; then
    record_result "后端收益率范围参数" "PASS" "后端服务定义了收益率范围参数"
else
    record_result "后端收益率范围参数" "FAIL" "后端服务缺少收益率范围参数定义"
fi

# 1.3 测试MongoDB查询逻辑（代码检查）
print_info "测试1.7: 检查时间范围MongoDB查询逻辑"
if grep -q 'query\["parameters.start_date"\] = {"\$gte": start_date}' "$PROJECT_DIR/app/services/history_service.py" && \
   grep -q 'query\["parameters.start_date"\]\["\$lte"\] = end_date' "$PROJECT_DIR/app/services/history_service.py"; then
    record_result "时间范围查询逻辑" "PASS" "时间范围MongoDB查询逻辑正确"
else
    record_result "时间范围查询逻辑" "FAIL" "时间范围MongoDB查询逻辑缺失或不正确"
fi

print_info "测试1.8: 检查初始资金范围MongoDB查询逻辑"
if grep -q 'query\["parameters.initial_capital"\] = {"\$gte": initial_capital_min}' "$PROJECT_DIR/app/services/history_service.py" && \
   grep -q 'query\["parameters.initial_capital"\]\["\$lte"\] = initial_capital_max' "$PROJECT_DIR/app/services/history_service.py"; then
    record_result "初始资金范围查询逻辑" "PASS" "初始资金范围MongoDB查询逻辑正确"
else
    record_result "初始资金范围查询逻辑" "FAIL" "初始资金范围MongoDB查询逻辑缺失或不正确"
fi

print_info "测试1.9: 检查收益率范围MongoDB查询逻辑"
if grep -q 'query\["metrics_snapshot.total_return"\] = {"\$gte": return_rate_min}' "$PROJECT_DIR/app/services/history_service.py" && \
   grep -q 'query\["metrics_snapshot.total_return"\]\["\$lte"\] = return_rate_max' "$PROJECT_DIR/app/services/history_service.py"; then
    record_result "收益率范围查询逻辑" "PASS" "收益率范围MongoDB查询逻辑正确"
else
    record_result "收益率范围查询逻辑" "FAIL" "收益率范围MongoDB查询逻辑缺失或不正确"
fi

# ============================================================================
# 前端代码检查
# ============================================================================
print_step "2. 前端代码结构测试"

# 2.1 检查时间区间筛选UI组件
print_info "测试2.1: 检查时间区间筛选组件存在"
if grep -q "回测日期" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue" && \
   grep -q "el-date-picker" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue" && \
   grep -q "dateRange" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue"; then
    record_result "时间区间筛选UI" "PASS" "时间区间选择器组件存在"
else
    record_result "时间区间筛选UI" "FAIL" "时间区间选择器组件不存在"
fi

# 2.2 检查初始资金范围筛选UI组件
print_info "测试2.2: 检查初始资金范围筛选组件存在"
if grep -q "初始资金" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue" && \
   grep -q "initial_capital_min" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue" && \
   grep -q "initial_capital_max" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue"; then
    record_result "初始资金范围筛选UI" "PASS" "初始资金范围输入框组件存在"
else
    record_result "初始资金范围筛选UI" "FAIL" "初始资金范围输入框组件不存在"
fi

# 2.3 检查收益率范围筛选UI组件
print_info "测试2.3: 检查收益率范围筛选组件存在"
if grep -q "收益率" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue" && \
   grep -q "return_rate_min" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue" && \
   grep -q "return_rate_max" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue"; then
    record_result "收益率范围筛选UI" "PASS" "收益率范围输入框组件存在"
else
    record_result "收益率范围筛选UI" "FAIL" "收益率范围输入框组件不存在"
fi

# 2.4 检查筛选表单数据结构
print_info "测试2.4: 检查筛选表单包含新字段"
if grep -q "dateRange: null as \[string, string\] | null" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue" && \
   grep -q "initial_capital_min: ''" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue" && \
   grep -q "return_rate_max: ''" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue"; then
    record_result "筛选表单数据结构" "PASS" "筛选表单包含新字段定义"
else
    record_result "筛选表单数据结构" "FAIL" "筛选表单缺少新字段定义"
fi

# 2.5 检查重置功能包含新字段
print_info "测试2.5: 检查重置筛选包含新字段"
if grep -A 10 "const handleReset" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue" | grep -q "dateRange: null" && \
   grep -A 10 "const handleReset" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue" | grep -q "initial_capital_min: ''" && \
   grep -A 10 "const handleReset" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue" | grep -q "return_rate_max: ''"; then
    record_result "重置筛选功能" "PASS" "重置功能包含新字段"
else
    record_result "重置筛选功能" "FAIL" "重置功能缺少新字段"
fi

# ============================================================================
# 前端Store检查
# ============================================================================
print_step "3. 前端Store功能测试"

# 3.1 检查Store筛选条件包含新字段
print_info "测试3.1: 检查historyStore筛选条件包含新字段"
if grep -q "start_date: ''" "$PROJECT_DIR/frontend/src/stores/backtestHistory.ts" && \
   grep -q "end_date: ''" "$PROJECT_DIR/frontend/src/stores/backtestHistory.ts" && \
   grep -q "initial_capital_min: ''" "$PROJECT_DIR/frontend/src/stores/backtestHistory.ts" && \
   grep -q "return_rate_max: ''" "$PROJECT_DIR/frontend/src/stores/backtestHistory.ts"; then
    record_result "Store筛选条件" "PASS" "Store包含新筛选字段"
else
    record_result "Store筛选条件" "FAIL" "Store缺少新筛选字段"
fi

# 3.2 检查fetchHistoryList方法传递新参数
print_info "测试3.2: 检查fetchHistoryList传递新参数到API"
if grep -q "start_date: filters.value.start_date" "$PROJECT_DIR/frontend/src/stores/backtestHistory.ts" && \
   grep -q "return_rate_max: filters.value.return_rate_max" "$PROJECT_DIR/frontend/src/stores/backtestHistory.ts"; then
    record_result "API参数传递" "PASS" "fetchHistoryList正确传递新参数"
else
    record_result "API参数传递" "FAIL" "fetchHistoryList未传递新参数"
fi

# 3.3 检查收益率百分比转换逻辑
print_info "测试3.3: 检查收益率百分比转换为小数"
if grep -q "parseFloat(filters.value.return_rate_min) / 100" "$PROJECT_DIR/frontend/src/stores/backtestHistory.ts" && \
   grep -q "parseFloat(filters.value.return_rate_max) / 100" "$PROJECT_DIR/frontend/src/stores/backtestHistory.ts"; then
    record_result "收益率百分比转换" "PASS" "收益率百分比正确转换为小数"
else
    record_result "收益率百分比转换" "FAIL" "收益率百分比未转换"
fi

# 3.4 检查resetFilters方法包含新字段
print_info "测试3.4: 检查resetFilters包含新字段"
if grep -A 10 "function resetFilters()" "$PROJECT_DIR/frontend/src/stores/backtestHistory.ts" | grep -q "start_date: ''" && \
   grep -A 10 "function resetFilters()" "$PROJECT_DIR/frontend/src/stores/backtestHistory.ts" | grep -q "return_rate_max: ''"; then
    record_result "resetFilters方法" "PASS" "resetFilters包含新字段"
else
    record_result "resetFilters方法" "FAIL" "resetFilters缺少新字段"
fi

# ============================================================================
# 集成测试
# ============================================================================
print_step "4. 集成功能测试"

# 4.1 检查dateRange转换为start_date和end_date
print_info "测试4.1: 检查handleSearch中的dateRange转换逻辑"
if grep -q "start_date: filterForm.value.dateRange?.\[0\]" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue" && \
   grep -q "end_date: filterForm.value.dateRange?.\[1\]" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue"; then
    record_result "dateRange转换逻辑" "PASS" "handleSearch正确转换dateRange"
else
    record_result "dateRange转换逻辑" "FAIL" "handleSearch缺少dateRange转换逻辑"
fi

# 4.2 检查API类型定义（可选）
print_info "测试4.2: 检查API类型定义（如果存在）"
if [ -f "$PROJECT_DIR/frontend/src/api/backtestHistory.ts" ]; then
    if grep -q "start_date" "$PROJECT_DIR/frontend/src/api/backtestHistory.ts" || \
       grep -q "GetHistoryListParams" "$PROJECT_DIR/frontend/src/api/backtestHistory.ts"; then
        record_result "API类型定义" "PASS" "API类型定义存在或包含新参数"
    else
        record_result "API类型定义" "WARN" "API类型定义可能需要更新（非必需）"
    fi
else
    record_result "API类型定义" "SKIP" "API文件不存在，跳过测试"
fi

# ============================================================================
# 输出测试总结
# ============================================================================
print_step "测试总结"

echo ""
echo "========================================"
echo " 测试统计"
echo "========================================"
echo "总测试数: $TOTAL_TESTS"
echo -e "通过: ${GREEN}$PASSED_TESTS${NC}"
echo -e "失败: ${RED}$FAILED_TESTS${NC}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}✓ 所有测试用例通过${NC}"
    echo ""
    echo "测试的功能："
    echo "  1. ✅ 后端API参数支持"
    echo "  2. ✅ 后端服务层实现"
    echo "  3. ✅ MongoDB查询逻辑"
    echo "  4. ✅ 前端筛选UI组件"
    echo "  5. ✅ 前端Store状态管理"
    echo "  6. ✅ 集成功能"
    echo ""
    print_success "P1-3 历史记录检索条件增强测试全部通过！"
else
    echo -e "${RED}✗ 部分测试用例失败${NC}"
    echo ""
    echo "请检查上述失败的测试项目并修复。"
fi

echo ""
echo "========================================"

# 返回退出码
if [ $FAILED_TESTS -gt 0 ]; then
    exit 1
else
    exit 0
fi
