#!/usr/bin/env python3
"""调试 MDVAES 策略估值计算"""
import asyncio
from datetime import datetime, timezone
from app.core.database import init_database, get_mongo_db
from app.services.backtest_engine_service import BacktestEngine


async def main():
    await init_database()
    db = get_mongo_db()

    print("="*60)
    print("调试 MDVAES 策略估值计算")
    print("="*60)

    # 直接调用策略进行单日测试
    from app.strategies.mdvaes import MDVAESStrategy

    strategy_params = {
        "symbol": "000001.SZ",
        "forecast_years": 5,
        "peg_base": 1.0,
        "rebalance_frequency": 90
    }

    print(f"\n策略参数: {strategy_params}")

    # 创建策略实例
    try:
        strategy = MDVAESStrategy(strategy_params)
        print("✅ 策略初始化成功")
    except Exception as e:
        print(f"❌ 策略初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 测试单日计算
    test_date = datetime.strptime("2024-01-02", "%Y-%m-%d")
    test_price = 10.5  # 假设价格

    print(f"\n测试估值计算:")
    print(f"  日期: {test_date}")
    print(f"  价格: {test_price}")

    # 检查是否有估值数据
    print(f"\n检查估值数据:")
    print(f"  last_valuation 是否为 None: {strategy.last_valuation is None}")

    # 调用 on_bar
    signal = strategy.on_bar(
        bar_id="test_1",
        timestamp=test_date,
        current_price=test_price,
        position=0,
        cash=100000.0
    )

    print(f"\n信号结果:")
    print(f"  action: {signal.get('action')}")
    print(f"  amount: {signal.get('amount')}")
    print(f"  reason: {signal.get('reason')[:100]}...")
    print(f"  有 metadata: {'metadata' in signal}")

    if 'metadata' in signal:
        metadata = signal['metadata']
        print(f"  metadata 内容: {metadata}")
    else:
        print("  ⚠️  没有 metadata - 估值可能计算失败")

    # 检查 MongoDB 中的数据
    print(f"\n检查 MongoDB 数据源:")
    sync_db = strategy.data_reader._get_sync_db()

    # 检查分析师预测
    analyst_count = await sync_db.mdvaes_analyst_forecasts.count_documents({
        "ts_code": "000001.SZ"
    })
    print(f"  分析师预测记录数: {analyst_count}")

    # 检查历史EPS
    eps_count = await sync_db.mdvaes_eps_history.count_documents({
        "ts_code": "000001.SZ"
    })
    print(f"  历史EPS记录数: {eps_count}")

    # 检查PE历史
    pe_count = await sync_db.mdvaes_pe_history.count_documents({
        "ts_code": "000001.SZ"
    })
    print(f"  PE历史记录数: {pe_count}")

    # 检查国债利率
    bond_count = await sync_db.mdvaes_bond_rate.count_documents({
        "curve_term": 10.0
    })
    print(f"  国债利率记录数: {bond_count}")

    # 尝试直接调用估值计算
    print(f"\n直接测试估值计算:")
    try:
        result = strategy._calculate_valuation(test_date, test_price)
        print(f"  估值计算结果:")
        print(f"    success: {result.get('success')}")
        if result.get('success'):
            val = result['valuation']
            print(f"    intrinsic_value: {val.intrinsic_value if val else 'N/A'}")
            print(f"    lower_bound: {val.lower_bound if val else 'N/A'}")
            print(f"    upper_bound: {val.upper_bound if val else 'N/A'}")
            print(f"    signal: {val.signal if val else 'N/A'}")
        else:
            print(f"    error: {result.get('error')}")
    except Exception as e:
        print(f"  估值计算异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
