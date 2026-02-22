"""
策略模块

该模块包含所有交易策略的实现，可在回测和模拟实盘交易中复用。
"""
from app.strategies.registry import StrategyRegistry
from app.strategies.dual_ma import DualMAStrategy
from app.strategies.mdvaes import MDVAESStrategy
from app.strategies.rsi import RSIStrategy
from app.strategies.macd import MACDStrategy
from app.strategies.kdj import KDJStrategy
from app.strategies.bollinger_bands import BollingerBandsStrategy

# 策略ID常量
STRATEGY_DUAL_MA = "dual_ma"
STRATEGY_MDVAES = "mdvaes"
STRATEGY_RSI = "rsi"
STRATEGY_MACD = "macd"
STRATEGY_KDJ = "kdj"
STRATEGY_BOLLINGER_BANDS = "bollinger_bands"

# 注册所有内置策略
def _register_builtin_strategies():
    """注册所有内置策略"""
    StrategyRegistry.register(STRATEGY_DUAL_MA, DualMAStrategy)
    StrategyRegistry.register(STRATEGY_MDVAES, MDVAESStrategy)
    StrategyRegistry.register(STRATEGY_RSI, RSIStrategy)
    StrategyRegistry.register(STRATEGY_MACD, MACDStrategy)
    StrategyRegistry.register(STRATEGY_KDJ, KDJStrategy)
    StrategyRegistry.register(STRATEGY_BOLLINGER_BANDS, BollingerBandsStrategy)

# 模块导入时自动注册
_register_builtin_strategies()

__all__ = [
    'StrategyRegistry',
    'STRATEGY_DUAL_MA',
    'STRATEGY_MDVAES',
    'STRATEGY_RSI',
    'STRATEGY_MACD',
    'STRATEGY_KDJ',
    'STRATEGY_BOLLINGER_BANDS'
]
