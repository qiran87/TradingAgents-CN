"""
MACD策略

基于MACD指标的金叉死叉进行交易。
MACD由快线（DIF）、慢线（DEA）和柱状图（MACD）组成。
"""
from typing import Dict, Any, List
from datetime import datetime
from app.strategies.base import BaseStrategy


class MACDStrategy(BaseStrategy):
    """MACD策略"""

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.fast_period = self.get_parameter("fast_period", 12)
        self.slow_period = self.get_parameter("slow_period", 26)
        self.signal_period = self.get_parameter("signal_period", 9)
        self.price_history = []
        self.dif_history = []  # DIF历史
        self.dea_history = []  # DEA历史

    def get_parameters_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "fast_period",
                "type": "int",
                "default_value": 12,
                "range": {"min": 5, "max": 50},
                "description": "快线周期",
                "required": True
            },
            {
                "name": "slow_period",
                "type": "int",
                "default_value": 26,
                "range": {"min": 10, "max": 100},
                "description": "慢线周期",
                "required": True
            },
            {
                "name": "signal_period",
                "type": "int",
                "default_value": 9,
                "range": {"min": 5, "max": 20},
                "description": "信号线周期",
                "required": True
            }
        ]

    def get_strategy_id(self) -> str:
        return "macd"

    def get_strategy_name(self) -> str:
        return "MACD策略"

    def get_strategy_description(self) -> str:
        return "基于MACD指标的金叉死叉进行交易。当DIF上穿DEA时买入（金叉），当DIF下穿DEA时卖出（死叉）。"

    def get_strategy_category(self) -> str:
        return "trend"

    def _calculate_ema(self, data: List[float], period: int) -> float:
        """计算指数移动平均线"""
        if not data:
            return 0.0

        multiplier = 2 / (period + 1)
        ema = data[0]

        for price in data[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))

        return ema

    def on_bar(
        self,
        bar_id: str,
        timestamp: datetime,
        current_price: float,
        position: int,
        cash: float
    ) -> Dict[str, Any]:
        """
        处理单个K线数据

        Args:
            bar_id: K线ID
            timestamp: 时间戳
            current_price: 当前价格
            position: 当前持仓（股数）
            cash: 当前现金（元）

        Returns:
            交易信号
        """
        # 添加到价格历史
        self.price_history.append(current_price)

        # 需要足够的历史数据
        required_period = self.slow_period + self.signal_period
        if len(self.price_history) < required_period:
            return {"action": "hold", "amount": 0, "reason": "数据积累中"}

        # 计算快线EMA
        fast_ema = self._calculate_ema(self.price_history[-self.fast_period:], self.fast_period)

        # 计算慢线EMA
        slow_ema = self._calculate_ema(self.price_history[-self.slow_period:], self.slow_period)

        # 计算DIF
        dif = fast_ema - slow_ema
        self.dif_history.append(dif)

        # 计算DEA（信号线，DIF的EMA）
        if len(self.dif_history) >= self.signal_period:
            dea = self._calculate_ema(self.dif_history[-self.signal_period:], self.signal_period)
            self.dea_history.append(dea)

            # 需要至少2个DEA值来判断交叉
            if len(self.dea_history) >= 2:
                prev_dif = self.dif_history[-2]
                prev_dea = self.dea_history[-2]
                curr_dif = self.dif_history[-1]
                curr_dea = self.dea_history[-1]

                # 金叉：DIF上穿DEA
                if prev_dif <= prev_dea and curr_dif > curr_dea:
                    if position == 0:
                        buy_amount = int((cash * 0.9) / current_price / 100) * 100
                        if buy_amount > 0:
                            return {
                                "action": "buy",
                                "amount": buy_amount,
                                "reason": f"MACD金叉: DIF({curr_dif:.4f})上穿DEA({curr_dea:.4f})"
                            }

                # 死叉：DIF下穿DEA
                elif prev_dif >= prev_dea and curr_dif < curr_dea:
                    if position > 0:
                        return {
                            "action": "sell",
                            "amount": position,
                            "reason": f"MACD死叉: DIF({curr_dif:.4f})下穿DEA({curr_dea:.4f})"
                        }

        return {"action": "hold", "amount": 0, "reason": "无交易信号"}
