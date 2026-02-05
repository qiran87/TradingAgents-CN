"""
策略注册表

所有策略代码硬编码在系统中，不动态加载。
策略可在回测和模拟实盘交易中复用。
"""
from typing import Dict, Type, Any, List
from app.strategies.base import BaseStrategy


class StrategyRegistry:
    """策略注册表"""

    _strategies: Dict[str, Type[BaseStrategy]] = {}
    _metadata: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(cls, strategy_id: str, strategy_class: Type[BaseStrategy]):
        """
        注册策略

        Args:
            strategy_id: 策略ID
            strategy_class: 策略类
        """
        cls._strategies[strategy_id] = strategy_class

        # 提取策略元数据
        try:
            instance = strategy_class({})
            cls._metadata[strategy_id] = {
                "strategy_id": strategy_id,
                "name": instance.get_strategy_name(),
                "description": instance.get_strategy_description(),
                "category": instance.get_strategy_category(),
                "parameters": instance.get_parameters_definition()
            }
        except Exception as e:
            # 如果实例化失败，只注册类
            pass

    @classmethod
    def get_strategy(cls, strategy_id: str, params: Dict[str, Any]) -> BaseStrategy:
        """
        获取策略实例

        Args:
            strategy_id: 策略ID
            params: 策略参数

        Returns:
            策略实例

        Raises:
            ValueError: 策略不存在
        """
        if strategy_id not in cls._strategies:
            raise ValueError(f"策略 {strategy_id} 未注册")

        strategy_class = cls._strategies[strategy_id]
        return strategy_class(params)

    @classmethod
    def get_strategy_class(cls, strategy_id: str) -> Type[BaseStrategy]:
        """
        获取策略类

        Args:
            strategy_id: 策略ID

        Returns:
            策略类

        Raises:
            ValueError: 策略不存在
        """
        if strategy_id not in cls._strategies:
            raise ValueError(f"策略 {strategy_id} 未注册")

        return cls._strategies[strategy_id]

    @classmethod
    def strategy_exists(cls, strategy_id: str) -> bool:
        """检查策略是否已注册"""
        return strategy_id in cls._strategies

    @classmethod
    def list_strategies(cls) -> List[str]:
        """列出所有已注册的策略ID"""
        return list(cls._strategies.keys())

    @classmethod
    def get_strategy_metadata(cls, strategy_id: str) -> Dict[str, Any]:
        """
        获取策略元数据

        Args:
            strategy_id: 策略ID

        Returns:
            策略元数据

        Raises:
            ValueError: 策略不存在
        """
        if strategy_id not in cls._metadata:
            raise ValueError(f"策略 {strategy_id} 元数据不存在")

        return cls._metadata[strategy_id]

    @classmethod
    def get_all_strategies_metadata(cls) -> List[Dict[str, Any]]:
        """
        获取所有策略元数据

        Returns:
            所有策略元数据列表
        """
        return list(cls._metadata.values())
