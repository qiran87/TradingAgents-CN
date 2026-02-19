"""
初始化策略数据

将内置策略元数据写入MongoDB

使用方法:
    python3 -m app.scripts.init_strategies              # 正常模式,连接数据库
    python3 -m app.scripts.init_strategies --dry-run    # 测试模式,不连接数据库
    python3 -m app.scripts.init_strategies --test       # 测试模式别名
"""
import asyncio
import sys
import argparse
from datetime import datetime
from typing import Dict, Any, List

# 测试模式下不导入数据库模块
TEST_MODE = False
if "--dry-run" in sys.argv or "--test" in sys.argv:
    TEST_MODE = True
    print("🧪 测试模式已启用 - 将不会连接数据库")
else:
    from app.core.database import get_mongo_db

# 内置策略数据
STRATEGIES = [
    {
        "strategy_id": "dual_ma",
        "name": "双均线策略",
        "description": "基于快慢均线的交叉信号进行交易",
        "long_description": "双均线策略是一种经典的趋势跟踪策略。当短期均线上穿长期均线时产生买入信号，当短期均线下穿长期均线时产生卖出信号。",
        "category": "trend",
        "parameters": [
            {
                "name": "short_window",
                "type": "int",
                "default_value": 5,
                "range": {"min": 2, "max": 60},
                "description": "短期均线窗口",
                "required": True
            },
            {
                "name": "long_window",
                "type": "int",
                "default_value": 20,
                "range": {"min": 5, "max": 250},
                "description": "长期均线窗口",
                "required": True
            }
        ],
        "usage_count": 0,
        "is_builtin": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "strategy_id": "bollinger_bands",
        "name": "布林带策略",
        "description": "基于布林带的突破和回归进行交易",
        "long_description": "布林带策略利用价格波动率，当价格触及下轨时可能超卖反弹，当价格回归中轨时获利了结。",
        "category": "oscillation",
        "parameters": [
            {
                "name": "window",
                "type": "int",
                "default_value": 20,
                "range": {"min": 5, "max": 50},
                "description": "均线窗口",
                "required": True
            },
            {
                "name": "num_std",
                "type": "float",
                "default_value": 2.0,
                "range": {"min": 0.5, "max": 4.0},
                "description": "标准差倍数",
                "required": True
            }
        ],
        "usage_count": 0,
        "is_builtin": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "strategy_id": "macd",
        "name": "MACD策略",
        "description": "基于MACD指标的金叉死叉进行交易",
        "long_description": "MACD策略通过快慢线的交叉来判断买卖时机。当DIF上穿DEA时买入（金叉），当DIF下穿DEA时卖出（死叉）。",
        "category": "trend",
        "parameters": [
            {
                "name": "fast_period",
                "type": "int",
                "default_value": 12,
                "range": {"min": 5, "max": 50},
                "description": "快线周期",
                "required": True
            },
            {
                "name": "slow_period",
                "type": "int",
                "default_value": 26,
                "range": {"min": 10, "max": 100},
                "description": "慢线周期",
                "required": True
            },
            {
                "name": "signal_period",
                "type": "int",
                "default_value": 9,
                "range": {"min": 5, "max": 20},
                "description": "信号线周期",
                "required": True
            }
        ],
        "usage_count": 0,
        "is_builtin": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "strategy_id": "rsi",
        "name": "RSI策略",
        "description": "基于RSI指标的超买超卖进行交易",
        "long_description": "RSI策略通过相对强弱指数判断超买超卖。RSI低于超卖阈值时买入，高于超买阈值时卖出。",
        "category": "oscillation",
        "parameters": [
            {
                "name": "window",
                "type": "int",
                "default_value": 14,
                "range": {"min": 5, "max": 30},
                "description": "RSI周期",
                "required": True
            },
            {
                "name": "oversold",
                "type": "float",
                "default_value": 30.0,
                "range": {"min": 20, "max": 40},
                "description": "超卖阈值",
                "required": True
            },
            {
                "name": "overbought",
                "type": "float",
                "default_value": 70.0,
                "range": {"min": 60, "max": 80},
                "description": "超买阈值",
                "required": True
            }
        ],
        "usage_count": 0,
        "is_builtin": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "strategy_id": "kdj",
        "name": "KDJ策略",
        "description": "基于KDJ指标的超买超卖进行交易",
        "long_description": "KDJ策略通过K值判断超买超卖。K线低于20时超卖，高于80时超买。",
        "category": "oscillation",
        "parameters": [
            {
                "name": "k_window",
                "type": "int",
                "default_value": 9,
                "range": {"min": 5, "max": 20},
                "description": "K值周期",
                "required": True
            },
            {
                "name": "d_window",
                "type": "int",
                "default_value": 3,
                "range": {"min": 2, "max": 10},
                "description": "D值平滑周期",
                "required": True
            },
            {
                "name": "j_window",
                "type": "int",
                "default_value": 3,
                "range": {"min": 2, "max": 10},
                "description": "J值平滑周期",
                "required": True
            }
        ],
        "usage_count": 0,
        "is_builtin": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    },
    {
        "strategy_id": "mdvaes",
        "name": "MDVAES估值策略",
        "description": "基于多锚点估值系统(MDVAES)进行价值投资决策",
        "long_description": "MDVAES估值策略通过分析师盈利预测和历史数据外推，使用对数最小二乘法计算增长率。结合PEG、历史PE、PB、DCF多锚点估值，动态调整安全边际，适合长期价值投资。",
        "category": "valuation",
        "parameters": [
            {
                "name": "symbol",
                "type": "string",
                "default_value": "000001.SZ",
                "description": "股票代码",
                "required": True
            },
            {
                "name": "forecast_years",
                "type": "int",
                "default_value": 5,
                "range": {"min": 1, "max": 10},
                "description": "EPS预测年数",
                "required": False
            },
            {
                "name": "peg_base",
                "type": "float",
                "default_value": 1.0,
                "range": {"min": 0.5, "max": 2.0},
                "description": "PEG基数",
                "required": False
            },
            {
                "name": "risk_adjustment",
                "type": "float",
                "default_value": 0.1,
                "range": {"min": 0.0, "max": 0.3},
                "description": "风险调整幅度",
                "required": False
            },
            {
                "name": "rebalance_frequency",
                "type": "int",
                "default_value": 90,
                "range": {"min": 1, "max": 365},
                "description": "重新估值频率(天)",
                "required": False
            },
            {
                "name": "use_margin",
                "type": "bool",
                "default_value": True,
                "description": "使用安全边际",
                "required": False
            },
            {
                "name": "margin_buy",
                "type": "float",
                "default_value": 0.8,
                "range": {"min": 0.5, "max": 0.95},
                "description": "买入安全边际(价格低于估值的百分比)",
                "required": False
            },
            {
                "name": "margin_sell",
                "type": "float",
                "default_value": 1.2,
                "range": {"min": 1.05, "max": 2.0},
                "description": "卖出安全边际(价格高于估值的百分比)",
                "required": False
            }
        ],
        "usage_count": 0,
        "is_builtin": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
]

# 策略分类数据
CATEGORIES = [
    {
        "category_id": "trend",
        "name": "趋势跟踪策略",
        "description": "基于价格趋势的策略，适合趋势明显的市场",
        "sort_order": 1,
        "created_at": datetime.utcnow()
    },
    {
        "category_id": "oscillation",
        "name": "震荡策略",
        "description": "基于价格波动的策略，适合横盘震荡市场",
        "sort_order": 2,
        "created_at": datetime.utcnow()
    },
    {
        "category_id": "momentum",
        "name": "动量策略",
        "description": "基于价格动量的策略",
        "sort_order": 3,
        "created_at": datetime.utcnow()
    },
    {
        "category_id": "valuation",
        "name": "估值策略",
        "description": "基于基本面估值的策略，适合长期投资",
        "sort_order": 4,
        "created_at": datetime.utcnow()
    }
]


def validate_strategy_data(strategy: Dict[str, Any]) -> List[str]:
    """
    验证策略数据完整性

    Args:
        strategy: 策略数据

    Returns:
        错误列表,空列表表示验证通过
    """
    errors = []

    # 必需字段
    required_fields = [
        "strategy_id", "name", "description", "category",
        "parameters", "usage_count", "is_builtin"
    ]
    for field in required_fields:
        if field not in strategy:
            errors.append(f"缺少必需字段: {field}")

    # strategy_id格式
    if "strategy_id" in strategy:
        sid = strategy["strategy_id"]
        if not isinstance(sid, str) or not sid:
            errors.append(f"strategy_id必须是非空字符串: {sid}")

    # 参数验证
    if "parameters" in strategy:
        if not isinstance(strategy["parameters"], list):
            errors.append("parameters必须是列表")
        else:
            for i, param in enumerate(strategy["parameters"]):
                if not isinstance(param, dict):
                    errors.append(f"参数{i}必须是字典")
                    continue

                param_required = ["name", "type", "default_value", "description", "required"]
                for field in param_required:
                    if field not in param:
                        errors.append(f"参数{i}缺少字段: {field}")

                # 验证range字段
                if "range" in param:
                    range_data = param["range"]
                    if not isinstance(range_data, dict):
                        errors.append(f"参数{i}的range必须是字典")
                    elif "min" in range_data or "max" in range_data:
                        if "min" in range_data and "max" in range_data:
                            if range_data["min"] >= range_data["max"]:
                                errors.append(f"参数{i}的range.min必须小于range.max")

    # 分类ID必须在分类列表中
    if "category" in strategy:
        category_ids = [c["category_id"] for c in CATEGORIES]
        if strategy["category"] not in category_ids:
            errors.append(f"无效的分类ID: {strategy['category']}")

    return errors


def validate_category_data(category: Dict[str, Any]) -> List[str]:
    """
    验证分类数据完整性

    Args:
        category: 分类数据

    Returns:
        错误列表,空列表表示验证通过
    """
    errors = []

    # 必需字段
    required_fields = ["category_id", "name", "sort_order"]
    for field in required_fields:
        if field not in category:
            errors.append(f"缺少必需字段: {field}")

    # category_id格式
    if "category_id" in category:
        cid = category["category_id"]
        if not isinstance(cid, str) or not cid:
            errors.append(f"category_id必须是非空字符串: {cid}")

    # sort_order必须是正整数
    if "sort_order" in category:
        if not isinstance(category["sort_order"], int) or category["sort_order"] <= 0:
            errors.append(f"sort_order必须是正整数: {category['sort_order']}")

    return errors


def print_index_plan():
    """打印将要创建的索引"""
    print("🔍 计划创建的索引:")
    print("   - strategies集合:")
    print("     * compound: {category: 1, usage_count: -1}")
    print("     * text: {name: 'text', description: 'text'}")
    print("     * unique: {strategy_id: 1}")
    print("   - strategy_categories集合:")
    print("     * unique: {category_id: 1}")
    print("✅ 索引计划验证完成\n")


def print_data_plan():
    """打印将要插入的数据"""
    print("📊 计划插入的数据:")

    print(f"\n   分类数据 ({len(CATEGORIES)}个):")
    for cat in CATEGORIES:
        print(f"   - {cat['category_id']}: {cat['name']}")

    print(f"\n   策略数据 ({len(STRATEGIES)}个):")
    for strategy in STRATEGIES:
        param_count = len(strategy.get("parameters", []))
        print(f"   - {strategy['strategy_id']}: {strategy['name']} ({param_count}个参数, 分类:{strategy['category']})")

    print("\n✅ 数据计划验证完成\n")


async def init_strategies():
    """初始化策略数据"""
    if TEST_MODE:
        # ===== 测试模式 =====
        print("🧪 测试模式 - 验证数据结构和逻辑\n")

        # 1. 验证分类数据
        print("📝 验证分类数据...")
        category_errors = []
        for i, category in enumerate(CATEGORIES):
            errors = validate_category_data(category)
            if errors:
                category_errors.append(f"分类{i}({category.get('category_id', 'UNKNOWN')}): {', '.join(errors)}")

        if category_errors:
            print("❌ 分类数据验证失败:")
            for error in category_errors:
                print(f"   {error}")
            return
        else:
            print(f"✅ 分类数据验证通过 ({len(CATEGORIES)}个分类)\n")

        # 2. 验证策略数据
        print("📝 验证策略数据...")
        strategy_errors = []
        for i, strategy in enumerate(STRATEGIES):
            errors = validate_strategy_data(strategy)
            if errors:
                strategy_errors.append(f"策略{i}({strategy.get('strategy_id', 'UNKNOWN')}): {', '.join(errors)}")

        if strategy_errors:
            print("❌ 策略数据验证失败:")
            for error in strategy_errors:
                print(f"   {error}")
            return
        else:
            print(f"✅ 策略数据验证通过 ({len(STRATEGIES)}个策略)\n")

        # 3. 打印执行计划
        print_index_plan()
        print_data_plan()

        # 4. 数据统计
        print("📊 数据统计:")
        print(f"   - 策略总数: {len(STRATEGIES)}")
        print(f"   - 分类总数: {len(CATEGORIES)}")

        # 统计各分类的策略数量
        category_counts = {}
        for strategy in STRATEGIES:
            cat = strategy["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1

        print(f"\n   各分类策略数量:")
        for cat_id, count in category_counts.items():
            cat_name = next(c["name"] for c in CATEGORIES if c["category_id"] == cat_id)
            print(f"   - {cat_name}({cat_id}): {count}个策略")

        # 统计参数总数
        total_params = sum(len(s.get("parameters", [])) for s in STRATEGIES)
        print(f"\n   参数统计:")
        print(f"   - 总参数数: {total_params}")
        print(f"   - 平均每策略: {total_params / len(STRATEGIES):.1f}个参数")

        print("\n✅ 测试模式完成 - 数据验证通过!")
        print("💡 提示: 使用不带--dry-run参数运行此脚本以实际初始化数据库")

    else:
        # ===== 正常模式 =====
        db = get_mongo_db()

        # 创建索引
        print("🔍 创建索引...")
        await db.strategies.create_index([("category", 1), ("usage_count", -1)])
        await db.strategies.create_index([("name", "text"), ("description", "text")])
        await db.strategies.create_index("strategy_id", unique=True)
        await db.strategy_categories.create_index("category_id", unique=True)
        print("✅ 索引创建完成")

        # 插入分类（先删除已存在的）
        print("📝 插入分类...")
        await db.strategy_categories.delete_many({})
        result = await db.strategy_categories.insert_many(CATEGORIES)
        print(f"✅ 已插入 {len(result.inserted_ids)} 个分类")

        # 插入策略（先删除已存在的）
        print("📝 插入策略...")
        await db.strategies.delete_many({})
        result = await db.strategies.insert_many(STRATEGIES)
        print(f"✅ 已插入 {len(result.inserted_ids)} 个策略")

        # 验证数据
        strategy_count = await db.strategies.count_documents({})
        category_count = await db.strategy_categories.count_documents({})
        print(f"\n📊 数据统计:")
        print(f"   - 策略总数: {strategy_count}")
        print(f"   - 分类总数: {category_count}")

        print("\n✅ 策略初始化完成！")


if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="初始化策略数据")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="测试模式,不连接数据库,只验证数据"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="测试模式别名,同--dry-run"
    )

    args = parser.parse_args()

    # 运行初始化
    asyncio.run(init_strategies())
