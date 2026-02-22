#!/usr/bin/env python3
"""
完整测试 MDVAES 策略回测
"""
import asyncio
from datetime import datetime, timezone
from app.core.database import init_database, get_mongo_db
from app.services.backtest_engine_service import execute_backtest_task


async def main():
    """主测试函数"""
    # 初始化数据库
    await init_database()
    db = get_mongo_db()

    print("="*60)
    print("测试 MDVAES 策略完整回测流程")
    print("="*60)

    backtest_id = f"test_mdvaes_full_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

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

    # 创建任务文档
    await db.backtest_tasks.insert_one({
        "backtest_id": backtest_id,
        "stock_code": params["stock_code"],
        "start_date": params["start_date"],
        "end_date": params["end_date"],
        "initial_capital": params["initial_capital"],
        "strategy_id": params["strategy_id"],
        "strategy_params": params["strategy_params"],
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    })

    print(f"回测任务ID: {backtest_id}")
    print(f"股票代码: {params['stock_code']}")
    print(f"策略: {params['strategy_id']}")
    print(f"时间范围: {params['start_date']} 至 {params['end_date']}")
    print(f"初始资金: {params['initial_capital']}")
    print("\n开始执行回测...\n")

    try:
        await execute_backtest_task(backtest_id, params)
        print("✅ 回测任务执行完成\n")
    except Exception as e:
        print(f"❌ 回测执行异常: {e}\n")
        import traceback
        traceback.print_exc()

    # 等待数据库更新
    await asyncio.sleep(1)

    # 检查任务状态
    task = await db.backtest_tasks.find_one({"backtest_id": backtest_id})

    if task:
        print("="*60)
        print("回测任务结果")
        print("="*60)
        print(f"状态: {task.get('status')}")
        print(f"错误信息: {task.get('error', {}).get('message') if task.get('error') else '无'}")

        # 检查每日状态
        daily_count = await db.backtest_daily_states.count_documents({"backtest_id": backtest_id})
        print(f"每日状态记录数: {daily_count}")

        # 检查交易记录
        trades_count = await db.backtest_trades.count_documents({"backtest_id": backtest_id})
        print(f"交易记录数: {trades_count}")

        # 检查估值数据
        valuation_count = await db.backtest_daily_states.count_documents({
            "backtest_id": backtest_id,
            "valuation.intrinsic_value": {"$exists": True}
        })
        print(f"估值状态记录数: {valuation_count}")

        # 显示最终状态
        if daily_count > 0:
            latest_state = await db.backtest_daily_states.find_one(
                {"backtest_id": backtest_id},
                sort=[("date", -1)]
            )
            if latest_state:
                print(f"\n最终状态:")
                print(f"  日期: {latest_state.get('date')}")
                print(f"  现金: {latest_state.get('cash', 0):.2f}")
                print(f"  持仓: {latest_state.get('position', 0)} 股")
                print(f"  总资产: {latest_state.get('total_value', 0):.2f}")

        # 显示交易记录
        if trades_count > 0:
            print(f"\n交易记录:")
            trades = await db.backtest_trades.find({"backtest_id": backtest_id}).to_list(None)
            for trade in trades:
                print(f"  {trade.get('date')}: {trade.get('action')} {trade.get('shares')} 股 @ {trade.get('price'):.2f}")
        else:
            print("\n无交易记录")

        # 显示估值样本
        if valuation_count > 0:
            print(f"\n估值数据样本:")
            sample = await db.backtest_daily_states.find_one({
                "backtest_id": backtest_id,
                "valuation.intrinsic_value": {"$exists": True}
            })
            if sample and sample.get("valuation"):
                val = sample["valuation"]
                print(f"  日期: {sample.get('date')}")
                print(f"  内在价值: {val.get('intrinsic_value', 0):.2f}")
                print(f"  估值区间: [{val.get('lower_bound', 0):.2f}, {val.get('upper_bound', 0):.2f}]")
                print(f"  信号: {val.get('signal')}")

    print("\n" + "="*60)
    if task and task.get("status") == "completed":
        print("✅ 测试成功: MDVAES 策略回测正常完成")
    elif task and task.get("status") == "error":
        print("❌ 测试失败: 回测执行出错")
    else:
        print("⚠️  测试未完成: 状态未知")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
