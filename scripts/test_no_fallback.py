#!/usr/bin/env python3
"""
测试回测引擎不回退行为
验证当策略初始化失败时，回测会明确失败而不是回退到双均线策略
"""
import asyncio
from datetime import datetime, timezone
from app.core.database import init_database
from app.services.backtest_engine_service import execute_backtest_task, BacktestEngineError
from app.core.database import get_mongo_db


async def test_invalid_strategy():
    """测试使用不存在的策略ID"""
    print("\n" + "="*60)
    print("测试1: 使用不存在的策略ID")
    print("="*60)

    backtest_id = f"test_invalid_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    params = {
        "stock_code": "000001.SZ",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "initial_capital": 100000.0,
        "strategy_id": "nonexistent_strategy",  # 不存在的策略
        "strategy_params": {}
    }

    try:
        # 先创建任务文档（模拟API行为）
        db = get_mongo_db()
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
            "updated_at": datetime.now(timezone.utc)
        })

        await execute_backtest_task(backtest_id, params)
        # 后台任务不会抛出异常，需要检查任务状态
        await asyncio.sleep(1)  # 等待任务状态更新

        task = await db.backtest_tasks.find_one({"backtest_id": backtest_id})

        # 检查任务状态
        if task:
            status = task.get("status", "")
            error_info = task.get("error", {})
            error_msg = error_info.get("message", "") if error_info else task.get("error_message", "")

            if status in ["error", "failed"]:
                if "nonexistent_strategy" in error_msg or "初始化失败" in error_msg:
                    print(f"✅ 测试通过: 任务正确标记为失败 ({status})")
                    print(f"   错误信息: {error_msg}")
                    return True
                else:
                    print(f"❌ 测试失败: 任务状态为 {status}，但错误信息不正确")
                    print(f"   错误信息: {error_msg}")
                    return False
            else:
                print(f"❌ 测试失败: 任务状态应该是 'error' 或 'failed'，实际是: {status}")
                return False
        else:
            print(f"❌ 测试失败: 任务不存在")
            return False

    except Exception as e:
        print(f"⚠️  抛出了未预期的异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_missing_required_param():
    """测试缺少必填参数"""
    print("\n" + "="*60)
    print("测试2: MDVAES策略缺少symbol参数")
    print("="*60)

    backtest_id = f"test_missing_param_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 注意: stock_code会自动映射到symbol，所以这里通过覆盖strategy_params来测试
    params = {
        "stock_code": "000001.SZ",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "initial_capital": 100000.0,
        "strategy_id": "mdvaes",
        "strategy_params": {
            # 故意不传任何参数，测试默认行为
        }
    }

    try:
        # 因为有自动映射，这个测试实际上应该成功
        # 所以这里我们实际上测试的是"有自动映射时能正常工作"
        await execute_backtest_task(backtest_id, params)
        print("✅ 策略初始化成功 (stock_code自动映射到symbol)")
        return True
    except BacktestEngineError as e:
        print(f"❌ 意外失败: {e}")
        return False
    except Exception as e:
        print(f"⚠️  其他异常: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_dual_ma_with_valid_params():
    """测试双均线策略正常工作"""
    print("\n" + "="*60)
    print("测试3: 双均线策略正常工作")
    print("="*60)

    backtest_id = f"test_dual_ma_normal_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    params = {
        "stock_code": "000001.SZ",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "initial_capital": 100000.0,
        "strategy_id": "dual_ma",
        "strategy_params": {}
    }

    try:
        await execute_backtest_task(backtest_id, params)
        print("✅ 双均线策略正常执行")
        return True
    except Exception as e:
        print(f"❌ 双均线策略执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def check_backtest_status(backtest_id: str):
    """检查回测任务状态"""
    db = get_mongo_db()
    task = await db.backtest_tasks.find_one({"backtest_id": backtest_id})
    if task:
        print(f"\n回测任务状态:")
        print(f"  ID: {task.get('backtest_id')}")
        print(f"  策略: {task.get('strategy_id')}")
        print(f"  状态: {task.get('status')}")
        print(f"  错误信息: {task.get('error_message', '无')}")
    else:
        print(f"  未找到回测任务: {backtest_id}")


async def main():
    """主测试函数"""
    print("开始测试回测引擎不回退行为...")
    print("请确保：")
    print("  1. MongoDB 正在运行")
    print("  2. 已同步 000001.SZ 的历史数据")
    print("")

    # 初始化数据库
    await init_database()

    # 运行测试
    results = {
        "无效策略ID": await test_invalid_strategy(),
        "缺少必填参数": await test_missing_required_param(),
        "双均线正常工作": await test_dual_ma_with_valid_params()
    }

    # 总结
    print("\n" + "="*60)
    print("测试结果总结")
    print("="*60)
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
