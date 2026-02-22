"""估值计算器"""

from typing import Dict
from app.domain.mdvaes import GrowthMetrics, RiskMetrics, ValuationResult, MDVAESParams, SignalType


class ValuationCalculator:
    """估值计算器"""

    @staticmethod
    def calculate(
        growth_metrics: GrowthMetrics,
        risk_metrics: RiskMetrics,
        eps: float,
        current_pe: float,
        bond_rate: float,
        params: MDVAESParams
    ) -> ValuationResult:
        """计算多锚点估值"""
        # 1. PEG 估值
        peg_valuation = ValuationCalculator._calc_peg_valuation(
            eps, growth_metrics, bond_rate, params
        )

        # 2. 历史 PE 估值
        pe_historical_valuation = ValuationCalculator._calc_pe_historical_valuation(
            eps, current_pe, growth_metrics
        )

        # 3. PB 估值（简化版，使用固定倍数）
        pb_valuation = eps * 1.5

        # 4. DCF 估值（简化版）
        dcf_valuation = ValuationCalculator._calc_dcf_valuation(
            eps, growth_metrics.growth_rate, bond_rate, params
        )

        # 5. 多锚点加权
        weighted_valuation = (
            params.anchor_weight["peg"] * peg_valuation +
            params.anchor_weight["pe_historical"] * pe_historical_valuation +
            params.anchor_weight["pb"] * pb_valuation +
            params.anchor_weight["dcf"] * dcf_valuation
        )

        # 6. 风险调整
        risk_adjustment_factor = ValuationCalculator._get_risk_adjustment_factor(
            risk_metrics.risk_level
        )
        adjusted_valuation = weighted_valuation * (1 - params.risk_adjustment * risk_adjustment_factor)

        # 7. 计算估值区间
        confidence = ValuationCalculator._calc_confidence(growth_metrics, risk_metrics)
        margin = adjusted_valuation * (1 - confidence) * 0.2

        lower_bound = adjusted_valuation - margin
        upper_bound = adjusted_valuation + margin

        # 8. 生成交易信号（注意：此时还没有当前价格，信号将在策略执行时根据价格生成）
        # 信号生成需要当前价格，但估值计算时没有价格信息
        # 因此这里只返回估值结果，信号由策略根据价格动态生成
        signal = SignalType.HOLD  # 默认持有，策略会根据价格重新计算

        return ValuationResult(
            intrinsic_value=adjusted_valuation,
            lower_bound=max(lower_bound, 0),
            upper_bound=upper_bound,
            confidence=confidence,
            valuation_method={
                "peg": peg_valuation,
                "pe_historical": pe_historical_valuation,
                "pb": pb_valuation,
                "dcf": dcf_valuation
            },
            signal=signal,
            eps=eps  # 存储当前使用的 EPS
        )

    @staticmethod
    def _calc_peg_valuation(eps: float, growth_metrics: GrowthMetrics, bond_rate: float, params: MDVAESParams) -> float:
        """计算 PEG 估值"""
        interest_adjustment = 1 - params.peg_interest_sensitivity * bond_rate
        peg_valuation = eps * growth_metrics.growth_rate * params.peg_base * interest_adjustment
        return max(peg_valuation, 0)

    @staticmethod
    def _calc_pe_historical_valuation(eps: float, current_pe: float, growth_metrics: GrowthMetrics) -> float:
        """基于历史 PE 估值"""
        growth_adjustment = 1 + growth_metrics.growth_rate
        pe_historical_valuation = eps * current_pe * growth_adjustment * 0.8
        return max(pe_historical_valuation, 0)

    @staticmethod
    def _calc_dcf_valuation(eps: float, growth_rate: float, discount_rate: float, params: MDVAESParams) -> float:
        """简化 DCF 估值"""
        terminal_growth = 0.03
        required_return = discount_rate + 0.05

        if growth_rate >= required_return:
            growth_rate = required_return - 0.01

        forecast_values = []
        for i in range(1, params.forecast_years + 1):
            forecast_eps = eps * ((1 + growth_rate) ** i)
            discounted_value = forecast_eps / ((1 + required_return) ** i)
            forecast_values.append(discounted_value)

        terminal_eps = eps * ((1 + growth_rate) ** params.forecast_years)
        terminal_value = terminal_eps * (1 + terminal_growth) / (required_return - terminal_growth)
        discounted_terminal = terminal_value / ((1 + required_return) ** params.forecast_years)

        dcf_valuation = sum(forecast_values) + discounted_terminal
        return max(dcf_valuation, 0)

    @staticmethod
    def _get_risk_adjustment_factor(risk_level: str) -> float:
        """获取风险调整系数"""
        risk_map = {"low": 0.5, "medium": 1.0, "high": 1.5}
        return risk_map.get(risk_level, 1.0)

    @staticmethod
    def _calc_confidence(growth_metrics: GrowthMetrics, risk_metrics: RiskMetrics) -> float:
        """计算估值置信度"""
        base_confidence = growth_metrics.r_squared
        risk_penalty = {"low": 0.0, "medium": 0.1, "high": 0.2}
        penalty = risk_penalty.get(risk_metrics.risk_level, 0.1)
        confidence = max(base_confidence - penalty, 0.3)
        return min(confidence, 0.95)

    @staticmethod
    def _generate_signal(intrinsic_value: float, lower_bound: float, upper_bound: float, params: MDVAESParams) -> SignalType:
        """生成交易信号"""
        if params.signal_mode == "valuation_range":
            if intrinsic_value < lower_bound:
                return SignalType.BUY
            elif intrinsic_value > upper_bound:
                return SignalType.SELL
            else:
                return SignalType.HOLD
        else:  # safety_margin
            buy_threshold = intrinsic_value * params.safety_margin_buy
            sell_threshold = intrinsic_value * params.safety_margin_sell

            if intrinsic_value <= buy_threshold:
                return SignalType.BUY
            elif intrinsic_value >= sell_threshold:
                return SignalType.SELL
            else:
                return SignalType.HOLD
