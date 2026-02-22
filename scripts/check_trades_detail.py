#!/usr/bin/env python3
"""检查交易详情"""
import asyncio
from app.core.database import init_database, get_mongo_db


async def main():
    await init_database()
    db = get_mongo_db()

    backtest_id = "test_mdvaes_full_20260221_192941"

    # 获取交易记录
    trades = await db.backtest_trades.find({
        "backtest_id": backtest_id
    }).sort("date", 1).to_list(None)

    print("="*80)
    print("交易记录详情")
    print("="*80)
    print(f"总交易数: {len(trades)}")
    print()

    for trade in trades:
        print(f"日期: {trade.get('date')}")
        print(f"  类型: {trade.get('action', 'N/A')}")
        print(f"  数量: {trade.get('shares', 0)} 股")
        print(f"  价格: {trade.get('price', 0):.2f} 元")
        print(f"  金额: {trade.get('amount', 0):.2f} 元")
        reason = trade.get('reason')
        if reason:
            print(f"  原因: {reason[:80]}...")
        print()

    # 获取最终状态
    final_state = await db.backtest_daily_states.find_one({
        "backtest_id": backtest_id
    }, sort=[("date", -1)])

    if final_state:
        print("="*80)
        print("最终状态")
        print("="*80)
        print(f"日期: {final_state.get('date')}")
        print(f"现金: {final_state.get('cash', 0):.2f} 元")
        print(f"持仓: {final_state.get('position', 0)} 股")
        print(f"当前价格: {final_state.get('current_price', 0):.2f} 元")
        print(f"持仓市值: {final_state.get('market_value', 0):.2f} 元")

        # 计算总资产
        total = final_state.get('cash', 0) + final_state.get('market_value', 0)
        print(f"总资产: {total:.2f} 元")

        # 计算收益
        initial_capital = 100000.0
        profit = total - initial_capital
        profit_pct = (profit / initial_capital) * 100
        print(f"初始资金: {initial_capital:.2f} 元")
        print(f"收益: {profit:.2f} 元 ({profit_pct:.2f}%)")

    # 检查价格变化
    print()
    print("="*80)
    print("价格变化分析")
    print("="*80)
    first_price = await db.backtest_daily_states.find_one({
        "backtest_id": backtest_id
    }, sort=[("date", 1)])

    if first_price and final_state:
        first = first_price.get("current_price", 0)
        last = final_state.get("current_price", 0)
        price_change = ((last - first) / first) * 100 if first > 0 else 0
        print(f"首日价格: {first:.2f} 元")
        print(f"末日价格: {last:.2f} 元")
        print(f"价格变化: {price_change:.2f}%")


if __name__ == "__main__":
    asyncio.run(main())
