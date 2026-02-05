"""
策略模块

该模块包含所有交易策略的实现，可在回测和模拟实盘交易中复用。
"""
from app.strategies.registry import StrategyRegistry

__all__ = ['StrategyRegistry']
