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


def extract_symbol(code: str) -> str:
    """从股票代码中提取 symbol（纯数字部分）

    支持格式：
    - ts_code: "600519.SH", "000001.SZ" -> "600519", "000001"
    - symbol: "600519", "000001" -> "600519", "000001"

    stock_daily_quotes 表使用 symbol 字段存储
    """
    if '.' in code:
        # "600519.SH" -> "600519"
        return code.split('.')[0]
    return code


def get_current_price(db, symbol: str, calculation_date: str) -> float:
    """获取当前价格

    从 MongoDB stock_daily_quotes 表获取价格数据。
    表使用 symbol 字段（如 "600519"），而不是 ts_code（如 "600519.SH"）。

    注意：使用 trade_date（交易日期），必须严格小于 calculation_date
    """
    calculation_date_yyyymmdd = calculation_date.replace("-", "")

    # 提取 symbol（纯数字代码）
    symbol_value = extract_symbol(symbol)

    # 从数据库查询价格
    print(f"    🔍 正在从数据库查询价格...")
    print(f"    📋 MongoDB 请求参数:")
    print(f"       - 计算日期: {calculation_date} (YYYY-MM-DD)")
    print(f"       - 查询截止日期: < {calculation_date_yyyymmdd} (YYYYMMDD)")
    print(f"       - 原始股票代码: {symbol}")
    print(f"       - 提取 symbol: {symbol_value}")

    try:
        # 构建查询条件 - 只使用 symbol 字段
        match_condition = {
            "symbol": symbol_value,
            "trade_date": {"$lt": calculation_date_yyyymmdd}
        }

        pipeline = [
            {"$match": match_condition},
            {"$sort": {"trade_date": -1}},
            {"$limit": 1},
            {"$project": {"close": 1, "_id": 0}}
        ]

        print(f"\n    📋 MongoDB 查询详情:")
        print(f"       - 查询字段: symbol")
        print(f"       - 查询值: {symbol_value}")
        print(f"       - 匹配条件: {match_condition}")
        print(f"       - 排序: {{'trade_date': -1}}")
        print(f"       - 聚合管道: {pipeline}")

        result = list(db.stock_daily_quotes.aggregate(pipeline))

        print(f"\n       - 返回结果数量: {len(result)}")
        if result:
            print(f"       - 结果内容: {result[0]}")

        if result and "close" in result[0]:
            print(f"    ✅ 查询成功: symbol={symbol_value} → 收盘价={result[0]['close']:.2f}")
            return float(result[0]["close"])

        # 如果没有查询到结果
        print(f"    ⚠️ 数据库中未找到 symbol={symbol_value} 在 {calculation_date} 之前的价格数据")

    except Exception as e:
        error_msg = str(e)
        if "MaxTimeMSExpired" in error_msg or "time limit" in error_msg:
            print(f"    ⏱️ symbol={symbol_value} 查询超时")
        else:
            print(f"    ⚠️ 查询 symbol={symbol_value} 失败: {e}")

    # 如果数据库查询失败，尝试 Tushare API 作为降级方案
    from app.core.config import settings
    if settings.TUSHARE_TOKEN:
        print(f"    ⚠️ 数据库查询失败，尝试从 Tushare API 获取...")
        try:
            import tushare as ts
            from datetime import datetime, timedelta

            pro = ts.pro_api(settings.TUSHARE_TOKEN)

            # 计算查询日期范围（向前推30天，确保能找到交易日）
            calc_dt = datetime.strptime(calculation_date, "%Y-%m-%d")
            start_date = (calc_dt - timedelta(days=30)).strftime("%Y%m%d")
            end_date = calculation_date_yyyymmdd

            # Tushare API 需要 ts_code 格式
            ts_code = symbol if '.' in symbol else f"{symbol}.SH" if symbol.startswith(('60', '68', '90')) else f"{symbol}.SZ"

            print(f"       - Tushare 查询代码: {ts_code}")

            df = pro.daily(
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date
            )

            if not df.empty and 'close' in df.columns:
                latest = df.iloc[-1]
                print(f"    ✅ 从 Tushare API 获取价格: {latest['close']:.2f}")
                return float(latest['close'])

        except Exception as e:
            print(f"    ⚠️ Tushare API 调用失败: {e}")

    # 如果所有尝试都失败，抛出错误（让用户手动输入）
    raise ValueError(f"无法获取 {symbol} 在 {calculation_date} 之前的价格数据")


def run_single_backtest(
    symbol: str,
    calculation_date: str,
    forecast_years: int,
    peg_base: float,
    risk_adjustment: float,
    margin_buy: float,
    margin_sell: float,
    peg_weight: float = None,
    pe_weight: float = None,
    pb_weight: float = None,
    dcf_weight: float = None
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

    # 处理权重参数
    if peg_weight is not None or pe_weight is not None or pb_weight is not None or dcf_weight is not None:
        # 用户传入了权重参数
        peg_weight = peg_weight if peg_weight is not None else 0.4
        pe_weight = pe_weight if pe_weight is not None else 0.3
        pb_weight = pb_weight if pb_weight is not None else 0.15
        dcf_weight = dcf_weight if dcf_weight is not None else 0.15

        # 验证权重总和
        total_weight = peg_weight + pe_weight + pb_weight + dcf_weight
        if abs(total_weight - 1.0) > 0.001:
            print(f"\n⚠️ 警告: 权重总和为 {total_weight:.3f}，不等于 1.0，将自动归一化处理")
            # 归一化处理
            peg_weight = peg_weight / total_weight
            pe_weight = pe_weight / total_weight
            pb_weight = pb_weight / total_weight
            dcf_weight = dcf_weight / total_weight
            print(f"   归一化后权重: PEG={peg_weight:.3f}, PE={pe_weight:.3f}, PB={pb_weight:.3f}, DCF={dcf_weight:.3f}")

        custom_anchor_weight = {
            "peg": peg_weight,
            "pe_historical": pe_weight,
            "pb": pb_weight,
            "dcf": dcf_weight
        }
    else:
        custom_anchor_weight = None

    # 初始化服务
    data_reader = MDVAESDataReader()
    growth_calculator = GrowthCalculator()
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

    # 验证日期格式
    if not calculation_date:
        print(f"\n⚠️ 计算日期为空，使用默认风险指标")
        risk_metrics = RiskMetrics(
            debt_to_assets=0.5,
            current_ratio=1.5,
            quick_ratio=1.2,
            cashflow_to_income=1.1,
            risk_level=RiskLevel.MEDIUM
        )
    else:
        # 尝试从数据库获取真实财务比率（使用同步查询）
        try:
            calculation_date_yyyymmdd = calculation_date.replace("-", "")

            # 先检查集合中是否有该股票的任何财务数据
            print(f"    🔍 正在从数据库查询财务比率...")
            print(f"    📋 MongoDB 请求参数:")
            print(f"       - 计算日期: {calculation_date} (YYYY-MM-DD)")
            print(f"       - 查询截止日期: < {calculation_date_yyyymmdd} (YYYYMMDD)")
            print(f"       - 查询股票代码: {symbol}")

            # 检查集合中是否有该股票的数据
            total_count = db.mdvaes_financial_ratios.count_documents({"ts_code": symbol})
            print(f"       - 数据库中该股票的总记录数: {total_count}")

            ratios_data = db.mdvaes_financial_ratios.find_one({
                "ts_code": symbol,
                "ann_date": {"$lt": calculation_date_yyyymmdd}
            }, sort=[("ann_date", -1)])

            print(f"       - 查询返回结果: {'找到' if ratios_data else '未找到'}")

            if ratios_data:
                ratios = {
                    "debt_to_assets": ratios_data.get("debt_to_assets"),
                    "current_ratio": ratios_data.get("current_ratio"),
                    "quick_ratio": ratios_data.get("quick_ratio"),
                    "roe": ratios_data.get("roe"),
                    "roa": ratios_data.get("roa")
                }
                print(f"\n✅ 使用真实财务数据:")
                ann_date_val = ratios_data.get('ann_date')
                print(f"   公告日期: {ann_date_val if ann_date_val else 'N/A'}")
                # 数据库中的百分比数值直接显示即可（如14.14表示14.14%）
                debt_val = ratios.get('debt_to_assets')
                current_val = ratios.get('current_ratio')
                quick_val = ratios.get('quick_ratio')
                roe_val = ratios.get('roe')
                roa_val = ratios.get('roa')
                print(f"   资产负债率: {debt_val if debt_val is not None else 50:.2f}%")
                print(f"   流动比率: {current_val if current_val is not None else 1.5:.2f}")
                print(f"   速动比率: {quick_val if quick_val is not None else 1.2:.2f}")
                print(f"   ROE: {roe_val if roe_val is not None else 10:.2f}%")
                print(f"   ROA: {roa_val if roa_val is not None else 5:.2f}%")

                # 根据财务数据评估风险等级（将百分比转换为小数）
                debt_ratio_pct = debt_val if debt_val is not None else 50
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
                    current_ratio=current_val if current_val is not None else 1.5,
                    quick_ratio=quick_val if quick_val is not None else 1.2,
                    cashflow_to_income=1.1,
                    risk_level=risk_level
                )
            else:
                # 提供更详细的诊断信息
                print(f"\n    ⚠️ 数据库中未找到符合条件的财务数据")
                if total_count > 0:
                    # 有该股票的数据，但不符合日期条件
                    latest = db.mdvaes_financial_ratios.find_one(
                        {"ts_code": symbol},
                        sort=[("ann_date", -1)]
                    )
                    if latest:
                        latest_ann_date = latest.get('ann_date')
                        print(f"       - 该股票最新财务数据公告日期: {latest_ann_date if latest_ann_date else 'N/A'}")
                        print(f"       - 计算日期: {calculation_date_yyyymmdd}")
                        print(f"       - 差异: 最新公告日期不早于计算日期")
                else:
                    print(f"       - 数据库中完全没有该股票的财务数据")
                    print(f"       - 💡 提示：请先运行批量同步财务数据")
                    print(f"          python -m app.worker.mdvaes_batch_sync --start-date 2020-01-01 --end-date 2024-12-31 --tables financial_ratios")
                raise ValueError("无财务数据")

        except Exception as e:
            import traceback
            print(f"\n⚠️ 未获取到真实财务数据，使用默认值")
            print(f"   错误原因: {e}")
            print(f"   详细堆栈:\n{traceback.format_exc()}")
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

    # ==================== 步骤5.5: 获取每股自由现金流 ====================
    print_section("步骤5.5: 获取每股自由现金流 (FCFPS)")

    try:
        current_fcfps = data_reader.get_current_fcfps_sync(symbol, calculation_date)

        if current_fcfps is not None:
            print(f"\n✅ 每股自由现金流 (FCFPS): {current_fcfps:.4f} 元")
            print(f"📊 FCFPS/EPS 比率: {current_fcfps / current_eps:.2%}")
        else:
            print(f"\n⚠️ 未找到 FCFPS 数据，将使用 EPS 进行 DCF 计算")
            current_fcfps = None

    except Exception as e:
        print(f"\n⚠️ 获取 FCFPS 失败: {e}，将使用 EPS 进行 DCF 计算")
        current_fcfps = None

    # ==================== 步骤6: 构建MDVAES参数 ====================
    print_section("步骤6: 构建MDVAES参数")

    # 构建参数，如果用户传入了权重则使用自定义权重
    params_kwargs = {
        "forecast_years": forecast_years,
        "peg_base": peg_base,
        "risk_adjustment": risk_adjustment,
        "signal_mode": "safety_margin",
        "safety_margin_buy": margin_buy,
        "safety_margin_sell": margin_sell
    }

    if custom_anchor_weight is not None:
        params_kwargs["anchor_weight"] = custom_anchor_weight
        print(f"\n📋 使用自定义权重配置:")
        print(f"   PEG权重: {custom_anchor_weight['peg']:.2%}")
        print(f"   PE权重: {custom_anchor_weight['pe_historical']:.2%}")
        print(f"   PB权重: {custom_anchor_weight['pb']:.2%}")
        print(f"   DCF权重: {custom_anchor_weight['dcf']:.2%}")

    params = MDVAESParams(**params_kwargs)
    params.validate()

    if custom_anchor_weight is None:
        print(f"\n使用默认权重配置:")

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
    # 修正公式：使用增长率百分比形式（如 4.47% → 4.47）而非小数形式（0.0447）
    peg_valuation = current_eps * (growth_metrics.growth_rate * 100) * params.peg_base * interest_adjustment
    print(f"公式: PEG估值 = EPS × 增长率(%) × PEG基数 × (1 - 利率敏感度 × 国债利率)")
    print(f"     = {current_eps:.4f} × {growth_metrics.growth_rate * 100:.2f} × {params.peg_base} × (1 - {params.peg_interest_sensitivity} × {bond_rate:.2%})")
    print(f"     = {current_eps:.4f} × {growth_metrics.growth_rate * 100:.2f} × {params.peg_base} × {interest_adjustment:.4f}")
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

    # 7.4 DCF估值 (使用 ValuationCalculator)
    print_subsection("7.4 DCF估值")

    # 根据是否有 FCFPS 决定计算方式
    if current_fcfps is not None and current_fcfps > 0:
        print(f"🎯 使用每股自由现金流 (FCFPS) 进行 DCF 估值")
        dcf_base = current_fcfps
        dcf_base_name = "FCFPS"
        # 使用 ValuationCalculator 的 FCFPS DCF 方法
        dcf_valuation = ValuationCalculator._calc_dcf_valuation_fcfps(
            fcfps=current_fcfps,
            growth_rate=growth_metrics.growth_rate,
            discount_rate=bond_rate,
            params=params
        )
    else:
        print(f"⚠️ 无 FCFPS 数据，使用每股收益 (EPS) 进行 DCF 估值")
        dcf_base = current_eps
        dcf_base_name = "EPS"
        # 使用 ValuationCalculator 的 EPS DCF 方法
        dcf_valuation = ValuationCalculator._calc_dcf_valuation(
            eps=current_eps,
            growth_rate=growth_metrics.growth_rate,
            discount_rate=bond_rate,
            params=params
        )

    # 打印详细计算过程（与 ValuationCalculator 保持一致）
    terminal_growth = 0.03
    required_return = bond_rate + 0.05
    adj_growth_rate = min(growth_metrics.growth_rate, required_return - 0.01)

    print(f"终值增长率: {terminal_growth:.2%}")
    print(f"必要回报率: 无风险利率({bond_rate:.2%}) + 5% = {required_return:.2%}")
    print(f"调整后增长率: {adj_growth_rate:.2%}")
    print(f"基础数据: {dcf_base_name} = {dcf_base:.4f} 元")

    forecast_values = []
    print(f"\n未来{forecast_years}年{dcf_base_name}预测及折现:")
    print(f"{'年份':<8} {'预测' + dcf_base_name:<15} {'折现因子':<15} {'折现值':<15}")
    print("-" * 50)

    for i in range(1, forecast_years + 1):
        forecast_value = dcf_base * ((1 + adj_growth_rate) ** i)
        discount_factor = (1 + required_return) ** i
        discounted_value = forecast_value / discount_factor
        forecast_values.append(discounted_value)
        print(f"第{i}年    {forecast_value:<15.4f} {discount_factor:<15.4f} {discounted_value:<15.4f}")

    # 终值
    terminal_base = dcf_base * ((1 + adj_growth_rate) ** forecast_years)
    terminal_value = terminal_base * (1 + terminal_growth) / (required_return - terminal_growth)
    discounted_terminal = terminal_value / ((1 + required_return) ** forecast_years)
    print(f"终值      -              -              {discounted_terminal:<15.4f}")

    print(f"\nDCF估值 = Σ折现值 + 折现终值 = {dcf_valuation:.2f} 元")
    print(f"         (使用 ValuationCalculator 计算结果)")

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
    # 基本用法（使用默认权重）
    python scripts/test_mdvaes_single_backtest.py 600941.SS 2024-01-02
    python scripts/test_mdvaes_single_backtest.py 000001.SZ 2024-06-15 --forecast-years 3 --peg-base 0.8

    # 自定义安全边际
    python scripts/test_mdvaes_single_backtest.py 600519.SH 2024-01-02 --margin-buy 0.7 --margin-sell 1.3

    # 自定义多锚点权重（必须同时指定四个权重，总和为1.0）
    python scripts/test_mdvaes_single_backtest.py 000001.SZ 2024-06-15 --peg-weight 0.5 --pe-weight 0.2 --pb-weight 0.15 --dcf-weight 0.15
    python scripts/test_mdvaes_single_backtest.py 600519.SH 2024-01-02 --peg-weight 0.3 --pe-weight 0.3 --pb-weight 0.2 --dcf-weight 0.2 --margin-buy 0.75

    # 默认权重配置: PEG=40%%, PE=30%%, PB=15%%, DCF=15%%
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

    # 多锚点权重参数
    parser.add_argument("--peg-weight", type=float, default=None,
                        help="PEG估值权重 (默认: 0.4，与 --pe-weight --pb-weight --dcf-weight 之和必须为1.0)")
    parser.add_argument("--pe-weight", type=float, default=None,
                        help="PE估值权重 (默认: 0.3，与 --peg-weight --pb-weight --dcf-weight 之和必须为1.0)")
    parser.add_argument("--pb-weight", type=float, default=None,
                        help="PB估值权重 (默认: 0.15，与 --peg-weight --pe-weight --dcf-weight 之和必须为1.0)")
    parser.add_argument("--dcf-weight", type=float, default=None,
                        help="DCF估值权重 (默认: 0.15，与 --peg-weight --pe-weight --pb-weight 之和必须为1.0)")

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

    # 验证权重参数（如果提供了的话）
    weight_args = [args.peg_weight, args.pe_weight, args.pb_weight, args.dcf_weight]
    if any(w is not None for w in weight_args):
        # 至少有一个权重参数被传入
        # 检查是否所有权重参数都传入了（不允许部分传入）
        if not all(w is not None for w in weight_args):
            print("❌ 权重参数必须全部指定或全部不指定")
            print("   请同时提供 --peg-weight, --pe-weight, --pb-weight, --dcf-weight")
            return 1

        # 检查权重范围
        for name, value in [("PEG", args.peg_weight), ("PE", args.pe_weight),
                            ("PB", args.pb_weight), ("DCF", args.dcf_weight)]:
            if value < 0 or value > 1:
                print(f"❌ {name}权重必须在 0.0-1.0 之间")
                return 1

        # 检查权重总和
        total_weight = args.peg_weight + args.pe_weight + args.pb_weight + args.dcf_weight
        if abs(total_weight - 1.0) > 0.01:
            print(f"⚠️ 警告: 权重总和为 {total_weight:.3f}，不等于 1.0")
            print(f"   将自动归一化处理")

    # 运行回测
    try:
        run_single_backtest(
            symbol=args.symbol,
            calculation_date=args.date,
            forecast_years=args.forecast_years,
            peg_base=args.peg_base,
            risk_adjustment=args.risk_adjustment,
            margin_buy=args.margin_buy,
            margin_sell=args.margin_sell,
            peg_weight=args.peg_weight,
            pe_weight=args.pe_weight,
            pb_weight=args.pb_weight,
            dcf_weight=args.dcf_weight
        )
        return 0

    except Exception as e:
        import traceback
        print(f"\n❌ 回测执行失败: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
