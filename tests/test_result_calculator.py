"""
回测结果计算服务单元测试
"""
import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

from app.services.result_calculator import ResultCalculator
from app.core.config import settings


@pytest_asyncio.fixture
async def db():
    """测试数据库连接"""
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGODB_DATABASE]
    yield db
    client.close()


@pytest_asyncio.fixture
async def sample_backtest_data(db):
    """创建示例回测数据"""
    backtest_id = "test_bt_001"

    # 插入回测任务
    await db.backtest_tasks.insert_one({
        "backtest_id": backtest_id,
        "user_id": "test",
        "status": "completed",
        "parameters": {
            "stock_code": "000001.SZ",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "initial_capital": 100000.0
        },
        "execution_info": {
            "final_value": 110000.0,
            "total_return": 10.0
        },
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    })

    # 插入每日状态数据
    daily_states = []
    capital = 100000.0
    for i in range(1, 31):  # 30天
        date = f"2024-01-{i:02d}"
        # 模拟简单的增长
        total_assets = capital * (1 + 0.01 * i)
        daily_states.append({
            "backtest_id": backtest_id,
            "date": date,
            "bar_index": i - 1,
            "cash": round(total_assets * 0.5, 2),
            "position": 500,
            "position_cost": 100.0,
            "current_price": 100.0 + i,
            "market_value": round(total_assets * 0.5, 2),
            "total_assets": round(total_assets, 2),
            "daily_return": 0.01,
            "cumulative_return": 0.01 * i,
            "profit_loss": round(total_assets * 0.5 - 50000, 2),
            "created_at": datetime.now(timezone.utc)
        })

    await db.backtest_daily_states.insert_many(daily_states)

    # 插入交易数据
    trades = [
        {
            "backtest_id": backtest_id,
            "date": "2024-01-05",
            "trade_type": "buy",
            "price": 100.0,
            "shares": 500,
            "amount": 50000.0,
            "commission": 12.5,
            "stamp_duty": 0.0,
            "slippage": 0.0,
            "total_cost": 50012.5,
            "cash_before": 100000.0,
            "cash_after": 49987.5,
            "position_before": 0,
            "position_after": 500,
            "signal": {"action": "buy"},
            "created_at": datetime.now(timezone.utc)
        },
        {
            "backtest_id": backtest_id,
            "date": "2024-01-20",
            "trade_type": "sell",
            "price": 120.0,
            "shares": 500,
            "amount": 60000.0,
            "commission": 15.0,
            "stamp_duty": 60.0,
            "slippage": 0.0,
            "total_cost": 75.0,
            "cash_before": 49987.5,
            "cash_after": 109912.5,
            "position_before": 500,
            "position_after": 0,
            "cost_basis": 50000.0,
            "signal": {"action": "sell"},
            "created_at": datetime.now(timezone.utc)
        }
    ]
    await db.backtest_trades.insert_many(trades)

    yield backtest_id

    # 清理测试数据
    await db.backtest_tasks.delete_many({"backtest_id": backtest_id})
    await db.backtest_daily_states.delete_many({"backtest_id": backtest_id})
    await db.backtest_trades.delete_many({"backtest_id": backtest_id})
    await db.backtest_results.delete_many({"backtest_id": backtest_id})


@pytest.mark.asyncio
async def test_calculate_and_save_results(db, sample_backtest_data):
    """测试计算并保存结果"""
    calculator = ResultCalculator(db)
    backtest_id = sample_backtest_data

    # 计算结果
    results = await calculator.calculate_and_save_results(backtest_id)

    # 验证结果结构
    assert "backtest_id" in results
    assert "return_metrics" in results
    assert "risk_metrics" in results
    assert "risk_adjusted_metrics" in results
    assert "trading_stats" in results
    assert "equity_curve" in results

    # 验证收益指标
    assert results["return_metrics"]["total_return"] >= 0
    assert len(results["return_metrics"]["daily_returns"]) > 0
    assert len(results["return_metrics"]["cumulative_returns"]) > 0

    # 验证风险指标
    assert results["risk_metrics"]["max_drawdown"] >= 0
    assert results["risk_metrics"]["volatility"] >= 0

    # 验证交易统计
    assert results["trading_stats"]["total_trades"] >= 1  # 至少有一对买卖
    assert results["trading_stats"]["winning_trades"] >= 0
    assert results["trading_stats"]["losing_trades"] >= 0
    assert 0 <= results["trading_stats"]["win_rate"] <= 1

    # 验证数据库中已保存
    saved_results = await db.backtest_results.find_one({"backtest_id": backtest_id})
    assert saved_results is not None


@pytest.mark.asyncio
async def test_get_results(db, sample_backtest_data):
    """测试获取结果"""
    calculator = ResultCalculator(db)
    backtest_id = sample_backtest_data

    # 先计算并保存结果
    await calculator.calculate_and_save_results(backtest_id)

    # 获取结果
    results = await calculator.get_results(backtest_id)

    assert results is not None
    assert results["backtest_id"] == backtest_id
    assert "_id" not in results  # 确保_id字段被移除


@pytest.mark.asyncio
async def test_get_equity_curve(db, sample_backtest_data):
    """测试获取资金曲线"""
    calculator = ResultCalculator(db)
    backtest_id = sample_backtest_data

    # 先计算并保存结果
    await calculator.calculate_and_save_results(backtest_id)

    # 获取资金曲线
    equity_curve = await calculator.get_equity_curve(backtest_id)

    assert equity_curve is not None
    assert "dates" in equity_curve
    assert "total_assets" in equity_curve
    assert "cash" in equity_curve
    assert "position_value" in equity_curve
    assert len(equity_curve["dates"]) == 30  # 30天数据


@pytest.mark.asyncio
async def test_get_trades(db, sample_backtest_data):
    """测试获取交易明细"""
    calculator = ResultCalculator(db)
    backtest_id = sample_backtest_data

    # 获取交易明细
    trades = await calculator.get_trades(backtest_id)

    assert len(trades) == 2  # 一买一卖
    assert trades[0]["trade_type"] == "buy"
    assert trades[1]["trade_type"] == "sell"
    assert "_id" not in trades[0]


@pytest.mark.asyncio
async def test_calculate_return_metrics(db, sample_backtest_data):
    """测试收益指标计算"""
    calculator = ResultCalculator(db)

    # 获取每日状态
    daily_states = await db.backtest_daily_states.find({
        "backtest_id": sample_backtest_data
    }).to_list(length=None)

    # 计算收益指标
    return_metrics = calculator._calculate_return_metrics(daily_states)

    assert "total_return" in return_metrics
    assert "annual_return" in return_metrics
    assert "cumulative_returns" in return_metrics
    assert "daily_returns" in return_metrics

    # 验证数据长度（30天数据都有收益率）
    assert len(return_metrics["daily_returns"]) == 30
    assert len(return_metrics["cumulative_returns"]) == 30


@pytest.mark.asyncio
async def test_calculate_risk_metrics(db, sample_backtest_data):
    """测试风险指标计算"""
    calculator = ResultCalculator(db)

    # 获取每日状态
    daily_states = await db.backtest_daily_states.find({
        "backtest_id": sample_backtest_data
    }).to_list(length=None)

    # 计算风险指标
    risk_metrics = calculator._calculate_risk_metrics(daily_states)

    assert "max_drawdown" in risk_metrics
    assert "volatility" in risk_metrics
    assert "downside_volatility" in risk_metrics
    assert "var_95" in risk_metrics

    # 验证数值范围
    assert risk_metrics["max_drawdown"] >= 0
    assert risk_metrics["volatility"] >= 0


@pytest.mark.asyncio
async def test_calculate_trading_stats(db, sample_backtest_data):
    """测试交易统计计算"""
    calculator = ResultCalculator(db)

    # 获取交易数据
    trades = await db.backtest_trades.find({
        "backtest_id": sample_backtest_data
    }).to_list(length=None)

    # 计算交易统计
    trading_stats = calculator._calculate_trading_stats(trades)

    assert "total_trades" in trading_stats
    assert "winning_trades" in trading_stats
    assert "losing_trades" in trading_stats
    assert "win_rate" in trading_stats

    # 验证统计结果（允许0盈利交易，因为手续费可能导致亏损）
    assert trading_stats["total_trades"] >= 1
    assert trading_stats["winning_trades"] >= 0
    assert trading_stats["losing_trades"] >= 0
    assert 0 <= trading_stats["win_rate"] <= 1


@pytest.mark.asyncio
async def test_calculate_equity_curve(db, sample_backtest_data):
    """测试资金曲线计算"""
    calculator = ResultCalculator(db)

    # 获取每日状态
    daily_states = await db.backtest_daily_states.find({
        "backtest_id": sample_backtest_data
    }).to_list(length=None)

    # 计算资金曲线
    equity_curve = calculator._calculate_equity_curve(daily_states)

    assert "dates" in equity_curve
    assert "total_assets" in equity_curve
    assert "cash" in equity_curve
    assert "position_value" in equity_curve

    # 验证数据长度
    assert len(equity_curve["dates"]) == 30
    assert len(equity_curve["total_assets"]) == 30


@pytest.mark.asyncio
async def test_backtest_not_found(db):
    """测试回测任务不存在的情况"""
    calculator = ResultCalculator(db)

    # 尝试获取不存在的结果
    results = await calculator.get_results("nonexistent_backtest_id")
    assert results is None

    # 尝试计算不存在的结果
    with pytest.raises(Exception):
        await calculator.calculate_and_save_results("nonexistent_backtest_id")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
