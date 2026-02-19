"""估值计算器测试"""

import pytest
from app.services.valuation_calculator import ValuationCalculator
from app.domain.mdvaes import (
    GrowthMetrics, RiskMetrics, MDVAESParams, SignalType, TrendStability, RiskLevel
)


class TestValuationCalculator:
    """估值计算器测试"""
    
    @pytest.fixture
    def sample_growth_metrics(self):
        """示例增长指标"""
        return GrowthMetrics(
            cagr=0.15,
            growth_rate=0.12,
            r_squared=0.85,
            growth_quality_score=0.8,
            trend_stability=TrendStability.STABLE
        )
    
    @pytest.fixture
    def sample_risk_metrics(self):
        """示例风险指标"""
        return RiskMetrics(
            debt_to_assets=0.4,
            current_ratio=1.5,
            quick_ratio=1.2,
            cashflow_to_income=1.1,
            risk_level=RiskLevel.MEDIUM
        )
    
    @pytest.fixture
    def sample_params(self):
        """示例参数"""
        return MDVAESParams(
            forecast_years=5,
            peg_base=1.0,
            risk_adjustment=0.1
        )
    
    def test_calculate_valuation(self, sample_growth_metrics, sample_risk_metrics, sample_params):
        """测试估值计算"""
        result = ValuationCalculator.calculate(
            growth_metrics=sample_growth_metrics,
            risk_metrics=sample_risk_metrics,
            eps=2.0,
            current_pe=15.0,
            bond_rate=0.0275,
            params=sample_params
        )
        
        assert result.intrinsic_value > 0  # 内在价值应为正
        assert result.lower_bound <= result.intrinsic_value <= result.upper_bound  # 价值在区间内
        assert 0 <= result.confidence <= 1  # 置信度在 0-1 之间
        assert result.signal in [SignalType.BUY, SignalType.SELL, SignalType.HOLD]
        assert "peg" in result.valuation_method
        assert "pe_historical" in result.valuation_method
    
    def test_peg_valuation_calculation(self, sample_growth_metrics, sample_params):
        """测试 PEG 估值计算"""
        peg = ValuationCalculator._calc_peg_valuation(
            eps=2.0,
            growth_metrics=sample_growth_metrics,
            bond_rate=0.0275,
            params=sample_params
        )
        assert peg > 0  # PEG 估值应为正
    
    def test_pe_historical_valuation(self, sample_growth_metrics):
        """测试历史 PE 估值"""
        pe_hist = ValuationCalculator._calc_pe_historical_valuation(
            eps=2.0,
            current_pe=15.0,
            growth_metrics=sample_growth_metrics
        )
        assert pe_hist > 0  # 历史 PE 估值应为正
    
    def test_dcf_valuation(self, sample_growth_metrics, sample_params):
        """测试 DCF 估值"""
        dcf = ValuationCalculator._calc_dcf_valuation(
            eps=2.0,
            growth_rate=0.12,
            discount_rate=0.0275,
            params=sample_params
        )
        assert dcf > 0  # DCF 估值应为正
    
    def test_risk_adjustment_factor(self):
        """测试风险调整系数"""
        assert ValuationCalculator._get_risk_adjustment_factor(RiskLevel.LOW) == 0.5
        assert ValuationCalculator._get_risk_adjustment_factor(RiskLevel.MEDIUM) == 1.0
        assert ValuationCalculator._get_risk_adjustment_factor(RiskLevel.HIGH) == 1.5
    
    def test_confidence_calculation(self, sample_growth_metrics, sample_risk_metrics):
        """测试置信度计算"""
        confidence = ValuationCalculator._calc_confidence(
            growth_metrics=sample_growth_metrics,
            risk_metrics=sample_risk_metrics
        )
        assert 0.3 <= confidence <= 0.95  # 置信度应在合理范围内
    
    def test_signal_generation_valuation_range(self, sample_params):
        """测试估值区间信号生成"""
        # 低于下限 → 买入
        signal = ValuationCalculator._generate_signal(
            intrinsic_value=50,
            lower_bound=60,
            upper_bound=80,
            params=sample_params
        )
        assert signal == SignalType.BUY
        
        # 高于上限 → 卖出
        signal = ValuationCalculator._generate_signal(
            intrinsic_value=90,
            lower_bound=60,
            upper_bound=80,
            params=sample_params
        )
        assert signal == SignalType.SELL
        
        # 在区间内 → 持有
        signal = ValuationCalculator._generate_signal(
            intrinsic_value=70,
            lower_bound=60,
            upper_bound=80,
            params=sample_params
        )
        assert signal == SignalType.HOLD
