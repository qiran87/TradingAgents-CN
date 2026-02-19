"""增长率计算器"""

import numpy as np
from typing import List
from app.domain.mdvaes import EPSForecast, GrowthMetrics, TrendStability


class GrowthCalculator:
    """增长指标计算器"""

    @staticmethod
    def calculate(eps_forecasts: List[EPSForecast]) -> GrowthMetrics:
        """计算增长指标

        使用对数最小二乘法回归分析 EPS 增长率
        """
        if len(eps_forecasts) < 2:
            raise ValueError("至少需要 2 个 EPS 预测数据点")

        # 提取年份和 EPS
        years = np.array([f.year for f in eps_forecasts])
        eps_values = np.array([f.eps_forecast for f in eps_forecasts])

        # 过滤掉非正数 EPS
        valid_mask = eps_values > 0
        if not valid_mask.any():
            raise ValueError("所有 EPS 值都必须为正数")

        years = years[valid_mask]
        eps_values = eps_values[valid_mask]

        # 对数最小二乘法回归
        log_eps = np.log(eps_values)
        coeffs = np.polyfit(years, log_eps, 1)
        slope = coeffs[0]

        # 计算 R²
        log_eps_pred = np.polyval(coeffs, years)
        ss_res = np.sum((log_eps - log_eps_pred) ** 2)
        ss_tot = np.sum((log_eps - np.mean(log_eps)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # 计算 CAGR (复合年均增长率)
        n_years = years[-1] - years[0]
        if n_years > 0:
            cagr = (eps_values[-1] / eps_values[0]) ** (1 / n_years) - 1
        else:
            cagr = 0

        # 增长率（基于斜率）
        growth_rate = np.exp(slope) - 1

        # 增长质量评分（基于 R² 和增长一致性）
        growth_quality_score = min(r_squared, 0.95)

        # 趋势稳定性
        if r_squared >= 0.8:
            trend_stability = TrendStability.STABLE
        elif r_squared >= 0.5:
            trend_stability = TrendStability.VOLATILE
        else:
            trend_stability = TrendStability.DECLINING

        return GrowthMetrics(
            cagr=cagr,
            growth_rate=growth_rate,
            r_squared=r_squared,
            growth_quality_score=growth_quality_score,
            trend_stability=trend_stability
        )
