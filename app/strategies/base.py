"""
策略基类

所有交易策略的基类，定义了策略必须实现的接口。
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from datetime import datetime


class BaseStrategy(ABC):
    """策略基类"""

    def __init__(self, params: Dict[str, Any]):
        """
        初始化策略

        Args:
            params: 策略参数
        """
        self.params = params
        self.validate_params()

    @abstractmethod
    def get_parameters_definition(self) -> List[Dict[str, Any]]:
        """
        获取参数定义

        Returns:
            参数定义列表，格式：
            [
                {
                    "name": "short_window",
                    "type": "int",
                    "default_value": 5,
                    "range": {"min": 2, "max": 60},
                    "description": "短期均线窗口",
                    "required": True
                }
            ]
        """
        pass

    def validate_params(self):
        """校验参数"""
        param_defs = self.get_parameters_definition()
        param_def_dict = {p["name"]: p for p in param_defs}

        for param_def in param_defs:
            param_name = param_def["name"]
            required = param_def.get("required", True)

            if required and param_name not in self.params:
                raise ValueError(f"参数 {param_name} 是必填的")

    @abstractmethod
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
            交易信号，格式：
            {
                "action": "buy" | "sell" | "hold",
                "amount": int,  # 交易股数
                "reason": str   # 原因说明
            }
        """
        pass

    @abstractmethod
    def get_strategy_id(self) -> str:
        """获取策略ID"""
        pass

    @abstractmethod
    def get_strategy_name(self) -> str:
        """获取策略名称"""
        pass

    @abstractmethod
    def get_strategy_description(self) -> str:
        """获取策略描述"""
        pass

    @abstractmethod
    def get_strategy_category(self) -> str:
        """
        获取策略分类

        Returns:
            策略分类：trend（趋势）/ oscillation（震荡）/ momentum（动量）
        """
        pass

    def get_parameter(self, name: str, default=None):
        """
        获取参数值

        Args:
            name: 参数名称
            default: 默认值

        Returns:
            参数值
        """
        return self.params.get(name, default)

    def __repr__(self) -> str:
        return f"{self.get_strategy_name()}({self.params})"
