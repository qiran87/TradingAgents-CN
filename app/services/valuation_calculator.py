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
        params: MDVAESParams,
        fcfps: float = None,
        bps: float = None,
        roe: float = None
    ) -> ValuationResult:
        """计算多锚点估值

        Args:
            growth_metrics: 增长指标
            risk_metrics: 风险指标
            eps: 每股收益
            current_pe: 当前市盈率
            bond_rate: 无风险利率
            params: MDVAES 参数
            fcfps: 每股自由现金流（可选，如果提供则用于 DCF 计算）
            bps: 每股净资产（可选，用于 PB 估值）
            roe: 净资产收益率（可选，用于 PB 估值）
        """
        # 1. PEG 估值
        peg_valuation = ValuationCalculator._calc_peg_valuation(
            eps, growth_metrics, bond_rate, params
        )

        # 2. 历史 PE 估值
        pe_historical_valuation = ValuationCalculator._calc_pe_historical_valuation(
            eps, current_pe, growth_metrics
        )

        # 3. PB 估值（基于 PB-ROE 模型）
        # 优先使用 risk_metrics 中的 bps/roe，否则使用传入的参数
        actual_bps = risk_metrics.bps if risk_metrics.bps is not None else bps
        actual_roe = risk_metrics.roe if risk_metrics.roe is not None else roe

        if actual_bps is not None and actual_bps > 0 and actual_roe is not None and actual_roe > 0:
            # 使用 PB-ROE 模型：合理 PB = ROE / 要求收益率
            # 目标收益率设为 10%
            target_return = 0.10  # 10%
            target_pb = actual_roe / target_return
            pb_valuation = actual_bps * target_pb
        else:
            # 降级：使用简化版本（基于 EPS）
            pb_valuation = eps * 1.5

        # 4. DCF 估值（优先使用 fcfps，否则使用 eps）
        if fcfps is not None and fcfps > 0:
            dcf_valuation = ValuationCalculator._calc_dcf_valuation_fcfps(
                fcfps, growth_metrics.growth_rate, bond_rate, params
            )
        else:
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
        """计算 PEG 估值

        修正版公式：使用 growth_rate × 100 而非 growth_rate
        原因：原始公式 EPS × growth_rate 适用于小EPS公司，对高EPS公司会严重低估
        """
        interest_adjustment = 1 - params.peg_interest_sensitivity * bond_rate
        # 修正：使用增长率百分比形式（如 4.47% → 4.47）而非小数形式（0.0447）
        peg_valuation = eps * (growth_metrics.growth_rate * 100) * params.peg_base * interest_adjustment
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
    def _calc_dcf_valuation_fcfps(fcfps: float, growth_rate: float, discount_rate: float, params: MDVAESParams) -> float:
        """使用每股自由现金流 (FCFPS) 的 DCF 估值

        相比基于 EPS 的简化 DCF，使用真实的自由现金流能更准确地反映公司价值。

        Args:
            fcfps: 每股自由现金流
            growth_rate: 增长率
            discount_rate: 折现率（无风险利率）
            params: MDVAES 参数

        Returns:
            DCF 估值结果
        """
        terminal_growth = 0.03  # 终值增长率 3%
        required_return = discount_rate + 0.05  # 必要回报率 = 无风险利率 + 5%风险溢价

        # 防御性检查：增长率不能超过必要回报率
        if growth_rate >= required_return:
            growth_rate = required_return - 0.01

        # 预测期现金流折现
        forecast_values = []
        for i in range(1, params.forecast_years + 1):
            # 预测未来自由现金流
            forecast_fcf = fcfps * ((1 + growth_rate) ** i)
            # 折现到现值
            discounted_value = forecast_fcf / ((1 + required_return) ** i)
            forecast_values.append(discounted_value)

        # 终值计算（永续增长模型）
        terminal_fcf = fcfps * ((1 + growth_rate) ** params.forecast_years)
        terminal_value = terminal_fcf * (1 + terminal_growth) / (required_return - terminal_growth)
        discounted_terminal = terminal_value / ((1 + required_return) ** params.forecast_years)

        # 总估值 = 预测期折现总和 + 终值折现
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
