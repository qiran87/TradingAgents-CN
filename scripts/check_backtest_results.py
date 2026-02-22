#!/usr/bin/env python3
"""检查回测结果"""
import asyncio
from app.core.database import init_database, get_mongo_db

async def main():
    await init_database()
    db = get_mongo_db()

    # 查找最近的测试回测任务
    tasks = await db.backtest_tasks.find(
        {'backtest_id': {'$regex': 'test_'}}
    ).sort([('created_at', -1)]).limit(2).to_list(None)

    print(f'找到 {len(tasks)} 个测试回测任务')
    for task in tasks:
        print(f"  - {task['backtest_id']}: strategy_id={task.get('strategy_id')}, status={task.get('status')}")

    # 检查每日状态
    daily_states = await db.backtest_daily_states.count_documents({'backtest_id': {'$regex': 'test_mdvaes'}})
    print(f"MDVAES 测试任务的每日状态记录数: {daily_states}")

    # 检查估值数据
    valuation_states = await db.backtest_daily_states.count_documents({
        'backtest_id': {'$regex': 'test_mdvaes'},
        'valuation': {'$exists': True}
    })
    print(f"MDVAES 测试任务的估值状态记录数: {valuation_states}")

if __name__ == "__main__":
    asyncio.run(main())
