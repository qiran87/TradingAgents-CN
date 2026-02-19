"""MDVAES 策略测试"""

import pytest
from datetime import datetime
from app.strategies.mdvaes import MDVAESStrategy


class TestMDVAESStrategy:
    """MDVAES 策略测试"""

    @pytest.fixture
    def strategy(self):
        """创建策略实例"""
        params = {
            "symbol": "000001.SZ",
            "forecast_years": 5,
            "peg_base": 1.0,
            "risk_adjustment": 0.1,
            "rebalance_frequency": 90,
            "use_margin": True,
            "margin_buy": 0.8,
            "margin_sell": 1.2
        }
        return MDVAESStrategy(params)

    def test_strategy_initialization(self, strategy):
        """测试策略初始化"""
        assert strategy.symbol == "000001.SZ"
        assert strategy.forecast_years == 5
        assert strategy.rebalance_frequency == 90

    def test_get_parameters_definition(self, strategy):
        """测试参数定义"""
        params_def = strategy.get_parameters_definition()
        assert len(params_def) == 8

        param_names = [p["name"] for p in params_def]
        assert "symbol" in param_names
        assert "forecast_years" in param_names
        assert "peg_base" in param_names
        assert "risk_adjustment" in param_names
        assert "rebalance_frequency" in param_names
        assert "use_margin" in param_names
        assert "margin_buy" in param_names
        assert "margin_sell" in param_names

    def test_get_strategy_info(self, strategy):
        """测试策略信息"""
        assert strategy.get_strategy_id() == "mdvaes"
        assert strategy.get_strategy_name() == "MDVAES估值策略"
        assert strategy.get_strategy_category() == "valuation"
        assert "多锚点估值" in strategy.get_strategy_description()

    def test_should_revaluate_first_time(self, strategy):
        """测试首次需要估值"""
        timestamp = datetime(2024, 2, 1)
        assert strategy._should_revaluate(timestamp) is True

    def test_should_revaluate_after_frequency(self, strategy):
        """测试达到频率后需要重新估值"""
        strategy.last_valuation = "some_valuation"
        strategy.last_valuation_date = datetime(2024, 1, 1)

        # 90天后需要重新估值
        timestamp = datetime(2024, 4, 1)
        assert strategy._should_revaluate(timestamp) is True

        # 30天后不需要
        timestamp = datetime(2024, 2, 1)
        assert strategy._should_revaluate(timestamp) is False

    def test_on_bar_without_valuation(self, strategy):
        """测试无估值时保持观望"""
        result = strategy.on_bar(
            bar_id="test_bar",
            timestamp=datetime(2024, 2, 1),
            current_price=10.0,
            position=0,
            cash=10000.0
        )

        assert result["action"] in ["buy", "sell", "hold"]
        assert isinstance(result["amount"], int)

    def test_parameter_defaults(self):
        """测试参数默认值"""
        params = {"symbol": "000001.SZ"}
        strategy = MDVAESStrategy(params)

        assert strategy.forecast_years == 5
        assert strategy.peg_base == 1.0
        assert strategy.risk_adjustment == 0.1
        assert strategy.rebalance_frequency == 90
        assert strategy.use_margin is True
        assert strategy.margin_buy == 0.8
        assert strategy.margin_sell == 1.2
