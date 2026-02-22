#!/usr/bin/env python3
"""检查回测每日状态的详细信息"""
import asyncio
from app.core.database import init_database, get_mongo_db


async def main():
    await init_database()
    db = get_mongo_db()

    # 查找最近的MDVAES测试任务
    task = await db.backtest_tasks.find_one(
        {'backtest_id': {'$regex': 'test_mdvaes'}},
        sort=[('created_at', -1)]
    )

    if not task:
        print("未找到MDVAES测试任务")
        return

    backtest_id = task['backtest_id']
    print(f"回测任务ID: {backtest_id}")
    print(f"策略: {task.get('strategy_id')}")
    print(f"状态: {task.get('status')}")
    print()

    # 查看每日状态样本
    sample_states = await db.backtest_daily_states.find(
        {'backtest_id': backtest_id}
    ).sort([('date', 1)]).limit(3).to_list(None)

    print("前3条每日状态样本:")
    for i, state in enumerate(sample_states, 1):
        print(f"\n--- 状态 {i} ({state.get('date')}) ---")
        print(f"  现金: {state.get('cash', 0):.2f}")
        print(f"  持仓: {state.get('position', 0)} 股")
        print(f"  总资产: {state.get('total_value', 0):.2f}")
        print(f"  action: {state.get('action', 'N/A')}")
        print(f"  amount: {state.get('amount', 0)}")
        print(f"  reason: {state.get('reason', 'N/A')[:100]}...")

        # 检查 valuation 字段
        valuation = state.get('valuation')
        if valuation:
            print(f"  估值数据存在:")
            print(f"    intrinsic_value: {valuation.get('intrinsic_value', 'N/A')}")
            print(f"    lower_bound: {valuation.get('lower_bound', 'N/A')}")
            print(f"    upper_bound: {valuation.get('upper_bound', 'N/A')}")
            print(f"    signal: {valuation.get('signal', 'N/A')}")
        else:
            print(f"  无估值数据")

    # 查看有估值的状态
    val_states = await db.backtest_daily_states.find({
        'backtest_id': backtest_id,
        'valuation.intrinsic_value': {'$exists': True}
    }).to_list(None)

    print(f"\n有估值数据的状态数: {len(val_states)}")

    if val_states:
        print("\n第一条估值状态:")
        state = val_states[0]
        val = state.get('valuation', {})
        print(f"  日期: {state.get('date')}")
        print(f"  内在价值: {val.get('intrinsic_value', 'N/A')}")
        print(f"  下限: {val.get('lower_bound', 'N/A')}")
        print(f"  上限: {val.get('upper_bound', 'N/A')}")
        print(f"  信号: {val.get('signal', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(main())
