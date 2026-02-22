#!/usr/bin/env python3
"""检查回测任务详情"""
import asyncio
from app.core.database import init_database, get_mongo_db

async def main():
    await init_database()
    db = get_mongo_db()

    # 查找最近的测试回测任务
    task = await db.backtest_tasks.find_one({'backtest_id': {'$regex': 'test_bt_export'}})
    if task:
        backtest_id = task['backtest_id']
        print(f'回测任务ID: {backtest_id}')
        print(f'策略ID: {task.get("strategy_id")}')
        print(f'策略参数: {task.get("parameters", {}).get("strategy_params")}')

    # 查看每日状态样本
    sample = await db.backtest_daily_states.find_one({'backtest_id': {'$regex': 'test_bt_export'}})
    if sample:
        print(f'\n每日状态样本:')
        print(f'  日期: {sample.get("date")}')
        print(f'  现金: {sample.get("cash")}')
        print(f'  持仓: {sample.get("position")}')
        print(f'  有估值字段: {"valuation" in sample}')
        print(f'  字典键: {list(sample.keys())}')
    else:
        print('没有找到每日状态记录')

if __name__ == "__main__":
    asyncio.run(main())
