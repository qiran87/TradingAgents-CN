#!/usr/bin/env python3
"""
测试估值历史API
"""
import asyncio
from datetime import datetime, timezone
from app.core.database import init_database, get_mongo_db
from app.services.backtest_engine_service import execute_backtest_task


async def main():
    await init_database()
    db = get_mongo_db()

    # 创建测试回测
    backtest_id = f"test_api_valuation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    params = {
        "stock_code": "000001.SZ",
        "start_date": "2024-01-01",
        "end_date": "2024-01-10",  # 缩短时间范围
        "initial_capital": 100000.0,
        "strategy_id": "mdvaes",
        "strategy_params": {
            "forecast_years": 5,
            "peg_base": 1.0,
            "rebalance_frequency": 90
        }
    }

    # 创建任务文档（需要模拟用户认证）
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
        "updated_at": datetime.now(timezone.utc),
        "user_id": "test_user"  # 模拟用户
    })

    # 执行回测
    print(f"执行回测: {backtest_id}")
    await execute_backtest_task(backtest_id, params)

    # 检查估值数据
    print("\n检查估值数据...")
    valuation_states = await db.backtest_daily_states.count_documents({
        "backtest_id": backtest_id,
        "valuation": {"$exists": True}
    })
    print(f"有估值数据的状态数: {valuation_states}")

    if valuation_states > 0:
        sample = await db.backtest_daily_states.find_one({
            "backtest_id": backtest_id,
            "valuation": {"$exists": True}
        })
        print(f"\n样本数据:")
        print(f"  日期: {sample.get('date')}")
        print(f"  估值字段: {sample.get('valuation')}")

        # 模拟API查询
        print(f"\n模拟API查询...")
        cursor = db.backtest_daily_states.find(
            {"backtest_id": backtest_id, "valuation": {"$exists": True}},
            sort=[("bar_index", 1)]
        ).project({
            "_id": 0,
            "date": 1,
            "current_price": 1,
            "valuation": 1
        })

        valuation_history = await cursor.to_list(length=None)
        print(f"查询到的记录数: {len(valuation_history)}")

        if valuation_history:
            print(f"\n格式化后的第一条记录:")
            item = valuation_history[0]
            valuation = item.get("valuation", {})
            formatted = {
                "date": item["date"],
                "current_price": item.get("current_price"),
                "intrinsic_value": valuation.get("intrinsic_value"),
                "lower_bound": valuation.get("lower_bound"),
                "upper_bound": valuation.get("upper_bound"),
                "confidence": valuation.get("confidence"),
                "signal": valuation.get("signal"),
                "valuation_method": valuation.get("valuation_method")
            }
            print(f"  {formatted}")
    else:
        print("没有估值数据！")

    print(f"\n测试回测ID: {backtest_id}")
    print(f"可通过 API 测试: GET /api/backtest/{backtest_id}/valuation-history")


if __name__ == "__main__":
    asyncio.run(main())
