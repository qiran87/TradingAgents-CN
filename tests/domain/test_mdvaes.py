"""MDVAES 领域模型测试"""

import pytest
from app.domain.mdvaes import (
    EPSForecast, GrowthMetrics, RiskMetrics, ValuationResult,
    MDVAESParams, SignalType, TrendStability, RiskLevel
)


class TestEPSForecast:
    """EPS 预测实体测试"""
    
    def test_create_eps_forecast(self):
        """测试创建 EPS 预测"""
        forecast = EPSForecast(
            year=2024,
            eps_forecast=2.5,
            forecast_date="2024-01-15",
            analyst_count=10,
            source="analyst"
        )
        assert forecast.year == 2024
        assert forecast.eps_forecast == 2.5
        assert forecast.source == "analyst"
    
    def test_eps_forecast_immutable(self):
        """测试 EPS 预测不可变"""
        forecast = EPSForecast(
            year=2024,
            eps_forecast=2.5,
            forecast_date="2024-01-15",
            analyst_count=10,
            source="analyst"
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            forecast.year = 2025


class TestGrowthMetrics:
    """增长指标值对象测试"""
    
    def test_create_growth_metrics(self):
        """测试创建增长指标"""
        metrics = GrowthMetrics(
            cagr=0.15,
            growth_rate=0.12,
            r_squared=0.85,
            growth_quality_score=0.8,
            trend_stability=TrendStability.STABLE
        )
        assert metrics.cagr == 0.15
        assert metrics.growth_rate == 0.12
        assert metrics.r_squared == 0.85
        assert metrics.trend_stability == TrendStability.STABLE


class TestRiskMetrics:
    """风险指标值对象测试"""
    
    def test_create_risk_metrics(self):
        """测试创建风险指标"""
        metrics = RiskMetrics(
            debt_to_assets=0.4,
            current_ratio=1.5,
            quick_ratio=1.2,
            cashflow_to_income=1.1,
            risk_level=RiskLevel.MEDIUM
        )
        assert metrics.debt_to_assets == 0.4
        assert metrics.current_ratio == 1.5
        assert metrics.risk_level == RiskLevel.MEDIUM


class TestValuationResult:
    """估值结果值对象测试"""
    
    def test_create_valuation_result(self):
        """测试创建估值结果"""
        result = ValuationResult(
            intrinsic_value=100.0,
            lower_bound=80.0,
            upper_bound=120.0,
            confidence=0.85,
            valuation_method={"peg": 95.0, "pe_historical": 105.0},
            signal=SignalType.BUY
        )
        assert result.intrinsic_value == 100.0
        assert result.signal == SignalType.BUY
        assert result.lower_bound < result.intrinsic_value < result.upper_bound


class TestMDVAESParams:
    """MDVAES 参数值对象测试"""
    
    def test_default_params(self):
        """测试默认参数"""
        params = MDVAESParams()
        assert params.forecast_years == 5
        assert params.peg_base == 1.0
        assert params.anchor_weight["peg"] == 0.4
    
    def test_validate_success(self):
        """测试参数验证成功"""
        params = MDVAESParams(
            forecast_years=5,
            peg_base=1.0,
            risk_adjustment=0.1
        )
        params.validate()  # 应该不抛出异常
    
    def test_validate_invalid_forecast_years(self):
        """测试无效预测年数"""
        params = MDVAESParams(forecast_years=15)
        with pytest.raises(ValueError, match="forecast_years 必须在 1-10 之间"):
            params.validate()
    
    def test_validate_invalid_peg_base(self):
        """测试无效 PEG 基数"""
        params = MDVAESParams(peg_base=3.0)
        with pytest.raises(ValueError, match="peg_base 必须在 0.5-2.0 之间"):
            params.validate()
    
    def test_validate_invalid_weights(self):
        """测试无效权重总和"""
        params = MDVAESParams(anchor_weight={"peg": 0.5, "pe_historical": 0.3})
        with pytest.raises(ValueError, match="anchor_weight 总和必须为 1.0"):
            params.validate()
    
    def test_preset_conservative(self):
        """测试保守预设标记"""
        params = MDVAESParams(preset="conservative")
        assert params.preset == "conservative"
        # 预设逻辑可在未来实现参数调整

    def test_preset_aggressive(self):
        """测试激进预设标记"""
        params = MDVAESParams(preset="aggressive")
        assert params.preset == "aggressive"
        # 预设逻辑可在未来实现参数调整
