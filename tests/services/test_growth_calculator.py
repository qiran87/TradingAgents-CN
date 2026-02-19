"""增长率计算器测试"""

import pytest
import numpy as np
from app.services.growth_calculator import GrowthCalculator
from app.domain.mdvaes import EPSForecast, TrendStability


class TestGrowthCalculator:
    """增长率计算器测试"""
    
    @pytest.fixture
    def sample_forecasts(self):
        """示例 EPS 预测数据"""
        return [
            EPSForecast(year=2020, eps_forecast=1.0, forecast_date="2020-01-01", analyst_count=5, source="analyst"),
            EPSForecast(year=2021, eps_forecast=1.15, forecast_date="2021-01-01", analyst_count=5, source="analyst"),
            EPSForecast(year=2022, eps_forecast=1.32, forecast_date="2022-01-01", analyst_count=5, source="analyst"),
            EPSForecast(year=2023, eps_forecast=1.52, forecast_date="2023-01-01", analyst_count=5, source="analyst"),
            EPSForecast(year=2024, eps_forecast=1.75, forecast_date="2024-01-01", analyst_count=5, source="analyst"),
        ]
    
    def test_calculate_growth_metrics(self, sample_forecasts):
        """测试增长指标计算"""
        metrics = GrowthCalculator.calculate(sample_forecasts)
        
        assert metrics.cagr > 0  # CAGR 应为正数
        assert metrics.growth_rate > 0  # 增长率应为正数
        assert 0 <= metrics.r_squared <= 1  # R² 在 0-1 之间
        assert 0 <= metrics.growth_quality_score <= 1  # 质量评分在 0-1 之间
        assert metrics.trend_stability in [TrendStability.STABLE, TrendStability.VOLATILE, TrendStability.DECLINING]
    
    def test_insufficient_data_raises_error(self):
        """测试数据不足时抛出异常"""
        with pytest.raises(ValueError, match="至少需要 2 个 EPS 预测数据点"):
            GrowthCalculator.calculate([
                EPSForecast(year=2024, eps_forecast=1.0, forecast_date="2024-01-01", analyst_count=5, source="analyst")
            ])
    
    def test_negative_eps_raises_error(self):
        """测试全为负数 EPS 时抛出异常"""
        with pytest.raises(ValueError, match="所有 EPS 值都必须为正数"):
            GrowthCalculator.calculate([
                EPSForecast(year=2023, eps_forecast=-1.0, forecast_date="2023-01-01", analyst_count=5, source="analyst"),
                EPSForecast(year=2024, eps_forecast=-2.0, forecast_date="2024-01-01", analyst_count=5, source="analyst"),
            ])
    
    def test_perfect_linear_growth(self):
        """测试完美线性增长"""
        # 完美对数线性增长的数据
        forecasts = [
            EPSForecast(year=2020, eps_forecast=1.0, forecast_date="2020-01-01", analyst_count=1, source="analyst"),
            EPSForecast(year=2021, eps_forecast=1.2, forecast_date="2021-01-01", analyst_count=1, source="analyst"),
            EPSForecast(year=2022, eps_forecast=1.44, forecast_date="2022-01-01", analyst_count=1, source="analyst"),
            EPSForecast(year=2023, eps_forecast=1.728, forecast_date="2023-01-01", analyst_count=1, source="analyst"),
        ]
        
        metrics = GrowthCalculator.calculate(forecasts)
        assert metrics.r_squared > 0.95  # 高 R²
        assert metrics.trend_stability == TrendStability.STABLE
