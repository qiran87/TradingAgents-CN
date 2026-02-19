"""MDVAES 估值模型"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime


# ===== 请求模型 =====

class MDVAESCalculateRequest(BaseModel):
    """MDVAES 估值计算请求"""
    symbol: str = Field(..., description="股票代码")
    calculation_date: str = Field(..., description="计算日期 (YYYY-MM-DD)")
    forecast_years: int = Field(default=5, ge=1, le=10, description="EPS预测年数")
    peg_base: float = Field(default=1.0, ge=0.5, le=2.0, description="PEG基数")
    risk_adjustment: float = Field(default=0.1, ge=0.0, le=0.3, description="风险调整幅度")
    use_margin: bool = Field(default=True, description="使用安全边际")
    margin_buy: float = Field(default=0.8, ge=0.5, le=0.95, description="买入安全边际")
    margin_sell: float = Field(default=1.2, ge=1.05, le=2.0, description="卖出安全边际")


class MDVAESParamsUpdateRequest(BaseModel):
    """MDVAES 参数更新请求"""
    forecast_years: Optional[int] = Field(None, ge=1, le=10, description="EPS预测年数")
    peg_base: Optional[float] = Field(None, ge=0.5, le=2.0, description="PEG基数")
    risk_adjustment: Optional[float] = Field(None, ge=0.0, le=0.3, description="风险调整幅度")
    use_margin: Optional[bool] = Field(None, description="使用安全边际")
    margin_buy: Optional[float] = Field(None, ge=0.5, le=0.95, description="买入安全边际")
    margin_sell: Optional[float] = Field(None, ge=1.05, le=2.0, description="卖出安全边际")


# ===== 响应模型 =====

class EPSForecastResponse(BaseModel):
    """EPS 预测响应"""
    year: int
    eps_forecast: float
    forecast_date: str
    analyst_count: int
    source: str


class GrowthMetricsResponse(BaseModel):
    """增长指标响应"""
    cagr: float
    growth_rate: float
    r_squared: float
    growth_quality_score: float
    trend_stability: str


class ValuationMethodBreakdown(BaseModel):
    """估值方法明细"""
    peg: float
    pe_historical: float
    pb: float
    dcf: float


class ValuationResultResponse(BaseModel):
    """估值结果响应"""
    intrinsic_value: float
    lower_bound: float
    upper_bound: float
    confidence: float
    valuation_method: ValuationMethodBreakdown
    signal: str  # "buy" | "sell" | "hold"


class MDVAESCalculateResponse(BaseModel):
    """MDVAES 计算响应"""
    success: bool
    symbol: str
    calculation_date: str
    valuation: Optional[ValuationResultResponse] = None
    growth_metrics: Optional[GrowthMetricsResponse] = None
    eps_forecasts: List[EPSForecastResponse] = []
    current_pe: Optional[float] = None
    bond_rate: Optional[float] = None
    error: Optional[str] = None


class MDVAESParametersResponse(BaseModel):
    """MDVAES 参数响应"""
    forecast_years: int
    peg_base: float
    risk_adjustment: float
    use_margin: bool
    margin_buy: float
    margin_sell: float


class CacheStatusResponse(BaseModel):
    """缓存状态响应"""
    total_entries: int
    symbols_cached: List[str]
    oldest_entry: Optional[str]
    newest_entry: Optional[str]
    cache_hit_rate: Optional[float] = None
