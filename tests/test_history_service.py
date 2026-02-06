"""
回测历史记录管理服务单元测试
"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient

from app.services.history_service import HistoryService
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
    import uuid
    backtest_id = f"test_bt_history_{uuid.uuid4().hex[:8]}"

    # 清理可能存在的旧测试数据
    await db.backtest_tasks.delete_many({"backtest_id": {"$regex": "^test_bt_history_"}})
    await db.backtest_results.delete_many({"backtest_id": {"$regex": "^test_bt_history_"}})
    await db.backtest_history.delete_many({"backtest_id": {"$regex": "^test_bt_history_"}})

    # 插入回测任务
    await db.backtest_tasks.insert_one({
        "backtest_id": backtest_id,
        "user_id": "test",
        "status": "completed",
        "parameters": {
            "stock_code": "000001.SZ",
            "start_date": "2023-01-01",
            "end_date": "2023-01-31",
            "initial_capital": 100000.0,
            "strategy_id": "dual_ma",
            "strategy_params": {}
        },
        "execution_info": {
            "final_value": 115000.0,
            "total_return": 15.0
        },
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    })

    # 插入回测结果
    result_id = await db.backtest_results.insert_one({
        "backtest_id": backtest_id,
        "return_metrics": {
            "total_return": 0.15,
            "annual_return": 1.82,
            "cumulative_returns": [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10, 0.11, 0.12, 0.13, 0.14, 0.15],
            "daily_returns": [0.01] * 15
        },
        "risk_metrics": {
            "max_drawdown": -0.0823,
            "volatility": 0.15,
            "downside_volatility": 0.12,
            "var_95": -0.025
        },
        "risk_adjusted_metrics": {
            "sharpe_ratio": 1.21,
            "sortino_ratio": 1.52,
            "calmar_ratio": 2.21
        },
        "trading_stats": {
            "total_trades": 10,
            "winning_trades": 6,
            "losing_trades": 4,
            "win_rate": 0.6,
            "avg_profit": 2500.0,
            "avg_loss": -1500.0,
            "profit_loss_ratio": 1.67
        },
        "equity_curve": {
            "dates": ["2023-01-03", "2023-01-04", "2023-01-05"],
            "total_assets": [100000, 101000, 102000],
            "cash": [50000, 50500, 51000],
            "position_value": [50000, 50500, 51000]
        },
        "created_at": datetime.now(timezone.utc)
    })

    return {
        "backtest_id": backtest_id,
        "result_id": str(result_id.inserted_id)
    }


@pytest_asyncio.fixture
async def history_service(db):
    """历史记录服务实例"""
    return HistoryService(db)


# ===================== 测试用例 =====================

@pytest.mark.asyncio
async def test_save_to_history(history_service, sample_backtest_data):
    """测试保存到历史记录"""
    backtest_id = sample_backtest_data["backtest_id"]

    result = await history_service.save_to_history(
        backtest_id=backtest_id,
        name="测试历史记录",
        description="这是一个测试记录",
        tags=["测试", "双均线"],
        user_id="test"
    )

    assert result["record_id"].startswith("hist_")
    assert result["name"] == "测试历史记录"
    assert result["message"] == "已保存到历史记录"


@pytest.mark.asyncio
async def test_save_to_history_not_found(history_service, db):
    """测试保存不存在的回测"""
    from app.services.history_service import BacktestResultNotFoundError

    with pytest.raises(BacktestResultNotFoundError):
        await history_service.save_to_history(
            backtest_id="non_existent_bt",
            name="测试",
            user_id="test"
        )


@pytest.mark.asyncio
async def test_get_history_list(history_service, sample_backtest_data):
    """测试获取历史记录列表"""
    # 先保存一条记录
    backtest_id = sample_backtest_data["backtest_id"]
    await history_service.save_to_history(
        backtest_id=backtest_id,
        name="测试记录1",
        user_id="test"
    )

    # 获取列表
    result = await history_service.get_history_list(
        user_id="test",
        skip=0,
        limit=20
    )

    assert result["total"] >= 1
    assert len(result["records"]) >= 1
    assert any(r["name"] == "测试记录1" for r in result["records"])


@pytest.mark.asyncio
async def test_get_history_list_with_filters(history_service, sample_backtest_data):
    """测试带筛选条件的历史记录列表"""
    backtest_id = sample_backtest_data["backtest_id"]

    # 保存两条记录
    await history_service.save_to_history(
        backtest_id=backtest_id,
        name="双均线测试",
        user_id="test"
    )

    # 按策略筛选
    result = await history_service.get_history_list(
        user_id="test",
        skip=0,
        limit=20,
        strategy_id="dual_ma"
    )

    assert result["total"] >= 1
    assert all(r["parameters"]["strategy_id"] == "dual_ma" for r in result["records"])

    # 按股票筛选
    result = await history_service.get_history_list(
        user_id="test",
        skip=0,
        limit=20,
        stock_code="000001.SZ"
    )

    assert result["total"] >= 1
    assert all(r["parameters"]["stock_code"] == "000001.SZ" for r in result["records"])

    # 按关键词搜索
    result = await history_service.get_history_list(
        user_id="test",
        skip=0,
        limit=20,
        search="双均线"
    )

    assert result["total"] >= 1


@pytest.mark.asyncio
async def test_get_history_detail(history_service, sample_backtest_data):
    """测试获取历史记录详情"""
    backtest_id = sample_backtest_data["backtest_id"]

    # 保存记录
    save_result = await history_service.save_to_history(
        backtest_id=backtest_id,
        name="详情测试",
        description="测试详情功能",
        user_id="test"
    )

    record_id = save_result["record_id"]

    # 获取详情
    result = await history_service.get_history_detail(
        record_id=record_id,
        user_id="test"
    )

    assert result["history"]["name"] == "详情测试"
    assert result["history"]["description"] == "测试详情功能"
    assert result["results"]["return_metrics"]["total_return"] == 0.15


@pytest.mark.asyncio
async def test_get_history_detail_not_found(history_service):
    """测试获取不存在的历史记录详情"""
    from app.services.history_service import HistoryRecordNotFoundError

    with pytest.raises(HistoryRecordNotFoundError):
        await history_service.get_history_detail(
            record_id="non_existent_hist",
            user_id="test"
        )


@pytest.mark.asyncio
async def test_compare_history(history_service, sample_backtest_data, db):
    """测试对比历史记录"""
    backtest_id = sample_backtest_data["backtest_id"]

    # 保存两条记录
    result1 = await history_service.save_to_history(
        backtest_id=backtest_id,
        name="对比记录1",
        user_id="test"
    )

    result2 = await history_service.save_to_history(
        backtest_id=backtest_id,
        name="对比记录2",
        user_id="test"
    )

    # 对比
    result = await history_service.compare_history(
        record_ids=[result1["record_id"], result2["record_id"]],
        user_id="test"
    )

    assert len(result["records"]) == 2
    assert result["records"][0]["name"] == "对比记录1"
    assert result["records"][1]["name"] == "对比记录2"


@pytest.mark.asyncio
async def test_compare_history_too_many(history_service):
    """测试对比过多记录"""
    from app.services.history_service import InvalidComparisonError

    with pytest.raises(InvalidComparisonError):
        await history_service.compare_history(
            record_ids=["hist1", "hist2", "hist3", "hist4"],
            user_id="test"
        )


@pytest.mark.asyncio
async def test_delete_history(history_service, sample_backtest_data):
    """测试软删除历史记录（移至回收站）"""
    backtest_id = sample_backtest_data["backtest_id"]

    # 保存记录
    save_result = await history_service.save_to_history(
        backtest_id=backtest_id,
        name="待删除记录",
        user_id="test"
    )

    record_id = save_result["record_id"]

    # 软删除记录（移至回收站）
    result = await history_service.delete_history(
        record_id=record_id,
        user_id="test",
        permanent=False  # 显式指定软删除
    )

    assert result["message"] == "历史记录已移至回收站"

    # 验证记录被标记为已删除
    history = await history_service.db.backtest_history.find_one({
        "record_id": record_id,
        "user_id": "test"
    })
    assert history is not None
    assert history["is_deleted"] == True
    assert history.get("deleted_at") is not None


@pytest.mark.asyncio
async def test_delete_history_permanent(history_service, sample_backtest_data):
    """测试永久删除历史记录"""
    backtest_id = sample_backtest_data["backtest_id"]

    # 保存记录
    save_result = await history_service.save_to_history(
        backtest_id=backtest_id,
        name="待永久删除记录",
        user_id="test"
    )

    record_id = save_result["record_id"]

    # 永久删除记录
    result = await history_service.delete_history(
        record_id=record_id,
        user_id="test",
        permanent=True  # 永久删除
    )

    assert result["message"] == "历史记录已永久删除"

    # 验证记录已从数据库中删除
    history = await history_service.db.backtest_history.find_one({
        "record_id": record_id,
        "user_id": "test"
    })
    assert history is None


@pytest.mark.asyncio
async def test_delete_history_not_found(history_service):
    """测试删除不存在的记录"""
    from app.services.history_service import HistoryRecordNotFoundError

    with pytest.raises(HistoryRecordNotFoundError):
        await history_service.delete_history(
            record_id="non_existent_hist",
            user_id="test"
        )
