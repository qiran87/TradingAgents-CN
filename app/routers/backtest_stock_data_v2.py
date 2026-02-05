"""
股票数据API路由 - 回测功能专用（改进版）
提供标准化的股票数据访问接口，用于回测系统

改进项：
3. 错误处理增强 - 统一错误处理和友好的错误信息
4. API响应格式统一 - 统一使用 ok(data) 格式
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from app.services.backtest_stock_data_service_v2 import (
    BacktestStockDataService,
    get_backtest_stock_data_service,
    StockNotFoundError,
    DataNotFoundError,
    StockDataError
)
from app.core.response import ok

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backtest/stock", tags=["backtest-stock-data"])


# ===================== 请求/响应模型 =====================

class StockInfoResponse(BaseModel):
    """股票信息响应"""
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    market: str = Field(..., description="市场")
    industry: Optional[str] = Field(None, description="行业")
    list_date: Optional[str] = Field(None, description="上市日期")

    # 数据统计信息
    data_range: dict = Field(..., description="数据范围")
    data_completeness: float = Field(..., description="数据完整性百分比")
    total_trading_days: int = Field(..., description="总交易日数")
    last_updated: Optional[str] = Field(None, description="最后更新时间")


class QuoteData(BaseModel):
    """行情数据"""
    date: str = Field(..., description="日期 YYYY-MM-DD")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: int = Field(..., description="成交量")
    amount: float = Field(..., description="成交额")


class QuotesListResponse(BaseModel):
    """行情列表响应"""
    stock_code: str = Field(..., description="股票代码")
    quotes: List[QuoteData] = Field(..., description="行情数据列表")
    total: int = Field(..., description="总记录数")


class DataAvailabilityInfo(BaseModel):
    """数据可用性信息"""
    stock_code: str = Field(..., description="股票代码")
    date_range: dict = Field(..., description="日期范围")
    is_available: bool = Field(..., description="是否可用")
    coverage: float = Field(..., description="数据覆盖率")
    missing_dates: List[str] = Field(default_factory=list, description="缺失日期")
    first_available_date: Optional[str] = Field(None, description="第一个可用日期")
    last_available_date: Optional[str] = Field(None, description="最后一个可用日期")


class StockSearchResult(BaseModel):
    """股票搜索结果"""
    stock_code: str = Field(..., description="股票代码")
    stock_name: str = Field(..., description="股票名称")
    market: str = Field(..., description="市场")
    industry: Optional[str] = Field(None, description="行业")


class StockSearchResponse(BaseModel):
    """股票搜索响应"""
    stocks: List[StockSearchResult] = Field(..., description="股票列表")


# ===================== 依赖注入 =====================

def get_stock_service() -> BacktestStockDataService:
    """获取回测股票数据服务实例"""
    return get_backtest_stock_data_service()


# ===================== API端点 =====================

@router.get("/info", response_model=dict)
async def get_stock_info(
    stock_code: str = Query(..., description="股票代码（如 000001.SZ 或 000001）"),
    service: BacktestStockDataService = Depends(get_stock_service)
):
    """
    获取股票基础信息

    返回股票的基本信息和数据统计信息，包括：
    - 基本信息：代码、名称、市场、行业、上市日期
    - 数据统计：数据范围、完整性、总交易日数

    示例：
    - GET /api/backtest/stock/info?stock_code=000001.SZ
    - GET /api/backtest/stock/info?stock_code=000001
    """
    try:
        stock_info = await service.get_stock_info(stock_code)
        # 改进4：统一响应格式
        return ok(data=stock_info)

    except StockNotFoundError as e:
        # 改进3：统一错误处理
        logger.warning(f"股票不存在: {stock_code}")
        raise HTTPException(
            status_code=404,
            detail=f"股票 {stock_code} 不存在"
        )
    except StockDataError as e:
        logger.error(f"获取股票信息失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取股票信息失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"获取股票信息时发生未预期错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="服务器内部错误"
        )


@router.get("/quotes", response_model=dict)
async def get_quotes(
    stock_code: str = Query(..., description="股票代码（如 000001.SZ 或 000001）"),
    start_date: str = Query(..., description="起始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    service: BacktestStockDataService = Depends(get_stock_service)
):
    """
    获取历史行情数据

    返回指定日期范围内的所有交易日行情数据，包括：
    - 开盘价、最高价、最低价、收盘价
    - 成交量、成交额

    示例：
    - GET /api/backtest/stock/quotes?stock_code=000001.SZ&start_date=2023-01-01&end_date=2023-12-31
    """
    try:
        quotes = await service.get_quotes(stock_code, start_date, end_date)

        # 改进4：统一响应格式
        return ok(data={
            "stock_code": stock_code,
            "quotes": quotes,
            "total": len(quotes)
        })

    except DataNotFoundError as e:
        # 改进3：统一错误处理
        logger.warning(f"行情数据不存在: {stock_code} {start_date} - {end_date}")
        raise HTTPException(
            status_code=404,
            detail=str(e)
        )
    except StockDataError as e:
        logger.error(f"获取行情数据失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取行情数据失败: {str(e)}"
        )
    except Exception as e:
        logger.error(f"获取行情数据时发生未预期错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="服务器内部错误"
        )


@router.get("/quotes/check-availability", response_model=dict)
async def check_data_availability(
    stock_code: str = Query(..., description="股票代码（如 000001.SZ 或 000001）"),
    start_date: str = Query(..., description="起始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    service: BacktestStockDataService = Depends(get_stock_service)
):
    """
    检查数据可用性

    检查指定日期范围内的数据是否完整，返回：
    - 数据覆盖率
    - 缺失的交易日列表
    - 第一个和最后一个可用日期
    - 是否可用（覆盖率 >= 95%）

    示例：
    - GET /api/backtest/stock/quotes/check-availability?stock_code=000001.SZ&start_date=2023-01-01&end_date=2023-12-31
    """
    try:
        availability = await service.check_data_availability(stock_code, start_date, end_date)

        # 改进4：统一响应格式
        return ok(data=availability)

    except Exception as e:
        logger.error(f"检查数据可用性失败: {e}", exc_info=True)
        # 改进3：即使失败也返回部分结果
        raise HTTPException(
            status_code=500,
            detail=f"检查数据可用性失败: {str(e)}"
        )


@router.get("/search", response_model=dict)
async def search_stocks(
    keyword: str = Query(..., min_length=1, description="搜索关键词（股票代码或名称）"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    service: BacktestStockDataService = Depends(get_stock_service)
):
    """
    搜索股票

    支持按股票代码或股票名称搜索：
    - 数字关键词：按股票代码搜索（支持模糊匹配）
    - 文字关键词：按股票名称搜索（支持模糊匹配）

    示例：
    - GET /api/backtest/stock/search?keyword=000001&limit=10
    - GET /api/backtest/stock/search?keyword=平安&limit=10
    """
    try:
        stocks = await service.search_stocks(keyword, limit)

        # 改进4：统一响应格式
        return ok(data={
            "stocks": stocks,
            "total": len(stocks)
        })

    except Exception as e:
        logger.error(f"搜索股票失败 keyword={keyword}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"搜索股票失败: {str(e)}"
        )
