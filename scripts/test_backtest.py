#!/usr/bin/env python3
"""
回测功能测试脚本
测试 MDVAES 策略和双均线策略的回测功能
"""
import asyncio
from datetime import datetime
from app.core.database import init_database
from app.services.backtest_engine_service import execute_backtest_task

async def test_dual_ma_backtest():
    """测试双均线策略回测"""
    print("\n" + "="*60)
    print("测试双均线策略回测")
    print("="*60)

    backtest_id = f"test_dual_ma_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    params = {
        "stock_code": "000001.SZ",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "initial_capital": 100000.0,
        "strategy_id": "dual_ma",
        "strategy_params": {
            "short_window": 5,
            "long_window": 20
        }
    }

    try:
        await execute_backtest_task(backtest_id, params)
        print(f"✅ 双均线策略回测成功: {backtest_id}")
        return True
    except Exception as e:
        print(f"❌ 双均线策略回测失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_mdvaes_backtest():
    """测试 MDVAES 策略回测"""
    print("\n" + "="*60)
    print("测试 MDVAES 策略回测")
    print("="*60)

    backtest_id = f"test_mdvaes_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    params = {
        "stock_code": "000001.SZ",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "initial_capital": 100000.0,
        "strategy_id": "mdvaes",
        "strategy_params": {
            "forecast_years": 5,
            "peg_base": 1.0,
            "rebalance_frequency": 90
        }
    }

    try:
        await execute_backtest_task(backtest_id, params)
        print(f"✅ MDVAES 策略回测成功: {backtest_id}")
        return True
    except Exception as e:
        print(f"❌ MDVAES 策略回测失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("开始回测功能测试...")
    print("请确保：")
    print("  1. MongoDB 正在运行")
    print("  2. 已同步 000001.SZ 的历史数据")
    print("")

    # 初始化数据库
    await init_database()

    # 测试双均线策略
    dual_ma_success = await test_dual_ma_backtest()

    # 测试 MDVAES 策略
    mdvaes_success = await test_mdvaes_backtest()

    # 总结
    print("\n" + "="*60)
    print("测试结果总结")
    print("="*60)
    print(f"双均线策略: {'✅ 通过' if dual_ma_success else '❌ 失败'}")
    print(f"MDVAES 策略: {'✅ 通过' if mdvaes_success else '❌ 失败'}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
