"""
KDJ策略

基于KDJ指标的超买超卖进行交易。
K线高于80时超买，低于20时超卖。
"""
from typing import Dict, Any, List
from datetime import datetime
from app.strategies.base import BaseStrategy


class KDJStrategy(BaseStrategy):
    """KDJ策略"""

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.k_window = self.get_parameter("k_window", 9)
        self.d_window = self.get_parameter("d_window", 3)
        self.j_window = self.get_parameter("j_window", 3)
        self.high_history = []
        self.low_history = []
        self.close_history = []

    def get_parameters_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "k_window",
                "type": "int",
                "default_value": 9,
                "range": {"min": 5, "max": 20},
                "description": "K值周期",
                "required": True
            },
            {
                "name": "d_window",
                "type": "int",
                "default_value": 3,
                "range": {"min": 2, "max": 10},
                "description": "D值平滑周期",
                "required": True
            },
            {
                "name": "j_window",
                "type": "int",
                "default_value": 3,
                "range": {"min": 2, "max": 10},
                "description": "J值平滑周期",
                "required": True
            }
        ]

    def get_strategy_id(self) -> str:
        return "kdj"

    def get_strategy_name(self) -> str:
        return "KDJ策略"

    def get_strategy_description(self) -> str:
        return "基于KDJ指标的超买超卖进行交易。K线高于80时超买，低于20时超卖。"

    def get_strategy_category(self) -> str:
        return "oscillation"

    def _calculate_kdj(self, high: float, low: float, close: float) -> tuple:
        """
        计算KDJ值

        Returns:
            (k, d, j) 元组
        """
        # 添加到历史
        self.high_history.append(high)
        self.low_history.append(low)
        self.close_history.append(close)

        # 保持历史长度
        if len(self.high_history) > self.k_window + self.d_window:
            self.high_history = self.high_history[-(self.k_window + self.d_window):]
            self.low_history = self.low_history[-(self.k_window + self.d_window):]
            self.close_history = self.close_history[-(self.k_window + self.d_window):]

        # 需要足够的历史数据
        if len(self.high_history) < self.k_window:
            return (50.0, 50.0, 50.0)

        # 计算RSV
        high_n = max(self.high_history[-self.k_window:])
        low_n = min(self.low_history[-self.k_window:])

        if high_n == low_n:
            rsv = 50.0
        else:
            rsv = (close - low_n) / (high_n - low_n) * 100

        # 初始化K值和D值
        if not hasattr(self, '_k_value'):
            self._k_value = 50.0
        if not hasattr(self, '_d_value'):
            self._d_value = 50.0

        # 计算K值
        self._k_value = (2 / 3) * self._k_value + (1 / 3) * rsv

        # 计算D值
        self._d_value = (2 / 3) * self._d_value + (1 / 3) * self._k_value

        # 计算J值
        j_value = 3 * self._k_value - 2 * self._d_value

        return (self._k_value, self._d_value, j_value)

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
            current_price: 当前价格（这里假设是收盘价）
            position: 当前持仓（股数）
            cash: 当前现金（元）

        Returns:
            交易信号
        """
        # 简化处理：假设high=low=close=current_price
        # 实际应用中应该传入完整的OHLC数据
        high = current_price
        low = current_price
        close = current_price

        # 计算KDJ
        k, d, j = self._calculate_kdj(high, low, close)

        # 交易逻辑
        if k < 20 and position == 0:
            # K线超卖，买入
            buy_amount = int((cash * 0.9) / current_price / 100) * 100
            if buy_amount > 0:
                return {
                    "action": "buy",
                    "amount": buy_amount,
                    "reason": f"KDJ超卖: K({k:.2f})低于20"
                }
        elif k > 80 and position > 0:
            # K线超买，卖出
            return {
                "action": "sell",
                "amount": position,
                "reason": f"KDJ超买: K({k:.2f})高于80"
            }

        return {
            "action": "hold",
            "amount": 0,
            "reason": f"KDJ正常: K={k:.2f}, D={d:.2f}, J={j:.2f}"
        }
