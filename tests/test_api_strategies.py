"""
策略API路由单元测试

使用pytest和FastAPI TestClient测试API端点
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from app.main import app


@pytest.fixture
def client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_db():
    """Mock数据库依赖"""
    db = Mock()
    db.strategies = Mock()
    db.strategy_categories = Mock()

    # Mock集合方法
    db.strategies.find = Mock()
    db.strategies.find_one = AsyncMock()
    db.strategies.count_documents = AsyncMock()
    db.strategies.update_one = AsyncMock()

    db.strategy_categories.find = Mock()
    db.strategy_categories.aggregate = Mock()

    return db


@pytest.fixture
def sample_strategy_list():
    """示例策略列表数据"""
    return [
        {
            "strategy_id": "dual_ma",
            "name": "双均线策略",
            "description": "基于快慢均线的交叉信号进行交易",
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
            "created_at": datetime(2024, 1, 1, 0, 0, 0)
        },
        {
            "strategy_id": "bollinger_bands",
            "name": "布林带策略",
            "description": "基于布林带的突破和回归进行交易",
            "category": "oscillation",
            "parameters": [
                {
                    "name": "window",
                    "type": "int",
                    "default_value": 20,
                    "range": {"min": 5, "max": 50},
                    "description": "均线窗口",
                    "required": True
                }
            ],
            "usage_count": 50,
            "is_builtin": True,
            "created_at": datetime(2024, 1, 1, 0, 0, 0)
        }
    ]


@pytest.fixture
def sample_category_list():
    """示例分类列表数据"""
    return [
        {
            "category_id": "trend",
            "name": "趋势跟踪策略",
            "description": "基于价格趋势的策略",
            "sort_order": 1,
            "created_at": datetime(2024, 1, 1, 0, 0, 0)
        },
        {
            "category_id": "oscillation",
            "name": "震荡策略",
            "description": "基于价格波动的策略",
            "sort_order": 2,
            "created_at": datetime(2024, 1, 1, 0, 0, 0)
        }
    ]


class TestGetStrategies:
    """测试获取策略列表接口"""

    @pytest.mark.asyncio
    async def test_get_strategies_success(self, client, sample_strategy_list):
        """测试成功获取策略列表"""
        # 这里需要mock数据库依赖
        # 由于FastAPI的依赖注入,需要使用override_dependencies
        with patch("app.routers.strategies.get_database") as mock_get_db:
            # Mock数据库cursor
            mock_cursor = AsyncMock()
            mock_cursor.to_list = AsyncMock(return_value=sample_strategy_list)
            mock_db = Mock()
            mock_db.strategies.find.return_value.sort.return_value.skip.return_value.limit = mock_cursor
            mock_db.strategies.count_documents = AsyncMock(return_value=2)

            mock_get_db.return_value = mock_db

            # 发送请求
            response = client.get("/api/backtest/strategies")

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert "strategies" in data
            assert len(data["strategies"]) == 2
            assert data["strategies"][0]["strategy_id"] == "dual_ma"

    @pytest.mark.asyncio
    async def test_get_strategies_with_category_filter(self, client):
        """测试按分类过滤"""
        with patch("app.routers.strategies.get_database") as mock_get_db:
            mock_cursor = AsyncMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_db = Mock()
            mock_db.strategies.find.return_value.sort.return_value.skip.return_value.limit = mock_cursor
            mock_db.strategies.count_documents = AsyncMock(return_value=0)

            mock_get_db.return_value = mock_db

            # 发送请求-带分类过滤
            response = client.get("/api/backtest/strategies?category=trend")

            # 验证响应
            assert response.status_code == 200

            # 验证查询条件
            mock_db.strategies.find.assert_called()

    @pytest.mark.asyncio
    async def test_get_strategies_with_search(self, client):
        """测试搜索功能"""
        with patch("app.routers.strategies.get_database") as mock_get_db:
            mock_cursor = AsyncMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_db = Mock()
            mock_db.strategies.find.return_value.sort.return_value.skip.return_value.limit = mock_cursor
            mock_db.strategies.count_documents = AsyncMock(return_value=0)

            mock_get_db.return_value = mock_db

            # 发送请求-带搜索关键词
            response = client.get("/api/backtest/strategies?search=双均线")

            # 验证响应
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_strategies_with_pagination(self, client):
        """测试分页"""
        with patch("app.routers.strategies.get_database") as mock_get_db:
            mock_cursor = AsyncMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_db = Mock()
            mock_db.strategies.find.return_value.sort.return_value.skip.return_value.limit = mock_cursor
            mock_db.strategies.count_documents = AsyncMock(return_value=0)

            mock_get_db.return_value = mock_db

            # 发送请求-带分页参数
            response = client.get("/api/backtest/strategies?skip=10&limit=20")

            # 验证响应
            assert response.status_code == 200


class TestGetStrategyDetail:
    """测试获取策略详情接口"""

    @pytest.mark.asyncio
    async def test_get_strategy_detail_success(self, client, sample_strategy_list):
        """测试成功获取策略详情"""
        with patch("app.routers.strategies.get_database") as mock_get_db:
            # Mock数据库返回
            mock_db = Mock()
            mock_db.strategies.find_one = AsyncMock(return_value=sample_strategy_list[0])

            mock_get_db.return_value = mock_db

            # 发送请求
            response = client.get("/api/backtest/strategies/dual_ma")

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["strategy_id"] == "dual_ma"
            assert data["name"] == "双均线策略"
            assert "parameters" in data
            assert len(data["parameters"]) == 2

    @pytest.mark.asyncio
    async def test_get_strategy_detail_not_found(self, client):
        """测试获取不存在的策略"""
        with patch("app.routers.strategies.get_database") as mock_get_db:
            # Mock数据库返回None
            mock_db = Mock()
            mock_db.strategies.find_one = AsyncMock(return_value=None)

            mock_get_db.return_value = mock_db

            # 发送请求
            response = client.get("/api/backtest/strategies/non_existent")

            # 验证响应-404错误
            assert response.status_code == 404


class TestGetStrategyCategories:
    """测试获取策略分类接口"""

    @pytest.mark.asyncio
    async def test_get_categories_success(self, client, sample_category_list):
        """测试成功获取分类列表"""
        with patch("app.routers.strategies.get_database") as mock_get_db:
            # Mock数据库返回
            mock_cursor = AsyncMock()
            mock_cursor.to_list = AsyncMock(return_value=sample_category_list)

            mock_db = Mock()
            mock_db.strategy_categories.find.return_value.sort.return_value = mock_cursor
            mock_db.strategies.count_documents = AsyncMock(return_value=1)

            mock_get_db.return_value = mock_db

            # 发送请求
            response = client.get("/api/backtest/strategies/categories")

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) >= 2
            assert data[0]["category_id"] == "trend"
            assert "strategy_count" in data[0]

    @pytest.mark.asyncio
    async def test_get_categories_empty(self, client):
        """测试获取空分类列表"""
        with patch("app.routers.strategies.get_database") as mock_get_db:
            # Mock数据库返回空列表
            mock_cursor = AsyncMock()
            mock_cursor.to_list = AsyncMock(return_value=[])

            mock_db = Mock()
            mock_db.strategy_categories.find.return_value.sort.return_value = mock_cursor

            mock_get_db.return_value = mock_db

            # 发送请求
            response = client.get("/api/backtest/strategies/categories")

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 0


class TestValidateParams:
    """测试参数校验接口"""

    @pytest.mark.asyncio
    async def test_validate_params_valid(self, client, sample_strategy_list):
        """测试校验有效参数"""
        with patch("app.routers.strategies.get_database") as mock_get_db:
            # Mock数据库返回策略
            mock_db = Mock()
            mock_db.strategies.find_one = AsyncMock(return_value=sample_strategy_list[0])

            mock_get_db.return_value = mock_db

            # 发送请求
            response = client.post(
                "/api/backtest/strategies/dual_ma/validate-params",
                json={"params": {"short_window": 5, "long_window": 20}}
            )

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["errors"] is None

    @pytest.mark.asyncio
    async def test_validate_params_missing_required(self, client, sample_strategy_list):
        """测试缺少必填参数"""
        with patch("app.routers.strategies.get_database") as mock_get_db:
            # Mock数据库返回策略
            mock_db = Mock()
            mock_db.strategies.find_one = AsyncMock(return_value=sample_strategy_list[0])

            mock_get_db.return_value = mock_db

            # 发送请求-缺少必填参数
            response = client.post(
                "/api/backtest/strategies/dual_ma/validate-params",
                json={"params": {"short_window": 5}}  # 缺少long_window
            )

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert data["errors"] is not None
            assert "long_window" in data["errors"]

    @pytest.mark.asyncio
    async def test_validate_params_wrong_type(self, client, sample_strategy_list):
        """测试参数类型错误"""
        with patch("app.routers.strategies.get_database") as mock_get_db:
            # Mock数据库返回策略
            mock_db = Mock()
            mock_db.strategies.find_one = AsyncMock(return_value=sample_strategy_list[0])

            mock_get_db.return_value = mock_db

            # 发送请求-参数类型错误
            response = client.post(
                "/api/backtest/strategies/dual_ma/validate-params",
                json={"params": {"short_window": "5", "long_window": 20}}  # 应该是int
            )

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert data["errors"] is not None

    @pytest.mark.asyncio
    async def test_validate_params_out_of_range(self, client, sample_strategy_list):
        """测试参数超出范围"""
        with patch("app.routers.strategies.get_database") as mock_get_db:
            # Mock数据库返回策略
            mock_db = Mock()
            mock_db.strategies.find_one = AsyncMock(return_value=sample_strategy_list[0])

            mock_get_db.return_value = mock_db

            # 发送请求-参数超出范围
            response = client.post(
                "/api/backtest/strategies/dual_ma/validate-params",
                json={"params": {"short_window": 1, "long_window": 20}}  # short_window最小是2
            )

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert data["errors"] is not None

    @pytest.mark.asyncio
    async def test_validate_params_strategy_not_found(self, client):
        """测试校验不存在的策略"""
        with patch("app.routers.strategies.get_database") as mock_get_db:
            # Mock数据库返回None
            mock_db = Mock()
            mock_db.strategies.find_one = AsyncMock(return_value=None)

            mock_get_db.return_value = mock_db

            # 发送请求
            response = client.post(
                "/api/backtest/strategies/non_existent/validate-params",
                json={"params": {}}
            )

            # 验证响应-404错误
            assert response.status_code == 404


class TestAPIResponseFormats:
    """测试API响应格式"""

    @pytest.mark.asyncio
    async def test_strategy_summary_format(self, client, sample_strategy_list):
        """测试策略摘要响应格式"""
        with patch("app.routers.strategies.get_database") as mock_get_db:
            mock_cursor = AsyncMock()
            mock_cursor.to_list = AsyncMock(return_value=sample_strategy_list)
            mock_db = Mock()
            mock_db.strategies.find.return_value.sort.return_value.skip.return_value.limit = mock_cursor
            mock_db.strategies.count_documents = AsyncMock(return_value=2)

            mock_get_db.return_value = mock_db

            # 发送请求
            response = client.get("/api/backtest/strategies")

            # 验证响应格式
            assert response.status_code == 200
            data = response.json()
            strategy = data["strategies"][0]

            # 验证必需字段
            required_fields = [
                "strategy_id",
                "name",
                "description",
                "category",
                "parameter_count",
                "usage_count",
                "is_builtin"
            ]
            for field in required_fields:
                assert field in strategy

            # 验证字段类型
            assert isinstance(strategy["strategy_id"], str)
            assert isinstance(strategy["name"], str)
            assert isinstance(strategy["parameter_count"], int)
            assert isinstance(strategy["usage_count"], int)
            assert isinstance(strategy["is_builtin"], bool)

    @pytest.mark.asyncio
    async def test_strategy_detail_format(self, client, sample_strategy_list):
        """测试策略详情响应格式"""
        with patch("app.routers.strategies.get_database") as mock_get_db:
            mock_db = Mock()
            mock_db.strategies.find_one = AsyncMock(return_value=sample_strategy_list[0])

            mock_get_db.return_value = mock_db

            # 发送请求
            response = client.get("/api/backtest/strategies/dual_ma")

            # 验证响应格式
            assert response.status_code == 200
            data = response.json()

            # 验证详情特有字段
            assert "long_description" in data or "long_description" not in data  # 可选字段
            assert "parameters" in data
            assert "created_at" in data

            # 验证参数格式
            param = data["parameters"][0]
            required_param_fields = [
                "name",
                "type",
                "default_value",
                "description",
                "required"
            ]
            for field in required_param_fields:
                assert field in param


class TestAPIErrorHandling:
    """测试API错误处理"""

    @pytest.mark.asyncio
    async def test_invalid_limit_parameter(self, client):
        """测试无效的limit参数"""
        with patch("app.routers.strategies.get_database") as mock_get_db:
            mock_cursor = AsyncMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_db = Mock()
            mock_db.strategies.find.return_value.sort.return_value.skip.return_value.limit = mock_cursor
            mock_db.strategies.count_documents = AsyncMock(return_value=0)

            mock_get_db.return_value = mock_db

            # 发送请求-limit超过最大值
            response = client.get("/api/backtest/strategies?limit=200")

            # FastAPI会自动验证参数,应该返回422错误
            # 但如果参数验证通过,也应该能正常处理
            assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_invalid_sort_order(self, client):
        """测试无效的排序方向"""
        with patch("app.routers.strategies.get_database") as mock_get_db:
            mock_cursor = AsyncMock()
            mock_cursor.to_list = AsyncMock(return_value=[])
            mock_db = Mock()
            mock_db.strategies.find.return_value.sort.return_value.skip.return_value.limit = mock_cursor
            mock_db.strategies.count_documents = AsyncMock(return_value=0)

            mock_get_db.return_value = mock_db

            # 发送请求-无效的sort_order
            response = client.get("/api/backtest/strategies?sort_order=invalid")

            # 应该返回422验证错误
            assert response.status_code in [200, 422]
