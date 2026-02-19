"""MDVAES API 路由测试"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


class TestMDVAESRouter:
    """MDVAES 路由测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_get_parameters_endpoint_exists(self, client):
        """测试获取参数端点存在"""
        response = client.get("/api/mdvaes/parameters")
        # 未认证应返回401或403
        assert response.status_code in [401, 403]

    def test_cache_status_endpoint_exists(self, client):
        """测试缓存状态端点存在"""
        response = client.get("/api/mdvaes/cache/status")
        # 未认证应返回401
        assert response.status_code in [401, 403]

    def test_calculate_endpoint_exists(self, client):
        """测试计算端点存在"""
        response = client.post("/api/mdvaes/calculate", json={
            "symbol": "000001.SZ",
            "calculation_date": "2024-01-15"
        })
        # 未认证应返回401或400
        assert response.status_code in [401, 400]
