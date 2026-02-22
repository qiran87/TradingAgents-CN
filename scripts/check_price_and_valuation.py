#!/usr/bin/env python3
"""检查价格和估值的关系"""
import asyncio
from app.core.database import init_database, get_mongo_db


async def main():
    await init_database()
    db = get_mongo_db()

    # 获取最新的MDVAES测试任务
    task = await db.backtest_tasks.find_one(
        {'backtest_id': {'$regex': 'test_mdvaes'}},
        sort=[('created_at', -1)]
    )

    if not task:
        print("未找到MDVAES测试任务")
        return

    backtest_id = task['backtest_id']
    print(f"检查回测任务: {backtest_id}\n")

    # 获取每日状态和价格
    states = await db.backtest_daily_states.find({
        "backtest_id": backtest_id
    }).sort("date", 1).to_list(None)

    print("="*80)
    print("价格 vs 估值分析")
    print("="*80)
    print(f"{'日期':<12} {'收盘价':<10} {'内在价值':<12} {'下限':<10} {'上限':<10} {'信号':<8} {'说明'}")
    print("-"*80)

    for state in states:
        date = state.get("date", "")
        price = state.get("current_price", 0)
        val = state.get("valuation", {})
        intrinsic = val.get("intrinsic_value", 0)
        lower = val.get("lower_bound", 0)
        upper = val.get("upper_bound", 0)
        signal = val.get("signal", "N/A")

        # 分析价格位置
        if intrinsic > 0:
            if price < lower:
                note = "低于下限，应买入"
            elif price > upper:
                note = "高于上限，应卖出"
            else:
                note = "在区间内，持有"
        else:
            note = "无估值"

        print(f"{date:<12} {price:<10.2f} {intrinsic:<12.2f} {lower:<10.2f} {upper:<10.2f} {signal:<8} {note}")

    print("="*80)

    # 统计
    buy_signals = sum(1 for s in states if s.get("valuation", {}).get("signal") == "buy")
    sell_signals = sum(1 for s in states if s.get("valuation", {}).get("signal") == "sell")
    hold_signals = sum(1 for s in states if s.get("valuation", {}).get("signal") == "hold")

    print(f"\n信号统计:")
    print(f"  买入信号: {buy_signals}")
    print(f"  卖出信号: {sell_signals}")
    print(f"  持有信号: {hold_signals}")

    # 检查是否有价格突破区间的情况
    breakthroughs = []
    for state in states:
        price = state.get("current_price", 0)
        val = state.get("valuation", {})
        lower = val.get("lower_bound", 0)
        upper = val.get("upper_bound", 0)
        if price < lower and val.get("signal") != "buy":
            breakthroughs.append(f"{state.get('date')}: 价格 {price:.2f} < 下限 {lower:.2f}，但信号不是buy")
        elif price > upper and val.get("signal") != "sell":
            breakthroughs.append(f"{state.get('date')}: 价格 {price:.2f} > 上限 {upper:.2f}，但信号不是sell")

    if breakthroughs:
        print(f"\n⚠️  发现不一致:")
        for b in breakthroughs[:5]:  # 只显示前5条
            print(f"  {b}")
    else:
        print(f"\n✅ 信号与价格区间一致")


if __name__ == "__main__":
    asyncio.run(main())
