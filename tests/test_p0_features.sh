#!/bin/bash

# 前端功能测试脚本
# 用于验证7项P0功能的正确性

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

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 进入前端目录
cd "$PROJECT_ROOT/frontend"

print_step "前端功能测试 - 7项P0功能验证"

# 1. 测试导航配置
print_step "测试1: 导航名称修改"
print_info "检查路由配置文件..."

if grep -q "title: '股票回测'" src/router/index.ts; then
    record_result "一级导航名称" "PASS" "路由标题为'股票回测'"
else
    record_result "一级导航名称" "FAIL" "路由标题不是'股票回测'"
fi

if grep -q "title: '执行股票回测'" src/router/index.ts; then
    record_result "二级菜单-执行股票回测" "PASS" "菜单名称正确"
else
    record_result "二级菜单-执行股票回测" "FAIL" "菜单名称不正确"
fi

if grep -q "title: '回测策略列表'" src/router/index.ts; then
    record_result "二级菜单-策略列表" "PASS" "菜单名称正确"
else
    record_result "二级菜单-策略列表" "FAIL" "菜单名称不正确"
fi

if grep -q "title: '历史回测汇总'" src/router/index.ts; then
    record_result "二级菜单-历史记录" "PASS" "菜单名称正确"
else
    record_result "二级菜单-历史记录" "FAIL" "菜单名称不正确"
fi

# 2. 测试页面布局
print_step "测试2: 页面布局改造"
print_info "检查组件布局结构..."

if grep -q "page-header-fixed" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "顶部固定区域" "PASS" "包含page-header-fixed类"
else
    record_result "顶部固定区域" "FAIL" "缺少page-header-fixed类"
fi

if grep -q "left-sidebar" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "左侧辅助栏" "PASS" "包含left-sidebar类"
else
    record_result "左侧辅助栏" "FAIL" "缺少left-sidebar类"
fi

if grep -q "right-main" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "右侧核心操作区" "PASS" "包含right-main类"
else
    record_result "右侧核心操作区" "FAIL" "缺少right-main类"
fi

if grep -q "page-footer-fixed" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "底部固定区域" "PASS" "包含page-footer-fixed类"
else
    record_result "底部固定区域" "FAIL" "缺少page-footer-fixed类"
fi

# 3. 测试操作步骤指引
print_step "测试3: 操作步骤指引组件"
print_info "检查步骤指引组件..."

if grep -q "操作步骤指引" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "步骤指引标题" "PASS" "包含'操作步骤指引'文本"
else
    record_result "步骤指引标题" "FAIL" "缺少'操作步骤指引'文本"
fi

if grep -q "回测参数设置" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "步骤1文本" "PASS" "包含'回测参数设置'"
else
    record_result "步骤1文本" "FAIL" "缺少'回测参数设置'"
fi

if grep -q "策略选择" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "步骤2文本" "PASS" "包含'策略选择'"
else
    record_result "步骤2文本" "FAIL" "缺少'策略选择'"
fi

if grep -q "当前状态提示" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "状态提示组件" "PASS" "包含'当前状态提示'文本"
else
    record_result "状态提示组件" "FAIL" "缺少'当前状态提示'文本"
fi

# 4. 测试重置参数按钮
print_step "测试4: 重置参数按钮"
print_info "检查重置参数功能..."

if grep -q "重置所有参数" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "重置按钮文本" "PASS" "包含'重置所有参数'文本"
else
    record_result "重置按钮文本" "FAIL" "缺少'重置所有参数'文本"
fi

if grep -q "handleResetParams" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "重置处理函数" "PASS" "包含handleResetParams函数"
else
    record_result "重置处理函数" "FAIL" "缺少handleResetParams函数"
fi

if grep -q "stock_code: '000001.SZ'" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "默认股票代码" "PASS" "默认为000001.SZ"
else
    record_result "默认股票代码" "FAIL" "默认值不正确"
fi

# 5. 测试参数确认弹窗
print_step "测试5: 参数确认弹窗"
print_info "检查参数确认弹窗..."

if grep -q "showParamsConfirmDialog" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "确认弹窗变量" "PASS" "包含showParamsConfirmDialog变量"
else
    record_result "确认弹窗变量" "FAIL" "缺少showParamsConfirmDialog变量"
fi

if grep -q "确认回测参数" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "确认弹窗标题" "PASS" "弹窗标题为'确认回测参数'"
else
    record_result "确认弹窗标题" "FAIL" "弹窗标题不正确"
fi

if grep -q "confirmStartBacktest" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "确认回测函数" "PASS" "包含confirmStartBacktest函数"
else
    record_result "确认回测函数" "FAIL" "缺少confirmStartBacktest函数"
fi

# 6. 测试股票最小购买量字段
print_step "测试6: 股票最小购买量字段"
print_info "检查最小购买量字段..."

if grep -q "股票最小购买量" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "最小购买量标签" "PASS" "包含'股票最小购买量'标签"
else
    record_result "最小购买量标签" "FAIL" "缺少'股票最小购买量'标签"
fi

if grep -q "min_purchase:" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "最小购买量字段" "PASS" "包含min_purchase字段"
else
    record_result "最小购买量字段" "FAIL" "缺少min_purchase字段"
fi

if grep -q "必须为100的倍数" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "100倍数提示" "PASS" "包含'必须为100的倍数'提示"
else
    record_result "100倍数提示" "FAIL" "缺少'必须为100的倍数'提示"
fi

if grep -q "100-10000股" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "范围提示" "PASS" "包含'100-10000股'范围提示"
else
    record_result "范围提示" "FAIL" "缺少'100-10000股'范围提示"
fi

# 7. 测试帮助文档入口
print_step "测试7: 帮助文档入口"
print_info "检查帮助文档功能..."

if grep -q "帮助文档" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "帮助文档按钮" "PASS" "包含'帮助文档'文本"
else
    record_result "帮助文档按钮" "FAIL" "缺少'帮助文档'文本"
fi

if grep -q "showHelpDialog" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "帮助弹窗变量" "PASS" "包含showHelpDialog变量"
else
    record_result "帮助弹窗变量" "FAIL" "缺少showHelpDialog变量"
fi

if grep -q "股票回测功能使用指南" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "帮助文档标题" "PASS" "帮助文档标题正确"
else
    record_result "帮助文档标题" "FAIL" "帮助文档标题不正确"
fi

if grep -q "Ctrl+S 保存参数，Ctrl+R 开始回测" src/views/Backtest/BacktestControlPanel.vue; then
    record_result "快捷键提示" "PASS" "包含快捷键提示"
else
    record_result "快捷键提示" "FAIL" "缺少快捷键提示"
fi

# 运行单元测试
print_step "运行Vitest单元测试"

if command -v npx &> /dev/null; then
    print_info "运行单元测试..."

    if npx vitest run --reporter=verbose 2>&1 | tee tests-output.log; then
        print_success "单元测试全部通过"
    else
        print_error "单元测试存在失败"
        cat tests-output.log
    fi
else
    print_warning "npx未找到，跳过单元测试"
fi

# 输出测试总结
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
    echo "  1. ✅ 导航名称修改"
    echo "  2. ✅ 页面布局改造"
    echo "  3. ✅ 操作步骤指引组件"
    echo "  4. ✅ 重置参数按钮"
    echo "  5. ✅ 参数确认弹窗"
    echo "  6. ✅ 股票最小购买量字段"
    echo "  7. ✅ 帮助文档入口"
    echo ""
    print_success "所有7项P0功能测试通过！"
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
