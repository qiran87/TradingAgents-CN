"""MDVAES 领域模型"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class SignalType(str, Enum):
    """交易信号类型"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class TrendStability(str, Enum):
    """趋势稳定性"""
    STABLE = "stable"
    VOLATILE = "volatile"
    DECLINING = "declining"


class RiskLevel(str, Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class EPSForecast:
    """EPS 预测（实体）"""
    year: int
    eps_forecast: float
    forecast_date: str
    analyst_count: int
    source: str  # "analyst" or "historical_extrapolation"


@dataclass(frozen=True)
class GrowthMetrics:
    """增长指标（值对象）"""
    cagr: float  # 复合年均增长率
    growth_rate: float  # 增长率
    r_squared: float  # R² 拟合优度
    growth_quality_score: float  # 增长质量评分 (0-1)
    trend_stability: TrendStability  # 趋势稳定性


@dataclass(frozen=True)
class RiskMetrics:
    """风险指标（值对象）"""
    debt_to_assets: float  # 资产负债率
    current_ratio: float  # 流动比率
    quick_ratio: float  # 速动比率
    cashflow_to_income: float  # 现金流/利润比率
    risk_level: RiskLevel  # 风险等级


@dataclass(frozen=True)
class ValuationResult:
    """估值结果（值对象）"""
    intrinsic_value: float  # 内在价值
    lower_bound: float  # 估值下限
    upper_bound: float  # 估值上限
    confidence: float  # 置信度 (0-1)
    valuation_method: Dict[str, float]  # 各方法估值
    signal: SignalType  # 交易信号


@dataclass(frozen=True)
class MDVAESParams:
    """MDVAES 参数（值对象）"""
    # 预测参数
    forecast_years: int = 5
    min_forecast_count: int = 3

    # 估值参数
    peg_base: float = 1.0
    peg_interest_sensitivity: float = 0.5
    risk_adjustment: float = 0.1

    # 多锚点权重
    anchor_weight: Dict[str, float] = field(default_factory=lambda: {
        "peg": 0.4,
        "pe_historical": 0.3,
        "pb": 0.15,
        "dcf": 0.15
    })

    # 信号参数
    signal_mode: str = "valuation_range"  # or "safety_margin"
    safety_margin_buy: float = 0.8
    safety_margin_sell: float = 1.2

    # 预设标识
    preset: Optional[str] = None  # conservative/neutral/aggressive

    def validate(self):
        """验证参数"""
        if not 1 <= self.forecast_years <= 10:
            raise ValueError("forecast_years 必须在 1-10 之间")
        if not 0.5 <= self.peg_base <= 2.0:
            raise ValueError("peg_base 必须在 0.5-2.0 之间")
        if not 0 <= self.risk_adjustment <= 0.3:
            raise ValueError("risk_adjustment 必须在 0-0.3 之间")
        if self.signal_mode not in ["valuation_range", "safety_margin"]:
            raise ValueError("signal_mode 必须是 valuation_range 或 safety_margin")

        # 验证权重总和
        total_weight = sum(self.anchor_weight.values())
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"anchor_weight 总和必须为 1.0，当前为 {total_weight}")
