"""MDVAES 数据读取器"""

import logging
from typing import List, Optional
from datetime import datetime
from app.core.database import get_mongo_db
from app.core.config import settings
from app.domain.mdvaes import EPSForecast
import pymongo

logger = logging.getLogger(__name__)


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
        """获取历史 EPS 数据（同比外推法处理季节性）

        策略：
        1. 优先使用年报数据（完整全年数据）
        2. 如果最近一期不是年报，使用同比外推法估算全年EPS

        同比外推公式：
            今年全年预估 = 上一年全年EPS × (最近季度EPS / 去年同季度EPS)

        这种方法保持了季节性特征，比简单乘法更准确。

        注意：
        - 使用 ann_date（公告日期）而非 end_date（报告期）
        - ann_date 必须严格小于 calculation_date
        - 必须排除 eps 为 None/NaN 的数据
        - 保留负EPS（亏损是真实存在的财务数据）
        - 至少需要3年数据才能计算增长率

        Args:
            limit: 最多获取多少年历史数据，默认5年（推荐3-5年）
        """
        # 将日期转换为 YYYYMMDD 格式进行比较
        calculation_date_yyyymmdd = calculation_date.replace("-", "")

        # 获取更多数据以便筛选和同比计算
        historical_eps = await db.mdvaes_eps_history.find({
            "ts_code": symbol,
            "ann_date": {"$lt": calculation_date_yyyymmdd},
            "eps": {"$ne": None, "$exists": True}
        }).sort("ann_date", -1).limit(limit * 6).to_list(None)

        # 过滤有效 EPS
        filtered = [ep for ep in (historical_eps or []) if ep.get("eps") is not None]

        # 构建报告期索引，用于同比计算
        # 按年分组，每年保存所有可用报告
        yearly_reports = {}  # {year: {report_type: data}}
        for ep in filtered:
            end_date_str = ep.get("end_date", "")
            if not end_date_str:
                continue

            # 解析报告期
            if "-" in end_date_str:
                end_date_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
            else:
                end_date_dt = datetime.strptime(end_date_str, "%Y%m%d")

            year = end_date_dt.year
            month_day = end_date_str[-4:]

            # 报告类型标识
            report_key = "annual" if month_day == "1231" else (
                "q2" if month_day == "0630" else
                "q3" if month_day == "0930" else
                "q1" if month_day == "0331" else
                f"other_{month_day}"
            )

            if year not in yearly_reports:
                yearly_reports[year] = {}
            # 保留该报告期最新公告的数据
            if report_key not in yearly_reports[year] or ep["ann_date"] > yearly_reports[year][report_key]["ann_date"]:
                yearly_reports[year][report_key] = ep

        # 构建年度数据，使用同比外推法
        yearly_data = []
        years_sorted = sorted(yearly_reports.keys(), reverse=True)

        for year in years_sorted[:limit]:
            reports = yearly_reports[year]

            # 优先使用年报
            if "annual" in reports:
                annual_report = reports["annual"]
                yearly_data.append({
                    **annual_report,
                    "annualized_eps": annual_report["eps"],
                    "report_type": "年报",
                    "is_annual": True
                })
            else:
                # 没有年报，使用同比外推法
                # 找到最新一期的报告
                latest_report = None
                latest_key = None
                for key in ["q3", "q2", "q1"]:
                    if key in reports:
                        latest_report = reports[key]
                        latest_key = key
                        break

                if latest_report and year - 1 in yearly_reports:
                    # 获取去年同期的报告
                    last_year_reports = yearly_reports[year - 1]
                    if latest_key in last_year_reports:
                        last_year_same_period = last_year_reports[latest_key]

                        # 获取去年全年EPS
                        last_year_annual = None
                        if "annual" in last_year_reports:
                            last_year_annual = last_year_reports["annual"]["eps"]
                        else:
                            # 去年也没有年报，使用去年的同比外推值
                            # 递归查找（简化处理：使用最新一期作为近似）
                            last_year_annual = last_year_same_period["eps"]

                        # 同比外推计算
                        current_period_eps = latest_report["eps"]
                        last_year_period_eps = last_year_same_period["eps"]

                        # 避免除零错误
                        if last_year_period_eps != 0:
                            growth_ratio = current_period_eps / last_year_period_eps
                            annualized_eps = last_year_annual * growth_ratio
                        else:
                            # 去年同期为0（可能是新上市），保守使用当前EPS
                            annualized_eps = current_period_eps

                        report_type_map = {"q1": "一季报(同比外推)", "q2": "半年报(同比外推)", "q3": "三季报(同比外推)"}
                        yearly_data.append({
                            **latest_report,
                            "annualized_eps": annualized_eps,
                            "report_type": report_type_map.get(latest_key, f"其他({latest_key})"),
                            "is_annual": False,
                            "yoy_growth": growth_ratio if last_year_period_eps != 0 else None
                        })

                        logger.info(
                            f"{symbol} {year}年使用同比外推: {latest_key} "
                            f"当前={current_period_eps:.2f}, 去年同期={last_year_period_eps:.2f}, "
                            f"去年全年={last_year_annual:.2f}, 预估全年={annualized_eps:.2f}"
                        )
                    else:
                        # 找不到去年同期的数据，降级处理
                        logger.warning(
                            f"{symbol} {year}年{latest_key}找不到去年同期数据，"
                            f"使用当前EPS作为近似值"
                        )
                        yearly_data.append({
                            **latest_report,
                            "annualized_eps": latest_report["eps"],
                            "report_type": f"{latest_key}(无同比)",
                            "is_annual": False
                        })
                else:
                    # 既没有年报，也找不到完整的历史数据
                    if latest_report:
                        yearly_data.append({
                            **latest_report,
                            "annualized_eps": latest_report["eps"],
                            "report_type": "数据不完整",
                            "is_annual": False
                        })

        return yearly_data[:limit]

    def _extrapolate_eps(self, historical_eps: List[dict], forecast_years: int) -> List[EPSForecast]:
        """基于历史 EPS 外推预测（使用年化 EPS）

        使用 CAGR 公式计算历史增长率，并外推预测未来 EPS。
        支持负EPS（亏损年份），自动处理计算边界情况。

        注意：historical_eps 中的数据已包含 annualized_eps 字段（年化后的 EPS）

        Args:
            historical_eps: 历史 EPS 数据（按 ann_date 降序排列，已年化）
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

        # 使用年化后的 EPS 进行计算
        latest_eps = historical_eps[0]["annualized_eps"]
        oldest_eps = historical_eps[-1]["annualized_eps"]
        n_years = len(historical_eps)

        # 计算历史增长率，处理负EPS的情况
        growth_rate = self._calculate_growth_rate(historical_eps)

        # 获取最新的 ann_date（公告日期）作为外推依据
        ann_date_str = historical_eps[0].get("ann_date", "")
        if ann_date_str:
            # 转换为 YYYY-MM-DD 格式
            if "-" not in ann_date_str:
                ann_date_formatted = f"{ann_date_str[:4]}-{ann_date_str[4:6]}-{ann_date_str[6:8]}"
            else:
                ann_date_formatted = ann_date_str
        else:
            ann_date_formatted = None

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
                source="historical_extrapolation",
                ann_date=ann_date_formatted  # 添加公告日期
            ))

        return forecasts

    def _calculate_growth_rate(self, historical_eps: List[dict]) -> float:
        """计算历史增长率，处理各种边界情况（使用年化 EPS）

        Args:
            historical_eps: 历史 EPS 数据（已包含 annualized_eps 字段）

        Returns:
            增长率（如 0.15 表示 15%）

        Raises:
            ValueError: 如果无法计算增长率（如持续亏损、波动太大）
        """
        # 使用年化后的 EPS
        latest_eps = historical_eps[0]["annualized_eps"]
        oldest_eps = historical_eps[-1]["annualized_eps"]
        n_years = len(historical_eps)

        # 检查1：最新EPS为负，公司仍在亏损，不适合外推预测
        if latest_eps < 0:
            raise ValueError(
                f"该公司最新年化EPS为负（{latest_eps}），公司仍在亏损。"
                f"历史外推方法不适用于亏损公司，建议使用分析师预测。"
            )

        # 检查2：检查是否有正负交替（盈利波动太大）
        has_negative = any(ep["annualized_eps"] < 0 for ep in historical_eps)
        if has_negative:
            raise ValueError(
                f"该公司历史年化EPS中存在负值（亏损年份），业绩波动太大。"
                f"历史外推方法不适用于业绩波动剧烈的公司，建议使用分析师预测。"
            )

        # 检查3：最旧EPS为0或负数，无法用CAGR公式
        if oldest_eps <= 0:
            raise ValueError(
                f"历史数据起始年化EPS为{oldest_eps}，无法计算增长率。"
                f"需要所有历史年化EPS都为正数才能使用CAGR公式。"
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
        """获取历史 EPS 数据（同步版本，同比外推法）

        策略：
        1. 优先使用年报数据（完整全年数据）
        2. 如果最近一期不是年报，使用同比外推法估算全年EPS

        同比外推公式：
            今年全年预估 = 上一年全年EPS × (最近季度EPS / 去年同季度EPS)
        """
        calculation_date_yyyymmdd = calculation_date.replace("-", "")

        historical_eps = list(db.mdvaes_eps_history.find({
            "ts_code": symbol,
            "ann_date": {"$lt": calculation_date_yyyymmdd},
            "eps": {"$ne": None, "$exists": True}
        }).sort("ann_date", -1).limit(limit * 6))

        # 过滤有效 EPS
        filtered = [ep for ep in historical_eps if ep.get("eps") is not None]

        # 构建报告期索引
        yearly_reports = {}
        for ep in filtered:
            end_date_str = ep.get("end_date", "")
            if not end_date_str:
                continue

            if "-" in end_date_str:
                end_date_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
            else:
                end_date_dt = datetime.strptime(end_date_str, "%Y%m%d")

            year = end_date_dt.year
            month_day = end_date_str[-4:]

            report_key = "annual" if month_day == "1231" else (
                "q2" if month_day == "0630" else
                "q3" if month_day == "0930" else
                "q1" if month_day == "0331" else
                f"other_{month_day}"
            )

            if year not in yearly_reports:
                yearly_reports[year] = {}
            if report_key not in yearly_reports[year] or ep["ann_date"] > yearly_reports[year][report_key]["ann_date"]:
                yearly_reports[year][report_key] = ep

        # 构建年度数据
        yearly_data = []
        years_sorted = sorted(yearly_reports.keys(), reverse=True)

        for year in years_sorted[:limit]:
            reports = yearly_reports[year]

            if "annual" in reports:
                annual_report = reports["annual"]
                yearly_data.append({
                    **annual_report,
                    "annualized_eps": annual_report["eps"],
                    "report_type": "年报",
                    "is_annual": True
                })
            else:
                # 同比外推
                latest_report = None
                latest_key = None
                for key in ["q3", "q2", "q1"]:
                    if key in reports:
                        latest_report = reports[key]
                        latest_key = key
                        break

                if latest_report and year - 1 in yearly_reports:
                    last_year_reports = yearly_reports[year - 1]
                    if latest_key in last_year_reports:
                        last_year_same_period = last_year_reports[latest_key]

                        last_year_annual = None
                        if "annual" in last_year_reports:
                            last_year_annual = last_year_reports["annual"]["eps"]
                        else:
                            last_year_annual = last_year_same_period["eps"]

                        current_period_eps = latest_report["eps"]
                        last_year_period_eps = last_year_same_period["eps"]

                        if last_year_period_eps != 0:
                            growth_ratio = current_period_eps / last_year_period_eps
                            annualized_eps = last_year_annual * growth_ratio
                        else:
                            annualized_eps = current_period_eps

                        report_type_map = {"q1": "一季报(同比外推)", "q2": "半年报(同比外推)", "q3": "三季报(同比外推)"}
                        yearly_data.append({
                            **latest_report,
                            "annualized_eps": annualized_eps,
                            "report_type": report_type_map.get(latest_key, f"其他({latest_key})"),
                            "is_annual": False,
                            "yoy_growth": growth_ratio if last_year_period_eps != 0 else None
                        })
                    else:
                        yearly_data.append({
                            **latest_report,
                            "annualized_eps": latest_report["eps"],
                            "report_type": f"{latest_key}(无同比)",
                            "is_annual": False
                        })
                else:
                    if latest_report:
                        yearly_data.append({
                            **latest_report,
                            "annualized_eps": latest_report["eps"],
                            "report_type": "数据不完整",
                            "is_annual": False
                        })

        return yearly_data[:limit]

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
        """获取当前每股自由现金流 FCFPS（同步版本，使用同比外推法）

        优先获取 fcfps（每股自由现金流），如果不存在则尝试使用 cfps（每股经营现金流）

        同比外推法（与 EPS 处理逻辑一致）：
        1. 优先使用年报数据（完整全年数据）
        2. 如果最近一期不是年报，使用同比外推：
           今年全年预估 = 去年全年FCF × (最近季度FCF / 去年同季度FCF)

        注意：
        - Tushare API 返回 fcfe_ps，同步服务会将其映射为 fcfps 存入数据库
        - fcfps/cfps 是累加值，存在季节性问题，需要同比外推处理
        """
        db = self._get_sync_db()
        calculation_date_yyyymmdd = calculation_date.replace("-", "")

        # 获取最近的 fcfps 数据（多取几条以便同比计算）
        fcf_data_list = list(db.mdvaes_eps_history.find({
            "ts_code": symbol,
            "ann_date": {"$lt": calculation_date_yyyymmdd},
            "$or": [
                {"fcfps": {"$ne": None, "$exists": True}},
                {"cfps": {"$ne": None, "$exists": True}}
            ]
        }).sort("ann_date", -1).limit(20))

        if not fcf_data_list:
            return None

        # 确定使用哪个字段（优先 fcfps，否则 cfps）
        use_fcfps = any(d.get("fcfps") is not None for d in fcf_data_list)
        field_name = "fcfps" if use_fcfps else "cfps"
        display_name = "每股自由现金流" if use_fcfps else "每股经营现金流"

        # 过滤有效数据
        valid_data = [d for d in fcf_data_list if d.get(field_name) is not None]

        if not valid_data:
            return None

        # 按年分组，优先选择年报
        yearly_reports = {}
        for data in valid_data:
            end_date_str = data.get("end_date", "")
            if not end_date_str:
                continue

            # 解析报告期
            if "-" in end_date_str:
                end_date_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
            else:
                end_date_dt = datetime.strptime(end_date_str, "%Y%m%d")

            year = end_date_dt.year
            month_day = end_date_str[-4:]

            # 报告类型标识
            report_key = "annual" if month_day == "1231" else (
                "q2" if month_day == "0630" else
                "q3" if month_day == "0930" else
                "q1" if month_day == "0331" else
                f"other_{month_day}"
            )

            if year not in yearly_reports:
                yearly_reports[year] = {}
            if report_key not in yearly_reports[year] or data["ann_date"] > yearly_reports[year][report_key]["ann_date"]:
                yearly_reports[year][report_key] = data

        # 获取最新一年的年度 fcfps
        years_sorted = sorted(yearly_reports.keys(), reverse=True)
        if not years_sorted:
            return None

        latest_year = years_sorted[0]
        latest_reports = yearly_reports[latest_year]

        # 优先使用年报
        if "annual" in latest_reports:
            annual_value = latest_reports["annual"].get(field_name)
            if annual_value is not None:
                logger.info(
                    f"{symbol} {display_name}: 使用{latest_year}年年报 = {annual_value:.2f}"
                )
                return float(annual_value)

        # 没有年报，使用同比外推法
        # 找到最新一期的报告
        latest_report = None
        latest_key = None
        for key in ["q3", "q2", "q1"]:
            if key in latest_reports:
                latest_report = latest_reports[key]
                latest_key = key
                break

        if latest_report and latest_year - 1 in yearly_reports:
            last_year_reports = yearly_reports[latest_year - 1]
            if latest_key in last_year_reports:
                last_year_same_period = last_year_reports[latest_key]

                # 获取去年全年 fcfps
                last_year_annual = None
                if "annual" in last_year_reports:
                    last_year_annual = last_year_reports["annual"].get(field_name)
                else:
                    # 去年也没有年报，保守使用当前值
                    last_year_annual = last_year_same_period.get(field_name)

                if last_year_annual is not None:
                    current_period_value = latest_report.get(field_name, 0)
                    last_year_period_value = last_year_same_period.get(field_name, 0)

                    # 同比外推计算
                    if last_year_period_value != 0:
                        growth_ratio = current_period_value / last_year_period_value
                        annualized_value = last_year_annual * growth_ratio
                    else:
                        # 去年同期为0，保守使用当前值
                        annualized_value = current_period_value

                    report_type_map = {"q1": "一季报", "q2": "半年报", "q3": "三季报"}
                    logger.info(
                        f"{symbol} {display_name}: {latest_year}年{report_type_map.get(latest_key, latest_key)}同比外推 | "
                        f"当前={current_period_value:.2f}, 去年同期={last_year_period_value:.2f}, "
                        f"去年全年={last_year_annual:.2f}, 预估全年={annualized_value:.2f}"
                    )
                    return float(annualized_value)

        # 降级：直接使用最新值
        latest_value = valid_data[0].get(field_name)
        if latest_value is not None:
            logger.warning(
                f"{symbol} {display_name}: 无法进行同比外推，使用最新季度值 = {latest_value:.2f}"
            )
            return float(latest_value)

        return None
