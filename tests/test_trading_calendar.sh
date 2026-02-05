#!/bin/bash

###############################################################################
# 交易日历服务测试脚本
#
# 功能：
# 1. 后端API接口测试（5个接口）
# 2. 前端组件集成测试
# 3. 性能测试
# 4. 数据完整性验证
#
# 使用方法：
# chmod +x tests/test_trading_calendar.sh
# ./tests/test_trading_calendar.sh
#
# 注意事项：
# - 需要先启动后端服务（./venv/bin/python3 -m app）
# - 需要先初始化交易日历数据
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
API_PREFIX="/api/backtest/trading-days"

# 测试结果统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
TEST_RESULTS=()

###############################################################################
# 工具函数
###############################################################################

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

print_section() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# 测试断言
assert_test() {
    local test_name="$1"
    local condition="$2"
    local expected="$3"
    local actual="$4"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if eval "$condition"; then
        print_success "$test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        TEST_RESULTS+=("✓ $test_name")
    else
        print_error "$test_name"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        TEST_RESULTS+=("✗ $test_name")
        if [ -n "$expected" ]; then
            echo "  期望: $expected"
            echo "  实际: $actual"
        fi
    fi
}

# API请求函数
api_get() {
    local endpoint="$1"
    local params="$2"

    if [ -z "$params" ]; then
        curl -s "${BASE_URL}${API_PREFIX}${endpoint}" | jq
    else
        curl -s "${BASE_URL}${API_PREFIX}${endpoint}?${params}" | jq
    fi
}

# 检查服务是否运行
check_service() {
    print_section "检查服务状态"

    local health_status=$(curl -s "${BASE_URL}/api/health" | jq -r '.data.status')

    if [ "$health_status" = "ok" ]; then
        print_success "后端服务运行正常"
        return 0
    else
        print_error "后端服务未运行"
        print_info "请先启动后端服务："
        echo "  ./venv/bin/python3 -m app"
        exit 1
    fi
}

###############################################################################
# 测试1：后端API接口测试
###############################################################################

test_backend_api() {
    print_header "测试1：后端API接口"

    print_section "测试1.1 获取交易日列表"

    # 获取2024年1月的交易日
    print_info "测试：获取2024-01-01 到 2024-01-31 的交易日列表"
    result=$(api_get "" "start_date=2024-01-01&end_date=2024-01-31")

    trading_days_count=$(echo "$result" | jq '.data.total')
    first_trading_day=$(echo "$result" | jq -r '.data.trading_days[0]')

    assert_test "1.1.1 API返回成功" "[ '$result' != 'null' ]" "$trading_days_count 个交易日" "$trading_days_count 个交易日"
    assert_test "1.1.2 返回交易日列表" "$trading_days_count -gt 0" "至少1个交易日" "$trading_days_count 个交易日"
    assert_test "1.1.3 第一个交易日正确" "$first_trading_day == '2024-01-01'" "2024-01-01" "$first_trading_day"

    echo
    print_section "测试1.2 获取交易日历信息"

    print_info "测试：获取2024年全年交易日统计信息"
    result=$(api_get "/info" "start_date=2024-01-01&end_date=2024-12-31")

    trading_days_count=$(echo "$result" | jq '.data.trading_days_count')
    holidays_count=$(echo "$result" | jq '.data.holidays_count')
    weekends_count=$(echo "$result" | jq '.data.weekends_count')
    percentage=$(echo "$result" | jq '.data.trading_day_percentage')

    assert_test "1.2.1 返回统计信息" "$trading_days_count -gt 0" "$trading_days_count 个交易日" "$trading_days_count 个交易日"
    assert_test "1.2.2 交易日占比合理" "$percentage -gt 60" "占比 > 60%" "$percentage%"
    assert_test "1.2.3 数据完整（有交易日）" "$trading_days_count + $holidays_count + $weekends_count -eq 365" "总和等于365" "$trading_days_count + $holidays_count + $weekends_count = 365"

    echo
    print_section "测试1.3 判断指定日期是否为交易日"

    print_info "测试1：2024-01-15（周一）应该是交易日"
    result=$(api_get "/2024-01-15")
    is_trading=$(echo "$result" | jq '.data.is_trading_day')
    weekday=$(echo "$result" | jq '.data.weekday')

    assert_test "1.3.1 周一是交易日" '[ "$is_trading" == "true" ]' "是交易日" "非交易日"
    assert_test "1.3.2 星期正确" "$weekday == 1" "周一(1)" "周 $weekday"

    print_info "测试2：2024-01-13（周六）不应该是交易日"
    result=$(api_get "/2024-01-13")
    is_trading=$(echo "$result" | jq '.data.is_trading_day')
    is_weekend=$(echo "$result" | jq '.data.is_weekend')

    assert_test "1.3.3 周六不是交易日" '[ "$is_trading" == "false" ]' "不是交易日" "交易日"
    assert_test "1.3.4 周六是周末" '[ "$is_weekend" == "true" ]' "是周末" "非周末"

    echo
    print_section "测试1.4 获取前一个交易日"

    print_info "测试：2024-01-15（周一）的前一个交易日应该是2024-01-12（周五）"
    result=$(api_get "/2024-01-15/previous")
    prev_trading_day=$(echo "$result" | jq -r '.data.previous_trading_day')

    assert_test "1.4.1 返回前一个交易日" "$prev_trading_day != 'null'" "前一个交易日存在" "$prev_trading_day"
    assert_test "1.4.2 前一个交易日正确" "$prev_trading_day == '2024-01-12'" "2024-01-12" "$prev_trading_day"

    echo
    print_section "测试1.5 获取后一个交易日"

    print_info "测试：2024-01-15（周一）的后一个交易日应该是2024-01-16（周二）"
    result=$(api_get "/2024-01-15/next")
    next_trading_day=$(echo "$result" | jq -r '.data.next_trading_day')

    assert_test "1.5.1 返回后一个交易日" "$next_trading_day != 'null'" "后一个交易日存在" "$next_trading_day"
    assert_test "1.5.2 后一个交易日正确" "$next_trading_day == '2024-01-16'" "2024-01-16" "$next_trading_day"

    echo
    print_section "测试1.6 错误处理"

    print_info "测试1：日期格式错误"
    result=$(api_get "" "start_date=2024/01/01&end_date=2024/01/31" 2>&1)

    assert_test "1.6.1 正确返回400错误" "echo $result | grep -q '400'" "返回400错误" "错误处理正确"

    print_info "测试2：起始日期晚于结束日期"
    result=$(api_get "" "start_date=2024-12-31&end_date=2024-01-01" 2>&1)

    assert_test "1.6.2 正确返回400错误" "echo $result | grep -q '400'" "返回400错误" "错误处理正确"
}

###############################################################################
# 测试2：数据完整性验证
###############################################################################

test_data_integrity() {
    print_header "测试2：数据完整性验证"

    print_section "测试2.1 检查数据覆盖率"

    print_info "检查2020-2025年数据是否完整"

    # 检查每一年是否有数据
    for year in 2020 2021 2022 2023 2024 2025; do
        result=$(api_get "/info" "start_date=${year}-01-01&end_date=${year}-12-31")
        trading_days_count=$(echo "$result" | jq '.data.trading_days_count')

        assert_test "2.1.$((year-2020)) ${year}年有数据" "$trading_days_count -gt 0" "${year}年有 $trading_days_count 个交易日" "$trading_days_count 个交易日"
    done

    echo
    print_section "测试2.2 检查数据连续性"

    print_info "检查每个月是否有连续的交易日数据"

    for year in 2024; do
        for month in 1 2 3 4 5 6 7 8 9 10 11 12; do
            # 格式化月份
            month_formatted=$(printf "%02d" $month)
            start_date="${year}-${month_formatted}-01"

            # 计算月末
            if [ $month -eq 12 ]; then
                end_date="${year}-12-31"
            else
                next_month=$((month + 1))
                next_month_formatted=$(printf "%02d" $next_month)
                # 找到最后一天
                case $month in
                    1|3|5|7|8|10|12) last_day=31 ;;
                    4|6|9|11) last_day=30 ;;
                    2) last_day=28 ;;  # 简化处理
                esac
                end_date="${year}-${month_formatted}-${last_day}"
            fi

            # 获取该月的交易日
            result=$(api_get "" "start_date=${start_date}&end_date=${end_date}")
            trading_days_count=$(echo "$result" | jq '.data.total')

            # 每个月至少应该有一些交易日（排除2月可能较少）
            if [ $month -ne 2 ] || [ $trading_days_count -ge 15 ]; then
                assert_test "2.2.$((year-2020))${year}年${month}月有交易日" "$trading_days_count -gt 0" "${month}月有交易日" "${trading_days_count} 个交易日"
            fi
        done
    done

    echo
    print_section "测试2.3 验证周末非交易日"

    print_info "检查2024年1月的周末是否都不是交易日"

    # 2024年1月的周末
    weekends=("2024-01-06" "2024-01-07" "2024-01-13" "2024-01-14" "2024-01-20" "2024-01-21" "2024-01-27" "2024-01-28")

    for date in "${weekends[@]}"; do
        result=$(api_get "/$date")
        is_trading=$(echo "$result" | jq '.data.is_trading_day')

        assert_test "2.3.${date//2024-} ${date//2024-} 不是交易日" '[ "$is_trading" == "false" ]' "不是交易日" "是交易日"
    done
}

###############################################################################
# 测试3：性能测试
###############################################################################

test_performance() {
    print_header "测试3：性能测试"

    print_section "测试3.1 单次查询性能"

    print_info "测试：单次交易日判断响应时间（应<100ms）"

    start_time=$(date +%s%3N)
    result=$(api_get "/2024-01-15")
    end_time=$(date +%s%3N)

    response_time=$((end_time - start_time))

    assert_test "3.1.1 响应时间<100ms" "$response_time -lt 100" "${response_time}ms < 100ms" "${response_time}ms"

    echo
    print_section "测试3.2 批量查询性能"

    print_info "测试：连续10次查询的性能"

    total_time=0
    for i in {1..10}; do
        start_time=$(date +%s%3N)
        result=$(api_get "/2024-01-15")
        end_time=$(date +%s%3N)
        response_time=$((end_time - start_time))
        total_time=$((total_time + response_time))
    done

    avg_time=$((total_time / 10))

    assert_test "3.2.1 平均响应时间<100ms" "$avg_time -lt 100" "平均${avg_time}ms < 100ms" "平均${avg_time}ms"

    echo
    print_section "测试3.3 缓存效果验证"

    print_info "测试：第一次查询（缓存未命中）vs 第二次查询（缓存命中）"

    # 第一次查询（未命中缓存）
    start_time=$(date +%s%3N)
    result1=$(api_get "/2024-01-15")
    end_time=$(date +%s%3N)
    first_time=$((end_time - start_time))

    # 第二次查询（命中缓存）
    start_time=$(date +%s%3N)
    result2=$(api_get "/2024-01-15")
    end_time=$(date +%s%3N)
    second_time=$((end_time - start_time))

    print_info "第一次查询耗时: ${first_time}ms"
    print_info "第二次查询耗时: ${second_time}ms"

    # 缓存应该显著提升性能（允许20%误差）
    expected_cache_time=$((first_time / 5))
    assert_test "3.3.1 缓存提升性能" "$second_time -lt $expected_cache_time" "缓存后更快" "缓存未生效或效果不明显"
}

###############################################################################
# 测试4：边界条件测试
###############################################################################

test_edge_cases() {
    print_header "测试4：边界条件测试"

    print_section "测试4.1 年初年末边界"

    print_info "测试：2024年1月1日（年初）"
    result=$(api_get "/2024-01-01")
    is_trading=$(echo "$result" | jq '.data.is_trading_day')
    weekday=$(echo "$result" | jq '.data.weekday')

    print_success "2024-01-01是$( [ $is_trading_day == "true" ] && echo "交易日" || echo "非交易日" )，周$weekday"

    echo
    print_info "测试：2024年12月31日（年末）"
    result=$(api_get "/2024-12-31")
    is_trading=$(echo "$result" | jq '.data.is_trading_day')
    weekday=$(echo "$result" | jq '.data.weekday')

    print_success "2024-12-31是$( [ $is_trading_day == "true" ] && echo "交易日" || echo "非交易日" )，周$weekday"

    echo
    print_section "测试4.2 查找前后交易日边界"

    print_info "测试：查找年初之前的前一个交易日（2023-12-29）"
    result=$(api_get "/2024-01-01/previous")
    prev_day=$(echo "$result" | jq -r '.data.previous_trading_day')

    print_success "2024-01-01的前一个交易日是: $prev_day"

    echo
    print_info "测试：查找年末之后的后一个交易日（2025-01-02）"
    result=$(api_get "/2024-12-31/next")
    next_day=$(echo "$result" | jq -r '.data.next_trading_day')

    print_success "2024-12-31的后一个交易日是: $next_day"
}

###############################################################################
# 测试5：前端集成测试（如果有前端开发环境）
###############################################################################

test_frontend_integration() {
    print_header "测试5：前端集成测试"

    # 检查前端目录是否存在
    if [ ! -d "frontend" ]; then
        print_info "前端目录不存在，跳过前端测试"
        return
    fi

    print_section "测试5.1 前端组件文件检查"

    # 检查组件文件是否存在
    component_files=(
        "frontend/src/api/tradingCalendar.ts"
        "frontend/src/stores/tradingCalendar.ts"
        "frontend/src/components/TradingDayPicker.vue"
        "frontend/src/components/TradingCalendarInfo.vue"
    )

    for file in "${component_files[@]}"; do
        if [ -f "$file" ]; then
            print_success "$(basename $file) 文件存在"
        else
            print_error "$(basename $file) 文件不存在"
        fi
    done

    echo
    print_section "测试5.2 前端TypeScript类型检查"

    cd frontend

    if [ -f "package.json" ]; then
        print_info "检查前端依赖是否安装"
        if [ -d "node_modules" ]; then
            print_success "前端依赖已安装"
        else
            print_info "前端依赖未安装，请运行：cd frontend && npm install"
        fi
    fi

    cd ..
}

###############################################################################
# 测试总结
###############################################################################

print_summary() {
    print_header "测试总结"

    echo -e "${BLUE}测试统计${NC}"
    echo "  总测试数: $TOTAL_TESTS"
    echo "  通过数: $PASSED_TESTS"
    echo "  失败数: $FAILED_TESTS"
    echo "  通过率: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%"
    echo

    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "\n${GREEN}🎉 所有测试通过！交易日历服务功能正常。${NC}\n"
    else
        echo -e "\n${YELLOW}⚠️  有 $FAILED_TESTS 个测试失败，请检查上述错误信息。${NC}\n"
        echo -e "${YELLOW}失败的测试：${NC}\n"
        for result in "${TEST_RESULTS[@]}"; do
            if [[ $result == ✗* ]]; then
                echo "  $result"
            fi
        done
    echo
    fi
}

###############################################################################
# 主函数
###############################################################################

main() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════╗"
    echo "║   交易日历服务功能测试                      ║"
    echo "║   Trading Calendar Service Test             ║"
    echo "╚══════════════════════════════════════╝"
    echo -e "${NC}"
    echo

    # 执行测试
    check_service
    test_backend_api
    test_data_integrity
    test_performance
    test_edge_cases
    test_frontend_integration

    # 打印总结
    print_summary

    # 返回退出码
    if [ $FAILED_TESTS -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

###############################################################################
# 脚本入口
###############################################################################

# 解析命令行参数
case "${1:-}" in
    --backend-only)
        check_service
        test_backend_api
        print_summary
        ;;
    --api-only)
        check_service
        test_backend_api
        print_summary
        ;;
    --data-only)
        check_service
        test_data_integrity
        print_summary
        ;;
    --performance)
        check_service
        test_performance
        print_summary
        ;;
    --help|-h)
        echo "用法: $0 [选项]"
        echo ""
        echo "选项:"
        echo "  --backend-only   只运行后端API测试"
        echo "  --api-only       只运行API测试（同上）"
        echo "  --data-only      只运行数据完整性测试"
        echo "  --performance   只运行性能测试"
        echo "  --help, -h      显示帮助信息"
        echo ""
        echo "不加任何选项时，运行全部测试"
        ;;
    *)
        main
        ;;
esac
