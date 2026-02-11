"""
双均线策略

基于快慢均线的交叉信号进行交易。
当短期均线上穿长期均线时产生买入信号（金叉），
当短期均线下穿长期均线时产生卖出信号（死叉）。
"""
from typing import Dict, Any, List
from datetime import datetime
from app.strategies.base import BaseStrategy


class DualMAStrategy(BaseStrategy):
    """双均线策略"""

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.short_window = self.get_parameter("short_window", 5)
        self.long_window = self.get_parameter("long_window", 20)
        self.price_history = []  # 价格历史

    def get_parameters_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "short_window",
                "type": "int",
                "default_value": 5,
                "range": {"min": 2, "max": 60},
                "description": "短期均线窗口",
                "required": True
            },
            {
                "name": "long_window",
                "type": "int",
                "default_value": 20,
                "range": {"min": 5, "max": 250},
                "description": "长期均线窗口",
                "required": True
            }
        ]

    def get_strategy_id(self) -> str:
        return "dual_ma"

    def get_strategy_name(self) -> str:
        return "双均线策略"

    def get_strategy_description(self) -> str:
        return "基于快慢均线的交叉信号进行交易。当短期均线上穿长期均线时产生买入信号，当短期均线下穿长期均线时产生卖出信号。"

    def get_strategy_category(self) -> str:
        return "trend"

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

        重要：回测中只能使用历史数据做决策，不能包含当天价格

        Args:
            bar_id: K线ID
            timestamp: 时间戳
            current_price: 当前价格（收盘价）
            position: 当前持仓（股数）
            cash: 当前现金（元）

        Returns:
            交易信号
        """
        # 如果历史数据不足，保持观望
        # 注意: 计算MA需要至少 long_window + 1 个历史数据
        # 因为需要比较前两天和前一天的均线
        if len(self.price_history) < self.long_window + 1:
            # 数据积累期,先添加到历史
            self.price_history.append(current_price)
            return {"action": "hold", "amount": 0, "reason": "数据积累中"}

        # 计算前两天的均线
        # 例如D7天决策时:
        # price_history = [D1, D2, D3, D4, D5, D6]
        # current_price = D7
        # prev_prev_short_ma (D5的MA5): [D1,D2,D3,D4,D5]
        # prev_short_ma (D6的MA5): [D2,D3,D4,D5,D6]
        prev_prev_short_ma = sum(self.price_history[-self.short_window-1:-1]) / self.short_window
        prev_prev_long_ma = sum(self.price_history[-self.long_window-1:-1]) / self.long_window

        # 计算前一天的均线
        prev_short_ma = sum(self.price_history[-self.short_window:]) / self.short_window
        prev_long_ma = sum(self.price_history[-self.long_window:]) / self.long_window

        # 金叉：短期均线上穿长期均线
        # 判断: 前两天的MA <= 前一天的MA (前两天短期MA低于或等于长期MA)
        #       前一天的短期MA > 前一天的长期MA (前一天短期MA高于长期MA)
        if prev_prev_short_ma <= prev_prev_long_ma and prev_short_ma > prev_long_ma:
            if position == 0:  # 没有持仓
                # 计算可买入股数（使用现金的90%）
                buy_amount = int((cash * 0.9) / current_price / 100) * 100
                if buy_amount > 0:
                    # 决策后再添加当天价格到历史
                    self.price_history.append(current_price)
                    return {
                        "action": "buy",
                        "amount": buy_amount,
                        "reason": f"金叉: 短期均线({prev_prev_short_ma:.4f}→{prev_short_ma:.4f})上穿长期均线({prev_prev_long_ma:.4f}→{prev_long_ma:.4f})"
                    }

        # 死叉：短期均线下穿长期均线
        # 判断: 前两天的MA >= 前一天的MA (前两天短期MA高于或等于长期MA)
        #       前一天的短期MA < 前一天的长期MA (前一天短期MA低于长期MA)
        elif prev_prev_short_ma >= prev_prev_long_ma and prev_short_ma < prev_long_ma:
            if position > 0:  # 有持仓
                # 决策后再添加当天价格到历史
                self.price_history.append(current_price)
                return {
                    "action": "sell",
                    "amount": position,
                    "reason": f"死叉: 短期均线({prev_prev_short_ma:.4f}→{prev_short_ma:.4f})下穿长期均线({prev_prev_long_ma:.4f}→{prev_long_ma:.4f})"
                }

        # 无信号,添加当天价格到历史
        self.price_history.append(current_price)
        return {"action": "hold", "amount": 0, "reason": "无交易信号"}
