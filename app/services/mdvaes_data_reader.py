"""MDVAES 数据读取器"""

from typing import List, Optional
from datetime import datetime
from app.core.database import get_mongo_db
from app.domain.mdvaes import EPSForecast


class MDVAESDataReader:
    """MDVAES 数据读取器"""

    async def get_eps_forecast(
        self,
        symbol: str,
        calculation_date: str,
        forecast_years: int
    ) -> List[EPSForecast]:
        """获取 EPS 预测数据

        优先使用分析师预测，不足时使用历史数据外推
        """
        db = await get_mongo_db()

        # 1. 尝试从分析师预测获取
        analyst_forecasts = await self._get_analyst_forecasts(
            db, symbol, calculation_date, forecast_years
        )

        if analyst_forecasts:
            return analyst_forecasts

        # 2. 如果分析师预测不足，使用历史 EPS 外推
        historical_eps = await self._get_historical_eps(db, symbol, calculation_date)
        if len(historical_eps) >= 2:
            return self._extrapolate_eps(historical_eps, forecast_years)

        raise ValueError(f"无法获取 {symbol} 的 EPS 数据")

    async def _get_analyst_forecasts(
        self,
        db,
        symbol: str,
        calculation_date: str,
        forecast_years: int
    ) -> Optional[List[EPSForecast]]:
        """从分析师预测获取 EPS"""
        current_year = datetime.strptime(calculation_date, "%Y-%m-%d").year

        forecasts = await db.mdvaes_analyst_forecasts.find({
            "ts_code": symbol,
            "forecast_date": {"$lte": calculation_date},
            "year": {"$gte": current_year, "$lte": current_year + forecast_years}
        }).sort("forecast_date", -1).to_list(None)

        if not forecasts:
            return None

        # 按年份去重，取最新预测
        latest_by_year = {}
        for f in forecasts:
            year = f.get("year") or self._extract_year_from_quarter(f.get("quarter", ""))
            if year and (year not in latest_by_year or f["forecast_date"] > latest_by_year[year]["forecast_date"]):
                latest_by_year[year] = f

        return [
            EPSForecast(
                year=year,
                eps_forecast=f["eps"],
                forecast_date=f["forecast_date"],
                analyst_count=f.get("analyst_count", 1),
                source="analyst"
            )
            for year, f in sorted(latest_by_year.items())
        ]

    async def _get_historical_eps(self, db, symbol: str, calculation_date: str, limit: int = 10) -> List[dict]:
        """获取历史 EPS 数据"""
        historical_eps = await db.mdvaes_eps_history.find({
            "ts_code": symbol,
            "end_date": {"$lte": calculation_date}
        }).sort("end_date", -1).limit(limit).to_list(None)

        return historical_eps or []

    def _extrapolate_eps(self, historical_eps: List[dict], forecast_years: int) -> List[EPSForecast]:
        """基于历史 EPS 外推预测"""
        latest_eps = historical_eps[0]["eps"]
        oldest_eps = historical_eps[-1]["eps"]
        n_years = len(historical_eps)
        growth_rate = (latest_eps / oldest_eps) ** (1 / (n_years - 1)) - 1 if n_years > 1 else 0.1

        base_year = datetime.strptime(historical_eps[0]["end_date"], "%Y-%m-%d").year

        forecasts = []
        for i in range(1, forecast_years + 1):
            forecast_eps = latest_eps * ((1 + growth_rate) ** i)
            forecasts.append(EPSForecast(
                year=base_year + i,
                eps_forecast=forecast_eps,
                forecast_date=datetime.now().strftime("%Y-%m-%d"),
                analyst_count=0,
                source="historical_extrapolation"
            ))

        return forecasts

    def _extract_year_from_quarter(self, quarter: str) -> Optional[int]:
        """从季度字符串提取年份"""
        try:
            return int(quarter[:4])
        except (ValueError, IndexError):
            return None

    async def get_current_pe(self, db, symbol: str, calculation_date: str) -> Optional[float]:
        """获取当前 PE"""
        pe_data = await db.mdvaes_pe_history.find_one({
            "ts_code": symbol,
            "trade_date": {"$lte": calculation_date}
        }, sort=[("trade_date", -1)])

        return pe_data["pe_ttm"] if pe_data else None

    async def get_bond_rate(self, calculation_date: str) -> Optional[float]:
        """获取 10 年期国债收益率"""
        db = await get_mongo_db()

        bond_data = await db.mdvaes_bond_rate.find_one({
            "trade_date": {"$lte": calculation_date},
            "curve_term": 10.0
        }, sort=[("trade_date", -1)])

        if bond_data:
            return bond_data.get("yield", 0) / 100

        # 默认无风险利率 2.75%
        return 0.0275
