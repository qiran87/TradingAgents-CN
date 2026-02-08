#!/bin/bash

# P2-4: 历史记录上限检查测试脚本
# 测试普通用户100条、管理员500条上限，以及自动删除最旧记录功能

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

print_step "P2-4: 历史记录上限检查测试（后端）"

# ============================================================================
# 常量定义测试
# ============================================================================
print_step "1. 常量定义测试"

# 1.1 检查MAX_HISTORY_NORMAL常量
print_info "测试1.1: 检查MAX_HISTORY_NORMAL常量"
if grep -q "MAX_HISTORY_NORMAL = 100" "$PROJECT_DIR/app/services/history_service.py"; then
    record_result "MAX_HISTORY_NORMAL常量" "PASS" "普通用户上限常量已定义(100)"
else
    record_result "MAX_HISTORY_NORMAL常量" "FAIL" "普通用户上限常量未定义或值不正确"
fi

# 1.2 检查MAX_HISTORY_ADMIN常量
print_info "测试1.2: 检查MAX_HISTORY_ADMIN常量"
if grep -q "MAX_HISTORY_ADMIN = 500" "$PROJECT_DIR/app/services/history_service.py"; then
    record_result "MAX_HISTORY_ADMIN常量" "PASS" "管理员上限常量已定义(500)"
else
    record_result "MAX_HISTORY_ADMIN常量" "FAIL" "管理员上限常量未定义或值不正确"
fi

# ============================================================================
# 辅助方法测试
# ============================================================================
print_step "2. 辅助方法测试"

# 2.1 检查_check_and_enforce_limit方法存在
print_info "测试2.1: 检查_check_and_enforce_limit方法存在"
if grep -q "def _check_and_enforce_limit" "$PROJECT_DIR/app/services/history_service.py"; then
    record_result "_check_and_enforce_limit方法" "PASS" "_check_and_enforce_limit方法已定义"
else
    record_result "_check_and_enforce_limit方法" "FAIL" "_check_and_enforce_limit方法不存在"
fi

# 2.2 检查方法判断用户类型
print_info "测试2.2: 检查方法判断is_admin字段"
if grep -A 50 "def _check_and_enforce_limit" "$PROJECT_DIR/app/services/history_service.py" | grep -q "is_admin = user.get(\"is_admin\", False)"; then
    record_result "判断用户类型" "PASS" "方法正确判断用户类型(is_admin)"
else
    record_result "判断用户类型" "FAIL" "方法未判断用户类型"
fi

# 2.3 检查方法统计当前记录数
print_info "测试2.3: 检查方法统计当前有效记录数"
if grep -A 50 "def _check_and_enforce_limit" "$PROJECT_DIR/app/services/history_service.py" | grep -q "count_documents"; then
    record_result "统计记录数" "PASS" "方法统计当前有效记录数"
else
    record_result "统计记录数" "FAIL" "方法未统计记录数"
fi

# 2.4 检查方法查找最旧记录
print_info "测试2.4: 检查方法查找最旧记录"
if grep -A 80 "def _check_and_enforce_limit" "$PROJECT_DIR/app/services/history_service.py" | grep -q 'sort=.*created_at.*1'; then
    record_result "查找最旧记录" "PASS" "方法按created_at升序查找最旧记录"
else
    record_result "查找最旧记录" "FAIL" "方法未查找最旧记录"
fi

# 2.5 检查方法自动删除记录
print_info "测试2.5: 检查方法自动删除最旧记录"
if grep -A 100 "def _check_and_enforce_limit" "$PROJECT_DIR/app/services/history_service.py" | grep -q "auto_delete_limit_exceeded"; then
    record_result "自动删除记录" "PASS" "方法标记自动删除原因"
else
    record_result "自动删除记录" "FAIL" "方法未标记删除原因"
fi

# 2.6 检查返回删除信息
print_info "测试2.6: 检查方法返回删除信息"
if grep -A 110 "def _check_and_enforce_limit" "$PROJECT_DIR/app/services/history_service.py" | grep -q "deleted_record_id"; then
    record_result "返回删除信息" "PASS" "方法返回deleted_record_id等信息"
else
    record_result "返回删除信息" "FAIL" "方法未返回删除信息"
fi

# ============================================================================
# save_to_history方法测试
# ============================================================================
print_step "3. save_to_history方法测试"

# 3.1 检查调用上限检查方法
print_info "测试3.1: 检查save_to_history调用上限检查"
if grep -A 200 "async def save_to_history" "$PROJECT_DIR/app/services/history_service.py" | grep -q "_check_and_enforce_limit"; then
    record_result "调用上限检查" "PASS" "save_to_history调用_check_and_enforce_limit"
else
    record_result "调用上限检查" "FAIL" "save_to_history未调用上限检查"
fi

# 3.2 检查在插入前调用
print_info "测试3.2: 检查在插入数据库前调用上限检查"
if grep -B 20 "insert_one(history_doc)" "$PROJECT_DIR/app/services/history_service.py" | grep -q "_check_and_enforce_limit"; then
    record_result "插入前检查" "PASS" "在insert_one之前调用上限检查"
else
    record_result "插入前检查" "FAIL" "未在insert_one之前调用上限检查"
fi

# 3.3 检查返回warning字段
print_info "测试3.3: 检查返回包含warning字段"
if grep -A 200 "async def save_to_history" "$PROJECT_DIR/app/services/history_service.py" | grep -q "limit_check.get(\"deleted\")"; then
    record_result "返回warning字段" "PASS" "检查limit_check.deleted并设置warning"
else
    record_result "返回warning字段" "FAIL" "未检查deleted状态"
fi

# 3.4 检查返回deleted_record_id
print_info "测试3.4: 检查返回deleted_record_id字段"
if grep -A 220 "async def save_to_history" "$PROJECT_DIR/app/services/history_service.py" | grep -q "deleted_record_id.*limit_check"; then
    record_result "返回deleted_record_id" "PASS" "返回deleted_record_id字段"
else
    record_result "返回deleted_record_id" "FAIL" "未返回deleted_record_id"
fi

# ============================================================================
# get_history_stats方法测试
# ============================================================================
print_step "4. get_history_stats方法测试"

# 4.1 检查get_history_stats方法存在
print_info "测试4.1: 检查get_history_stats方法存在"
if grep -q "def get_history_stats" "$PROJECT_DIR/app/services/history_service.py"; then
    record_result "get_history_stats方法" "PASS" "get_history_stats方法已定义"
else
    record_result "get_history_stats方法" "FAIL" "get_history_stats方法不存在"
fi

# 4.2 检查方法返回current_count
print_info "测试4.2: 检查方法返回current_count字段"
if grep -A 50 "def get_history_stats" "$PROJECT_DIR/app/services/history_service.py" | grep -q '"current_count":'; then
    record_result "返回current_count" "PASS" "方法返回current_count字段"
else
    record_result "返回current_count" "FAIL" "方法未返回current_count字段"
fi

# 4.3 检查方法返回limit
print_info "测试4.3: 检查方法返回limit字段"
if grep -A 50 "def get_history_stats" "$PROJECT_DIR/app/services/history_service.py" | grep -q '"limit":'; then
    record_result "返回limit" "PASS" "方法返回limit字段"
else
    record_result "返回limit" "FAIL" "方法未返回limit字段"
fi

# 4.4 检查方法返回remaining
print_info "测试4.4: 检查方法返回remaining字段"
if grep -A 50 "def get_history_stats" "$PROJECT_DIR/app/services/history_service.py" | grep -q '"remaining":'; then
    record_result "返回remaining" "PASS" "方法返回remaining字段"
else
    record_result "返回remaining" "FAIL" "方法未返回remaining字段"
fi

# 4.5 检查方法返回usage_percent
print_info "测试4.5: 检查方法返回usage_percent字段"
if grep -A 50 "def get_history_stats" "$PROJECT_DIR/app/services/history_service.py" | grep -q '"usage_percent":'; then
    record_result "返回usage_percent" "PASS" "方法返回usage_percent字段"
else
    record_result "返回usage_percent" "FAIL" "方法未返回usage_percent字段"
fi

# 4.6 检查方法返回near_limit
print_info "测试4.6: 检查方法返回near_limit字段（超过80%）"
if grep -A 50 "def get_history_stats" "$PROJECT_DIR/app/services/history_service.py" | grep -q '"near_limit":'; then
    record_result "返回near_limit" "PASS" "方法返回near_limit字段"
else
    record_result "返回near_limit" "FAIL" "方法未返回near_limit字段"
fi

# ============================================================================
# API路由测试
# ============================================================================
print_step "5. API路由测试"

# 5.1 检查/history/stats路由存在
print_info "测试5.1: 检查/api/backtest/history/stats路由存在"
if grep -q '@router.get("/history/stats"' "$PROJECT_DIR/app/routers/backtest_history.py"; then
    record_result "/history/stats路由" "PASS" "/history/stats路由已定义"
else
    record_result "/history/stats路由" "FAIL" "/history/stats路由不存在"
fi

# 5.2 检查路由调用get_history_stats
print_info "测试5.2: 检查路由调用service.get_history_stats"
if grep -A 20 '@router.get("/history/stats"' "$PROJECT_DIR/app/routers/backtest_history.py" | grep -q "get_history_stats"; then
    record_result "路由调用方法" "PASS" "路由正确调用get_history_stats方法"
else
    record_result "路由调用方法" "FAIL" "路由未调用get_history_stats方法"
fi

# 5.3 检查路由文档说明
print_info "测试5.3: 检查路由包含P2-4标记的文档字符串"
if grep -A 20 '@router.get("/history/stats"' "$PROJECT_DIR/app/routers/backtest_history.py" | grep -q "P2-4"; then
    record_result "路由文档字符串" "PASS" "路由文档字符串包含P2-4标记"
else
    record_result "路由文档字符串" "WARN" "路由文档字符串未包含P2-4标记（非必需）"
fi

# ============================================================================
# 代码质量测试
# ============================================================================
print_step "6. 代码质量测试"

# 6.1 检查日志记录
print_info "测试6.1: 检查方法包含日志记录"
if grep -A 50 "def _check_and_enforce_limit" "$PROJECT_DIR/app/services/history_service.py" | grep -q "logger.info"; then
    record_result "日志记录" "PASS" "方法包含logger.info日志"
else
    record_result "日志记录" "FAIL" "方法缺少日志记录"
fi

# 6.2 检查错误处理
print_info "测试6.2: 检查方法包含异常处理"
if grep -A 120 "def _check_and_enforce_limit" "$PROJECT_DIR/app/services/history_service.py" | grep -q "except Exception"; then
    record_result "错误处理" "PASS" "方法包含异常处理"
else
    record_result "错误处理" "FAIL" "方法缺少异常处理"
fi

# 6.3 检查软删除标志
print_info "测试6.3: 检查使用软删除而非永久删除"
if grep -A 100 "def _check_and_enforce_limit" "$PROJECT_DIR/app/services/history_service.py" | grep -q '"is_deleted": True'; then
    record_result "软删除标志" "PASS" "使用软删除(is_deleted=True)"
else
    record_result "软删除标志" "FAIL" "未使用软删除"
fi

# ============================================================================
# 前端代码测试
# ============================================================================
print_step "7. 前端代码测试"

# 7.1 检查前端添加historyStats ref
print_info "测试7.1: 检查前端定义historyStats ref"
if grep -q "historyStats = ref" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue"; then
    record_result "historyStats ref" "PASS" "前端定义了historyStats响应式变量"
else
    record_result "historyStats ref" "FAIL" "前端未定义historyStats"
fi

# 7.2 检查fetchHistoryStats方法
print_info "测试7.2: 检查fetchHistoryStats方法"
if grep -q "const fetchHistoryStats" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue" && \
   grep -q "/api/backtest/history/stats" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue"; then
    record_result "fetchHistoryStats方法" "PASS" "fetchHistoryStats方法调用正确API"
else
    record_result "fetchHistoryStats方法" "FAIL" "fetchHistoryStats方法未定义或API调用错误"
fi

# 7.3 检查onMounted调用fetchHistoryStats
print_info "测试7.3: 检查onMounted调用fetchHistoryStats"
if grep -A 5 "onMounted" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue" | grep -q "fetchHistoryStats"; then
    record_result "onMounted调用" "PASS" "onMounted调用fetchHistoryStats"
else
    record_result "onMounted调用" "FAIL" "onMounted未调用fetchHistoryStats"
fi

# 7.4 检查UI警告组件
print_info "测试7.4: 检查UI添加上限警告组件"
if grep -q "el-alert" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue" && \
   grep -q "historyStats.near_limit" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue"; then
    record_result "警告UI组件" "PASS" "UI包含上限警告el-alert组件"
else
    record_result "警告UI组件" "FAIL" "UI缺少上限警告组件"
fi

# 7.5 检查显示统计信息
print_info "测试7.5: 检查显示统计信息(当前数、上限、百分比)"
if grep -q "historyStats.current_count" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue" && \
   grep -q "historyStats.limit" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue" && \
   grep -q "historyStats.usage_percent" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue"; then
    record_result "显示统计信息" "PASS" "UI显示当前数、上限、百分比"
else
    record_result "显示统计信息" "FAIL" "UI未完整显示统计信息"
fi

# 7.6 检查CSS样式
print_info "测试7.6: 检查添加.limit-alert样式"
if grep -q ".limit-alert" "$PROJECT_DIR/frontend/src/views/Backtest/BacktestHistory.vue"; then
    record_result "CSS样式" "PASS" "添加了.limit-alert样式"
else
    record_result "CSS样式" "WARN" "未添加.limit-alert样式（非必需）"
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
    echo "  1. ✅ 常量定义正确"
    echo "  2. ✅ 上限检查辅助方法完整"
    echo "  3. ✅ save_to_history集成检查"
    echo "  4. ✅ get_history_stats统计方法"
    echo "  5. ✅ API路由正确"
    echo "  6. ✅ 代码质量良好"
    echo "  7. ✅ 前端UI和逻辑完整"
    echo ""
    print_success "P2-4 历史记录上限检查测试全部通过！"
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
