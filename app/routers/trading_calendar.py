"""
交易日历API路由
提供交易日查询、判断、统计等接口
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
import logging

from app.core.database import get_mongo_db
from app.core.response import ok
from app.services.trading_calendar_service import TradingCalendarService
from app.models.trading_calendar import (
    TradingDayInfo,
    TradingDaysListResponse,
    TradingCalendarInfo as TradingCalendarInfoModel,
    PreviousTradingDayResponse,
    NextTradingDayResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backtest/trading-days", tags=["backtest-trading-calendar"])


def get_trading_calendar_service() -> TradingCalendarService:
    """获取交易日历服务实例"""
    db = get_mongo_db()
    return TradingCalendarService(db)


@router.get("", response_model=dict)
async def get_trading_days(
    start_date: str = Query(..., description="起始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    service: TradingCalendarService = Depends(get_trading_calendar_service)
):
    """
    获取交易日列表

    返回指定日期范围内的所有交易日
    """
    # 日期格式校验
    try:
        from datetime import datetime
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为YYYY-MM-DD")

    if start > end:
        raise HTTPException(status_code=400, detail="起始日期不能晚于结束日期")

    try:
        trading_days = await service.get_trading_days(start_date, end_date)
        return ok(data={
            "trading_days": trading_days,
            "total": len(trading_days)
        })
    except Exception as e:
        logger.error(f"获取交易日列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取交易日列表失败: {str(e)}")


@router.get("/info", response_model=dict)
async def get_trading_calendar_info(
    start_date: str = Query(..., description="起始日期 YYYY-MM-DD"),
    end_date: str = Query(..., description="结束日期 YYYY-MM-DD"),
    service: TradingCalendarService = Depends(get_trading_calendar_service)
):
    """
    获取交易日历统计信息

    返回指定日期范围的交易日统计信息
    """
    # 日期格式校验
    try:
        from datetime import datetime
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为YYYY-MM-DD")

    if start > end:
        raise HTTPException(status_code=400, detail="起始日期不能晚于结束日期")

    try:
        info = await service.get_trading_calendar_info(start_date, end_date)
        return ok(data=info)
    except Exception as e:
        logger.error(f"获取交易日历信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取交易日历信息失败: {str(e)}")


@router.get("/{date}", response_model=dict)
async def is_trading_day(
    date: str,
    service: TradingCalendarService = Depends(get_trading_calendar_service)
):
    """
    判断指定日期是否为交易日

    返回指定日期的详细信息
    """
    # 日期格式校验
    try:
        from datetime import datetime
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为YYYY-MM-DD")

    try:
        trading_day_info = await service.get_trading_day_info(date)

        # 如果数据库中没有该日期，返回默认值（非交易日）
        if not trading_day_info:
            return ok(data={
                "date": date,
                "is_trading_day": False,
                "is_holiday": False,
                "is_weekend": False,
                "weekday": 0,
                "holiday_name": None
            })

        return ok(data=trading_day_info)
    except Exception as e:
        logger.error(f"判断交易日失败: {e}")
        raise HTTPException(status_code=500, detail=f"判断交易日失败: {str(e)}")


@router.get("/{date}/previous", response_model=dict)
async def get_previous_trading_day(
    date: str,
    service: TradingCalendarService = Depends(get_trading_calendar_service)
):
    """
    获取指定日期的前一个交易日

    如果指定日期是交易日，返回该交易日之前最近的一个交易日
    """
    # 日期格式校验
    try:
        from datetime import datetime
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为YYYY-MM-DD")

    try:
        prev_trading_day = await service.get_previous_trading_day(date)

        if not prev_trading_day:
            raise HTTPException(status_code=404, detail=f"未找到 {date} 之前的交易日")

        # 计算前一个日历日期
        from datetime import timedelta
        previous_date = (target_date - timedelta(days=1)).strftime("%Y-%m-%d")

        return ok(data={
            "previous_trading_day": prev_trading_day,
            "previous_date": previous_date
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取前一个交易日失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取前一个交易日失败: {str(e)}")


@router.get("/{date}/next", response_model=dict)
async def get_next_trading_day(
    date: str,
    service: TradingCalendarService = Depends(get_trading_calendar_service)
):
    """
    获取指定日期的后一个交易日

    如果指定日期是交易日，返回该交易日之后最近的一个交易日
    """
    # 日期格式校验
    try:
        from datetime import datetime
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，应为YYYY-MM-DD")

    try:
        next_trading_day = await service.get_next_trading_day(date)

        if not next_trading_day:
            raise HTTPException(status_code=404, detail=f"未找到 {date} 之后的交易日")

        # 计算后一个日历日期
        from datetime import timedelta
        next_calendar_date = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")

        return ok(data={
            "next_trading_day": next_trading_day,
            "next_date": next_calendar_date
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取后一个交易日失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取后一个交易日失败: {str(e)}")
