"""
Redis缓存键定义 - 股票数据服务
使用结构化的缓存键格式，避免冲突
"""

class BacktestStockCacheKeys:
    """股票数据服务缓存键"""

    # 前缀
    PREFIX = "backtest:stock"

    @staticmethod
    def stock_info(stock_code: str) -> str:
        """股票信息缓存键"""
        return f"{BacktestStockCacheKeys.PREFIX}:info:{stock_code}"

    @staticmethod
    def stock_quotes(stock_code: str, start_date: str, end_date: str) -> str:
        """行情数据缓存键"""
        return f"{BacktestStockCacheKeys.PREFIX}:quotes:{stock_code}:{start_date}:{end_date}"

    @staticmethod
    def data_availability(stock_code: str, start_date: str, end_date: str) -> str:
        """数据可用性缓存键"""
        return f"{BacktestStockCacheKeys.PREFIX}:availability:{stock_code}:{start_date}:{end_date}"

    @staticmethod
    def search(keyword: str, limit: int) -> str:
        """搜索结果缓存键"""
        return f"{BacktestStockCacheKeys.PREFIX}:search:{keyword}:{limit}"

    # TTL配置（秒）
    TTL_STOCK_INFO = 86400      # 24小时
    TTL_QUOTES = 3600            # 1小时
    TTL_AVAILABILITY = 1800      # 30分钟
    TTL_SEARCH = 300             # 5分钟
