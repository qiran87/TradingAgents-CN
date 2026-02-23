#!/usr/bin/env python3
"""MDVAES估值策略单次回测脚本

用于计算单个股票在指定日期的MDVAES估值，展示每个步骤的计算细节。

输入:
    1) 股票代码 (如 600941.SS 或 000001.SZ)
    2) 日期 (如 2024-01-02)
    3) EPS预测年数 (默认5)
    4) PEG基数 (默认1.0)
    5) 风险调整幅度 (默认0.1)
    6) 买入安全边际 (默认0.8)
    7) 卖出安全边际 (默认1.2)

输出:
    - 每个估值步骤的计算取值
    - 最终估值结果
    - 与当前价格比对得出的交易结论
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from datetime import datetime
import pymongo
from app.core.config import settings
from app.domain.mdvaes import (
    MDVAESParams, RiskMetrics, RiskLevel, EPSForecast
)
from app.services.mdvaes_data_reader import MDVAESDataReader
from app.services.growth_calculator import GrowthCalculator
from app.services.valuation_calculator import ValuationCalculator


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_subsection(title: str):
    """打印子分隔线"""
    print(f"\n--- {title} ---")


def get_sync_db():
    """获取同步 MongoDB 客户端"""
    client = pymongo.MongoClient(
        settings.MONGODB_HOST,
        settings.MONGODB_PORT,
        username=settings.MONGODB_USERNAME,
        password=settings.MONGODB_PASSWORD,
        authSource=settings.MONGODB_AUTH_SOURCE
    )
    return client[settings.MONGODB_DATABASE]


def get_current_price(db, symbol: str, calculation_date: str) -> float:
    """获取当前价格

    从 stock_daily_quotes 表获取最近交易日的收盘价
    注意：使用 trade_date（交易日期），必须严格小于 calculation_date
    """
    calculation_date_yyyymmdd = calculation_date.replace("-", "")

    price_data = db.stock_daily_quotes.find_one({
        "ts_code": symbol,
        "trade_date": {"$lt": calculation_date_yyyymmdd}
    }, sort=[("trade_date", -1)], projection=["close"])

    if price_data and "close" in price_data:
        return float(price_data["close"])

    raise ValueError(f"无法获取 {symbol} 在 {calculation_date} 之前的价格数据")


def run_single_backtest(
    symbol: str,
    calculation_date: str,
    forecast_years: int,
    peg_base: float,
    risk_adjustment: float,
    margin_buy: float,
    margin_sell: float
):
    """运行单次MDVAES估值回测"""

    print_section("MDVAES估值策略单次回测")
    print(f"\n股票代码: {symbol}")
    print(f"计算日期: {calculation_date}")
    print(f"EPS预测年数: {forecast_years}年")
    print(f"PEG基数: {peg_base}")
    print(f"风险调整幅度: {risk_adjustment}")
    print(f"买入安全边际: {margin_buy} (价格低于估值的{margin_buy*100}%)")
    print(f"卖出安全边际: {margin_sell} (价格高于估值的{margin_sell*100}%)")

    # 初始化服务
    data_reader = MDVAESDataReader()
    growth_calculator = GrowthCalculator()
    valuation_calculator = ValuationCalculator()
    db = get_sync_db()

    # ==================== 步骤1: 获取EPS预测 ====================
    print_section("步骤1: 获取EPS预测数据")

    try:
        eps_forecasts = data_reader.get_eps_forecast_sync(
            symbol, calculation_date, forecast_years
        )

        print(f"\n✅ EPS预测来源: {eps_forecasts[0].source}")
        print(f"预测年数: {len(eps_forecasts)} 年")
        print("\n各年度EPS预测:")
        print(f"{'年份':<8} {'EPS预测':<15} {'预测日期':<15} {'来源':<20}")
        print("-" * 60)
        for forecast in eps_forecasts:
            source_str = "分析师预测" if forecast.source == "analyst" else "历史外推"
            print(f"{forecast.year:<8} {forecast.eps_forecast:<15.4f} {forecast.forecast_date:<15} {source_str:<20}")

        current_eps = eps_forecasts[0].eps_forecast
        print(f"\n📊 当前EPS (第{eps_forecasts[0].year}年): {current_eps:.4f}")

    except Exception as e:
        print(f"\n❌ 获取EPS预测失败: {e}")
        return

    # ==================== 步骤2: 计算增长指标 ====================
    print_section("步骤2: 计算增长指标")

    try:
        growth_metrics = growth_calculator.calculate(eps_forecasts)

        print(f"\n📈 复合年均增长率 (CAGR): {growth_metrics.cagr:.2%}")
        print(f"📈 增长率: {growth_metrics.growth_rate:.2%}")
        print(f"📊 R² 拟合优度: {growth_metrics.r_squared:.4f}")
        print(f"⭐ 增长质量评分: {growth_metrics.growth_quality_score:.2f}/1.0")
        print(f"📉 趋势稳定性: {growth_metrics.trend_stability.value}")

    except Exception as e:
        print(f"\n❌ 计算增长指标失败: {e}")
        return

    # ==================== 步骤3: 获取当前PE ====================
    print_section("步骤3: 获取当前PE")

    try:
        current_pe = data_reader.get_current_pe_sync(symbol, calculation_date)

        if current_pe:
            print(f"\n✅ 当前PE (TTM): {current_pe:.2f} 倍")
        else:
            print(f"\n⚠️ 未找到PE数据，使用默认值 15.0 倍")
            current_pe = 15.0

    except Exception as e:
        print(f"\n⚠️ 获取PE失败: {e}，使用默认值 15.0 倍")
        current_pe = 15.0

    # ==================== 步骤4: 获取国债利率 ====================
    print_section("步骤4: 获取无风险利率")

    try:
        bond_rate = data_reader.get_bond_rate_sync(calculation_date)
        print(f"\n✅ 10年期国债收益率: {bond_rate:.2%}")

    except Exception as e:
        print(f"\n⚠️ 获取国债利率失败: {e}，使用默认值 2.75%")
        bond_rate = 0.0275

    # ==================== 步骤5: 构建风险指标 ====================
    print_section("步骤5: 构建风险指标")

    # 尝试从数据库获取真实财务比率（使用同步查询）
    try:
        calculation_date_yyyymmdd = calculation_date.replace("-", "")
        ratios_data = db.mdvaes_financial_ratios.find_one({
            "ts_code": symbol,
            "ann_date": {"$lt": calculation_date_yyyymmdd}
        }, sort=[("ann_date", -1)])

        if ratios_data:
            ratios = {
                "debt_to_assets": ratios_data.get("debt_to_assets"),
                "current_ratio": ratios_data.get("current_ratio"),
                "quick_ratio": ratios_data.get("quick_ratio"),
                "roe": ratios_data.get("roe"),
                "roa": ratios_data.get("roa")
            }
            print(f"\n✅ 使用真实财务数据:")
            # 数据库中的百分比数值直接显示即可（如14.14表示14.14%）
            print(f"   资产负债率: {ratios.get('debt_to_assets', 50):.2f}%")
            print(f"   流动比率: {ratios.get('current_ratio', 1.5):.2f}")
            print(f"   速动比率: {ratios.get('quick_ratio', 1.2):.2f}")
            print(f"   ROE: {ratios.get('roe', 10):.2f}%")
            print(f"   ROA: {ratios.get('roa', 5):.2f}%")

            # 根据财务数据评估风险等级（将百分比转换为小数）
            debt_ratio_pct = ratios.get('debt_to_assets', 50)
            debt_ratio = debt_ratio_pct / 100.0  # 转换为小数（14.14 → 0.1414）
            if debt_ratio < 0.3:
                risk_level = RiskLevel.LOW
            elif debt_ratio < 0.6:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.HIGH
            print(f"   风险等级评估: {risk_level.value} (资产负债率 {debt_ratio_pct:.2f}%)")

            risk_metrics = RiskMetrics(
                debt_to_assets=debt_ratio,  # 使用转换后的小数
                current_ratio=ratios.get('current_ratio', 1.5),
                quick_ratio=ratios.get('quick_ratio', 1.2),
                cashflow_to_income=1.1,
                risk_level=risk_level
            )
        else:
            raise ValueError("无财务数据")

    except Exception as e:
        print(f"\n⚠️ 未获取到真实财务数据，使用默认值")
        print(f"   资产负债率: 50%")
        print(f"   流动比率: 1.5")
        print(f"   速动比率: 1.2")
        print(f"   风险等级: MEDIUM")

        risk_metrics = RiskMetrics(
            debt_to_assets=0.5,
            current_ratio=1.5,
            quick_ratio=1.2,
            cashflow_to_income=1.1,
            risk_level=RiskLevel.MEDIUM
        )

    # ==================== 步骤6: 构建MDVAES参数 ====================
    print_section("步骤6: 构建MDVAES参数")

    params = MDVAESParams(
        forecast_years=forecast_years,
        peg_base=peg_base,
        risk_adjustment=risk_adjustment,
        signal_mode="safety_margin",
        safety_margin_buy=margin_buy,
        safety_margin_sell=margin_sell
    )
    params.validate()

    print(f"\n预测年数: {params.forecast_years}")
    print(f"PEG基数: {params.peg_base}")
    print(f"PEG利率敏感度: {params.peg_interest_sensitivity}")
    print(f"风险调整幅度: {params.risk_adjustment}")
    print(f"信号模式: {params.signal_mode}")
    print(f"买入安全边际: {params.safety_margin_buy}")
    print(f"卖出安全边际: {params.safety_margin_sell}")
    print(f"\n多锚点权重:")
    for anchor, weight in params.anchor_weight.items():
        print(f"   {anchor}: {weight:.2%}")

    # ==================== 步骤7: 多锚点估值计算 ====================
    print_section("步骤7: 多锚点估值计算")

    # 7.1 PEG估值
    print_subsection("7.1 PEG估值")
    interest_adjustment = 1 - params.peg_interest_sensitivity * bond_rate
    peg_valuation = current_eps * growth_metrics.growth_rate * params.peg_base * interest_adjustment
    print(f"公式: PEG估值 = EPS × 增长率 × PEG基数 × (1 - 利率敏感度 × 国债利率)")
    print(f"     = {current_eps:.4f} × {growth_metrics.growth_rate:.2%} × {params.peg_base} × (1 - {params.peg_interest_sensitivity} × {bond_rate:.2%})")
    print(f"     = {current_eps:.4f} × {growth_metrics.growth_rate:.2%} × {params.peg_base} × {interest_adjustment:.4f}")
    print(f"     = {peg_valuation:.2f} 元")

    # 7.2 历史PE估值
    print_subsection("7.2 历史PE估值")
    growth_adjustment = 1 + growth_metrics.growth_rate
    pe_historical_valuation = current_eps * current_pe * growth_adjustment * 0.8
    print(f"公式: PE估值 = EPS × 当前PE × (1 + 增长率) × 0.8")
    print(f"     = {current_eps:.4f} × {current_pe:.2f} × (1 + {growth_metrics.growth_rate:.2%}) × 0.8")
    print(f"     = {current_eps:.4f} × {current_pe:.2f} × {growth_adjustment:.4f} × 0.8")
    print(f"     = {pe_historical_valuation:.2f} 元")

    # 7.3 PB估值
    print_subsection("7.3 PB估值")
    pb_valuation = current_eps * 1.5
    print(f"公式: PB估值 = EPS × 1.5")
    print(f"     = {current_eps:.4f} × 1.5")
    print(f"     = {pb_valuation:.2f} 元")

    # 7.4 DCF估值
    print_subsection("7.4 DCF估值 (简化版)")
    terminal_growth = 0.03
    required_return = bond_rate + 0.05
    if growth_metrics.growth_rate >= required_return:
        adj_growth_rate = required_return - 0.01
    else:
        adj_growth_rate = growth_metrics.growth_rate

    print(f"终值增长率: {terminal_growth:.2%}")
    print(f"必要回报率: 无风险利率({bond_rate:.2%}) + 5% = {required_return:.2%}")
    print(f"调整后增长率: {adj_growth_rate:.2%}")

    forecast_values = []
    print(f"\n未来{forecast_years}年EPS预测及折现:")
    print(f"{'年份':<8} {'预测EPS':<15} {'折现因子':<15} {'折现值':<15}")
    print("-" * 50)

    for i in range(1, forecast_years + 1):
        forecast_eps = current_eps * ((1 + adj_growth_rate) ** i)
        discount_factor = (1 + required_return) ** i
        discounted_value = forecast_eps / discount_factor
        forecast_values.append(discounted_value)
        print(f"第{i}年    {forecast_eps:<15.4f} {discount_factor:<15.4f} {discounted_value:<15.4f}")

    # 终值
    terminal_eps = current_eps * ((1 + adj_growth_rate) ** forecast_years)
    terminal_value = terminal_eps * (1 + terminal_growth) / (required_return - terminal_growth)
    discounted_terminal = terminal_value / ((1 + required_return) ** forecast_years)
    print(f"终值      -              -              {discounted_terminal:<15.4f}")

    dcf_valuation = sum(forecast_values) + discounted_terminal
    print(f"\nDCF估值 = Σ折现值 + 折现终值 = {dcf_valuation:.2f} 元")

    # 7.5 多锚点加权
    print_subsection("7.5 多锚点加权估值")
    weighted_valuation = (
        params.anchor_weight["peg"] * peg_valuation +
        params.anchor_weight["pe_historical"] * pe_historical_valuation +
        params.anchor_weight["pb"] * pb_valuation +
        params.anchor_weight["dcf"] * dcf_valuation
    )

    print(f"公式: 加权估值 = PEG权重×PEG + PE权重×PE + PB权重×PB + DCF权重×DCF")
    print(f"     = {params.anchor_weight['peg']:.2%}×{peg_valuation:.2f} + "
          f"{params.anchor_weight['pe_historical']:.2%}×{pe_historical_valuation:.2f} + "
          f"{params.anchor_weight['pb']:.2%}×{pb_valuation:.2f} + "
          f"{params.anchor_weight['dcf']:.2%}×{dcf_valuation:.2f}")
    print(f"     = {params.anchor_weight['peg']:.2%}×{peg_valuation:.2f} + "
          f"{params.anchor_weight['pe_historical']:.2%}×{pe_historical_valuation:.2f} + "
          f"{params.anchor_weight['pb']:.2%}×{pb_valuation:.2f} + "
          f"{params.anchor_weight['dcf']:.2%}×{dcf_valuation:.2f}")
    print(f"     = {weighted_valuation:.2f} 元")

    # ==================== 步骤8: 风险调整 ====================
    print_section("步骤8: 风险调整")

    risk_factor_map = {"low": 0.5, "medium": 1.0, "high": 1.5}
    risk_factor = risk_factor_map.get(risk_metrics.risk_level.value, 1.0)
    adjusted_valuation = weighted_valuation * (1 - params.risk_adjustment * risk_factor)

    print(f"风险等级: {risk_metrics.risk_level.value}")
    print(f"风险调整系数: {risk_factor}")
    print(f"风险调整幅度: {params.risk_adjustment:.2%}")
    print(f"\n公式: 风险调整后估值 = 加权估值 × (1 - 风险调整幅度 × 风险系数)")
    print(f"     = {weighted_valuation:.2f} × (1 - {params.risk_adjustment:.2%} × {risk_factor})")
    print(f"     = {weighted_valuation:.2f} × (1 - {params.risk_adjustment * risk_factor:.2%})")
    print(f"     = {adjusted_valuation:.2f} 元")

    # ==================== 步骤9: 计算估值区间 ====================
    print_section("步骤9: 计算估值区间")

    base_confidence = growth_metrics.r_squared
    risk_penalty = {"low": 0.0, "medium": 0.1, "high": 0.2}
    penalty = risk_penalty.get(risk_metrics.risk_level.value, 0.1)
    confidence = max(base_confidence - penalty, 0.3)
    confidence = min(confidence, 0.95)

    margin = adjusted_valuation * (1 - confidence) * 0.2
    lower_bound = max(adjusted_valuation - margin, 0)
    upper_bound = adjusted_valuation + margin

    print(f"R² 拟合优度: {base_confidence:.4f}")
    print(f"风险惩罚: {penalty:.2%}")
    print(f"置信度: {confidence:.2%}")
    print(f"估值波动幅度: {margin:.2f} 元")
    print(f"\n估值下限: {lower_bound:.2f} 元")
    print(f"估值上限: {upper_bound:.2f} 元")
    print(f"内在价值: {adjusted_valuation:.2f} 元")

    # ==================== 步骤10: 获取当前价格并生成交易信号 ====================
    print_section("步骤10: 交易决策")

    try:
        current_price = get_current_price(db, symbol, calculation_date)
        print(f"\n当前价格: {current_price:.2f} 元")

    except Exception as e:
        print(f"\n⚠️ 获取价格失败: {e}")
        print("请手动输入当前价格用于计算交易信号:")
        current_price = float(input("当前价格 (元): "))

    # 计算买入/卖出阈值
    buy_threshold = adjusted_valuation * margin_buy
    sell_threshold = adjusted_valuation * margin_sell

    print(f"\n买入阈值: 内在价值 × {margin_buy} = {adjusted_valuation:.2f} × {margin_buy} = {buy_threshold:.2f} 元")
    print(f"卖出阈值: 内在价值 × {margin_sell} = {adjusted_valuation:.2f} × {margin_sell} = {sell_threshold:.2f} 元")

    # 判断交易信号
    print_subsection("交易信号判断")

    if current_price <= buy_threshold:
        signal = "买入"
        signal_emoji = "🟢"
        safety_margin = (1 - current_price / adjusted_valuation) * 100
        reason = f"当前价格低于买入阈值，安全边际 {safety_margin:.1f}%"
    elif current_price >= sell_threshold:
        signal = "卖出"
        signal_emoji = "🔴"
        overvalued = (current_price / adjusted_valuation - 1) * 100
        reason = f"当前价格高于卖出阈值，高估 {overvalued:.1f}%"
    else:
        signal = "持有"
        signal_emoji = "🟡"
        if current_price < adjusted_valuation:
            discount = (adjusted_valuation - current_price) / adjusted_valuation * 100
            reason = f"当前价格低于内在价值 {discount:.1f}%，但未达到买入阈值"
        elif current_price > adjusted_valuation:
            premium = (current_price / adjusted_valuation - 1) * 100
            reason = f"当前价格高于内在价值 {premium:.1f}%，但未达到卖出阈值"
        else:
            reason = f"当前价格接近内在价值"

    print(f"\n{signal_emoji} 交易信号: {signal}")
    print(f"决策理由: {reason}")

    # ==================== 最终汇总 ====================
    print_section("最终汇总")

    print(f"\n┌─ {'MDVAES估值结果':^74} ─┐")
    print(f"│ {'':^76} │")
    print(f"│  股票代码: {symbol:<60} │")
    print(f"│  计算日期: {calculation_date:<60} │")
    print(f"│ {'':^76} │")
    print(f"│  {'锚点估值':<20} {'估值 (元)':<20} {'权重':<20} │")
    print(f"│  {'-' * 60:<60} │")
    print(f"│  {'PEG估值':<20} {peg_valuation:>18.2f} 元 {params.anchor_weight['peg']:>18.2%} │")
    print(f"│  {'PE估值':<20} {pe_historical_valuation:>18.2f} 元 {params.anchor_weight['pe_historical']:>18.2%} │")
    print(f"│  {'PB估值':<20} {pb_valuation:>18.2f} 元 {params.anchor_weight['pb']:>18.2%} │")
    print(f"│  {'DCF估值':<20} {dcf_valuation:>18.2f} 元 {params.anchor_weight['dcf']:>18.2%} │")
    print(f"│  {'-' * 60:<60} │")
    print(f"│  {'加权估值':<20} {weighted_valuation:>18.2f} 元 {'100%':>18} │")
    print(f"│ {'':^76} │")
    print(f"│  {'风险调整后内在价值':<30} {adjusted_valuation:>18.2f} 元 │")
    print(f"│  {'估值区间':<30} [{lower_bound:.2f}, {upper_bound:.2f}] 元 │")
    print(f"│  {'置信度':<30} {confidence:>18.2%} │")
    print(f"│ {'':^76} │")
    print(f"│  {'当前价格':<30} {current_price:>18.2f} 元 │")
    print(f"│  {'买入阈值':<30} {buy_threshold:>18.2f} 元 ({margin_buy:.0%}) │")
    print(f"│  {'卖出阈值':<30} {sell_threshold:>18.2f} 元 ({margin_sell:.0%}) │")
    print(f"│ {'':^76} │")
    print(f"│  {signal_emoji} {'交易信号':<28} {signal:>18} │")
    print(f"│  {'决策理由':<30} {reason:>18} │")
    print(f"│ {'':^76} │")
    print(f"└─{'-' * 78}─┘")


def main():
    parser = argparse.ArgumentParser(
        description="MDVAES估值策略单次回测脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python scripts/test_mdvaes_single_backtest.py 600941.SS 2024-01-02
    python scripts/test_mdvaes_single_backtest.py 000001.SZ 2024-06-15 --forecast-years 3 --peg-base 0.8
    python scripts/test_mdvaes_single_backtest.py 600519.SH 2024-01-02 --margin-buy 0.7 --margin-sell 1.3
        """
    )

    parser.add_argument("symbol", help="股票代码 (如 600941.SS 或 000001.SZ)")
    parser.add_argument("date", help="计算日期 (格式: YYYY-MM-DD)")
    parser.add_argument("--forecast-years", type=int, default=5,
                        help="EPS预测年数 (默认: 5)")
    parser.add_argument("--peg-base", type=float, default=1.0,
                        help="PEG基数 (默认: 1.0)")
    parser.add_argument("--risk-adjustment", type=float, default=0.1,
                        help="风险调整幅度 (默认: 0.1)")
    parser.add_argument("--margin-buy", type=float, default=0.8,
                        help="买入安全边际 (默认: 0.8, 即价格低于估值80%%时买入)")
    parser.add_argument("--margin-sell", type=float, default=1.2,
                        help="卖出安全边际 (默认: 1.2, 即价格高于估值120%%时卖出)")

    args = parser.parse_args()

    # 验证日期格式
    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print("❌ 日期格式错误，请使用 YYYY-MM-DD 格式")
        return 1

    # 验证参数范围
    if not 1 <= args.forecast_years <= 10:
        print("❌ EPS预测年数必须在 1-10 之间")
        return 1

    if not 0.5 <= args.peg_base <= 2.0:
        print("❌ PEG基数必须在 0.5-2.0 之间")
        return 1

    if not 0 <= args.risk_adjustment <= 0.3:
        print("❌ 风险调整幅度必须在 0-0.3 之间")
        return 1

    if not 0.5 <= args.margin_buy <= 0.95:
        print("❌ 买入安全边际必须在 0.5-0.95 之间")
        return 1

    if not 1.05 <= args.margin_sell <= 2.0:
        print("❌ 卖出安全边际必须在 1.05-2.0 之间")
        return 1

    # 运行回测
    try:
        run_single_backtest(
            symbol=args.symbol,
            calculation_date=args.date,
            forecast_years=args.forecast_years,
            peg_base=args.peg_base,
            risk_adjustment=args.risk_adjustment,
            margin_buy=args.margin_buy,
            margin_sell=args.margin_sell
        )
        return 0

    except Exception as e:
        import traceback
        print(f"\n❌ 回测执行失败: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
