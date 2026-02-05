"""
股票数据服务层 - 回测功能专用
提供标准化的股票数据访问接口，用于回测系统
"""
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase
import redis.asyncio as redis

from app.core.database import get_mongo_db, get_redis_client

logger = logging.getLogger(__name__)


class BacktestStockDataService:
    """
    股票数据服务 - 回测功能专用

    设计说明：
    - 使用 stock_info 和 stock_quotes 集合（方案要求）
    - 映射现有的 stock_basic_info 和 market_quotes 数据
    - 实现 Redis 缓存以提升性能
    """

    def __init__(self, db: AsyncIOMotorDatabase, redis_client: Optional[redis.Redis] = None):
        """
        初始化服务

        Args:
            db: MongoDB 数据库实例
            redis_client: Redis 客户端实例（可选）
        """
        self.db = db
        self.stock_info_collection = db.stock_info
        self.stock_quotes_collection = db.stock_quotes

        # 兼容集合：用于映射现有数据
        self.stock_basic_info_collection = db.stock_basic_info
        self.market_quotes_collection = db.market_quotes

        if redis_client is None:
            redis_client = get_redis_client()
        self.redis = redis_client

    async def get_stock_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票基础信息

        Args:
            stock_code: 股票代码（如 000001.SZ 或 000001）

        Returns:
            股票信息字典，不存在返回 None
        """
        try:
            # 1. 先查 Redis 缓存
            cache_key = f"stock_info:{stock_code}"
            cached = await self.redis.get(cache_key)
            if cached:
                logger.debug(f"从缓存获取股票信息: {stock_code}")
                return json.loads(cached)

            # 2. 标准化股票代码（确保6位）
            code_6 = str(stock_code).zfill(6).split('.')[0]

            # 3. 查询 stock_info 集合（方案要求的集合）
            stock_info = await self.stock_info_collection.find_one(
                {"stock_code": {"$regex": f"^{code_6}"}},
                {"_id": 0}
            )

            # 4. 如果 stock_info 没有，从 stock_basic_info 映射（兼容现有数据）
            if not stock_info:
                logger.info(f"stock_info 中未找到 {stock_code}，尝试从 stock_basic_info 映射")
                basic_info = await self.stock_basic_info_collection.find_one(
                    {"$or": [{"symbol": code_6}, {"code": code_6}]},
                    {"_id": 0}
                )

                if basic_info:
                    # 映射到 stock_info 格式
                    stock_info = self._map_to_stock_info(basic_info)

                    # 保存到 stock_info 集合
                    await self.stock_info_collection.update_one(
                        {"stock_code": stock_info["stock_code"]},
                        {"$set": stock_info},
                        upsert=True
                    )

            if not stock_info:
                logger.warning(f"未找到股票 {stock_code} 的信息")
                return None

            # 5. 查询数据统计信息
            stats = await self._get_stock_stats(stock_info["stock_code"])

            # 6. 组合结果
            result = {
                "stock_code": stock_info["stock_code"],
                "stock_name": stock_info["stock_name"],
                "market": stock_info["market"],
                "industry": stock_info.get("industry"),
                "list_date": stock_info.get("list_date"),
                "data_range": stats["data_range"],
                "data_completeness": stats["data_completeness"],
                "total_trading_days": stats["total_trading_days"],
                "last_updated": stock_info.get("updated_at")
            }

            # 7. 写入 Redis 缓存（24小时）
            await self.redis.setex(cache_key, 86400, json.dumps(result, default=str))

            return result

        except Exception as e:
            logger.error(f"获取股票信息失败 stock_code={stock_code}: {e}")
            return None

    async def get_quotes(
        self,
        stock_code: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        获取历史行情数据

        Args:
            stock_code: 股票代码
            start_date: 起始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD

        Returns:
            行情数据列表
        """
        try:
            # 1. 先查 Redis 缓存
            cache_key = f"stock_quotes:{stock_code}:{start_date}:{end_date}"
            cached = await self.redis.get(cache_key)
            if cached:
                logger.debug(f"从缓存获取行情数据: {stock_code} {start_date} - {end_date}")
                return json.loads(cached)

            # 2. 标准化股票代码
            code_6 = str(stock_code).zfill(6).split('.')[0]
            full_code = self._get_full_stock_code(code_6)

            # 3. 查询 stock_quotes 集合（方案要求的集合）
            cursor = self.stock_quotes_collection.find({
                "stock_code": {"$regex": f"^{code_6}"},
                "date": {"$gte": start_date, "$lte": end_date}
            }).sort("date", 1)

            quotes = await cursor.to_list(length=3000)

            # 4. 如果 stock_quotes 没有数据，从 market_quotes 映射（兼容现有数据）
            if not quotes:
                logger.info(f"stock_quotes 中未找到 {stock_code}，尝试从 market_quotes 映射")
                cursor = self.market_quotes_collection.find({
                    "symbol": code_6,
                    "trade_date": {"$gte": start_date.replace('-', ''), "$lte": end_date.replace('-', '')}
                }).sort("trade_date", 1)

                market_quotes = await cursor.to_list(length=3000)

                if market_quotes:
                    # 映射并批量保存到 stock_quotes
                    quotes = []
                    for mq in market_quotes:
                        quote = self._map_to_stock_quote(mq, full_code)
                        quotes.append(quote)

                        # 异步保存（不等待）
                        await self.stock_quotes_collection.update_one(
                            {"stock_code": quote["stock_code"], "date": quote["date"]},
                            {"$set": quote},
                            upsert=True
                        )

            if not quotes:
                logger.warning(f"未找到股票 {stock_code} 在 {start_date} 至 {end_date} 的行情数据")
                return []

            # 5. 转换为标准格式
            result = []
            for quote in quotes:
                result.append({
                    "date": quote["date"],
                    "open": quote["open"],
                    "high": quote["high"],
                    "low": quote["low"],
                    "close": quote["close"],
                    "volume": quote["volume"],
                    "amount": quote["amount"]
                })

            # 6. 写入 Redis 缓存（1小时）
            await self.redis.setex(cache_key, 3600, json.dumps(result, default=str))

            return result

        except Exception as e:
            logger.error(f"获取行情数据失败 stock_code={stock_code}: {e}")
            return []

    async def check_data_availability(
        self,
        stock_code: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        检查数据可用性

        Args:
            stock_code: 股票代码
            start_date: 起始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD

        Returns:
            数据可用性信息
        """
        try:
            # 1. 先查 Redis 缓存
            cache_key = f"stock_availability:{stock_code}:{start_date}:{end_date}"
            cached = await self.redis.get(cache_key)
            if cached:
                logger.debug(f"从缓存获取数据可用性: {stock_code} {start_date} - {end_date}")
                return json.loads(cached)

            # 2. 获取该日期范围内的所有交易日
            from app.services.trading_calendar_service import TradingCalendarService
            trading_calendar_service = TradingCalendarService(self.db)

            trading_days = await trading_calendar_service.get_trading_days(start_date, end_date)

            if not trading_days:
                result = {
                    "stock_code": stock_code,
                    "date_range": {"start_date": start_date, "end_date": end_date},
                    "is_available": False,
                    "coverage": 0.0,
                    "missing_dates": [],
                    "first_available_date": None,
                    "last_available_date": None
                }
                await self.redis.setex(cache_key, 1800, json.dumps(result, default=str))
                return result

            # 3. 查询数据库中已有的行情数据
            code_6 = str(stock_code).zfill(6).split('.')[0]
            cursor = self.stock_quotes_collection.find({
                "stock_code": {"$regex": f"^{code_6}"},
                "date": {"$in": trading_days}
            })

            existing_quotes = await cursor.to_list(length=len(trading_days))
            existing_dates = set(q["date"] for q in existing_quotes)

            # 4. 找出缺失的日期
            missing_dates = sorted([d for d in trading_days if d not in existing_dates])

            # 5. 计算覆盖率
            coverage = len(existing_dates) / len(trading_days) if trading_days else 0

            # 6. 判断是否可用（覆盖率 >= 95%）
            is_available = coverage >= 0.95

            result = {
                "stock_code": stock_code,
                "date_range": {"start_date": start_date, "end_date": end_date},
                "is_available": is_available,
                "coverage": round(coverage, 4),
                "missing_dates": missing_dates[:100],  # 最多返回100个缺失日期
                "first_available_date": sorted(existing_dates)[0] if existing_dates else None,
                "last_available_date": sorted(existing_dates)[-1] if existing_dates else None
            }

            # 7. 写入 Redis 缓存（30分钟）
            await self.redis.setex(cache_key, 1800, json.dumps(result, default=str))

            return result

        except Exception as e:
            logger.error(f"检查数据可用性失败 stock_code={stock_code}: {e}")
            return {
                "stock_code": stock_code,
                "date_range": {"start_date": start_date, "end_date": end_date},
                "is_available": False,
                "coverage": 0.0,
                "missing_dates": [],
                "first_available_date": None,
                "last_available_date": None
            }

    async def search_stocks(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索股票

        Args:
            keyword: 搜索关键词（股票代码或名称）
            limit: 返回数量限制

        Returns:
            搜索结果列表
        """
        try:
            # 1. 构建查询条件
            query = {}

            # 如果关键词是纯数字，优先按代码搜索
            if keyword.isdigit():
                code_6 = str(keyword).zfill(6)
                query["stock_code"] = {"$regex": f"^{code_6}"}
            else:
                # 否则按名称搜索
                query["stock_name"] = {"$regex": keyword, "$options": "i"}

            # 2. 查询 stock_info 集合
            cursor = self.stock_info_collection.find(query, {"_id": 0}).limit(limit)
            stocks = await cursor.to_list(length=limit)

            # 3. 如果 stock_info 没有结果，从 stock_basic_info 搜索（兼容现有数据）
            if not stocks:
                logger.info(f"stock_info 中未找到 {keyword}，尝试从 stock_basic_info 搜索")
                query = {}
                if keyword.isdigit():
                    code_6 = str(keyword).zfill(6)
                    query["$or"] = [{"symbol": {"$regex": f"^{code_6}"}}, {"code": {"$regex": f"^{code_6}"}}]
                else:
                    query["name"] = {"$regex": keyword, "$options": "i"}

                cursor = self.stock_basic_info_collection.find(query, {"_id": 0}).limit(limit)
                basic_stocks = await cursor.to_list(length=limit)

                stocks = []
                for bs in basic_stocks:
                    stock_info = self._map_to_stock_info(bs)
                    stocks.append(stock_info)

                    # 保存到 stock_info
                    await self.stock_info_collection.update_one(
                        {"stock_code": stock_info["stock_code"]},
                        {"$set": stock_info},
                        upsert=True
                    )

            # 4. 转换为搜索结果格式
            results = []
            for stock in stocks:
                results.append({
                    "stock_code": stock["stock_code"],
                    "stock_name": stock["stock_name"],
                    "market": stock["market"],
                    "industry": stock.get("industry")
                })

            return results

        except Exception as e:
            logger.error(f"搜索股票失败 keyword={keyword}: {e}")
            return []

    async def _get_stock_stats(self, stock_code: str) -> Dict[str, Any]:
        """
        获取股票数据统计信息

        Args:
            stock_code: 股票代码

        Returns:
            统计信息字典
        """
        try:
            code_6 = str(stock_code).zfill(6).split('.')[0]

            # 获取数据范围
            first_quote = await self.stock_quotes_collection.find_one(
                {"stock_code": {"$regex": f"^{code_6}"}},
                sort=[("date", 1)],
                projection={"_id": 0, "date": 1}
            )
            last_quote = await self.stock_quotes_collection.find_one(
                {"stock_code": {"$regex": f"^{code_6}"}},
                sort=[("date", -1)],
                projection={"_id": 0, "date": 1}
            )

            data_range = {
                "first_date": first_quote["date"] if first_quote else None,
                "last_date": last_quote["date"] if last_quote else None
            }

            # 获取总交易日数
            total_trading_days = await self.stock_quotes_collection.count_documents({
                "stock_code": {"$regex": f"^{code_6}"}
            })

            # 计算数据完整性（简化版本：假设每年244个交易日）
            data_completeness = 0.0
            if first_quote and last_quote:
                start_date = datetime.strptime(first_quote["date"], "%Y-%m-%d")
                end_date = datetime.strptime(last_quote["date"], "%Y-%m-%d")
                days_diff = (end_date - start_date).days
                if days_diff > 0:
                    expected_days = days_diff * 244 / 365
                    data_completeness = min(100, round(total_trading_days / expected_days * 100, 2))

            return {
                "data_range": data_range,
                "data_completeness": data_completeness,
                "total_trading_days": total_trading_days
            }

        except Exception as e:
            logger.error(f"获取股票统计信息失败 stock_code={stock_code}: {e}")
            return {
                "data_range": {"first_date": None, "last_date": None},
                "data_completeness": 0.0,
                "total_trading_days": 0
            }

    def _map_to_stock_info(self, basic_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        将 stock_basic_info 格式映射到 stock_info 格式

        Args:
            basic_info: stock_basic_info 文档

        Returns:
            stock_info 格式的文档
        """
        symbol = basic_info.get("symbol") or basic_info.get("code", "")
        code_6 = str(symbol).zfill(6)

        # 判断市场
        if code_6.startswith(('60', '68', '90')):
            market = "上海"
            full_code = f"{code_6}.SS"
        elif code_6.startswith(('00', '30', '20')):
            market = "深圳"
            full_code = f"{code_6}.SZ"
        else:
            market = "深圳"
            full_code = f"{code_6}.SZ"

        # 处理上市日期
        list_date = basic_info.get("list_date")
        if list_date:
            if isinstance(list_date, int):
                date_str = str(list_date)
                if len(date_str) == 8:
                    list_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                else:
                    list_date = str(list_date)
            else:
                list_date = str(list_date)

        return {
            "stock_code": full_code,
            "stock_name": basic_info.get("name", ""),
            "market": market,
            "industry": basic_info.get("industry"),
            "list_date": list_date,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

    def _map_to_stock_quote(self, market_quote: Dict[str, Any], stock_code: str) -> Dict[str, Any]:
        """
        将 market_quotes 格式映射到 stock_quotes 格式

        Args:
            market_quote: market_quotes 文档
            stock_code: 股票代码

        Returns:
            stock_quotes 格式的文档
        """
        # 转换日期格式 (YYYYMMDD -> YYYY-MM-DD)
        trade_date = market_quote.get("trade_date", "")
        if isinstance(trade_date, int) or (isinstance(trade_date, str) and len(trade_date) == 8):
            date_str = str(trade_date)
            date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        else:
            date = str(trade_date)

        return {
            "stock_code": stock_code,
            "date": date,
            "open": float(market_quote.get("open", 0)),
            "high": float(market_quote.get("high", 0)),
            "low": float(market_quote.get("low", 0)),
            "close": float(market_quote.get("close", 0)),
            "volume": int(market_quote.get("volume", 0)),
            "amount": float(market_quote.get("amount", 0)),
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

    def _get_full_stock_code(self, code_6: str) -> str:
        """
        获取完整的股票代码

        Args:
            code_6: 6位股票代码

        Returns:
            完整代码（如 000001.SZ）
        """
        if code_6.startswith(('60', '68', '90')):
            return f"{code_6}.SS"
        else:
            return f"{code_6}.SZ"


# 全局服务实例
_backtest_stock_data_service = None


def get_backtest_stock_data_service() -> BacktestStockDataService:
    """获取回测股票数据服务实例"""
    global _backtest_stock_data_service
    if _backtest_stock_data_service is None:
        db = get_mongo_db()
        redis_client = get_redis_client()
        _backtest_stock_data_service = BacktestStockDataService(db, redis_client)
    return _backtest_stock_data_service
