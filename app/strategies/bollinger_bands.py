"""
布林带策略

基于布林带的突破和回归进行交易。
当价格触及上轨时可能超买，触及下轨时可能超卖。
"""
from typing import Dict, Any, List
from datetime import datetime
import math
from app.strategies.base import BaseStrategy


class BollingerBandsStrategy(BaseStrategy):
    """布林带策略"""

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.window = self.get_parameter("window", 20)
        self.num_std = self.get_parameter("num_std", 2.0)
        self.price_history = []

    def get_parameters_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "window",
                "type": "int",
                "default_value": 20,
                "range": {"min": 5, "max": 50},
                "description": "均线窗口",
                "required": True
            },
            {
                "name": "num_std",
                "type": "float",
                "default_value": 2.0,
                "range": {"min": 0.5, "max": 4.0},
                "description": "标准差倍数",
                "required": True
            }
        ]

    def get_strategy_id(self) -> str:
        return "bollinger_bands"

    def get_strategy_name(self) -> str:
        return "布林带策略"

    def get_strategy_description(self) -> str:
        return "基于布林带的突破和回归进行交易。当价格触及下轨时超卖可能反弹，当价格回归中轨时卖出。"

    def get_strategy_category(self) -> str:
        return "oscillation"

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

        # 如果历史数据不足，保持观望
        if len(self.price_history) < self.window:
            return {"action": "hold", "amount": 0, "reason": "数据积累中"}

        # 计算中轨（简单移动平均）
        sma = sum(self.price_history[-self.window:]) / self.window

        # 计算标准差
        squared_diffs = [(price - sma) ** 2 for price in self.price_history[-self.window:]]
        variance = sum(squared_diffs) / self.window
        std = math.sqrt(variance)

        # 计算上轨和下轨
        upper_band = sma + (self.num_std * std)
        lower_band = sma - (self.num_std * std)

        # 交易逻辑
        if current_price <= lower_band and position == 0:
            # 价格触及下轨，买入
            buy_amount = int((cash * 0.9) / current_price / 100) * 100
            if buy_amount > 0:
                return {
                    "action": "buy",
                    "amount": buy_amount,
                    "reason": f"价格({current_price:.2f})触及下轨({lower_band:.2f})，超卖反弹"
                }
        elif current_price >= sma and position > 0:
            # 价格回归中轨，卖出
            return {
                "action": "sell",
                "amount": position,
                "reason": f"价格({current_price:.2f})回归中轨({sma:.2f})，获利了结"
            }

        return {
            "action": "hold",
            "amount": 0,
            "reason": f"价格({current_price:.2f})在上轨({upper_band:.2f})和下轨({lower_band:.2f})之间"
        }
