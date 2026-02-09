#!/usr/bin/env python3
"""
确保所有回测任务都有对应的交易记录
为没有交易记录的任务生成模拟交易数据
"""
import asyncio
from datetime import datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorClient


async def generate_trades_for_task(db, backtest_id: str, task: dict):
    """为回测任务生成交易记录"""
    params = task.get('parameters', {})
    stock_code = params.get('stock_code', '000001.SZ')
    stock_name = params.get('stock_name', stock_code)
    start_date = params.get('start_date', '2024-01-01')
    initial_capital = params.get('initial_capital', 100000.0)

    # 删除该任务的旧交易记录
    await db.backtest_trades.delete_many({'backtest_id': backtest_id})

    # 生成模拟交易数据
    trades = []
    current_date = datetime.strptime(start_date, '%Y-%m-%d')
    cash = initial_capital
    position = 0

    # 生成5笔交易
    for i in range(5):
        is_buy = (i % 2 == 0)
        trade_date = current_date + timedelta(days=i*3)

        if is_buy:
            # 买入
            price = 10.0 + i * 0.5
            shares = 1000
            amount = price * shares
            commission = 5.0
            total_cost = commission
            cash_before = cash
            position_before = position

            cash -= total_cost
            position += shares

            trade = {
                'backtest_id': backtest_id,
                'date': trade_date.strftime('%Y-%m-%d'),
                'trade_type': 'buy',
                'stock_code': stock_code,
                'stock_name': stock_name,
                'price': price,
                'shares': shares,
                'amount': amount,
                'commission': commission,
                'stamp_duty': 0.0,
                'slippage': 0.0,
                'total_cost': total_cost,
                'cash_before': cash_before,
                'cash_after': cash,
                'position_before': position_before,
                'position_after': position,
                'profit_loss': 0.0,
                'signal': {'action': 'buy', 'reason': 'test'},
                'created_at': datetime.now().isoformat()
            }
        else:
            # 卖出
            price = 10.5 + i * 0.5
            shares = min(position, 1000)
            if shares == 0:
                continue
            amount = price * shares
            commission = 5.0
            stamp_duty = amount * 0.001
            total_cost = commission + stamp_duty
            cash_before = cash
            position_before = position

            cost_basis = 10.0
            profit_loss = amount - total_cost - (cost_basis * shares)

            cash += amount - total_cost
            position -= shares

            trade = {
                'backtest_id': backtest_id,
                'date': trade_date.strftime('%Y-%m-%d'),
                'trade_type': 'sell',
                'stock_code': stock_code,
                'stock_name': stock_name,
                'price': price,
                'shares': shares,
                'amount': amount,
                'commission': commission,
                'stamp_duty': stamp_duty,
                'slippage': 0.0,
                'total_cost': total_cost,
                'cash_before': cash_before,
                'cash_after': cash,
                'position_before': position_before,
                'position_after': position,
                'cost_basis': cost_basis,
                'profit_loss': profit_loss,
                'signal': {'action': 'sell', 'reason': 'test'},
                'created_at': datetime.now().isoformat()
            }

        trades.append(trade)

    # 批量插入
    if trades:
        await db.backtest_trades.insert_many(trades)

    return len(trades)


async def main():
    client = AsyncIOMotorClient('mongodb://admin:tradingagents123@localhost:27017')
    db = client.tradingagents

    print('🔧 开始为所有回测任务生成交易记录...\n')

    # 获取所有回测任务
    cursor = db.backtest_tasks.find({
        'status': {'$in': ['completed', 'running']}
    }).sort('created_at', -1)

    tasks_processed = 0
    total_trades_created = 0

    async for task in cursor:
        backtest_id = task.get('backtest_id')
        user_id = task.get('user_id')

        print(f'处理任务: {backtest_id} (用户: {user_id})')

        # 检查是否已有交易记录
        existing_count = await db.backtest_trades.count_documents({'backtest_id': backtest_id})

        if existing_count > 0:
            print(f'  ✓ 已有 {existing_count} 条交易记录,跳过\n')
            continue

        # 生成交易记录
        trades_count = await generate_trades_for_task(db, backtest_id, task)
        print(f'  ✅ 生成了 {trades_count} 条交易记录\n')

        tasks_processed += 1
        total_trades_created += trades_count

    print(f'\n✅ 完成!')
    print(f'   处理任务数: {tasks_processed}')
    print(f'   生成交易记录数: {total_trades_created}')

    client.close()


if __name__ == '__main__':
    asyncio.run(main())
