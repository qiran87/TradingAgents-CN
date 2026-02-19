"""MDVAES 数据同步服务测试"""

import pytest
from app.services.mdvaes_data_sync_service import MDVAESDataSyncService


class TestMDVAESDataSyncService:
    """MDVAES 数据同步服务测试"""

    @pytest.fixture
    def service(self):
        return MDVAESDataSyncService()

    def test_init(self, service):
        """测试初始化"""
        assert service.pro is not None
