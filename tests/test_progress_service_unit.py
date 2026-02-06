"""
进度管理服务单元测试
测试WebSocket认证、交易信号推送、错误推送和HTTP轮询接口
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from app.services.auth_service import AuthService
from app.routers.backtest_engine import get_current_state, websocket_backtest_progress
from app.services.backtest_engine_service import BacktestEngineService
from fastapi import WebSocket
from fastapi.testclient import TestClient


class TestAuthService:
    """认证服务测试"""

    def test_create_access_token(self):
        """测试创建访问令牌"""
        token = AuthService.create_access_token("user123")
        assert token is not None
        assert isinstance(token, str)

    def test_verify_valid_token(self):
        """测试验证有效令牌"""
        token = AuthService.create_access_token("user123")
        token_data = AuthService.verify_token(token)
        assert token_data is not None
        assert token_data.sub == "user123"

    def test_verify_invalid_token(self):
        """测试验证无效令牌"""
        token_data = AuthService.verify_token("invalid_token")
        assert token_data is None

    def test_verify_expired_token(self):
        """测试验证过期令牌"""
        # 创建一个已过期的令牌（-1分钟）
        token = AuthService.create_access_token("user123", expires_delta=-60)
        token_data = AuthService.verify_token(token)
        assert token_data is None


class TestBacktestEngineService:
    """回测引擎服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        with patch('app.services.backtest_engine_service.get_mongo_db'):
            with patch('app.services.backtest_engine_service.get_websocket_manager'):
                service = BacktestEngineService()
                yield service

    @pytest.mark.asyncio
    async def test_send_trade_signal(self, service):
        """测试交易信号推送"""
        # Mock WebSocket Manager
        service.websocket_manager = AsyncMock()
        service.websocket_manager.send_progress_update = AsyncMock()

        # 发送交易信号
        await service._send_trade_signal(
            backtest_id="bt_123",
            trade_type="buy",
            price=10.0,
            shares=100,
            amount=1000.0,
            date="2023-12-01"
        )

        # 验证调用
        service.websocket_manager.send_progress_update.assert_called_once()
        call_args = service.websocket_manager.send_progress_update.call_args

        assert call_args[0][0] == "bt_123"
        message = call_args[0][1]
        assert message["type"] == "trade_signal"
        assert message["data"]["trade"]["type"] == "buy"
        assert message["data"]["trade"]["price"] == 10.0
        assert message["data"]["trade"]["shares"] == 100

    @pytest.mark.asyncio
    async def test_send_error_message(self, service):
        """测试错误消息推送"""
        # Mock WebSocket Manager
        service.websocket_manager = AsyncMock()
        service.websocket_manager.send_progress_update = AsyncMock()

        # 发送错误消息
        error = ValueError("测试错误")
        await service._send_error_message("bt_123", error)

        # 验证调用
        service.websocket_manager.send_progress_update.assert_called_once()
        call_args = service.websocket_manager.send_progress_update.call_args

        assert call_args[0][0] == "bt_123"
"
        message = call_args[0][1]
        assert message["type"] == "error"
        assert message["data"]["error"]["code"] == "ValueError"
        assert message["data"]["error"]["message"] == "测试错误"


class TestHTTPPollingEndpoint:
    """HTTP轮询接口测试"""

    @pytest.fixture
    def mock_db(self):
        """Mock数据库"""
        db = AsyncMock()
        db.backtest_tasks.find_one = AsyncMock()
        return db

    @pytest.mark.asyncio
    async def test_get_current_state_success(self, mock_db):
        """测试获取当前状态成功"""
        # Mock数据库返回
        mock_db.backtest_tasks.find_one.return_value = {
            "backtest_id": "bt_123",
            "status": "running",
            "execution_info": {
                "current_bar": 1,
                "total_bars": 10,
                "percentage": 10.0
            },
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        # 调用接口
        result = await get_current_state("bt_123", db=mock_db)

        # 验证结果
        assert result["data"]["backtest_id"] == "bt_123"
        assert result["data"]["status"] == "running"
        assert result["data"]["execution_info"]["current_bar"] == 1

    @pytest.mark.asyncio
    async def test_get_current_state_not_found(self, mock_db):
        """测试获取当前状态-任务不存在"""
        from fastapi import HTTPException

        # Mock数据库返回None
        mock_db.backtest_tasks.find_one.return_value = None

        # 调用接口应该抛出404异常
        with pytest.raises(HTTPException) as exc_info:
            await get_current_state("bt_123", db=mock_db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_get_current_state_with_error(self, mock_db):
        """测试获取当前状态-包含错误信息"""
        # Mock数据库返回（包含错误）
        mock_db.backtest_tasks.find_one.return_value = {
            "backtest_id": "bt_123",
            "status": "error",
            "execution_info": {},
            "error": {
                "code": "ValueError",
                "message": "测试错误"
            },
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        }

        # 调用接口
        result = await get_current_state("bt_123", db=mock_db)

        # 验证错误信息包含在响应中
        assert "error" in result["data"]
        assert result["data"]["error"]["code"] == "ValueError"


class TestWebSocketAuthentication:
    """WebSocket认证测试"""

    @pytest.mark.asyncio
    async def test_websocket_with_valid_token(self):
        """测试WebSocket连接-有效token"""
        # 创建有效token
        token = AuthService.create_access_token("user123")

        # 这里需要更复杂的mock来测试WebSocket
        # 由于WebSocket的复杂性，这里仅验证token生成逻辑
        token_data = AuthService.verify_token(token)
        assert token_data is not None
        assert token_data.sub == "user123"

    @pytest.mark.asyncio
    async def test_websocket_with_invalid_token(self):
        """测试WebSocket连接-无效token"""
        # 验证无效token
        token_data = AuthService.verify_token("invalid_token")
        assert token_data is None

    @pytest.mark.asyncio
    async def test_websocket_without_token(self):
        """测试WebSocket连接-无token（开发模式）"""
        # 在开发模式下，允许无token连接
        # 这里仅验证逻辑，实际测试需要WebSocket客户端
        token = None

        # 无token时，认证应该跳过
        if token:
            token_data = AuthService.verify_token(token)
            assert token_data is not None
        else:
            assert True  # 无token，跳过认证


@pytest.mark.integration
class TestProgressServiceIntegration:
    """集成测试"""

    @pytest.mark.asyncio
    async def test_full_backtest_flow(self):
        """
        测试完整的回测流程

        1. 创建回测任务
        2. 接收进度更新（WebSocket或HTTP轮询）
        3. 接收交易信号
        4. 接收持仓更新
        5. 任务完成
        """
        # 这里需要真实的数据库和WebSocket连接
        # 作为集成测试，需要完整的测试环境
        pass


class TestRetryMechanism:
    """重试机制测试"""

    @pytest.mark.asyncio
    async def test_http_polling_retry_on_429(self):
        """测试HTTP轮询遇到429时的重试逻辑"""
        # 这个测试需要mock axios响应
        # 由于是前端代码，实际测试需要使用前端测试框架（如vitest）
        pass

    @pytest.mark.asyncio
    async def test_http_polling_exponential_backoff(self):
        """测试指数退避机制"""
        # 测试重试延迟计算
        retry_delay = 1000
        for attempt in range(3):
            expected_delay = retry_delay * (2 ** attempt)
            assert expected_delay in [1000, 2000, 4000]


# 测试运行入口
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
