"""
交易日历服务
提供交易日查询、判断、缓存等功能
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import redis.asyncio as redis
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_redis_client

logger = logging.getLogger(__name__)


class TradingCalendarCacheKeys:
    """交易日历缓存键"""

    @staticmethod
    def trading_day(date: str) -> str:
        """单个日期交易日判断"""
        return f"trading_day:{date}"

    @staticmethod
    def trading_days_range(start_date: str, end_date: str) -> str:
        """日期范围交易日列表"""
        return f"trading_days:{start_date}:{end_date}"

    @staticmethod
    def trading_days_year(year: int) -> str:
        """年度交易日列表"""
        return f"trading_days:{year}"

    @staticmethod
    def previous_trading_day(date: str) -> str:
        """前一个交易日"""
        return f"prev_trading_day:{date}"

    @staticmethod
    def next_trading_day(date: str) -> str:
        """后一个交易日"""
        return f"next_trading_day:{date}"


class TradingCalendarService:
    """交易日历服务"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.trading_calendar
        self.redis: redis.Redis = get_redis_client()

    async def is_trading_day(self, date: str) -> bool:
        """
        判断指定日期是否为交易日

        Args:
            date: 日期 YYYY-MM-DD

        Returns:
            是否为交易日
        """
        # 先查Redis缓存
        cache_key = TradingCalendarCacheKeys.trading_day(date)
        cached = await self.redis.get(cache_key)
        if cached is not None:
            return cached == "true"

        # 查询数据库
        trading_day = await self.collection.find_one({"date": date})

        is_trading = False
        if trading_day:
            is_trading = trading_day.get("is_trading_day", False)

        # 写入Redis缓存（24小时）
        await self.redis.setex(cache_key, 86400, "true" if is_trading else "false")

        return is_trading

    async def get_trading_days(self, start_date: str, end_date: str) -> List[str]:
        """
        获取交易日列表

        Args:
            start_date: 起始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD

        Returns:
            交易日列表
        """
        # 先查Redis缓存
        cache_key = TradingCalendarCacheKeys.trading_days_range(start_date, end_date)
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # 查询数据库
        cursor = self.collection.find({
            "date": {"$gte": start_date, "$lte": end_date},
            "is_trading_day": True
        }).sort("date", 1)

        trading_days = await cursor.to_list(length=1000)
        trading_day_list = [td["date"] for td in trading_days]

        # 写入Redis缓存（1小时）
        await self.redis.setex(
            cache_key,
            3600,
            json.dumps(trading_day_list)
        )

        return trading_day_list

    async def get_previous_trading_day(self, date: str) -> Optional[str]:
        """
        获取前一个交易日

        Args:
            date: 日期 YYYY-MM-DD

        Returns:
            前一个交易日，如果不存在返回None
        """
        # 先查缓存
        cache_key = TradingCalendarCacheKeys.previous_trading_day(date)
        cached = await self.redis.get(cache_key)
        if cached:
            return cached

        # 向前查找交易日（最多查找30天）
        for i in range(1, 31):
            prev_date = datetime.strptime(date, "%Y-%m-%d") - timedelta(days=i)
            prev_date_str = prev_date.strftime("%Y-%m-%d")

            if await self.is_trading_day(prev_date_str):
                # 写入缓存（1小时）
                await self.redis.setex(cache_key, 3600, prev_date_str)
                return prev_date_str

        return None

    async def get_next_trading_day(self, date: str) -> Optional[str]:
        """
        获取后一个交易日

        Args:
            date: 日期 YYYY-MM-DD

        Returns:
            后一个交易日，如果不存在返回None
        """
        # 先查缓存
        cache_key = TradingCalendarCacheKeys.next_trading_day(date)
        cached = await self.redis.get(cache_key)
        if cached:
            return cached

        # 向后查找交易日（最多查找30天）
        for i in range(1, 31):
            next_date = datetime.strptime(date, "%Y-%m-%d") + timedelta(days=i)
            next_date_str = next_date.strftime("%Y-%m-%d")

            if await self.is_trading_day(next_date_str):
                # 写入缓存（1小时）
                await self.redis.setex(cache_key, 3600, next_date_str)
                return next_date_str

        return None

    async def get_trading_days_by_year(self, year: int) -> List[str]:
        """
        获取指定年份的所有交易日

        Args:
            year: 年份

        Returns:
            交易日列表
        """
        # 先查Redis缓存
        cache_key = TradingCalendarCacheKeys.trading_days_year(year)
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)

        # 查询数据库
        cursor = self.collection.find({
            "year": year,
            "is_trading_day": True
        }).sort("date", 1)

        trading_days = await cursor.to_list(length=400)
        trading_day_list = [td["date"] for td in trading_days]

        # 写入Redis缓存（24小时）
        await self.redis.setex(
            cache_key,
            86400,
            json.dumps(trading_day_list)
        )

        return trading_day_list

    async def get_trading_day_info(self, date: str) -> Optional[dict]:
        """
        获取交易日详细信息

        Args:
            date: 日期 YYYY-MM-DD

        Returns:
            交易日信息，如果不存在返回None
        """
        trading_day = await self.collection.find_one({"date": date})
        if not trading_day:
            return None

        return {
            "date": trading_day.get("date"),
            "is_trading_day": trading_day.get("is_trading_day", False),
            "is_holiday": trading_day.get("is_holiday", False),
            "is_weekend": trading_day.get("is_weekend", False),
            "weekday": trading_day.get("weekday", 0),
            "holiday_name": trading_day.get("holiday_name")
        }

    async def get_trading_calendar_info(
        self,
        start_date: str,
        end_date: str
    ) -> dict:
        """
        获取交易日历统计信息

        Args:
            start_date: 起始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD

        Returns:
            统计信息
        """
        # 查询所有日期
        cursor = self.collection.find({
            "date": {"$gte": start_date, "$lte": end_date}
        }).sort("date", 1)

        all_days = await cursor.to_list(length=1000)

        if not all_days:
            return {
                "date_range": {
                    "start_date": start_date,
                    "end_date": end_date
                },
                "trading_days_count": 0,
                "holidays_count": 0,
                "weekends_count": 0,
                "first_trading_day": {
                    "date": start_date,
                    "weekday": ""
                },
                "last_trading_day": {
                    "date": end_date,
                    "weekday": ""
                },
                "trading_day_percentage": 0.0
            }

        # 统计信息
        trading_days = [d for d in all_days if d.get("is_trading_day")]
        holidays = [d for d in all_days if d.get("is_holiday")]
        weekends = [d for d in all_days if d.get("is_weekend")]

        # 计算星期
        weekday_map = {
            1: "周一", 2: "周二", 3: "周三", 4: "周四",
            5: "周五", 6: "周六", 7: "周日"
        }

        return {
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            },
            "trading_days_count": len(trading_days),
            "holidays_count": len(holidays),
            "weekends_count": len(weekends),
            "first_trading_day": {
                "date": trading_days[0]["date"] if trading_days else start_date,
                "weekday": weekday_map.get(trading_days[0]["weekday"], "") if trading_days else ""
            },
            "last_trading_day": {
                "date": trading_days[-1]["date"] if trading_days else end_date,
                "weekday": weekday_map.get(trading_days[-1]["weekday"], "") if trading_days else ""
            },
            "trading_day_percentage": round(len(trading_days) / len(all_days) * 100, 2) if all_days else 0
        }


# 全局服务实例
_trading_calendar_service: Optional[TradingCalendarService] = None


def get_trading_calendar_service() -> TradingCalendarService:
    """
    获取交易日历服务实例

    Returns:
        TradingCalendarService 实例
    """
    global _trading_calendar_service
    if _trading_calendar_service is None:
        from app.core.database import get_mongo_db
        db = get_mongo_db()
        _trading_calendar_service = TradingCalendarService(db)
    return _trading_calendar_service
