"""MDVAES 数据读取器测试"""

import pytest
from app.services.mdvaes_data_reader import MDVAESDataReader


class TestMDVAESDataReader:
    """MDVAES 数据读取器测试"""

    @pytest.fixture
    def data_reader(self):
        """创建数据读取器实例"""
        return MDVAESDataReader()

    def test_extrapolate_eps(self, data_reader):
        """测试 EPS 外推"""
        historical_eps = [
            {"eps": 1.0, "end_date": "2020-12-31"},
            {"eps": 1.15, "end_date": "2021-12-31"},
            {"eps": 1.32, "end_date": "2022-12-31"}
        ]

        forecasts = data_reader._extrapolate_eps(historical_eps, 2)

        assert len(forecasts) == 2
        # base_year = 2020 (latest end_date), +1 = 2021, +2 = 2022
        assert forecasts[0].year == 2021
        assert forecasts[0].source == "historical_extrapolation"

    def test_extract_year_from_quarter(self, data_reader):
        """测试从季度提取年份"""
        assert data_reader._extract_year_from_quarter("2024Q1") == 2024
        assert data_reader._extract_year_from_quarter("2023Q4") == 2023
        assert data_reader._extract_year_from_quarter("invalid") is None
