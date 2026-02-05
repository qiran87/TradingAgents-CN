"""
交易日历数据模型
"""
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


class TradingDayInfo(BaseModel):
    """交易日信息"""
    date: str = Field(..., description="日期 YYYY-MM-DD")
    is_trading_day: bool = Field(..., description="是否为交易日")
    is_holiday: bool = Field(default=False, description="是否为节假日")
    is_weekend: bool = Field(default=False, description="是否为周末")
    weekday: int = Field(..., description="星期几（1-7，1为周一）")
    holiday_name: Optional[str] = Field(None, description="节假日名称")


class TradingDaysListResponse(BaseModel):
    """交易日列表响应"""
    trading_days: list[str] = Field(..., description="交易日列表")
    total: int = Field(..., description="总数")


class TradingCalendarInfo(BaseModel):
    """交易日历统计信息"""
    date_range: dict
    trading_days_count: int
    holidays_count: int
    weekends_count: int
    first_trading_day: dict
    last_trading_day: dict
    trading_day_percentage: float


class PreviousTradingDayResponse(BaseModel):
    """前一个交易日响应"""
    previous_trading_day: str = Field(..., description="前一个交易日")
    previous_date: str = Field(..., description="前一个日历日期")


class NextTradingDayResponse(BaseModel):
    """后一个交易日响应"""
    next_trading_day: str = Field(..., description="后一个交易日")
    next_date: str = Field(..., description="后一个日历日期")
