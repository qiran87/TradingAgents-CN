"""MDVAES 估值服务"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.core.database import get_mongo_db
from app.domain.mdvaes import (
    MDVAESParams, RiskMetrics, RiskLevel, SignalType,
    EPSForecast as DomainEPSForecast
)
from app.services.mdvaes_data_reader import MDVAESDataReader
from app.services.growth_calculator import GrowthCalculator
from app.services.valuation_calculator import ValuationCalculator
from app.models.mdvaes import (
    MDVAESCalculateResponse, ValuationResultResponse, GrowthMetricsResponse,
    EPSForecastResponse, MDVAESParametersResponse, CacheStatusResponse
)

logger = logging.getLogger(__name__)


class MDVAESService:
    """MDVAES 估值服务"""

    def __init__(self):
        self.data_reader = MDVAESDataReader()
        self.growth_calculator = GrowthCalculator()
        self.valuation_calculator = ValuationCalculator()
        self._default_params = MDVAESParams()

    async def calculate_valuation(
        self,
        symbol: str,
        calculation_date: str,
        forecast_years: int = 5,
        peg_base: float = 1.0,
        risk_adjustment: float = 0.1,
        use_margin: bool = True,
        margin_buy: float = 0.8,
        margin_sell: float = 1.2,
        anchor_weight: Optional[Dict[str, float]] = None
    ) -> MDVAESCalculateResponse:
        """计算 MDVAES 估值

        Args:
            symbol: 股票代码
            calculation_date: 计算日期
            forecast_years: EPS预测年数
            peg_base: PEG基数
            risk_adjustment: 风险调整幅度
            use_margin: 是否使用安全边际
            margin_buy: 买入安全边际
            margin_sell: 卖出安全边际
            anchor_weight: 多锚点权重配置，格式: {"peg": 0.4, "pe_historical": 0.3, "pb": 0.15, "dcf": 0.15}
                          如果为 None，则使用 MDVAESParams 中的默认权重
        """
        try:
            # 1. 构建参数（如果传了 anchor_weight 则使用，否则使用默认值）
            params_kwargs = {
                "forecast_years": forecast_years,
                "peg_base": peg_base,
                "risk_adjustment": risk_adjustment,
                "signal_mode": "safety_margin" if use_margin else "valuation_range",
                "safety_margin_buy": margin_buy,
                "safety_margin_sell": margin_sell
            }

            # 如果前端传了 anchor_weight，则使用前端的权重
            if anchor_weight is not None:
                # 验证权重总和
                total_weight = sum(anchor_weight.values())
                if abs(total_weight - 1.0) > 0.01:
                    raise ValueError(f"权重总和必须为1.0，当前为{total_weight:.2f}")
                params_kwargs["anchor_weight"] = anchor_weight

            params = MDVAESParams(**params_kwargs)
            params.validate()

            # 2. 获取 EPS 预测
            eps_forecasts = await self.data_reader.get_eps_forecast(
                symbol, calculation_date, forecast_years
            )

            # 3. 计算增长指标
            growth_metrics = self.growth_calculator.calculate(eps_forecasts)

            # 4. 获取当前数据
            db = get_mongo_db()
            current_eps = eps_forecasts[0].eps_forecast

            current_pe = await self.data_reader.get_current_pe(db, symbol, calculation_date)
            if current_pe is None:
                current_pe = 15.0  # 默认值

            # 5. 获取国债利率
            bond_rate = await self.data_reader.get_bond_rate(calculation_date)

            # 6. 获取财务比率数据
            ratios_data = await self.data_reader.get_financial_ratios(symbol, calculation_date)

            # 6.5 获取年化ROE（使用同比外推法）
            annualized_roe = await self.data_reader.get_current_roe(symbol, calculation_date)

            # 7. 构建风险指标
            if ratios_data:
                # 使用数据库中的实际数据
                # 根据资产负债率动态计算风险等级
                debt_to_assets_pct = ratios_data.get("debt_to_assets", 50)
                debt_ratio = debt_to_assets_pct / 100.0  # 转换为小数

                if debt_ratio < 0.3:
                    risk_level = RiskLevel.LOW
                elif debt_ratio < 0.6:
                    risk_level = RiskLevel.MEDIUM
                else:
                    risk_level = RiskLevel.HIGH

                risk_metrics = RiskMetrics(
                    debt_to_assets=debt_ratio,  # 使用转换后的小数
                    current_ratio=ratios_data.get("current_ratio", 1.5),
                    quick_ratio=ratios_data.get("quick_ratio", 1.2),
                    cashflow_to_income=1.1,  # 暂时保持默认值
                    risk_level=risk_level,  # 使用动态计算的风险等级
                    bps=ratios_data.get("bps"),  # 每股净资产
                    roe=annualized_roe  # 使用年化后的ROE（已经是小数形式）
                )
            else:
                # 使用默认值
                risk_metrics = RiskMetrics(
                    debt_to_assets=0.5,
                    current_ratio=1.5,
                    quick_ratio=1.2,
                    cashflow_to_income=1.1,
                    risk_level=RiskLevel.MEDIUM,
                    bps=None,  # 每股净资产（无数据时为 None）
                    roe=None   # 净资产收益率（无数据时为 None）
                )

            # 8. 计算估值
            valuation_result = self.valuation_calculator.calculate(
                growth_metrics=growth_metrics,
                risk_metrics=risk_metrics,
                eps=current_eps,
                current_pe=current_pe,
                bond_rate=bond_rate,
                params=params
            )

            # 8. 转换为响应模型
            return MDVAESCalculateResponse(
                success=True,
                symbol=symbol,
                calculation_date=calculation_date,
                valuation=self._to_valuation_response(valuation_result),
                growth_metrics=self._to_growth_response(growth_metrics),
                eps_forecasts=[self._to_eps_response(f) for f in eps_forecasts],
                current_pe=current_pe,
                bond_rate=bond_rate
            )

        except Exception as e:
            logger.error(f"MDVAES 计算失败: {e}", exc_info=True)
            return MDVAESCalculateResponse(
                success=False,
                symbol=symbol,
                calculation_date=calculation_date,
                error=str(e)
            )

    async def get_eps_forecasts(
        self,
        symbol: str,
        calculation_date: str,
        forecast_years: int = 5
    ) -> List[EPSForecastResponse]:
        """获取 EPS 预测"""
        eps_forecasts = await self.data_reader.get_eps_forecast(
            symbol, calculation_date, forecast_years
        )
        return [self._to_eps_response(f) for f in eps_forecasts]

    async def get_default_parameters(self) -> MDVAESParametersResponse:
        """获取默认参数"""
        from app.models.mdvaes import AnchorWeightModel

        # 构建默认权重响应
        default_anchor_weight = AnchorWeightModel(
            peg=self._default_params.anchor_weight["peg"],
            pe_historical=self._default_params.anchor_weight["pe_historical"],
            pb=self._default_params.anchor_weight["pb"],
            dcf=self._default_params.anchor_weight["dcf"]
        )

        return MDVAESParametersResponse(
            forecast_years=self._default_params.forecast_years,
            peg_base=self._default_params.peg_base,
            risk_adjustment=self._default_params.risk_adjustment,
            use_margin=self._default_params.signal_mode == "safety_margin",
            margin_buy=self._default_params.safety_margin_buy,
            margin_sell=self._default_params.safety_margin_sell,
            anchor_weight=default_anchor_weight
        )

    async def update_parameters(self, updates: Dict[str, Any]) -> MDVAESParametersResponse:
        """更新参数（返回更新后的参数）

        支持更新 anchor_weight，格式: {"peg": 0.4, "pe_historical": 0.3, "pb": 0.15, "dcf": 0.15}
        """
        from app.models.mdvaes import AnchorWeightModel

        # 处理 anchor_weight
        anchor_weight = None
        if "anchor_weight" in updates and updates["anchor_weight"] is not None:
            weight_dict = updates["anchor_weight"]
            # 验证权重总和
            total_weight = sum(weight_dict.values())
            if abs(total_weight - 1.0) > 0.01:
                raise ValueError(f"权重总和必须为1.0，当前为{total_weight:.2f}")
            anchor_weight = weight_dict

        # 构建参数（移除 anchor_weight，因为 MDVAESParams 会处理）
        updates_for_params = {k: v for k, v in updates.items() if k != "anchor_weight"}

        # 合并默认参数和更新参数
        params_dict = {**self._default_params.__dict__, **updates_for_params}
        if anchor_weight is not None:
            params_dict["anchor_weight"] = anchor_weight

        params = MDVAESParams(**params_dict)
        params.validate()

        # 构建响应权重
        response_anchor_weight = AnchorWeightModel(
            peg=params.anchor_weight["peg"],
            pe_historical=params.anchor_weight["pe_historical"],
            pb=params.anchor_weight["pb"],
            dcf=params.anchor_weight["dcf"]
        )

        return MDVAESParametersResponse(
            forecast_years=params.forecast_years,
            peg_base=params.peg_base,
            risk_adjustment=params.risk_adjustment,
            use_margin=params.signal_mode == "safety_margin",
            margin_buy=params.safety_margin_buy,
            margin_sell=params.safety_margin_sell,
            anchor_weight=response_anchor_weight
        )

    async def get_cache_status(self) -> CacheStatusResponse:
        """获取缓存状态"""
        db = get_mongo_db()

        # 统计缓存条目
        total_entries = await db.mdvaes_valuation_cache.count_documents({})

        # 获取缓存的股票列表
        symbols = await db.mdvaes_valuation_cache.distinct("symbol")

        # 获取最早和最晚的缓存条目
        oldest = await db.mdvaes_valuation_cache.find_one(
            sort=[("calculation_date", 1)]
        )
        newest = await db.mdvaes_valuation_cache.find_one(
            sort=[("calculation_date", -1)]
        )

        return CacheStatusResponse(
            total_entries=total_entries,
            symbols_cached=symbols,
            oldest_entry=oldest.get("calculation_date") if oldest else None,
            newest_entry=newest.get("calculation_date") if newest else None,
            cache_hit_rate=None  # 可以后续添加统计
        )

    def _to_valuation_response(self, valuation) -> ValuationResultResponse:
        """转换估值结果为响应模型"""
        from app.models.mdvaes import ValuationMethodBreakdown

        return ValuationResultResponse(
            intrinsic_value=valuation.intrinsic_value,
            lower_bound=valuation.lower_bound,
            upper_bound=valuation.upper_bound,
            confidence=valuation.confidence,
            valuation_method=ValuationMethodBreakdown(
                peg=valuation.valuation_method["peg"],
                pe_historical=valuation.valuation_method["pe_historical"],
                pb=valuation.valuation_method["pb"],
                dcf=valuation.valuation_method["dcf"]
            ),
            signal=valuation.signal.value
        )

    def _to_growth_response(self, growth_metrics) -> GrowthMetricsResponse:
        """转换增长指标为响应模型"""
        return GrowthMetricsResponse(
            cagr=growth_metrics.cagr,
            growth_rate=growth_metrics.growth_rate,
            r_squared=growth_metrics.r_squared,
            growth_quality_score=growth_metrics.growth_quality_score,
            trend_stability=growth_metrics.trend_stability.value
        )

    def _to_eps_response(self, eps: DomainEPSForecast) -> EPSForecastResponse:
        """转换 EPS 预测为响应模型"""
        return EPSForecastResponse(
            year=eps.year,
            eps_forecast=eps.eps_forecast,
            forecast_date=eps.forecast_date,
            analyst_count=eps.analyst_count,
            source=eps.source,
            ann_date=eps.ann_date  # 添加公告日期
        )


# 全局服务实例
_mdvaes_service: Optional[MDVAESService] = None


def get_mdvaes_service() -> MDVAESService:
    """获取 MDVAES 服务实例"""
    global _mdvaes_service
    if _mdvaes_service is None:
        _mdvaes_service = MDVAESService()
    return _mdvaes_service
