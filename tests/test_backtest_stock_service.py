"""
股票数据服务单元测试

测试覆盖：
- Service层核心功能
- 数据映射逻辑
- 缓存功能
- 错误处理

运行方法：
pytest tests/test_backtest_stock_service.py -v
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from app.services.backtest_stock_data_service_v2 import (
    BacktestStockDataService,
    StockNotFoundError,
    DataNotFoundError,
    StockDataError
)


@pytest.fixture
def mock_db():
    """模拟MongoDB数据库"""
    db = Mock()
    db.stock_info = AsyncMock()
    db.stock_quotes = AsyncMock()
    db.stock_basic_info = AsyncMock()
    db.market_quotes = AsyncMock()
    db.stock_mapping_flags = AsyncMock()
    return db


@pytest.fixture
def mock_redis():
    """模拟Redis客户端"""
    redis_client = AsyncMock()
    return redis_client


@pytest.fixture
def service(mock_db, mock_redis):
    """创建服务实例"""
    return BacktestStockDataService(mock_db, mock_redis)


class TestBacktestStockDataService:
    """股票数据服务测试类"""

    @pytest.mark.asyncio
    async def test_get_stock_info_from_cache(self, service, mock_redis):
        """测试从缓存获取股票信息"""
        # Arrange
        stock_code = "000001.SZ"
        cached_data = {
            "stock_code": stock_code,
            "stock_name": "平安银行",
            "market": "深圳"
        }
        mock_redis.get.return_value = '{"stock_code": "000001.SZ", "stock_name": "平安银行", "market": "深圳"}'

        # Act
        result = await service.get_stock_info(stock_code)

        # Assert
        assert result["stock_code"] == stock_code
        assert result["stock_name"] == "平安银行"
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_stock_info_not_found(self, service, mock_db, mock_redis):
        """测试股票不存在"""
        # Arrange
        stock_code = "999999.SZ"
        mock_redis.get.return_value = None

        # 模拟数据库查询为空
        mock_db.stock_info.find_one.return_value = None
        mock_db.stock_mapping_flags.find_one.return_value = None
        mock_db.stock_basic_info.find_one.return_value = None

        # Act & Assert
        with pytest.raises(StockNotFoundError):
            await service.get_stock_info(stock_code)

    @pytest.mark.asyncio
    async def test_map_to_stock_info(self, service):
        """测试数据映射逻辑"""
        # Arrange
        basic_info = {
            "symbol": "000001",
            "name": "平安银行",
            "industry": "银行"
        }

        # Act
        result = service._map_to_stock_info(basic_info)

        # Assert
        assert result["stock_code"] == "000001.SZ"
        assert result["stock_name"] == "平安银行"
        assert result["market"] == "深圳"
        assert result["industry"] == "银行"

    @pytest.mark.asyncio
    async def test_map_to_stock_quote(self, service):
        """测试行情数据映射逻辑"""
        # Arrange
        market_quote = {
            "trade_date": "20240101",
            "open": 10.0,
            "high": 11.0,
            "low": 9.5,
            "close": 10.5,
            "volume": 1000000,
            "amount": 10500000.0
        }
        stock_code = "000001.SZ"

        # Act
        result = service._map_to_stock_quote(market_quote, stock_code)

        # Assert
        assert result["stock_code"] == stock_code
        assert result["date"] == "2024-01-01"
        assert result["open"] == 10.0
        assert result["close"] == 10.5
        assert result["volume"] == 1000000

    @pytest.mark.asyncio
    async def test_get_full_stock_code(self, service):
        """测试完整股票代码生成"""
        # Test Shanghai
        assert service._get_full_stock_code("600000") == "600000.SS"
        assert service._get_full_stock_code("688001") == "688001.SS"

        # Test Shenzhen
        assert service._get_full_stock_code("000001") == "000001.SZ"
        assert service._get_full_stock_code("300001") == "300001.SZ"

    @pytest.mark.asyncio
    async def test_search_stocks_empty_result(self, service, mock_db, mock_redis):
        """测试搜索无结果"""
        # Arrange
        keyword = "NOTEXIST"
        mock_redis.get.return_value = None
        mock_db.stock_info.find.return_value.to_list.return_value = []
        mock_db.stock_basic_info.find.return_value.to_list.return_value = []

        # Act
        result = await service.search_stocks(keyword)

        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_check_data_availability_no_trading_days(
        self, service, mock_db, mock_redis
    ):
        """测试无交易日时的数据可用性检查"""
        # Arrange
        stock_code = "000001.SZ"
        start_date = "2024-01-01"
        end_date = "2024-01-31"

        mock_redis.get.return_value = None

        # 模拟交易日历服务返回空列表
        with patch('app.services.trading_calendar_service.TradingCalendarService') as MockTC:
            mock_tc_instance = AsyncMock()
            mock_tc_instance.get_trading_days.return_value = []
            MockTC.return_value = mock_tc_instance

            # Act
            result = await service.check_data_availability(stock_code, start_date, end_date)

            # Assert
            assert result["is_available"] == False
            assert result["coverage"] == 0.0
            assert result["missing_dates"] == []


class TestStockDataErrors:
    """错误处理测试"""

    def test_stock_not_found_error(self):
        """测试股票未找到错误"""
        error = StockNotFoundError("000001.SZ")
        assert error.code == "STOCK_NOT_FOUND"
        assert "000001.SZ" in error.message

    def test_data_not_found_error(self):
        """测试数据未找到错误"""
        error = DataNotFoundError("000001.SZ", "2024-01-01 至 2024-01-31")
        assert error.code == "DATA_NOT_FOUND"
        assert "000001.SZ" in error.message

    def test_stock_data_error(self):
        """测试通用股票数据错误"""
        error = StockDataError("测试错误")
        assert error.code == "STOCK_DATA_ERROR"
        assert error.message == "测试错误"


@pytest.mark.integration
class TestServiceIntegration:
    """集成测试（需要实际数据库）"""

    @pytest.mark.asyncio
    async def test_end_to_end_flow(self):
        """端到端流程测试"""
        # 此类测试需要实际的数据库连接
        # 在CI/CD环境中运行
        pass

    @pytest.mark.asyncio
    async def test_cache_hit_rate(self):
        """测试缓存命中率"""
        # 测试连续调用同一接口的缓存效果
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
