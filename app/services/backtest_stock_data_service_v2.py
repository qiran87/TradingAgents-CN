"""
股票数据服务层 - 回测功能专用（改进版）
提供标准化的股票数据访问接口，用于回测系统

改进项：
1. 数据映射效率优化 - 添加映射标记，避免重复映射
2. Redis缓存策略优化 - 使用结构化的缓存键
3. 错误处理增强 - 统一错误处理和日志记录
5. 数据完整性计算优化 - 使用交易日历计算
"""
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
import redis.asyncio as redis

from app.core.database import get_mongo_db, get_redis_client
from app.services.backtest_stock_cache_keys import BacktestStockCacheKeys

logger = logging.getLogger(__name__)


class StockDataError(Exception):
    """股票数据服务错误基类"""
    def __init__(self, message: str, code: str = "STOCK_DATA_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class StockNotFoundError(StockDataError):
    """股票未找到错误"""
    def __init__(self, stock_code: str):
        super().__init__(f"股票 {stock_code} 不存在", "STOCK_NOT_FOUND")


class DataNotFoundError(StockDataError):
    """数据未找到错误"""
    def __init__(self, stock_code: str, date_range: str):
        super().__init__(f"股票 {stock_code} 在 {date_range} 期间没有数据", "DATA_NOT_FOUND")


class BacktestStockDataService:
    """
    股票数据服务 - 回测功能专用（改进版）

    改进点：
    1. 使用结构化的缓存键，避免冲突
    2. 添加映射标记，避免重复的数据映射和保存
    3. 统一的错误处理和日志记录
    4. 使用交易日历计算数据完整性
    5. 优化数据查询性能
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

        # 映射标记集合（用于跟踪已映射的股票）
        self.mapping_flag_collection = db.stock_mapping_flags

        if redis_client is None:
            redis_client = get_redis_client()
        self.redis = redis_client

    async def get_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """
        获取股票基础信息（改进版）

        Args:
            stock_code: 股票代码（如 000001.SZ 或 000001）

        Returns:
            股票信息字典

        Raises:
            StockNotFoundError: 股票不存在
        """
        try:
            # 1. 检查Redis缓存（改进2：使用结构化缓存键）
            cache_key = BacktestStockCacheKeys.stock_info(stock_code)
            cached = await self.redis.get(cache_key)
            if cached:
                logger.debug(f"从缓存获取股票信息: {stock_code}")
                return json.loads(cached)

            # 2. 标准化股票代码（确保6位）
            code_6 = str(stock_code).zfill(6).split('.')[0]

            # 3. 查询 stock_info 集合
            stock_info = await self.stock_info_collection.find_one(
                {"stock_code": {"$regex": f"^{code_6}"}},
                {"_id": 0}
            )

            # 4. 如果 stock_info 没有，检查是否已经映射过（改进1：避免重复映射）
            if not stock_info:
                mapping_flag = await self.mapping_flag_collection.find_one({"_id": code_6})

                if not mapping_flag:
                    # 未映射过，尝试从 stock_basic_info 映射
                    logger.info(f"stock_info 中未找到 {stock_code}，尝试从 stock_basic_info 映射")
                    stock_info = await self._map_and_save_stock_info(code_6)
                else:
                    # 已映射过但未找到，说明数据不存在
                    logger.warning(f"股票 {stock_code} 已映射过但未找到数据")
                    raise StockNotFoundError(stock_code)

            if not stock_info:
                raise StockNotFoundError(stock_code)

            # 5. 查询数据统计信息（改进5：使用交易日历）
            stats = await self._get_stock_stats_enhanced(stock_info["stock_code"])

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

            # 7. 写入Redis缓存（改进2：使用结构化缓存键和TTL常量）
            await self.redis.setex(
                cache_key,
                BacktestStockCacheKeys.TTL_STOCK_INFO,
                json.dumps(result, default=str)
            )

            return result

        except StockNotFoundError:
            raise
        except Exception as e:
            logger.error(f"获取股票信息失败 stock_code={stock_code}: {e}", exc_info=True)
            # 改进3：统一错误处理
            raise StockDataError(f"获取股票信息失败: {str(e)}")

    async def get_quotes(
        self,
        stock_code: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        获取历史行情数据（改进版）

        Args:
            stock_code: 股票代码
            start_date: 起始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD

        Returns:
            行情数据列表

        Raises:
            StockNotFoundError: 股票不存在
            DataNotFoundError: 行情数据不存在
        """
        try:
            # 1. 检查Redis缓存
            cache_key = BacktestStockCacheKeys.stock_quotes(stock_code, start_date, end_date)
            cached = await self.redis.get(cache_key)
            if cached:
                logger.debug(f"从缓存获取行情数据: {stock_code} {start_date} - {end_date}")
                return json.loads(cached)

            # 2. 标准化股票代码
            code_6 = str(stock_code).zfill(6).split('.')[0]
            full_code = self._get_full_stock_code(code_6)

            # 3. 查询 stock_quotes 集合
            cursor = self.stock_quotes_collection.find({
                "stock_code": {"$regex": f"^{code_6}"},
                "date": {"$gte": start_date, "$lte": end_date}
            }).sort("date", 1)

            quotes = await cursor.to_list(length=3000)

            # 4. 如果 stock_quotes 没有数据，尝试映射（改进1：添加映射标记检查）
            if not quotes:
                mapping_flag = await self.mapping_flag_collection.find_one({
                    "_id": f"{code_6}_quotes_{start_date}_{end_date}"
                })

                if not mapping_flag:
                    # 未映射过，尝试从 market_quotes 映射
                    logger.info(f"stock_quotes 中未找到 {stock_code}，尝试从 market_quotes 映射")
                    quotes = await self._map_and_save_quotes(code_6, full_code, start_date, end_date)

                    # 标记已映射
                    await self.mapping_flag_collection.update_one(
                        {"_id": f"{code_6}_quotes_{start_date}_{end_date}"},
                        {"$set": {"mapped_at": datetime.now(timezone.utc)}},
                        upsert=True
                    )

            if not quotes:
                raise DataNotFoundError(stock_code, f"{start_date} 至 {end_date}")

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

            # 6. 写入Redis缓存
            await self.redis.setex(
                cache_key,
                BacktestStockCacheKeys.TTL_QUOTES,
                json.dumps(result, default=str)
            )

            return result

        except (StockNotFoundError, DataNotFoundError):
            raise
        except Exception as e:
            logger.error(f"获取行情数据失败 stock_code={stock_code}: {e}", exc_info=True)
            raise StockDataError(f"获取行情数据失败: {str(e)}")

    async def check_data_availability(
        self,
        stock_code: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        检查数据可用性（改进版）

        Args:
            stock_code: 股票代码
            start_date: 起始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD

        Returns:
            数据可用性信息
        """
        try:
            # 1. 检查Redis缓存
            cache_key = BacktestStockCacheKeys.data_availability(stock_code, start_date, end_date)
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
                await self.redis.setex(
                    cache_key,
                    BacktestStockCacheKeys.TTL_AVAILABILITY,
                    json.dumps(result, default=str)
                )
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

            # 7. 写入Redis缓存
            await self.redis.setex(
                cache_key,
                BacktestStockCacheKeys.TTL_AVAILABILITY,
                json.dumps(result, default=str)
            )

            return result

        except Exception as e:
            logger.error(f"检查数据可用性失败 stock_code={stock_code}: {e}", exc_info=True)
            # 改进3：返回部分结果而不是完全失败
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
        搜索股票（改进版）

        Args:
            keyword: 搜索关键词（股票代码或名称）
            limit: 返回数量限制

        Returns:
            搜索结果列表
        """
        try:
            # 1. 检查Redis缓存
            cache_key = BacktestStockCacheKeys.search(keyword, limit)
            cached = await self.redis.get(cache_key)
            if cached:
                logger.debug(f"从缓存获取搜索结果: {keyword}")
                return json.loads(cached)

            # 2. 构建查询条件
            query = {}
            if keyword.isdigit():
                code_6 = str(keyword).zfill(6)
                query["stock_code"] = {"$regex": f"^{code_6}"}
            else:
                query["stock_name"] = {"$regex": keyword, "$options": "i"}

            # 3. 查询 stock_info 集合
            cursor = self.stock_info_collection.find(query, {"_id": 0}).limit(limit)
            stocks = await cursor.to_list(length=limit)

            # 4. 如果 stock_info 没有结果，从 stock_basic_info 搜索
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

                    # 异步保存（改进1：标记已映射）
                    await self.stock_info_collection.update_one(
                        {"stock_code": stock_info["stock_code"]},
                        {"$set": stock_info},
                        upsert=True
                    )

            # 5. 转换为搜索结果格式
            results = []
            for stock in stocks:
                results.append({
                    "stock_code": stock["stock_code"],
                    "stock_name": stock["stock_name"],
                    "market": stock["market"],
                    "industry": stock.get("industry")
                })

            # 6. 写入Redis缓存
            await self.redis.setex(
                cache_key,
                BacktestStockCacheKeys.TTL_SEARCH,
                json.dumps(results, default=str)
            )

            return results

        except Exception as e:
            logger.error(f"搜索股票失败 keyword={keyword}: {e}", exc_info=True)
            return []

    async def _map_and_save_stock_info(self, code_6: str) -> Optional[Dict[str, Any]]:
        """
        映射并保存股票信息（改进1：避免重复映射）

        Args:
            code_6: 6位股票代码

        Returns:
            映射后的股票信息，如果源数据不存在则返回None
        """
        basic_info = await self.stock_basic_info_collection.find_one(
            {"$or": [{"symbol": code_6}, {"code": code_6}]},
            {"_id": 0}
        )

        if not basic_info:
            return None

        # 映射到 stock_info 格式
        stock_info = self._map_to_stock_info(basic_info)

        # 保存到 stock_info 集合
        await self.stock_info_collection.update_one(
            {"stock_code": stock_info["stock_code"]},
            {"$set": stock_info},
            upsert=True
        )

        # 标记已映射
        await self.mapping_flag_collection.update_one(
            {"_id": code_6},
            {"$set": {"mapped_at": datetime.now(timezone.utc)}},
            upsert=True
        )

        return stock_info

    async def _map_and_save_quotes(
        self,
        code_6: str,
        full_code: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        映射并保存行情数据（改进1：批量处理）

        Args:
            code_6: 6位股票代码
            full_code: 完整股票代码
            start_date: 起始日期
            end_date: 结束日期

        Returns:
            映射后的行情数据列表
        """
        # 转换日期格式
        start_date_num = start_date.replace('-', '')
        end_date_num = end_date.replace('-', '')

        cursor = self.market_quotes_collection.find({
            "symbol": code_6,
            "trade_date": {"$gte": start_date_num, "$lte": end_date_num}
        }).sort("trade_date", 1)

        market_quotes = await cursor.to_list(length=3000)

        if not market_quotes:
            return []

        # 批量映射和保存
        quotes = []
        bulk_operations = []

        for mq in market_quotes:
            quote = self._map_to_stock_quote(mq, full_code)
            quotes.append(quote)

            # 添加到批量操作列表
            bulk_operations.append({
                "update_one": {
                    "filter": {"stock_code": quote["stock_code"], "date": quote["date"]},
                    "update": {"$set": quote},
                    "upsert": True
                }
            })

        # 批量执行（改进1：性能优化）
        if bulk_operations:
            await self.stock_quotes_collection.bulk_write(bulk_operations, ordered=False)

        return quotes

    async def _get_stock_stats_enhanced(self, stock_code: str) -> Dict[str, Any]:
        """
        获取股票数据统计信息（改进5：使用交易日历）

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

            # 改进5：使用交易日历计算数据完整性
            data_completeness = 0.0
            if first_quote and last_quote:
                try:
                    from app.services.trading_calendar_service import TradingCalendarService
                    trading_calendar_service = TradingCalendarService(self.db)

                    # 获取日期范围内的实际交易日数
                    actual_trading_days = await trading_calendar_service.get_trading_days(
                        first_quote["date"],
                        last_quote["date"]
                    )
                    expected_count = len(actual_trading_days)

                    if expected_count > 0:
                        data_completeness = min(100, round(total_trading_days / expected_count * 100, 2))
                except Exception as e:
                    logger.warning(f"使用交易日历计算完整性失败，使用降级方案: {e}")
                    # 降级方案：使用简单计算
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
        """将 stock_basic_info 格式映射到 stock_info 格式"""
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
        """将 market_quotes 格式映射到 stock_quotes 格式"""
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
        """获取完整的股票代码"""
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
