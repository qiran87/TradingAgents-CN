#!/bin/bash

# P2-3: Excel导出格式调整测试脚本
# 测试导出功能已调整为3个标准工作表

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

print_step "P2-3: Excel导出格式调整测试（3个标准工作表）"

# ============================================================================
# 后端代码结构测试
# ============================================================================
print_step "1. 后端代码结构测试"

# 1.1 检查导出服务类存在
print_info "测试1.1: 检查ExcelExporter类存在"
if grep -q "class ExcelExporter" "$PROJECT_DIR/app/services/export_service.py"; then
    record_result "ExcelExporter类" "PASS" "ExcelExporter类已定义"
else
    record_result "ExcelExporter类" "FAIL" "ExcelExporter类不存在"
fi

# 1.2 检查export_backtest_results方法更新为3表格式
print_info "测试1.2: 检查export_backtest_results调用3个标准工作表创建方法"
if grep -q "self._create_parameters_sheet" "$PROJECT_DIR/app/services/export_service.py" && \
   grep -q "self._create_core_results_sheet" "$PROJECT_DIR/app/services/export_service.py" && \
   grep -q "self._create_trades_sheet" "$PROJECT_DIR/app/services/export_service.py"; then
    record_result "3表格式调用" "PASS" "export_backtest_results调用3个标准工作表方法"
else
    record_result "3表格式调用" "FAIL" "export_backtest_results未调用3个标准工作表方法"
fi

# 1.3 检查不再调用旧的4表方法
print_info "测试1.3: 检查不再调用旧的详细指标和资金曲线工作表"
if ! grep -q "_create_metrics_sheet(wb, results)" "$PROJECT_DIR/app/services/export_service.py" && \
   ! grep -q "_create_equity_curve_sheet(wb, equity_curve)" "$PROJECT_DIR/app/services/export_service.py"; then
    record_result "旧方法移除" "PASS" "不再调用旧的4表格式方法"
else
    record_result "旧方法移除" "FAIL" "仍然调用旧的4表格式方法"
fi

# ============================================================================
# 新工作表创建方法测试
# ============================================================================
print_step "2. 新工作表创建方法测试"

# 2.1 检查_create_parameters_sheet方法存在
print_info "测试2.1: 检查_create_parameters_sheet方法存在"
if grep -q "def _create_parameters_sheet" "$PROJECT_DIR/app/services/export_service.py"; then
    record_result "回测参数表方法" "PASS" "_create_parameters_sheet方法已定义"
else
    record_result "回测参数表方法" "FAIL" "_create_parameters_sheet方法不存在"
fi

# 2.2 检查_create_core_results_sheet方法存在
print_info "测试2.2: 检查_create_core_results_sheet方法存在"
if grep -q "def _create_core_results_sheet" "$PROJECT_DIR/app/services/export_service.py"; then
    record_result "核心结果表方法" "PASS" "_create_core_results_sheet方法已定义"
else
    record_result "核心结果表方法" "FAIL" "_create_core_results_sheet方法不存在"
fi

# 2.3 检查_create_trades_sheet方法保留
print_info "测试2.3: 检查_create_trades_sheet方法保留"
if grep -q "def _create_trades_sheet" "$PROJECT_DIR/app/services/export_service.py"; then
    record_result "交易明细表方法" "PASS" "_create_trades_sheet方法已保留"
else
    record_result "交易明细表方法" "FAIL" "_create_trades_sheet方法不存在"
fi

# ============================================================================
# 工作表名称测试
# ============================================================================
print_step "3. 工作表名称测试"

# 3.1 检查使用"回测参数"作为工作表名称
print_info "测试3.1: 检查使用'回测参数'作为工作表名称"
if grep -q 'wb.create_sheet("回测参数"' "$PROJECT_DIR/app/services/export_service.py"; then
    record_result "回测参数表名称" "PASS" "使用'回测参数'作为工作表名称"
else
    record_result "回测参数表名称" "FAIL" "未使用'回测参数'作为工作表名称"
fi

# 3.2 检查使用"核心结果"作为工作表名称
print_info "测试3.2: 检查使用'核心结果'作为工作表名称"
if grep -q 'wb.create_sheet("核心结果"' "$PROJECT_DIR/app/services/export_service.py"; then
    record_result "核心结果表名称" "PASS" "使用'核心结果'作为工作表名称"
else
    record_result "核心结果表名称" "FAIL" "未使用'核心结果'作为工作表名称"
fi

# 3.3 检查使用"交易明细"作为工作表名称（或保留原名称）
print_info "测试3.3: 检查使用'交易明细'作为工作表名称"
if grep -q 'wb.create_sheet("交易明细"' "$PROJECT_DIR/app/services/export_service.py"; then
    record_result "交易明细表名称" "PASS" "使用'交易明细'作为工作表名称"
else
    # 检查旧版本是否使用"交易记录"
    if grep -q 'wb.create_sheet("交易记录"' "$PROJECT_DIR/app/services/export_service.py"; then
        record_result "交易明细表名称" "PASS" "使用'交易记录'作为工作表名称（旧版本）"
    else
        record_result "交易明细表名称" "FAIL" "未找到交易明细工作表"
    fi
fi

# ============================================================================
# 工作表内容测试
# ============================================================================
print_step "4. 工作表内容测试"

# 4.1 检查"回测参数"表包含基本信息
print_info "测试4.1: 检查回测参数表包含基本信息（记录名称、描述、标签）"
if grep -A 100 "def _create_parameters_sheet" "$PROJECT_DIR/app/services/export_service.py" | grep -q "记录名称" && \
   grep -A 100 "def _create_parameters_sheet" "$PROJECT_DIR/app/services/export_service.py" | grep -q "基本信息"; then
    record_result "回测参数-基本信息" "PASS" "回测参数表包含基本信息部分"
else
    record_result "回测参数-基本信息" "FAIL" "回测参数表缺少基本信息部分"
fi

# 4.2 检查"回测参数"表包含回测参数配置
print_info "测试4.2: 检查回测参数表包含回测参数配置（股票代码、日期范围、初始资金、策略）"
if grep -A 150 "def _create_parameters_sheet" "$PROJECT_DIR/app/services/export_service.py" | grep -q "回测参数配置" && \
   grep -A 150 "def _create_parameters_sheet" "$PROJECT_DIR/app/services/export_service.py" | grep -q "股票代码"; then
    record_result "回测参数-参数配置" "PASS" "回测参数表包含参数配置部分"
else
    record_result "回测参数-参数配置" "FAIL" "回测参数表缺少参数配置部分"
fi

# 4.3 检查"核心结果"表包含关键指标摘要
print_info "测试4.3: 检查核心结果表包含关键指标摘要"
if grep -A 50 "def _create_core_results_sheet" "$PROJECT_DIR/app/services/export_service.py" | grep -q "关键指标摘要"; then
    record_result "核心结果-关键指标" "PASS" "核心结果表包含关键指标摘要部分"
else
    record_result "核心结果-关键指标" "FAIL" "核心结果表缺少关键指标摘要部分"
fi

# 4.4 检查"核心结果"表包含收益指标
print_info "测试4.4: 检查核心结果表包含收益指标"
if grep -A 100 "def _create_core_results_sheet" "$PROJECT_DIR/app/services/export_service.py" | grep -q "收益指标"; then
    record_result "核心结果-收益指标" "PASS" "核心结果表包含收益指标部分"
else
    record_result "核心结果-收益指标" "FAIL" "核心结果表缺少收益指标部分"
fi

# 4.5 检查"核心结果"表包含风险指标
print_info "测试4.5: 检查核心结果表包含风险指标"
if grep -A 150 "def _create_core_results_sheet" "$PROJECT_DIR/app/services/export_service.py" | grep -q "风险指标"; then
    record_result "核心结果-风险指标" "PASS" "核心结果表包含风险指标部分"
else
    record_result "核心结果-风险指标" "FAIL" "核心结果表缺少风险指标部分"
fi

# 4.6 检查"核心结果"表包含交易统计
print_info "测试4.6: 检查核心结果表包含交易统计"
if grep -A 200 "def _create_core_results_sheet" "$PROJECT_DIR/app/services/export_service.py" | grep -q "交易统计"; then
    record_result "核心结果-交易统计" "PASS" "核心结果表包含交易统计部分"
else
    record_result "核心结果-交易统计" "FAIL" "核心结果表缺少交易统计部分"
fi

# ============================================================================
# 代码质量测试
# ============================================================================
print_step "5. 代码质量测试"

# 5.1 检查方法包含文档字符串
print_info "测试5.1: 检查新方法包含文档字符串"
if grep -A 10 "def _create_parameters_sheet" "$PROJECT_DIR/app/services/export_service.py" | grep -q "P2-3" && \
   grep -A 10 "def _create_core_results_sheet" "$PROJECT_DIR/app/services/export_service.py" | grep -q "P2-3"; then
    record_result "方法文档字符串" "PASS" "新方法包含P2-3标记的文档字符串"
else
    record_result "方法文档字符串" "FAIL" "新方法缺少文档字符串"
fi

# 5.2 检查工作表顺序正确（回测参数、核心结果、交易明细）
print_info "测试5.2: 检查工作表创建顺序正确"
if grep -q 'create_sheet("回测参数".*0' "$PROJECT_DIR/app/services/export_service.py" && \
   grep -q 'create_sheet("核心结果".*1' "$PROJECT_DIR/app/services/export_service.py" && \
   grep -q 'create_sheet("交易明细".*2' "$PROJECT_DIR/app/services/export_service.py"; then
    record_result "工作表顺序" "PASS" "工作表创建顺序正确（0, 1, 2）"
else
    record_result "工作表顺序" "FAIL" "工作表创建顺序不正确"
fi

# 5.3 检查日志消息更新
print_info "测试5.3: 检查导出日志消息提及3表格式"
if grep -q "标准3表格式" "$PROJECT_DIR/app/services/export_service.py" || \
   grep -q "3个标准工作表" "$PROJECT_DIR/app/services/export_service.py"; then
    record_result "日志消息更新" "PASS" "日志消息提及3表格式"
else
    record_result "日志消息更新" "WARN" "日志消息未提及3表格式（非必需）"
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
    echo "  1. ✅ 后端代码结构正确"
    echo "  2. ✅ 新工作表创建方法存在"
    echo "  3. ✅ 工作表名称符合标准"
    echo "  4. ✅ 工作表内容完整"
    echo "  5. ✅ 代码质量良好"
    echo ""
    print_success "P2-3 Excel导出格式调整测试全部通过！"
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
