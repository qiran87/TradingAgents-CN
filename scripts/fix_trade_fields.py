#!/usr/bin/env python3
"""
修复 backtest_trades 集合中缺失的字段
- stock_code, stock_name: 从 backtest_tasks 获取
- cash_before, position_before: 从交易序列推算
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, List


async def fix_trade_fields():
    """修复所有缺失的字段"""
    client = AsyncIOMotorClient('mongodb://admin:tradingagents123@localhost:27017')
    db = client.tradingagents

    print('🔧 开始修复交易记录缺失字段...')

    # 获取所有需要修复的回测任务
    backtest_ids = await db.backtest_trades.distinct('backtest_id', {
        '$or': [
            {'stock_code': {'$exists': False}},
            {'cash_before': {'$exists': False}}
        ]
    })

    print(f'📊 找到 {len(backtest_ids)} 个需要修复的回测任务')

    for backtest_id in backtest_ids:
        print(f'\n🔄 处理回测任务: {backtest_id}')

        # 获取任务信息
        task = await db.backtest_tasks.find_one({'backtest_id': backtest_id})
        if not task:
            print(f'  ⚠️ 跳过: 找不到任务信息')
            continue

        params = task.get('parameters', {})
        stock_code = params.get('stock_code')
        stock_name = params.get('stock_name', stock_code)
        initial_capital = params.get('initial_capital', 100000.0)

        if not stock_code:
            print(f'  ⚠️ 跳过: 缺少 stock_code')
            continue

        # 获取该任务的所有交易,按日期排序
        trades = await db.backtest_trades.find({
            'backtest_id': backtest_id
        }).sort('date', 1).to_list(None)

        print(f'  📈 找到 {len(trades)} 条交易记录')

        # 初始化状态
        cash = initial_capital
        position = 0

        # 逐条修复交易记录
        for i, trade in enumerate(trades):
            update_data = {}

            # 1. 添加股票代码和名称
            if 'stock_code' not in trade:
                update_data['stock_code'] = stock_code
                update_data['stock_name'] = stock_name

            # 2. 计算并添加交易前状态
            if 'cash_before' not in trade or 'position_before' not in trade:
                update_data['cash_before'] = cash
                update_data['position_before'] = position

                # 更新当前状态(为下一条交易做准备)
                if trade.get('trade_type') == 'buy':
                    total_cost = trade.get('total_cost', 0)
                    cash -= total_cost
                    position = trade.get('position_after', position)
                elif trade.get('trade_type') == 'sell':
                    amount = trade.get('amount', 0)
                    total_cost = trade.get('total_cost', 0)
                    cash += amount - total_cost
                    position = trade.get('position_after', position)

            # 执行更新
            if update_data:
                result = await db.backtest_trades.update_one(
                    {'_id': trade['_id']},
                    {'$set': update_data}
                )
                if result.modified_count > 0:
                    print(f'  ✅ 交易 {i+1}: {trade.get("date")} - 已修复 {len(update_data)} 个字段')

    print(f'\n✅ 修复完成!')
    client.close()


if __name__ == '__main__':
    asyncio.run(fix_trade_fields())
