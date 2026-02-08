#!/bin/bash

# 集成测试脚本：回测页面组件集成测试
# 测试 TradingDayRangePicker 和 StockSelector 在 BacktestControlPanel 中的集成

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

# 项目目录
PROJECT_DIR="/Users/qiran/LLM_Proj/LS_Proj/zp_ls/TradingAgents-CN"
FRONTEND_DIR="$PROJECT_DIR/frontend"

print_step "回测页面组件集成测试"

# ============================================================================
# 1. 文件存在性测试
# ============================================================================
print_step "1. 文件存在性测试"

# 1.1 检查TradingDayRangePicker组件
print_info "测试1.1: 检查TradingDayRangePicker组件文件"
if [ -f "$FRONTEND_DIR/src/components/TradingDayRangePicker.vue" ]; then
    record_result "TradingDayRangePicker组件文件" "PASS" "组件文件已创建"
else
    record_result "TradingDayRangePicker组件文件" "FAIL" "组件文件不存在"
fi

# 1.2 检查StockSelector组件
print_info "测试1.2: 检查StockSelector组件文件"
if [ -f "$FRONTEND_DIR/src/components/StockSelector.vue" ]; then
    record_result "StockSelector组件文件" "PASS" "组件文件已存在"
else
    record_result "StockSelector组件文件" "FAIL" "组件文件不存在"
fi

# 1.3 检查BacktestControlPanel页面
print_info "测试1.3: 检查BacktestControlPanel页面文件"
if [ -f "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue" ]; then
    record_result "BacktestControlPanel页面文件" "PASS" "页面文件已存在"
else
    record_result "BacktestControlPanel页面文件" "FAIL" "页面文件不存在"
fi

# ============================================================================
# 2. 组件导入测试
# ============================================================================
print_step "2. 组件导入测试"

# 2.1 检查BacktestControlPanel导入TradingDayRangePicker
print_info "测试2.1: 检查BacktestControlPanel导入TradingDayRangePicker"
if grep -q "import TradingDayRangePicker from '@/components/TradingDayRangePicker.vue'" "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue"; then
    record_result "导入TradingDayRangePicker" "PASS" "BacktestControlPanel正确导入TradingDayRangePicker"
else
    record_result "导入TradingDayRangePicker" "FAIL" "未找到导入语句"
fi

# 2.2 检查BacktestControlPanel导入StockSelector
print_info "测试2.2: 检查BacktestControlPanel导入StockSelector"
if grep -q "import StockSelector from '@/components/StockSelector.vue'" "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue"; then
    record_result "导入StockSelector" "PASS" "BacktestControlPanel正确导入StockSelector"
else
    record_result "导入StockSelector" "FAIL" "未找到导入语句"
fi

# ============================================================================
# 3. 组件使用测试
# ============================================================================
print_step "3. 组件使用测试"

# 3.1 检查使用TradingDayRangePicker组件
print_info "测试3.1: 检查TradingDayRangePicker组件使用"
if grep -q "<TradingDayRangePicker" "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue"; then
    record_result "使用TradingDayRangePicker" "PASS" "TradingDayRangePicker组件已使用"
else
    record_result "使用TradingDayRangePicker" "FAIL" "未使用TradingDayRangePicker组件"
fi

# 3.2 检查使用StockSelector组件
print_info "测试3.2: 检查StockSelector组件使用"
if grep -q "<StockSelector" "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue"; then
    record_result "使用StockSelector" "PASS" "StockSelector组件已使用"
else
    record_result "使用StockSelector" "FAIL" "未使用StockSelector组件"
fi

# 3.3 检查TradingDayRangePicker绑定
print_info "测试3.3: 检查TradingDayRangePicker数据绑定"
if grep -q 'v-model:start-date="form.start_date"' "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue" && \
   grep -q 'v-model:end-date="form.end_date"' "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue"; then
    record_result "TradingDayRangePicker绑定" "PASS" "数据绑定正确"
else
    record_result "TradingDayRangePicker绑定" "FAIL" "数据绑定不完整"
fi

# 3.4 检查StockSelector绑定
print_info "测试3.4: 检查StockSelector数据绑定"
if grep -q 'v-model="form.stock_code"' "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue"; then
    record_result "StockSelector绑定" "PASS" "数据绑定正确"
else
    record_result "StockSelector绑定" "FAIL" "数据绑定不正确"
fi

# ============================================================================
# 4. 事件处理测试
# ============================================================================
print_step "4. 事件处理测试"

# 4.1 检查handleTradingDaysChange方法
print_info "测试4.1: 检查handleTradingDaysChange方法"
if grep -q "function handleTradingDaysChange" "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue" || \
   grep -q "const handleTradingDaysChange" "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue"; then
    record_result "handleTradingDaysChange方法" "PASS" "方法已定义"
else
    record_result "handleTradingDaysChange方法" "FAIL" "方法未定义"
fi

# 4.2 检查@trading-days-change事件绑定
print_info "测试4.2: 检查@trading-days-change事件绑定"
if grep -q '@trading-days-change="handleTradingDaysChange"' "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue"; then
    record_result "trading-days-change事件" "PASS" "事件绑定正确"
else
    record_result "trading-days-change事件" "FAIL" "事件未绑定"
fi

# ============================================================================
# 5. 数据模型测试
# ============================================================================
print_step "5. 数据模型测试"

# 5.1 检查form包含start_date和end_date
print_info "测试5.1: 检查form包含start_date和end_date字段"
if grep -q "start_date:" "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue" && \
   grep -q "end_date:" "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue"; then
    record_result "form日期字段" "PASS" "form包含start_date和end_date"
else
    record_result "form日期字段" "FAIL" "form缺少日期字段"
fi

# 5.2 检查移除了dateRange ref
print_info "测试5.2: 检查已移除dateRange ref"
if ! grep -q "const dateRange = ref" "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue"; then
    record_result "移除dateRange" "PASS" "已移除dateRange ref"
else
    record_result "移除dateRange" "FAIL" "仍存在dateRange ref"
fi

# 5.3 检查添加了tradingDaysCount ref
print_info "测试5.3: 检查添加tradingDaysCount ref"
if grep -q "const tradingDaysCount = ref" "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue"; then
    record_result "tradingDaysCount ref" "PASS" "已添加tradingDaysCount"
else
    record_result "tradingDaysCount ref" "FAIL" "未添加tradingDaysCount"
fi

# ============================================================================
# 6. 移除旧代码测试
# ============================================================================
print_step "6. 移除旧代码测试"

# 6.1 检查移除disabledDate方法
print_info "测试6.1: 检查移除disabledDate方法"
if ! grep -q "function disabledDate" "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue"; then
    record_result "移除disabledDate" "PASS" "已移除disabledDate方法"
else
    record_result "移除disabledDate" "FAIL" "仍存在disabledDate方法"
fi

# 6.2 检查移除handleSearchStock方法
print_info "测试6.2: 检查移除handleSearchStock方法"
if ! grep -q "function handleSearchStock" "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue"; then
    record_result "移除handleSearchStock" "PASS" "已移除handleSearchStock方法"
else
    record_result "移除handleSearchStock" "FAIL" "仍存在handleSearchStock方法"
fi

# 6.3 检查移除dateRangeDays computed
print_info "测试6.3: 检查移除dateRangeDays computed"
if ! grep -q "const dateRangeDays = computed" "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue"; then
    record_result "移除dateRangeDays" "PASS" "已移除dateRangeDays computed"
else
    record_result "移除dateRangeDays" "FAIL" "仍存在dateRangeDays computed"
fi

# ============================================================================
# 7. 表单验证测试
# ============================================================================
print_step "7. 表单验证测试"

# 7.1 检查移除dateRange验证规则
print_info "测试7.1: 检查移除dateRange验证规则"
if ! grep -q "dateRange:.*required" "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue"; then
    record_result "移除dateRange验证" "PASS" "已移除dateRange验证规则"
else
    record_result "移除dateRange验证" "FAIL" "仍存在dateRange验证规则"
fi

# 7.2 检查canStartBacktest使用新字段
print_info "测试7.2: 检查canStartBacktest使用start_date和end_date"
if grep -q "form.value.start_date &&" "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue" && \
   grep -q "form.value.end_date &&" "$FRONTEND_DIR/src/views/Backtest/BacktestControlPanel.vue"; then
    record_result "canStartBacktest更新" "PASS" "canStartBacktest使用新字段"
else
    record_result "canStartBacktest更新" "FAIL" "canStartBacktest未更新"
fi

# ============================================================================
# 8. 单元测试文件测试
# ============================================================================
print_step "8. 单元测试文件测试"

# 8.1 检查TradingDayRangePicker单元测试
print_info "测试8.1: 检查TradingDayRangePicker单元测试文件"
if [ -f "$FRONTEND_DIR/tests/unit/TradingDayRangePicker.test.ts" ]; then
    record_result "TradingDayRangePicker单元测试" "PASS" "单元测试文件已创建"
else
    record_result "TradingDayRangePicker单元测试" "FAIL" "单元测试文件不存在"
fi

# 8.2 检查单元测试文件内容
print_info "测试8.2: 检查单元测试文件内容"
if [ -f "$FRONTEND_DIR/tests/unit/TradingDayRangePicker.test.ts" ]; then
    test_count=$(grep -c "it(" "$FRONTEND_DIR/tests/unit/TradingDayRangePicker.test.ts" || true)
    if [ "$test_count" -ge 5 ]; then
        record_result "单元测试用例数" "PASS" "包含${test_count}个测试用例"
    else
        record_result "单元测试用例数" "WARN" "仅包含${test_count}个测试用例（建议至少5个）"
    fi
fi

# ============================================================================
# 9. TradingDayRangePicker组件功能测试
# ============================================================================
print_step "9. TradingDayRangePicker组件功能测试"

# 9.1 检查组件Props定义
print_info "测试9.1: 检查TradingDayRangePicker Props定义"
if grep -q "interface Props" "$FRONTEND_DIR/src/components/TradingDayRangePicker.vue" && \
   grep -q "startDate.*string" "$FRONTEND_DIR/src/components/TradingDayRangePicker.vue" && \
   grep -q "endDate.*string" "$FRONTEND_DIR/src/components/TradingDayRangePicker.vue"; then
    record_result "Props定义" "PASS" "Props正确定义"
else
    record_result "Props定义" "FAIL" "Props定义不完整"
fi

# 9.2 检查组件Emits定义
print_info "测试9.2: 检查TradingDayRangePicker Emits定义"
if grep -q "interface Emits" "$FRONTEND_DIR/src/components/TradingDayRangePicker.vue" && \
   grep -q "update:startDate" "$FRONTEND_DIR/src/components/TradingDayRangePicker.vue" && \
   grep -q "update:endDate" "$FRONTEND_DIR/src/components/TradingDayRangePicker.vue" && \
   grep -q "trading-days-change" "$FRONTEND_DIR/src/components/TradingDayRangePicker.vue"; then
    record_result "Emits定义" "PASS" "Emits正确定义"
else
    record_result "Emits定义" "FAIL" "Emits定义不完整"
fi

# 9.3 检查组件使用TradingCalendarStore
print_info "测试9.3: 检查使用TradingCalendarStore"
if grep -q "useTradingCalendarStore" "$FRONTEND_DIR/src/components/TradingDayRangePicker.vue" && \
   grep -q "getTradingDaysInRange" "$FRONTEND_DIR/src/components/TradingDayRangePicker.vue"; then
    record_result "使用TradingCalendarStore" "PASS" "正确使用TradingCalendarStore"
else
    record_result "使用TradingCalendarStore" "FAIL" "未正确使用TradingCalendarStore"
fi

# 9.4 检查快捷选项功能
print_info "测试9.4: 检查快捷选项功能"
if grep -q "quickOptions" "$FRONTEND_DIR/src/components/TradingDayRangePicker.vue" && \
   grep -q "selectQuickOption" "$FRONTEND_DIR/src/components/TradingDayRangePicker.vue"; then
    record_result "快捷选项功能" "PASS" "快捷选项功能已实现"
else
    record_result "快捷选项功能" "FAIL" "快捷选项功能未实现"
fi

# ============================================================================
# 10. 代码质量测试
# ============================================================================
print_step "10. 代码质量测试"

# 10.1 检查TradingDayRangePicker组件注释
print_info "测试10.1: 检查组件注释完整性"
comment_count=$(grep -c "^/\*\*\|^\s*\*" "$FRONTEND_DIR/src/components/TradingDayRangePicker.vue" || true)
if [ "$comment_count" -ge 5 ]; then
    record_result "组件注释" "PASS" "组件包含${comment_count}行注释"
else
    record_result "组件注释" "WARN" "组件注释较少（${comment_count}行）"
fi

# 10.2 检查样式定义
print_info "测试10.2: 检查组件样式定义"
if grep -q "<style scoped" "$FRONTEND_DIR/src/components/TradingDayRangePicker.vue"; then
    record_result "样式定义" "PASS" "组件包含scoped样式"
else
    record_result "样式定义" "FAIL" "组件缺少样式定义"
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
    echo "  1. ✅ 文件存在性验证"
    echo "  2. ✅ 组件导入检查"
    echo "  3. ✅ 组件使用验证"
    echo "  4. ✅ 事件处理验证"
    echo "  5. ✅ 数据模型检查"
    echo "  6. ✅ 旧代码移除验证"
    echo "  7. ✅ 表单验证更新"
    echo "  8. ✅ 单元测试文件检查"
    echo "  9. ✅ TradingDayRangePicker功能测试"
    echo " 10. ✅ 代码质量检查"
    echo ""
    print_success "回测页面组件集成测试全部通过！"
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
