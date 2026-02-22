#!/usr/bin/env python3
"""
直接测试估值API（不使用project方法）
"""
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
    print(f"测试回测任务: {backtest_id}")
    print(f"策略ID: {task.get('strategy_id')}")
    print()

    # 模拟API查询（不使用project）
    print("模拟API查询...")
    cursor = db.backtest_daily_states.find(
        {"backtest_id": backtest_id, "valuation": {"$exists": True}},
        sort=[("bar_index", 1)]
    )

    valuation_history = await cursor.to_list(length=None)
    print(f"查询到的记录数: {len(valuation_history)}")

    if valuation_history:
        # 手动选择字段（替代project）
        formatted_history = []
        for item in valuation_history:
            valuation = item.get("valuation", {})
            formatted_history.append({
                "date": item.get("date"),
                "current_price": item.get("current_price"),
                "intrinsic_value": valuation.get("intrinsic_value"),
                "lower_bound": valuation.get("lower_bound"),
                "upper_bound": valuation.get("upper_bound"),
                "confidence": valuation.get("confidence"),
                "signal": valuation.get("signal"),
                "valuation_method": valuation.get("valuation_method")
            })

        print(f"\n格式化后的记录数: {len(formatted_history)}")
        print(f"\n前3条记录:")
        for i, item in enumerate(formatted_history[:3], 1):
            print(f"  {i}. {item}")

        # 检查API响应格式
        print(f"\n模拟API响应:")
        api_response = {
            "success": True,
            "data": {
                "backtest_id": backtest_id,
                "strategy_id": task.get('strategy_id'),
                "total_count": len(formatted_history),
                "valuation_history": formatted_history
            },
            "message": "",
            "timestamp": "2024-01-01T00:00:00"
        }
        print(f"  success: {api_response['success']}")
        print(f"  total_count: {api_response['data']['total_count']}")
        print(f"  data keys: {list(api_response['data'].keys())}")

        # 检查前端期望的数据结构
        print(f"\n前端数据验证:")
        if formatted_history:
            first = formatted_history[0]
            print(f"  date: {first.get('date')}")
            print(f"  current_price: {first.get('current_price')}")
            print(f"  intrinsic_value: {first.get('intrinsic_value')}")
            print(f"  lower_bound: {first.get('lower_bound')}")
            print(f"  upper_bound: {first.get('upper_bound')}")
            print(f"  signal: {first.get('signal')}")
            print(f"  所有字段存在: {all(k in first for k in ['date', 'current_price', 'intrinsic_value', 'lower_bound', 'upper_bound', 'signal'])}")

    else:
        print("没有估值数据！")


if __name__ == "__main__":
    asyncio.run(main())
