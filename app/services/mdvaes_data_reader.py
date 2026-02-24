"""MDVAES 数据读取器"""

from typing import List, Optional
from datetime import datetime
from app.core.database import get_mongo_db
from app.core.config import settings
from app.domain.mdvaes import EPSForecast
import pymongo


class MDVAESDataReader:
    """MDVAES 数据读取器"""

    def __init__(self):
        """初始化数据读取器"""
        self._sync_client = None  # 延迟初始化的同步客户端

    def _get_sync_db(self):
        """获取同步 MongoDB 客户端（用于从同步上下文调用）"""
        if self._sync_client is None:
            self._sync_client = pymongo.MongoClient(
                settings.MONGODB_HOST,
                settings.MONGODB_PORT,
                username=settings.MONGODB_USERNAME,
                password=settings.MONGODB_PASSWORD,
                authSource=settings.MONGODB_AUTH_SOURCE
            )
        return self._sync_client[settings.MONGODB_DATABASE]

    async def get_eps_forecast(
        self,
        symbol: str,
        calculation_date: str,
        forecast_years: int
    ) -> List[EPSForecast]:
        """获取 EPS 预测数据

        优先使用分析师预测，不足时使用历史数据外推
        """
        db = get_mongo_db()

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
        """从分析师预测获取 EPS

        注意：
        - report_date: 研报发布日期（YYYYMMDD 格式）
        - quarter: 预测季度（如 2024Q1、2024Q2）
        - eps: EPS 预测值

        重要：
        - report_date 必须严格小于 calculation_date（当天发布的研报当天看不到）
        - 必须排除 eps 为 None/NaN 的数据
        """
        current_year = datetime.strptime(calculation_date, "%Y-%m-%d").year
        # 将日期转换为 YYYYMMDD 格式进行比较
        calculation_date_yyyymmdd = calculation_date.replace("-", "")

        forecasts = await db.mdvaes_analyst_forecasts.find({
            "ts_code": symbol,
            "report_date": {"$lt": calculation_date_yyyymmdd},  # 严格小于（当天发布的研报当天看不到）
            "eps": {"$ne": None, "$exists": True}  # 排除 eps 为 None 或不存在的记录
        }).sort("report_date", -1).to_list(None)

        if not forecasts:
            return None

        # 按年份去重，取最新预测（从 quarter 字段提取年份）
        latest_by_year = {}
        for f in forecasts:
            year = self._extract_year_from_quarter(f.get("quarter", ""))
            eps_val = f.get("eps")
            # 再次检查 eps 有效性（排除 NaN、0、负值）
            if year and year >= current_year and year <= current_year + forecast_years and eps_val is not None:
                # 如果该年份还没有预测，或者当前预测更新
                if year not in latest_by_year or f["report_date"] > latest_by_year[year]["report_date"]:
                    latest_by_year[year] = f

        if not latest_by_year:
            return None

        return [
            EPSForecast(
                year=year,
                eps_forecast=f["eps"],
                forecast_date=datetime.strptime(f["report_date"], "%Y%m%d").strftime("%Y-%m-%d"),
                analyst_count=1,  # 每条记录代表一份预测
                source="analyst"
            )
            for year, f in sorted(latest_by_year.items())
        ]

    async def _get_historical_eps(self, db, symbol: str, calculation_date: str, limit: int = 5) -> List[dict]:
        """获取历史 EPS 数据

        默认使用最近5年数据，平衡稳定性和时效性。

        注意：
        - 使用 ann_date（公告日期）而非 end_date（报告期）
        - ann_date 必须严格小于 calculation_date（当天公告的数据当天看不到）
        - 必须排除 eps 为 None/NaN 的数据
        - 保留负EPS（亏损是真实存在的财务数据）
        - 至少需要3年数据才能计算增长率

        Args:
            limit: 最多获取多少年历史数据，默认5年（推荐3-5年）
        """
        # 将日期转换为 YYYYMMDD 格式进行比较
        calculation_date_yyyymmdd = calculation_date.replace("-", "")

        # 使用 ann_date（公告日期）而非 end_date（报告期）
        # 公告日期必须严格小于计算日期
        historical_eps = await db.mdvaes_eps_history.find({
            "ts_code": symbol,
            "ann_date": {"$lt": calculation_date_yyyymmdd},  # 严格小于（当天公告的数据当天看不到）
            "eps": {"$ne": None, "$exists": True}  # 排除 eps 为 None 或不存在的记录
        }).sort("ann_date", -1).limit(limit).to_list(None)

        # 再次过滤：确保 eps 不是 None/NaN（保留负EPS）
        filtered = [ep for ep in (historical_eps or []) if ep.get("eps") is not None]

        return filtered

    def _extrapolate_eps(self, historical_eps: List[dict], forecast_years: int) -> List[EPSForecast]:
        """基于历史 EPS 外推预测

        使用 CAGR 公式计算历史增长率，并外推预测未来 EPS。
        支持负EPS（亏损年份），自动处理计算边界情况。

        Args:
            historical_eps: 历史 EPS 数据（按 ann_date 降序排列）
            forecast_years: 预测未来多少年

        Returns:
            EPS 预测列表

        Raises:
            ValueError: 如果历史数据不足3年，或无法计算增长率
        """
        # 最小数据量检查：至少需要3年数据才能计算稳定的增长率
        if len(historical_eps) < 3:
            raise ValueError(
                f"历史 EPS 数据不足，无法计算增长率。"
                f"当前有 {len(historical_eps)} 年数据，至少需要 3 年数据。"
                f"建议：补充历史数据或使用分析师预测。"
            )

        latest_eps = historical_eps[0]["eps"]
        oldest_eps = historical_eps[-1]["eps"]
        n_years = len(historical_eps)

        # 计算历史增长率，处理负EPS的情况
        growth_rate = self._calculate_growth_rate(historical_eps)

        # end_date 格式可能是 YYYYMMDD 或 YYYY-MM-DD
        end_date_str = historical_eps[0]["end_date"]
        if "-" in end_date_str:
            base_year = datetime.strptime(end_date_str, "%Y-%m-%d").year
        else:
            base_year = int(end_date_str[:4])

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

    def _calculate_growth_rate(self, historical_eps: List[dict]) -> float:
        """计算历史增长率，处理各种边界情况

        Args:
            historical_eps: 历史 EPS 数据

        Returns:
            增长率（如 0.15 表示 15%）

        Raises:
            ValueError: 如果无法计算增长率（如持续亏损、波动太大）
        """
        latest_eps = historical_eps[0]["eps"]
        oldest_eps = historical_eps[-1]["eps"]
        n_years = len(historical_eps)

        # 检查1：最新EPS为负，公司仍在亏损，不适合外推预测
        if latest_eps < 0:
            raise ValueError(
                f"该公司最新EPS为负（{latest_eps}），公司仍在亏损。"
                f"历史外推方法不适用于亏损公司，建议使用分析师预测。"
            )

        # 检查2：检查是否有正负交替（盈利波动太大）
        has_negative = any(ep["eps"] < 0 for ep in historical_eps)
        if has_negative:
            raise ValueError(
                f"该公司历史EPS中存在负值（亏损年份），业绩波动太大。"
                f"历史外推方法不适用于业绩波动剧烈的公司，建议使用分析师预测。"
            )

        # 检查3：最旧EPS为0或负数，无法用CAGR公式
        if oldest_eps <= 0:
            raise ValueError(
                f"历史数据起始EPS为{oldest_eps}，无法计算增长率。"
                f"需要所有历史EPS都为正数才能使用CAGR公式。"
            )

        # 正常情况：使用CAGR公式
        # CAGR = (最新值 / 最旧值) ^ (1 / 年数差) - 1
        try:
            growth_rate = (latest_eps / oldest_eps) ** (1 / (n_years - 1)) - 1
            return growth_rate
        except (ZeroDivisionError, ValueError):
            raise ValueError(
                f"无法计算增长率，请检查历史数据或使用分析师预测。"
            )

    def _extract_year_from_quarter(self, quarter: str) -> Optional[int]:
        """从季度字符串提取年份"""
        try:
            return int(quarter[:4])
        except (ValueError, IndexError):
            return None

    async def get_current_pe(self, db, symbol: str, calculation_date: str) -> Optional[float]:
        """获取当前 PE

        注意：使用 trade_date（交易日期），必须严格小于 calculation_date
        回测时只能看到前一天及之前的收盘价（避免使用未来信息）
        """
        # 将日期转换为 YYYYMMDD 格式进行比较
        calculation_date_yyyymmdd = calculation_date.replace("-", "")

        pe_data = await db.mdvaes_pe_history.find_one({
            "ts_code": symbol,
            "trade_date": {"$lt": calculation_date_yyyymmdd}  # 严格小于（只能看到前一天的收盘价）
        }, sort=[("trade_date", -1)])

        return pe_data["pe_ttm"] if pe_data else None

    async def get_bond_rate(self, calculation_date: str) -> Optional[float]:
        """获取 10 年期国债收益率

        注意：使用 trade_date（交易日期），必须严格小于 calculation_date
        回测时只能看到前一天及之前的收益率（避免使用未来信息）
        """
        db = get_mongo_db()

        # 将日期转换为 YYYYMMDD 格式进行比较
        calculation_date_yyyymmdd = calculation_date.replace("-", "")

        bond_data = await db.mdvaes_bond_rate.find_one({
            "trade_date": {"$lt": calculation_date_yyyymmdd},  # 严格小于（只能看到前一天的收益率）
            "curve_term": 10.0
        }, sort=[("trade_date", -1)])

        if bond_data:
            return bond_data.get("yield", 0) / 100

        # 默认无风险利率 2.75%
        return 0.0275

    async def get_financial_ratios(self, symbol: str, calculation_date: str) -> Optional[dict]:
        """获取财务比率数据

        从 mdvaes_financial_ratios 表读取最新的财务指标

        注意：
        - 使用 ann_date（公告日期）而非 end_date（报告期）
        - ann_date 必须严格小于 calculation_date（当天公告的财报当天看不到）
        """
        db = get_mongo_db()

        # 将日期转换为 YYYYMMDD 格式进行比较
        calculation_date_yyyymmdd = calculation_date.replace("-", "")

        # 使用 ann_date（公告日期）而非 end_date（报告期）
        # 公告日期必须严格小于计算日期
        ratios_data = await db.mdvaes_financial_ratios.find_one({
            "ts_code": symbol,
            "ann_date": {"$lt": calculation_date_yyyymmdd}  # 严格小于（当天公告的数据当天看不到）
        }, sort=[("ann_date", -1)])

        if ratios_data:
            return {
                "debt_to_assets": ratios_data.get("debt_to_assets"),
                "current_ratio": ratios_data.get("current_ratio"),
                "quick_ratio": ratios_data.get("quick_ratio"),
                "roe": ratios_data.get("roe"),
                "roa": ratios_data.get("roa")
            }

        return None

    # ===================== 同步方法（用于从同步上下文调用）=====================

    def get_eps_forecast_sync(
        self,
        symbol: str,
        calculation_date: str,
        forecast_years: int
    ) -> List[EPSForecast]:
        """获取 EPS 预测数据（同步版本）

        优先使用分析师预测，不足时使用历史数据外推
        """
        db = self._get_sync_db()

        # 1. 尝试从分析师预测获取
        analyst_forecasts = self._get_analyst_forecasts_sync(
            db, symbol, calculation_date, forecast_years
        )

        if analyst_forecasts:
            return analyst_forecasts

        # 2. 如果分析师预测不足，使用历史 EPS 外推
        historical_eps = self._get_historical_eps_sync(db, symbol, calculation_date)
        if len(historical_eps) >= 2:
            return self._extrapolate_eps(historical_eps, forecast_years)

        raise ValueError(f"无法获取 {symbol} 的 EPS 数据")

    def _get_analyst_forecasts_sync(
        self,
        db,
        symbol: str,
        calculation_date: str,
        forecast_years: int
    ) -> Optional[List[EPSForecast]]:
        """从分析师预测获取 EPS（同步版本）"""
        current_year = datetime.strptime(calculation_date, "%Y-%m-%d").year
        calculation_date_yyyymmdd = calculation_date.replace("-", "")

        forecasts = list(db.mdvaes_analyst_forecasts.find({
            "ts_code": symbol,
            "report_date": {"$lt": calculation_date_yyyymmdd},
            "eps": {"$ne": None, "$exists": True}
        }).sort("report_date", -1).limit(forecast_years * 2))

        if not forecasts:
            return None

        # 按年份去重，取最新预测
        latest_by_year = {}
        for f in forecasts:
            year = self._extract_year_from_quarter(f.get("quarter", ""))
            eps_val = f.get("eps")
            if year and year >= current_year and year <= current_year + forecast_years and eps_val is not None:
                if year not in latest_by_year or f["report_date"] > latest_by_year[year]["report_date"]:
                    latest_by_year[year] = f

        if not latest_by_year:
            return None

        return [
            EPSForecast(
                year=year,
                eps_forecast=f["eps"],
                forecast_date=datetime.strptime(f["report_date"], "%Y%m%d").strftime("%Y-%m-%d"),
                analyst_count=1,
                source="analyst"
            )
            for year, f in sorted(latest_by_year.items())
        ]

    def _get_historical_eps_sync(self, db, symbol: str, calculation_date: str, limit: int = 5) -> List[dict]:
        """获取历史 EPS 数据（同步版本）"""
        calculation_date_yyyymmdd = calculation_date.replace("-", "")

        historical_eps = list(db.mdvaes_eps_history.find({
            "ts_code": symbol,
            "ann_date": {"$lt": calculation_date_yyyymmdd},
            "eps": {"$ne": None, "$exists": True}
        }).sort("ann_date", -1).limit(limit))

        filtered = [ep for ep in historical_eps if ep.get("eps") is not None]
        return filtered

    def get_current_pe_sync(self, symbol: str, calculation_date: str) -> Optional[float]:
        """获取当前 PE（同步版本）"""
        db = self._get_sync_db()
        calculation_date_yyyymmdd = calculation_date.replace("-", "")

        pe_data = db.mdvaes_pe_history.find_one({
            "ts_code": symbol,
            "trade_date": {"$lt": calculation_date_yyyymmdd}
        }, sort=[("trade_date", -1)])

        return pe_data["pe_ttm"] if pe_data else None

    def get_bond_rate_sync(self, calculation_date: str) -> Optional[float]:
        """获取 10 年期国债收益率（同步版本）"""
        db = self._get_sync_db()
        calculation_date_yyyymmdd = calculation_date.replace("-", "")

        bond_data = db.mdvaes_bond_rate.find_one({
            "trade_date": {"$lt": calculation_date_yyyymmdd},
            "curve_term": 10.0
        }, sort=[("trade_date", -1)])

        if bond_data:
            return bond_data.get("yield", 0) / 100
        return 0.0275

    def get_current_fcfps_sync(self, symbol: str, calculation_date: str) -> Optional[float]:
        """获取当前每股自由现金流 FCFPS（同步版本）

        优先获取 fcfps（每股自由现金流），如果不存在则尝试使用 cfps（每股经营现金流）

        注意：Tushare API 返回 fcfe_ps，同步服务会将其映射为 fcfps 存入数据库
        """
        db = self._get_sync_db()
        calculation_date_yyyymmdd = calculation_date.replace("-", "")

        # 优先使用 fcfps（每股自由现金流）
        fcf_data = db.mdvaes_eps_history.find_one({
            "ts_code": symbol,
            "ann_date": {"$lt": calculation_date_yyyymmdd},
            "fcfps": {"$ne": None, "$exists": True}
        }, sort=[("ann_date", -1)], projection=["fcfps", "cfps"])

        if fcf_data:
            # 优先返回 fcfps
            if "fcfps" in fcf_data and fcf_data["fcfps"] is not None:
                return float(fcf_data["fcfps"])
            # 如果没有 fcfps，尝试使用 cfps（每股经营现金流）作为近似
            elif "cfps" in fcf_data and fcf_data["cfps"] is not None:
                return float(fcf_data["cfps"])

        # 如果数据库没有数据，返回 None（调用方需要处理）
        return None
