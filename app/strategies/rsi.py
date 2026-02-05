"""
RSI策略

基于RSI指标的超买超卖进行交易。
RSI高于超买阈值时卖出，低于超卖阈值时买入。
"""
from typing import Dict, Any, List
from datetime import datetime
from app.strategies.base import BaseStrategy


class RSIStrategy(BaseStrategy):
    """RSI策略"""

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.window = self.get_parameter("window", 14)
        self.oversold = self.get_parameter("oversold", 30.0)
        self.overbought = self.get_parameter("overbought", 70.0)
        self.price_history = []

    def get_parameters_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "window",
                "type": "int",
                "default_value": 14,
                "range": {"min": 5, "max": 30},
                "description": "RSI周期",
                "required": True
            },
            {
                "name": "oversold",
                "type": "float",
                "default_value": 30.0,
                "range": {"min": 20, "max": 40},
                "description": "超卖阈值",
                "required": True
            },
            {
                "name": "overbought",
                "type": "float",
                "default_value": 70.0,
                "range": {"min": 60, "max": 80},
                "description": "超买阈值",
                "required": True
            }
        ]

    def get_strategy_id(self) -> str:
        return "rsi"

    def get_strategy_name(self) -> str:
        return "RSI策略"

    def get_strategy_description(self) -> str:
        return "基于RSI指标的超买超卖进行交易。RSI低于超卖阈值时买入，高于超买阈值时卖出。"

    def get_strategy_category(self) -> str:
        return "oscillation"

    def _calculate_rsi(self) -> float:
        """计算RSI指标"""
        if len(self.price_history) < self.window + 1:
            return 50.0  # 默认中性值

        # 计算价格变化
        price_changes = []
        for i in range(len(self.price_history) - self.window, len(self.price_history)):
            change = self.price_history[i] - self.price_history[i - 1]
            price_changes.append(change)

        # 分离涨跌
        gains = [max(change, 0) for change in price_changes]
        losses = [abs(min(change, 0)) for change in price_changes]

        # 计算平均涨跌
        avg_gain = sum(gains) / self.window
        avg_loss = sum(losses) / self.window

        # 避免除零
        if avg_loss == 0:
            return 100.0

        # 计算RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

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
        if len(self.price_history) < self.window + 1:
            return {"action": "hold", "amount": 0, "reason": "数据积累中"}

        # 计算RSI
        rsi = self._calculate_rsi()

        # 交易逻辑
        if rsi <= self.oversold and position == 0:
            # RSI超卖，买入
            buy_amount = int((cash * 0.9) / current_price / 100) * 100
            if buy_amount > 0:
                return {
                    "action": "buy",
                    "amount": buy_amount,
                    "reason": f"RSI({rsi:.2f})低于超卖阈值({self.oversold})，可能反弹"
                }
        elif rsi >= self.overbought and position > 0:
            # RSI超买，卖出
            return {
                "action": "sell",
                "amount": position,
                "reason": f"RSI({rsi:.2f})高于超买阈值({self.overbought})，可能回调"
            }

        return {
            "action": "hold",
            "amount": 0,
            "reason": f"RSI({rsi:.2f})在正常区间"
        }
