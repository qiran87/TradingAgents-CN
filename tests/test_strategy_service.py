"""
策略服务层单元测试

使用pytest和mock测试StrategyService的所有方法
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, MagicMock, patch
import sys

# Mock所有数据库相关模块
sys.modules['motor'] = MagicMock()
sys.modules['motor.motor_asyncio'] = MagicMock()
sys.modules['pymongo'] = MagicMock()
sys.modules['bson'] = MagicMock()
sys.modules['app.core.database'] = MagicMock()

from app.services.strategy_service import StrategyService


@pytest.fixture
def mock_db():
    """Mock数据库对象"""
    db = Mock()
    db.strategies = Mock()
    db.strategy_categories = Mock()
    return db


@pytest.fixture
def strategy_service(mock_db):
    """创建StrategyService实例"""
    with patch('app.services.strategy_service.get_mongo_db', return_value=mock_db):
        return StrategyService()


@pytest.fixture
def sample_strategy_data():
    """示例策略数据"""
    return {
        "_id": "507f1f77bcf86cd799439011",
        "strategy_id": "dual_ma",
        "name": "双均线策略",
        "description": "基于快慢均线的交叉信号进行交易",
        "long_description": "双均线策略是一种经典的趋势跟踪策略",
        "category": "trend",
        "parameters": [
            {
                "name": "short_window",
                "type": "int",
                "default_value": 5,
                "range": {"min": 2, "max": 60},
                "description": "短期均线窗口",
                "required": True
            },
            {
                "name": "long_window",
                "type": "int",
                "default_value": 20,
                "range": {"min": 5, "max": 250},
                "description": "长期均线窗口",
                "required": True
            }
        ],
        "usage_count": 100,
        "is_builtin": True,
        "created_at": datetime(2024, 1, 1, 0, 0, 0),
        "updated_at": datetime(2024, 1, 1, 0, 0, 0)
    }


@pytest.fixture
def sample_category_data():
    """示例分类数据"""
    return [
        {
            "_id": "507f1f77bcf86cd799439012",
            "category_id": "trend",
            "name": "趋势跟踪策略",
            "description": "基于价格趋势的策略",
            "sort_order": 1,
            "created_at": datetime(2024, 1, 1, 0, 0, 0)
        },
        {
            "_id": "507f1f77bcf86cd799439013",
            "category_id": "oscillation",
            "name": "震荡策略",
            "description": "基于价格波动的策略",
            "sort_order": 2,
            "created_at": datetime(2024, 1, 1, 0, 0, 0)
        }
    ]


class TestStrategyService:
    """测试StrategyService类"""

    @pytest.mark.asyncio
    async def test_get_strategy_by_id(self, strategy_service, mock_db, sample_strategy_data):
        """测试根据ID获取策略"""
        # Mock数据库返回
        mock_db.strategies.find_one = AsyncMock(return_value=sample_strategy_data)

        # 调用方法
        result = await strategy_service.get_strategy_by_id("dual_ma")

        # 验证结果
        assert result is not None
        assert result["strategy_id"] == "dual_ma"
        assert result["name"] == "双均线策略"

        # 验证数据库调用
        mock_db.strategies.find_one.assert_called_once_with({"strategy_id": "dual_ma"})

    @pytest.mark.asyncio
    async def test_get_strategy_by_id_not_found(self, strategy_service, mock_db):
        """测试获取不存在的策略"""
        # Mock数据库返回None
        mock_db.strategies.find_one = AsyncMock(return_value=None)

        # 调用方法
        result = await strategy_service.get_strategy_by_id("non_existent")

        # 验证结果
        assert result is None

    @pytest.mark.asyncio
    async def test_strategy_exists(self, strategy_service, mock_db):
        """测试检查策略是否存在"""
        # Mock count_documents返回值
        mock_db.strategies.count_documents = AsyncMock(return_value=1)

        # 调用方法
        exists = await strategy_service.strategy_exists("dual_ma")

        # 验证结果
        assert exists is True
        mock_db.strategies.count_documents.assert_called_once_with({"strategy_id": "dual_ma"})

    @pytest.mark.asyncio
    async def test_strategy_not_exists(self, strategy_service, mock_db):
        """测试策略不存在"""
        # Mock count_documents返回0
        mock_db.strategies.count_documents = AsyncMock(return_value=0)

        # 调用方法
        exists = await strategy_service.strategy_exists("non_existent")

        # 验证结果
        assert exists is False

    @pytest.mark.asyncio
    async def test_increment_usage_count(self, strategy_service, mock_db):
        """测试增加使用次数"""
        # Mock update_one
        mock_db.strategies.update_one = AsyncMock(return_value=Mock(matched_count=1))

        # 调用方法
        await strategy_service.increment_usage_count("dual_ma")

        # 验证调用
        mock_db.strategies.update_one.assert_called_once_with(
            {"strategy_id": "dual_ma"},
            {"$inc": {"usage_count": 1}}
        )

    @pytest.mark.asyncio
    async def test_get_strategy_parameters(self, strategy_service, mock_db, sample_strategy_data):
        """测试获取策略参数"""
        # Mock数据库返回
        mock_db.strategies.find_one = AsyncMock(return_value=sample_strategy_data)

        # 调用方法
        params = await strategy_service.get_strategy_parameters("dual_ma")

        # 验证结果
        assert len(params) == 2
        assert params[0]["name"] == "short_window"
        assert params[1]["name"] == "long_window"

    @pytest.mark.asyncio
    async def test_get_strategy_parameters_not_found(self, strategy_service, mock_db):
        """测试获取不存在策略的参数"""
        # Mock数据库返回None
        mock_db.strategies.find_one = AsyncMock(return_value=None)

        # 调用方法
        params = await strategy_service.get_strategy_parameters("non_existent")

        # 验证结果
        assert params == []

    @pytest.mark.asyncio
    async def test_search_strategies_without_filters(self, strategy_service, mock_db, sample_strategy_data):
        """测试搜索策略(无过滤条件)"""
        # Mock数据库返回
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=[sample_strategy_data])
        mock_db.strategies.find.return_value.sort.return_value.skip.return_value.limit = mock_cursor

        # 调用方法
        results = await strategy_service.search_strategies()

        # 验证结果
        assert len(results) == 1
        assert results[0]["strategy_id"] == "dual_ma"

    @pytest.mark.asyncio
    async def test_search_strategies_with_category(self, strategy_service, mock_db, sample_strategy_data):
        """测试按分类搜索策略"""
        # Mock数据库返回
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=[sample_strategy_data])
        mock_db.strategies.find.return_value.sort.return_value.skip.return_value.limit = mock_cursor

        # 调用方法
        results = await strategy_service.search_strategies(category="trend")

        # 验证查询条件
        mock_db.strategies.find.assert_called_once_with({"category": "trend"})

    @pytest.mark.asyncio
    async def test_search_strategies_with_keyword(self, strategy_service, mock_db, sample_strategy_data):
        """测试按关键词搜索策略"""
        # Mock数据库返回
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=[sample_strategy_data])
        mock_db.strategies.find.return_value.sort.return_value.skip.return_value.limit = mock_cursor

        # 调用方法
        results = await strategy_service.search_strategies(keyword="双均线")

        # 验证查询条件
        mock_db.strategies.find.assert_called_once_with({"$text": {"$search": "双均线"}})

    @pytest.mark.asyncio
    async def test_get_all_categories(self, strategy_service, mock_db, sample_category_data):
        """测试获取所有分类"""
        # Mock数据库返回
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=sample_category_data)
        mock_db.strategy_categories.find.return_value.sort.return_value = mock_cursor

        # 调用方法
        categories = await strategy_service.get_all_categories()

        # 验证结果
        assert len(categories) == 2
        assert categories[0]["category_id"] == "trend"
        assert categories[1]["category_id"] == "oscillation"

        # 验证数据库调用
        mock_db.strategy_categories.find.assert_called_once()
        mock_db.strategy_categories.find.return_value.sort.assert_called_once_with("sort_order", 1)

    @pytest.mark.asyncio
    async def test_validate_parameters_valid(self, strategy_service, mock_db, sample_strategy_data):
        """测试参数校验-有效参数"""
        # Mock数据库返回
        mock_db.strategies.find_one = AsyncMock(return_value=sample_strategy_data)

        # 调用方法
        is_valid, errors = await strategy_service.validate_parameters(
            "dual_ma",
            {"short_window": 5, "long_window": 20}
        )

        # 验证结果
        assert is_valid is True
        assert errors is None

    @pytest.mark.asyncio
    async def test_validate_parameters_missing_required(self, strategy_service, mock_db, sample_strategy_data):
        """测试参数校验-缺少必填参数"""
        # Mock数据库返回
        mock_db.strategies.find_one = AsyncMock(return_value=sample_strategy_data)

        # 调用方法-缺少long_window
        is_valid, errors = await strategy_service.validate_parameters(
            "dual_ma",
            {"short_window": 5}
        )

        # 验证结果
        assert is_valid is False
        assert errors is not None
        assert "long_window" in errors
        assert "必填" in errors["long_window"]

    @pytest.mark.asyncio
    async def test_validate_parameters_wrong_type(self, strategy_service, mock_db, sample_strategy_data):
        """测试参数校验-类型错误"""
        # Mock数据库返回
        mock_db.strategies.find_one = AsyncMock(return_value=sample_strategy_data)

        # 调用方法-类型错误
        is_valid, errors = await strategy_service.validate_parameters(
            "dual_ma",
            {"short_window": "5", "long_window": 20}  # short_window应该是int
        )

        # 验证结果
        assert is_valid is False
        assert errors is not None
        assert "short_window" in errors

    @pytest.mark.asyncio
    async def test_validate_parameters_out_of_range(self, strategy_service, mock_db, sample_strategy_data):
        """测试参数校验-超出范围"""
        # Mock数据库返回
        mock_db.strategies.find_one = AsyncMock(return_value=sample_strategy_data)

        # 调用方法-超出范围
        is_valid, errors = await strategy_service.validate_parameters(
            "dual_ma",
            {"short_window": 1, "long_window": 20}  # short_window最小值是2
        )

        # 验证结果
        assert is_valid is False
        assert errors is not None
        assert "short_window" in errors

    @pytest.mark.asyncio
    async def test_validate_parameters_strategy_not_found(self, strategy_service, mock_db):
        """测试参数校验-策略不存在"""
        # Mock数据库返回None
        mock_db.strategies.find_one = AsyncMock(return_value=None)

        # 调用方法
        is_valid, errors = await strategy_service.validate_parameters(
            "non_existent",
            {"param": "value"}
        )

        # 验证结果
        assert is_valid is False
        assert errors is not None
        assert "strategy" in errors or "不存在" in errors["strategy"]

    @pytest.mark.asyncio
    async def test_validate_parameters_with_options(self, strategy_service, mock_db):
        """测试参数校验-选项验证"""
        # 创建带选项的策略数据
        strategy_with_options = {
            "strategy_id": "test_strategy",
            "parameters": [
                {
                    "name": "mode",
                    "type": "list",
                    "options": ["option1", "option2", "option3"],
                    "required": True
                }
            ]
        }

        # Mock数据库返回
        mock_db.strategies.find_one = AsyncMock(return_value=strategy_with_options)

        # 测试有效选项
        is_valid, errors = await strategy_service.validate_parameters(
            "test_strategy",
            {"mode": "option1"}
        )
        assert is_valid is True

        # 测试无效选项
        is_valid, errors = await strategy_service.validate_parameters(
            "test_strategy",
            {"mode": "invalid_option"}
        )
        assert is_valid is False
        assert "mode" in errors


class TestStrategyServiceEdgeCases:
    """测试StrategyService边界情况"""

    @pytest.mark.asyncio
    async def test_search_with_pagination(self, strategy_service, mock_db):
        """测试分页搜索"""
        # Mock数据库返回
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=[])
        mock_db.strategies.find.return_value.sort.return_value.skip.return_value.limit = mock_cursor

        # 调用方法-带分页
        await strategy_service.search_strategies(skip=10, limit=20)

        # 验证分页参数
        mock_db.strategies.find.return_value.sort.return_value.skip.assert_called_once_with(10)
        mock_db.strategies.find.return_value.sort.return_value.skip.return_value.limit.assert_called_once_with(20)

    @pytest.mark.asyncio
    async def test_validate_parameters_optional_param_missing(self, strategy_service, mock_db):
        """测试可选参数缺失"""
        # 创建带可选参数的策略
        strategy_data = {
            "strategy_id": "test_strategy",
            "parameters": [
                {
                    "name": "required_param",
                    "type": "int",
                    "required": True
                },
                {
                    "name": "optional_param",
                    "type": "int",
                    "required": False
                }
            ]
        }

        # Mock数据库返回
        mock_db.strategies.find_one = AsyncMock(return_value=strategy_data)

        # 只提供必填参数
        is_valid, errors = await strategy_service.validate_parameters(
            "test_strategy",
            {"required_param": 10}
        )

        # 验证结果-应该通过
        assert is_valid is True
        assert errors is None

    @pytest.mark.asyncio
    async def test_validate_parameters_empty_range(self, strategy_service, mock_db):
        """测试参数没有范围限制"""
        # 创建没有范围限制的参数
        strategy_data = {
            "strategy_id": "test_strategy",
            "parameters": [
                {
                    "name": "any_value",
                    "type": "int",
                    "required": True
                    # 没有range字段
                }
            ]
        }

        # Mock数据库返回
        mock_db.strategies.find_one = AsyncMock(return_value=strategy_data)

        # 测试任意值
        is_valid, errors = await strategy_service.validate_parameters(
            "test_strategy",
            {"any_value": 99999}
        )

        # 验证结果-应该通过
        assert is_valid is True
        assert errors is None
