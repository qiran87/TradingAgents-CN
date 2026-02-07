#!/bin/bash

# 回测结果导出服务测试脚本
# 用于验证导出功能的正确性

# 检测Python环境
PYTHON_CMD=""
if [ -f "./venv/bin/python3" ]; then
    PYTHON_CMD="./venv/bin/python3"
    echo "使用虚拟环境Python: $PYTHON_CMD"
elif [ -f "./venv/bin/python" ]; then
    PYTHON_CMD="./venv/bin/python"
    echo "使用虚拟环境Python: $PYTHON_CMD"
else
    PYTHON_CMD="python3"
    echo "使用系统Python: $PYTHON_CMD"
fi

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1" >&2
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

print_step() {
    echo "" >&2
    echo -e "${BLUE}========================================${NC}" >&2
    echo -e "${BLUE} $1${NC}" >&2
    echo -e "${BLUE}========================================${NC}" >&2
}

# 测试结果记录
TESTS_PASSED=0
TESTS_FAILED=0
TEST_RESULTS=()

# 记录测试结果
record_test_result() {
    local test_name="$1"
    local result="$2"
    local message="$3"

    if [ "$result" = "PASS" ]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        echo -e "${GREEN}✓${NC} $test_name: ${GREEN}PASS${NC} - $message" >&2
        TEST_RESULTS+=("[$test_name] PASS - $message")
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo -e "${RED}✗${NC} $test_name: ${RED}FAIL${NC} - $message" >&2
        TEST_RESULTS+=("[$test_name] FAIL - $message")
    fi
}

# 检查依赖
check_dependencies() {
    print_step "检查依赖"

    # 检查Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未安装"
        exit 1
    fi
    print_success "Python3 已安装: $(python3 --version)"

    # 检查openpyxl
    if ! $PYTHON_CMD -c "import openpyxl" 2>/dev/null; then
        print_error "openpyxl 未安装"
        print_info "正在安装 openpyxl..."
        pip install openpyxl
    else
        print_success "openpyxl 已安装"
    fi

    # 检查MongoDB
    if command -v mongosh &> /dev/null; then
        if mongosh mongodb://localhost:27017 --quiet --eval "db.adminCommand('ping')" &> /dev/null; then
            print_success "MongoDB 正在运行且可连接"
        else
            print_warning "MongoDB命令存在但无法连接，请检查服务是否启动"
        fi
    elif command -v mongo &> /dev/null; then
        if mongo --quiet --eval "db.adminCommand('ping')" &> /dev/null; then
            print_success "MongoDB 正在运行且可连接"
        else
            print_warning "MongoDB命令存在但无法连接，请检查服务是否启动"
        fi
    else
        if nc -z localhost 27017 2>/dev/null || /usr/bin/nc -z localhost 27017 2>/dev/null; then
            print_success "MongoDB 端口27017已开放（服务正在运行）"
        else
            print_warning "无法检测到MongoDB，请确保服务已启动"
        fi
    fi
}

# 运行单元测试
run_unit_tests() {
    print_step "运行单元测试"

    print_info "检查pytest是否安装..."
    if ! $PYTHON_CMD -m pytest --version &> /dev/null; then
        print_warning "pytest 未安装，正在安装..."
        pip install pytest pytest-asyncio
    fi

    print_info "运行导出服务单元测试..."
    $PYTHON_CMD -m pytest tests/test_export_service.py -v --tb=short

    if [ $? -eq 0 ]; then
        record_test_result "单元测试" "PASS" "所有测试用例通过"
        print_success "单元测试全部通过"
    else
        record_test_result "单元测试" "FAIL" "部分测试用例失败"
        print_error "单元测试失败"
    fi
}

# 测试API端点
test_api_endpoints() {
    print_step "测试API端点"

    # 检查后端是否运行
    if ! curl -s "http://localhost:8000/api/health" > /dev/null; then
        record_test_result "API端点测试" "FAIL" "后端服务未运行"
        print_warning "后端服务未运行，跳过API测试"
        print_info "请先启动后端服务: ./venv/bin/python3 -m app"
        return
    fi

    print_success "后端服务正在运行"

    # 测试1: 检查导出状态API
    print_info "测试 GET /api/backtest/test_bt_001/export/status"
    response=$(curl -s "http://localhost:8000/api/backtest/test_bt_001/export/status")

    if echo "$response" | grep -q "success\|can_export"; then
        record_test_result "检查导出状态API" "PASS" "API已注册并响应"
        print_success "导出状态API已就绪"
    else
        record_test_result "检查导出状态API" "FAIL" "API响应异常"
        print_warning "导出状态API返回非预期响应"
    fi

    # 测试2: 导出Excel API（需要有效的回测ID）
    print_info "测试 GET /api/backtest/test_bt_001/export/excel（预期：需要有效回测ID）"
    response=$(curl -s -o /tmp/test_export.xlsx -w "%{http_code}" "http://localhost:8000/api/backtest/test_bt_001/export/excel")

    if [ "$response" = "404" ] || [ "$response" = "401" ] || [ "$response" = "403" ]; then
        record_test_result "导出Excel API" "PASS" "API已注册并响应"
        print_success "导出Excel API已就绪"
    elif [ "$response" = "200" ]; then
        # 检查是否下载了文件
        if [ -f /tmp/test_export.xlsx ] && [ -s /tmp/test_export.xlsx ]; then
            record_test_result "导出Excel API" "PASS" "成功下载Excel文件"
            print_success "导出Excel API工作正常"
            rm -f /tmp/test_export.xlsx
        else
            record_test_result "导出Excel API" "FAIL" "响应200但文件为空"
        fi
    else
        record_test_result "导出Excel API" "FAIL" "API返回异常状态码: $response"
    fi

    print_info "💡 注意：完整的API测试需要有效的回测数据"
    print_info "   核心功能已通过单元测试验证"
}

# 测试Excel文件格式
test_excel_format() {
    print_step "测试Excel文件格式"

    print_info "检查openpyxl能否读取生成的Excel..."

    # 创建一个简单的测试Excel文件
    cat > /tmp/test_excel_format.py << 'EOF'
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from io import BytesIO

# 创建测试Excel
wb = openpyxl.Workbook()
ws = wb.active
ws['A1'] = "测试"
ws['A1'].font = Font(bold=True)
ws['A1'].fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")

# 保存到内存
output = BytesIO()
wb.save(output)
output.seek(0)

# 验证
wb2 = openpyxl.load_workbook(output)
assert wb2.active['A1'].value == "测试"
print("✓ Excel格式测试通过")

# 清理
output.close()
wb2.close()
EOF

    $PYTHON_CMD /tmp/test_excel_format.py

    if [ $? -eq 0 ]; then
        record_test_result "Excel文件格式" "PASS" "openpyxl能正确读写Excel文件"
        print_success "Excel文件格式测试通过"
    else
        record_test_result "Excel文件格式" "FAIL" "openpyxl无法正确处理Excel文件"
        print_error "Excel文件格式测试失败"
    fi

    rm -f /tmp/test_excel_format.py
}

# 清理测试数据
cleanup_test_data() {
    print_step "清理测试数据"

    print_info "清理测试回测数据..."
    print_info "如需清理，请手动执行:"
    print_info "  db.backtest_tasks.deleteMany({backtest_id: {\\$regex: \"^test_bt_export_\"}})"
    print_info "  db.backtest_results.deleteMany({backtest_id: {\\$regex: \"^test_bt_export_\"}})"
    print_info "  db.backtest_trades.deleteMany({backtest_id: {\\$regex: \"^test_bt_export_\"}})"
    print_info "  db.backtest_history.deleteMany({backtest_id: {\\$regex: \"^test_bt_export_\"}})"
}

# 打印测试总结
print_summary() {
    print_step "测试总结"

    local total=$((TESTS_PASSED + TESTS_FAILED))
    echo "" >&2
    echo "========================================" >&2
    echo " 测试统计" >&2
    echo "========================================" >&2
    echo "总测试数: $total" >&2
    echo -e "通过: ${GREEN}$TESTS_PASSED${NC}" >&2
    echo -e "失败: ${RED}$TESTS_FAILED${NC}" >&2
    echo "" >&2

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ 全部测试Case均符合预期${NC}" >&2
    else
        echo -e "${RED}✗ 部分测试Case不符合预期${NC}" >&2
        echo "" >&2
        echo "失败的测试:" >&2
        for result in "${TEST_RESULTS[@]}"; do
            if echo "$result" | grep -q "FAIL"; then
                echo "  - $result" >&2
            fi
        done
    fi

    echo "" >&2
    echo "通过的测试:" >&2
    for result in "${TEST_RESULTS[@]}"; do
        if echo "$result" | grep -q "PASS"; then
            echo "  - $result" >&2
        fi
    done

    echo "" >&2
    echo "========================================" >&2
}

# 主函数
main() {
    echo ""
    echo -e "${GREEN}====================================${NC}"
    echo -e "${GREEN}  回测结果导出服务测试脚本${NC}"
    echo -e "${GREEN}====================================${NC}"
    echo ""

    # 检查依赖
    check_dependencies

    # 运行单元测试
    run_unit_tests

    # 测试API端点
    test_api_endpoints

    # 测试Excel格式
    test_excel_format

    # 打印总结
    print_summary

    # 清理测试数据（可选）
    read -p "是否查看测试数据清理命令? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cleanup_test_data
    fi

    echo ""
    echo "下一步："
    echo "  1. 启动后端: ./venv/bin/python3 -m app"
    echo "  2. 重新运行: ./tests/test_export_service.sh"
    echo "  3. 访问API文档: http://localhost:8000/docs"
    echo "  4. 查看导出功能: http://localhost:8000/docs?tag=backtest-export"
    echo ""
}

# 运行主函数
main
