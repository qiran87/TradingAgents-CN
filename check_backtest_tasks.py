#!/usr/bin/env python3
"""检查回测任务"""
import motor.motor_asyncio
import asyncio
from datetime import datetime

MONGO_URI = "mongodb://admin:password@localhost:27017/tradingagents"

async def check_backtest_tasks():
    """查询回测任务"""
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
    db = client.tradingagents

    try:
        # 查询最近的5个回测任务
        cursor = db.backtest_tasks.find().sort("created_at", -1).limit(5)

        print("\n========== 最近的回测任务 ==========")
        count = 0
        async for task in cursor:
            count += 1
            print(f"\n任务 {count}:")
            print(f"  回测ID: {task.get('backtest_id')}")
            print(f"  状态: {task.get('status')}")
            print(f"  股票代码: {task.get('parameters', {}).get('stock_code')}")
            print(f"  创建时间: {task.get('created_at')}")
            print(f"  更新时间: {task.get('updated_at')}")

            exec_info = task.get('execution_info', {})
            print(f"  执行信息:")
            print(f"    当前进度: {exec_info.get('progress', 0)}%")
            print(f"    当前K线: {exec_info.get('current_bar_index', 0)}/{exec_info.get('total_bars', 0)}")
            print(f"    当前日期: {exec_info.get('current_date')}")

        if count == 0:
            print("\n❌ 没有找到任何回测任务")
        else:
            print(f"\n✅ 共找到 {count} 个回测任务")

    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(check_backtest_tasks())
