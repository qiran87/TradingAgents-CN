"""
回测结果导出服务单元测试
"""
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from openpyxl import load_workbook
import io

from app.services.export_service import ExportService, ExcelExporter, BacktestResultNotFoundError
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
    backtest_id = f"test_bt_export_{uuid.uuid4().hex[:8]}"

    # 清理可能存在的旧测试数据
    await db.backtest_tasks.delete_many({"backtest_id": {"$regex": "^test_bt_export_"}})
    await db.backtest_results.delete_many({"backtest_id": {"$regex": "^test_bt_export_"}})
    await db.backtest_trades.delete_many({"backtest_id": {"$regex": "^test_bt_export_"}})
    await db.backtest_history.delete_many({"backtest_id": {"$regex": "^test_bt_export_"}})

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
    await db.backtest_results.insert_one({
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
            "dates": ["2023-01-03", "2023-01-04", "2023-01-05", "2023-01-06", "2023-01-09"],
            "total_assets": [100000, 101000, 102000, 103000, 104000],
            "cash": [50000, 50500, 51000, 51500, 52000],
            "position_value": [50000, 50500, 51000, 51500, 52000]
        },
        "created_at": datetime.now(timezone.utc)
    })

    # 插入交易明细
    trades_data = []
    for i in range(5):
        trades_data.append({
            "backtest_id": backtest_id,
            "date": f"2023-01-{i+3:02d}",
            "trade_type": "buy" if i % 2 == 0 else "sell",
            "price": 10.5 + i * 0.1,
            "shares": 1000,
            "amount": (10.5 + i * 0.1) * 1000,
            "commission": 5.0,
            "stamp_duty": 0.0 if i % 2 == 0 else 10.5,
            "total_cost": 5.0 if i % 2 == 0 else 15.5,
            "cash_after": 50000 - i * 1000,
            "position_after": 1000 if i % 2 == 0 else 0
        })

    await db.backtest_trades.insert_many(trades_data)

    # 插入历史记录
    await db.backtest_history.insert_one({
        "record_id": f"hist_export_{backtest_id}",
        "backtest_id": backtest_id,
        "user_id": "test",
        "name": "测试导出记录",
        "description": "用于测试导出功能",
        "tags": ["测试", "导出"],
        "parameters": {
            "stock_code": "000001.SZ",
            "start_date": "2023-01-01",
            "end_date": "2023-01-31",
            "initial_capital": 100000.0,
            "strategy_id": "dual_ma"
        },
        "metrics_snapshot": {
            "total_return": 0.15,
            "max_drawdown": -0.0823,
            "sharpe_ratio": 1.21,
            "win_rate": 0.6,
            "total_trades": 10
        },
        "created_at": datetime.now(timezone.utc)
    })

    return backtest_id


@pytest_asyncio.fixture
def export_service(db):
    """导出服务实例"""
    return ExportService(db)


# ===================== ExcelExporter 测试 =====================

def test_excel_exporter_initialization():
    """测试ExcelExporter初始化"""
    exporter = ExcelExporter()
    assert exporter.styles is not None
    assert exporter.fills is not None
    assert exporter.borders is not None
    assert exporter.alignments is not None


@pytest.mark.asyncio
async def test_export_backtest_results_to_excel(sample_backtest_data, db):
    """测试导出回测结果为Excel"""
    backtest_id = sample_backtest_data

    # 获取数据
    results = await db.backtest_results.find_one({"backtest_id": backtest_id})
    trades_cursor = db.backtest_trades.find({"backtest_id": backtest_id}).sort("date", 1)
    trades = await trades_cursor.to_list(length=None)
    history_record = await db.backtest_history.find_one({"backtest_id": backtest_id})

    # 导出Excel
    exporter = ExcelExporter()
    excel_bytes = exporter.export_backtest_results(
        backtest_id=backtest_id,
        history_record=history_record,
        results=results,
        trades=trades,
        equity_curve=results["equity_curve"]
    )

    # 验证Excel文件
    assert excel_bytes is not None
    assert len(excel_bytes) > 0

    # 加载Excel文件验证结构
    wb = load_workbook(filename=io.BytesIO(excel_bytes))
    assert wb is not None

    # 验证工作表
    assert "回测摘要" in wb.sheetnames
    assert "详细指标" in wb.sheetnames
    assert "交易明细" in wb.sheetnames
    assert "资金曲线" in wb.sheetnames
    assert len(wb.sheetnames) == 4

    # 验证摘要工作表
    summary_ws = wb["回测摘要"]
    assert summary_ws['A1'].value == "回测结果摘要报告"
    assert summary_ws['A4'].value == "基本信息"
    assert summary_ws['A6'].value == "记录名称"
    assert summary_ws['B6'].value == "测试导出记录"

    # 验证交易明细工作表
    trades_ws = wb["交易明细"]
    assert trades_ws['A1'].value == "日期"
    assert trades_ws['B1'].value == "类型"
    assert trades_ws.max_row >= 6  # 5行数据 + 1行表头

    # 验证资金曲线工作表
    equity_ws = wb["资金曲线"]
    assert equity_ws['A1'].value == "日期"
    assert equity_ws['B1'].value == "总资产"
    assert equity_ws.max_row >= 6  # 5行数据 + 1行表头

    wb.close()


# ===================== ExportService 测试 =====================

@pytest.mark.asyncio
async def test_export_backtest_to_excel_success(export_service, sample_backtest_data):
    """测试导出回测结果为Excel文件（成功场景）"""
    backtest_id = sample_backtest_data

    # 导出Excel
    excel_bytes, filename = await export_service.export_backtest_to_excel(
        backtest_id=backtest_id,
        user_id="test"
    )

    # 验证返回值
    assert excel_bytes is not None
    assert len(excel_bytes) > 0
    assert filename.startswith("backtest_")
    assert filename.endswith(".xlsx")

    # 验证可以加载为Excel文件
    wb = load_workbook(filename=io.BytesIO(excel_bytes))
    assert wb is not None
    assert len(wb.sheetnames) == 4
    wb.close()


@pytest.mark.asyncio
async def test_export_backtest_to_excel_not_found(export_service):
    """测试导出不存在的回测结果"""
    from app.services.export_service import ExportServiceError

    with pytest.raises(BacktestResultNotFoundError):
        await export_service.export_backtest_to_excel(
            backtest_id="non_existent_bt",
            user_id="test"
        )


@pytest.mark.asyncio
async def test_export_backtest_to_excel_without_history(export_service, sample_backtest_data, db):
    """测试导出回测结果（无历史记录）"""
    backtest_id = sample_backtest_data

    # 删除历史记录
    await db.backtest_history.delete_many({"backtest_id": backtest_id})

    # 导出Excel
    excel_bytes, filename = await export_service.export_backtest_to_excel(
        backtest_id=backtest_id,
        user_id="test"
    )

    # 验证仍然成功
    assert excel_bytes is not None
    assert len(excel_bytes) > 0

    # 验证Excel文件（没有历史记录部分）
    wb = load_workbook(filename=io.BytesIO(excel_bytes))
    summary_ws = wb["回测摘要"]
    # 应该直接显示参数部分，没有记录名称
    wb.close()


@pytest.mark.asyncio
async def test_export_backtest_to_excel_without_trades(export_service, sample_backtest_data, db):
    """测试导出回测结果（无交易明细）"""
    backtest_id = sample_backtest_data

    # 删除交易明细
    await db.backtest_trades.delete_many({"backtest_id": backtest_id})

    # 导出Excel
    excel_bytes, filename = await export_service.export_backtest_to_excel(
        backtest_id=backtest_id,
        user_id="test"
    )

    # 验证仍然成功
    assert excel_bytes is not None
    assert len(excel_bytes) > 0

    # 验证交易明细工作表只有表头
    wb = load_workbook(filename=io.BytesIO(excel_bytes))
    trades_ws = wb["交易明细"]
    assert trades_ws.max_row == 1  # 只有表头
    wb.close()


# ===================== 集成测试 =====================

@pytest.mark.asyncio
async def test_export_full_workflow(sample_backtest_data, db):
    """测试完整导出工作流"""
    backtest_id = sample_backtest_data

    # 创建服务实例
    service = ExportService(db)

    # 1. 检查导出状态
    results = await db.backtest_results.find_one({"backtest_id": backtest_id})
    trades_count = await db.backtest_trades.count_documents({"backtest_id": backtest_id})

    assert results is not None
    assert trades_count > 0

    # 2. 执行导出
    excel_bytes, filename = await service.export_backtest_to_excel(
        backtest_id=backtest_id,
        user_id="test"
    )

    # 3. 验证文件
    assert excel_bytes is not None
    assert len(excel_bytes) > 1000  # 至少1KB
    assert ".xlsx" in filename

    # 4. 验证Excel内容完整性
    wb = load_workbook(filename=io.BytesIO(excel_bytes))

    # 验证所有工作表存在
    required_sheets = ["回测摘要", "详细指标", "交易明细", "资金曲线"]
    for sheet_name in required_sheets:
        assert sheet_name in wb.sheetnames, f"缺少工作表: {sheet_name}"

    # 验证摘要工作表有关键数据
    summary_ws = wb["回测摘要"]
    assert summary_ws['A1'].value is not None

    # 验证交易明细工作表有正确行数
    trades_ws = wb["交易明细"]
    assert trades_ws.max_row >= trades_count + 1  # 数据行 + 表头

    # 验证资金曲线工作表有数据
    equity_ws = wb["资金曲线"]
    assert equity_ws.max_row > 1

    wb.close()
