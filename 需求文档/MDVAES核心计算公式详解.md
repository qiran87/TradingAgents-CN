# MDVAES 核心计算公式详解

> **文档版本**: v1.0
> **更新日期**: 2026-02-20
> **作者**: Claude Code
> **项目**: TradingAgents-CN

---

## 📚 目录

1. [EPS 预测](#1-eps-预测)
2. [增长指标计算](#2-增长指标计算)
3. [风险评估](#3-风险评估)
4. [估值结果计算](#4-估值结果计算)
5. [交易信号生成](#5-交易信号生成)
6. [批量同步逻辑](#6-批量同步逻辑)

---

## 1. EPS 预测

### 1.1 来源一：分析师预测

**优先级**: 最高
**数据表**: `mdvaes_analyst_forecasts`
**接口**: Tushare `report_rc`

**实现逻辑**:
```
1. 从 mdvaes_analyst_forecasts 表查询
2. 筛选条件: ts_code + report_date <= 计算日期
3. 按年份去重，取最新预测
```

**代码位置**: `app/services/mdvaes_data_reader.py:39-86`

```python
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
    """
    current_year = datetime.strptime(calculation_date, "%Y-%m-%d").year
    calculation_date_yyyymmdd = calculation_date.replace("-", "")

    forecasts = await db.mdvaes_analyst_forecasts.find({
        "ts_code": symbol,
        "report_date": {"$lt": calculation_date_yyyymmdd}
    }).sort("report_date", -1).to_list(None)

    if not forecasts:
        return None

    # 按年份去重，取最新预测（从 quarter 字段提取年份）
    latest_by_year = {}
    for f in forecasts:
        year = self._extract_year_from_quarter(f.get("quarter", ""))
        if year and year >= current_year and year <= current_year + forecast_years:
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
```

---

### 1.2 来源二：历史 EPS 外推

**优先级**: 备选（当分析师预测不足时使用）
**数据表**: `mdvaes_eps_history`

#### 核心公式

**公式 1.1: 历史增长率计算**

```
                    ┌─────────────────┐
                    │  latest_eps     │
                    │  ────────────   │     ^(1/(n_years - 1))
                    │  oldest_eps      │
  growth_rate =   └─────────────────┘                              - 1
```

**其中**:
- `latest_eps`: 最新年度 EPS（历史数据的第一条，按 end_date 倒序）
- `oldest_eps`: 最旧年度 EPS（历史数据的最后一条）
- `n_years`: 历史数据年份数

**公式 1.2: 未来 EPS 预测**

```
  EPS_year_i = latest_eps × (1 + growth_rate)^i
```

**其中**:
- `year_i = base_year + i` (i = 1, 2, ..., forecast_years)
- `base_year`: 最新 EPS 的年份

#### 代码位置

**文件**: `app/services/mdvaes_data_reader.py:97-122`

```python
def _extrapolate_eps(self, historical_eps: List[dict], forecast_years: int) -> List[EPSForecast]:
    """基于历史 EPS 外推预测"""
    latest_eps = historical_eps[0]["eps"]       # 最新 EPS (第一条)
    oldest_eps = historical_eps[-1]["eps"]       # 最旧 EPS (最后一条)
    n_years = len(historical_eps)

    # 核心公式: 历史增长率
    growth_rate = (latest_eps / oldest_eps) ** (1 / (n_years - 1)) - 1 if n_years > 1 else 0.1

    # 提取基准年份
    end_date_str = historical_eps[0]["end_date"]
    if "-" in end_date_str:
        base_year = datetime.strptime(end_date_str, "%Y-%m-%d").year
    else:
        base_year = int(end_date_str[:4])

    # 核心公式: 未来 EPS 预测
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
```

#### 计算示例

**平安银行 (000001.SZ)** 示例：

```
历史数据:
  2020年: 1.40 元
  2021年: 1.73 元
  2022年: 2.20 元
  2023年: 2.25 元 (最新)

增长率计算:
  growth_rate = (2.25 / 1.40) ^ (1/3) - 1 = 0.1713 = 17.13%

未来预测:
  2024年: 2.25 × (1.1713)^1 = 2.64 元
  2025年: 2.25 × (1.1713)^2 = 3.09 元
  2026年: 2.25 × (1.1713)^3 = 3.62 元
  2027年: 2.25 × (1.1713)^4 = 4.24 元
  2028年: 2.25 × (1.1713)^5 = 4.96 元
```

---

## 2. 增长指标计算

### 2.1 对数最小二乘法回归

**核心思想**: 对 EPS 取对数后进行线性回归，得到稳定的增长率

#### 核心公式

**公式 2.1: 对数转换**

```
  log_eps = ln(EPS_values)
```

**公式 2.2: 线性回归**

```
  log_eps = slope × year + intercept
```

**公式 2.3: 增长率（基于斜率）**

```
  growth_rate = exp(slope) - 1
```

#### 代码位置

**文件**: `app/services/growth_calculator.py:12-51`

```python
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

    # 核心公式: 对数最小二乘法回归
    log_eps = np.log(eps_values)
    coeffs = np.polyfit(years, log_eps, 1)  # 线性回归: [slope, intercept]
    slope = coeffs[0]

    # 核心公式: 增长率
    growth_rate = np.exp(slope) - 1

    # ... 其他计算
    return GrowthMetrics(...)
```

---

### 2.2 R² (拟合优度)

**含义**: 衡量回归模型对数据的拟合程度，取值范围 [0, 1]

#### 核心公式

```
  SS_res = Σ(ln(EPS)_actual - ln(EPS)_predicted)²      # 残差平方和
  SS_tot = Σ(ln(EPS)_actual - mean(ln(EPS)))²         # 总平方和

                SS_res
  R² = 1 - ─────────
                SS_tot
```

#### 代码位置

**文件**: `app/services/growth_calculator.py:37-41`

```python
# 计算 R²
log_eps_pred = np.polyval(coeffs, years)           # 预测值
ss_res = np.sum((log_eps - log_eps_pred) ** 2)      # 残差平方和
ss_tot = np.sum((log_eps - np.mean(log_eps)) ** 2)  # 总平方和
r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
```

---

### 2.3 CAGR (复合年均增长率)

**含义**: 衡量投资的年均复合增长率

#### 核心公式

```
  ┌─────────────────────────┐
  │       EPS_final           │     ^(1/n)
  │   ───────────────────    │
  │       EPS_initial         │
  CAGR =                           - 1
  └─────────────────────────┘
```

**其中**: `n = 最后年份 - 第一年份`

#### 代码位置

**文件**: `app/services/growth_calculator.py:43-48`

```python
# 计算 CAGR (复合年均增长率)
n_years = years[-1] - years[0]
if n_years > 0:
    cagr = (eps_values[-1] / eps_values[0]) ** (1 / n_years) - 1
else:
    cagr = 0
```

---

### 2.4 增长质量评分 & 趋势稳定性

#### 核心公式

**增长质量评分**:
```
  growth_quality_score = min(R², 0.95)
```

**趋势稳定性**:
```
  R² ≥ 0.8    → STABLE (稳定增长)
  0.5 ≤ R² < 0.8  → VOLATILE (波动增长)
  R² < 0.5     → DECLINING (增长不稳定)
```

#### 代码位置

**文件**: `app/services/growth_calculator.py:53-62`

```python
# 增长质量评分（基于 R² 和增长一致性）
growth_quality_score = min(r_squared, 0.95)

# 趋势稳定性
if r_squared >= 0.8:
    trend_stability = TrendStability.STABLE
elif r_squared >= 0.5:
    trend_stability = TrendStability.VOLATILE
else:
    trend_stability = TrendStability.DECLINING
```

---

## 3. 风险评估

### 3.1 风险指标数据来源

**数据表**: `mdvaes_financial_ratios`
**接口**: Tushare `fina_indicator`

#### 指标说明

| 指标 | 公式 | 说明 |
|------|------|------|
| **debt_to_assets** | 总负债 / 总资产 × 100% | 资产负债率，越高风险越大 |
| **current_ratio** | 流动资产 / 流动负债 | 流动比率，>2 较安全 |
| **quick_ratio** | (流动资产 - 存货) / 流动负债 | 速动比率，>1 较安全 |
| **roe** | 净利润 / 股东权益 × 100% | 净资产收益率 |
| **roa** | 净利润 / 总资产 × 100% | 总资产收益率 |
| **cashflow_to_income** | 经营现金流 / 净利润 | 现金流/利润比率 (当前使用默认值 1.1) |

### 3.2 风险等级

**当前实现**: 使用固定值 `MEDIUM` (中等风险)

#### 风险调整系数

```
  LOW:    0.5
  MEDIUM: 1.0    ← 当前使用
  HIGH:   1.5
```

#### 代码位置

**文件**: `app/services/mdvaes_service.py:75-96`

```python
# 6. 获取财务比率数据
ratios_data = await self.data_reader.get_financial_ratios(symbol, calculation_date)

# 7. 构建风险指标
if ratios_data:
    # 使用数据库中的实际数据
    risk_metrics = RiskMetrics(
        debt_to_assets=ratios_data.get("debt_to_assets", 0.5),
        current_ratio=ratios_data.get("current_ratio", 1.5),
        quick_ratio=ratios_data.get("quick_ratio", 1.2),
        cashflow_to_income=1.1,  # 暂时保持默认值
        risk_level=RiskLevel.MEDIUM
    )
else:
    # 使用默认值
    risk_metrics = RiskMetrics(
        debt_to_assets=0.5,
        current_ratio=1.5,
        quick_ratio=1.2,
        cashflow_to_income=1.1,
        risk_level=RiskLevel.MEDIUM
    )
```

---

## 4. 估值结果计算

### 4.1 多锚点估值框架

**核心思想**: 使用 4 种估值方法加权平均，避免单一方法偏差

#### 估值方法权重

```
  PEG (40%)      ← 成长型公司权重最高
  PE 历史 (30%)   ← 市场认可度
  PB (15%)        ← 资产估值
  DCF (15%)       ← 内在价值
  ────────────────
  总和 = 100%
```

#### 代码位置

**文件**: `app/domain/mdvaes.py:83-89`

```python
@dataclass(frozen=True)
class MDVAESParams:
    """MDVAES 参数（值对象）"""
    # 多锚点权重
    anchor_weight: Dict[str, float] = field(default_factory=lambda: {
        "peg": 0.4,
        "pe_historical": 0.3,
        "pb": 0.15,
        "dcf": 0.15
    })
```

---

### 4.2 PEG 估值

#### 核心公式

```
  interest_adjustment = 1 - peg_interest_sensitivity × bond_rate

  peg_valuation = EPS × growth_rate × peg_base × interest_adjustment
```

**参数说明**:
- `peg_interest_sensitivity = 0.5`: 利率敏感度
- `peg_base = 1.0`: PEG 基准倍数
- `bond_rate`: 10年期国债收益率

#### 代码位置

**文件**: `app/services/valuation_calculator.py:78-83`

```python
@staticmethod
def _calc_peg_valuation(eps: float, growth_metrics: GrowthMetrics, bond_rate: float, params: MDVAESParams) -> float:
    """计算 PEG 估值"""
    interest_adjustment = 1 - params.peg_interest_sensitivity * bond_rate
    peg_valuation = eps * growth_metrics.growth_rate * params.peg_base * interest_adjustment
    return max(peg_valuation, 0)
```

---

### 4.3 历史 PE 估值

#### 核心公式

```
  growth_adjustment = 1 + growth_rate

  pe_historical_valuation = EPS × current_PE × growth_adjustment × 0.8
```

**说明**:
- 增长调整: 增长率越高，给予越高的估值倍数
- 系数 0.8: 保守系数

#### 代码位置

**文件**: `app/services/valuation_calculator.py:85-90`

```python
@staticmethod
def _calc_pe_historical_valuation(eps: float, current_pe: float, growth_metrics: GrowthMetrics) -> float:
    """基于历史 PE 估值"""
    growth_adjustment = 1 + growth_metrics.growth_rate
    pe_historical_valuation = eps * current_pe * growth_adjustment * 0.8
    return max(pe_historical_valuation, 0)
```

---

### 4.4 PB 估值 (简化版)

#### 核心公式

```
  pb_valuation = EPS × 1.5
```

**说明**: 使用固定 1.5 倍市净率作为简化估值

#### 代码位置

**文件**: `app/services/valuation_calculator.py:30-31`

```python
# 3. PB 估值（简化版，使用固定倍数）
pb_valuation = eps * 1.5
```

---

### 4.5 DCF 估值 (简化版)

#### 核心公式

**必要回报率**:
```
  required_return = bond_rate + 0.05  # 无风险利率 + 风险溢价
```

**预测期现值**:
```
                   EPS × (1 + growth_rate)^i
  PV_i = ────────────────────────────────
          (1 + required_return)^i
```

**终值现值**:
```
  terminal_growth = 0.03  # 永续增长率

                        EPS × (1 + g)^n × (1 + terminal_growth)
  TV = ─────────────────────────────────────────────────
                      (required_return - terminal_growth)

  PV_terminal = TV / (1 + required_return)^n
```

**总估值**:
```
  dcf_valuation = Σ(PV_i) + PV_terminal
```

#### 代码位置

**文件**: `app/services/valuation_calculator.py:92-112`

```python
@staticmethod
def _calc_dcf_valuation(eps: float, growth_rate: float, discount_rate: float, params: MDVAESParams) -> float:
    """简化 DCF 估值"""
    terminal_growth = 0.03
    required_return = discount_rate + 0.05

    if growth_rate >= required_return:
        growth_rate = required_return - 0.01

    # 预测期现值
    forecast_values = []
    for i in range(1, params.forecast_years + 1):
        forecast_eps = eps * ((1 + growth_rate) ** i)
        discounted_value = forecast_eps / ((1 + required_return) ** i)
        forecast_values.append(discounted_value)

    # 终值现值
    terminal_eps = eps * ((1 + growth_rate) ** params.forecast_years)
    terminal_value = terminal_eps * (1 + terminal_growth) / (required_return - terminal_growth)
    discounted_terminal = terminal_value / ((1 + required_return) ** params.forecast_years)

    dcf_valuation = sum(forecast_values) + discounted_terminal
    return max(dcf_valuation, 0)
```

---

### 4.6 多锚点加权

#### 核心公式

```
  weighted_valuation =
      0.4 × peg_valuation +
      0.3 × pe_historical_valuation +
      0.15 × pb_valuation +
      0.15 × dcf_valuation
```

#### 代码位置

**文件**: `app/services/valuation_calculator.py:38-44`

```python
# 5. 多锚点加权
weighted_valuation = (
    params.anchor_weight["peg"] * peg_valuation +
    params.anchor_weight["pe_historical"] * pe_historical_valuation +
    params.anchor_weight["pb"] * pb_valuation +
    params.anchor_weight["dcf"] * dcf_valuation
)
```

---

### 4.7 风险调整

#### 核心公式

```
  风险调整系数:
    LOW:    0.5
    MEDIUM: 1.0
    HIGH:   1.5

  adjusted_valuation = weighted_valuation × (1 - risk_adjustment × risk_factor)
```

**参数**:
- `risk_adjustment = 0.1`: 风险调整幅度
- `risk_factor`: 风险等级对应的系数

#### 代码位置

**文件**: `app/services/valuation_calculator.py:46-50`

```python
# 6. 风险调整
risk_adjustment_factor = ValuationCalculator._get_risk_adjustment_factor(
    risk_metrics.risk_level
)
adjusted_valuation = weighted_valuation * (1 - params.risk_adjustment * risk_adjustment_factor)
```

---

### 4.8 估值区间

#### 核心公式

**置信度计算**:
```
  risk_penalty:
    LOW:    0.0
    MEDIUM: 0.1
    HIGH:   0.2

  confidence = max(R² - risk_penalty, 0.3)
  confidence = min(confidence, 0.95)
```

**估值区间**:
```
  margin = adjusted_valuation × (1 - confidence) × 0.2

  lower_bound = adjusted_valuation - margin
  upper_bound = adjusted_valuation + margin
```

#### 代码位置

**文件**: `app/services/valuation_calculator.py:52-57, 120-127`

```python
# 7. 计算估值区间
confidence = ValuationCalculator._calc_confidence(growth_metrics, risk_metrics)
margin = adjusted_valuation * (1 - confidence) * 0.2

lower_bound = adjusted_valuation - margin
upper_bound = adjusted_valuation + margin
```

```python
@staticmethod
def _calc_confidence(growth_metrics: GrowthMetrics, risk_metrics: RiskMetrics) -> float:
    """计算估值置信度"""
    base_confidence = growth_metrics.r_squared
    risk_penalty = {"low": 0.0, "medium": 0.1, "high": 0.2}
    penalty = risk_penalty.get(risk_metrics.risk_level, 0.1)
    confidence = max(base_confidence - penalty, 0.3)
    return min(confidence, 0.95)
```

---

## 5. 交易信号生成

### 5.1 信号模式

**模式 1: valuation_range (估值区间)**

```
  如果 当前价格 < lower_bound → BUY
  如果 当前价格 > upper_bound → SELL
  其他情况 → HOLD
```

**模式 2: safety_margin (安全边际)**

```
  buy_threshold = intrinsic_value × safety_margin_buy    (默认 0.8)
  sell_threshold = intrinsic_value × safety_margin_sell  (默认 1.2)

  如果 当前价格 ≤ buy_threshold → BUY
  如果 当前价格 ≥ sell_threshold → SELL
  其他情况 → HOLD
```

### 5.2 代码位置

**文件**: `app/services/valuation_calculator.py:130-148`

```python
@staticmethod
def _generate_signal(intrinsic_value: float, lower_bound: float, upper_bound: float, params: MDVAESParams) -> SignalType:
    """生成交易信号"""
    if params.signal_mode == "valuation_range":
        if intrinsic_value < lower_bound:
            return SignalType.BUY
        elif intrinsic_value > upper_bound:
            return SignalType.SELL
        else:
            return SignalType.HOLD
    else:  # safety_margin
        buy_threshold = intrinsic_value * params.safety_margin_buy
        sell_threshold = intrinsic_value * params.safety_margin_sell

        if intrinsic_value <= buy_threshold:
            return SignalType.BUY
        elif intrinsic_value >= sell_threshold:
            return SignalType.SELL
        else:
            return SignalType.HOLD
```

---

## 6. 批量同步逻辑

### 6.1 同步策略

**目标**: 获取全部 A 股上市股票的财务数据

**策略**:
1. 先获取全部上市股票列表 (~16,000 只)
2. 按年度分批处理
3. 每批 100 只股票（避免 API 限制）
4. 使用 upsert 避免重复

### 6.2 执行流程

```
┌─────────────────────────────────────────────────────────────────┐
│ Step 1: 获取股票列表                                           │
│   pro.stock_basic(list_status='L')                             │
│   结果: ~16,000 只上市股票                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 2: 生成年份列表                                             │
│   years = [start_year, ..., end_year]                           │
│   例如: [2020, 2021, 2022, 2023]                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Step 3: 双重循环                                                   │
│   for year in years:                                              │
│       for i in range(0, len(stock_codes), 100):                  │
│           batch_codes = stock_codes[i:i+100]                     │
│           调用 API 获取这 100 只股票的数据                          │
└─────────────────────────────────────────────────────────────────┘
```

### 6.3 代码位置

**文件**: `app/services/mdvaes_data_sync_service.py:655-733`

```python
async def _batch_sync_financial_ratios(self, db, start_dt: datetime, end_dt: datetime):
    """批量同步财务比率数据

    策略：
    1. 先获取股票列表
    2. 分批查询（每次100只股票）避免 API 限制
    3. 使用 start_date/end_date 参数获取日期范围内的数据
    """
    synced = 0
    updated = 0
    skipped = 0

    # 1. 获取股票列表
    logger.info("  📋 获取股票列表...")
    stock_df = await asyncio.to_thread(
        self.pro.stock_basic,
        list_status='L',
        fields='ts_code,symbol,name'
    )

    if stock_df.empty:
        logger.error("  ❌ 无法获取股票列表")
        return {"synced": 0, "updated": 0, "skipped": 0}

    stock_codes = stock_df['ts_code'].tolist()
    logger.info(f"  ✅ 获取到 {len(stock_codes)} 只股票")

    # 2. 生成年份列表
    years = []
    current = start_dt
    while current.year <= end_dt.year:
        years.append(current.year)
        current = current.replace(year=current.year + 1, month=1, day=1)

    logger.info(f"  📅 计划同步 {len(years)} 个年份的财务比率数据")

    # 3. 按年份和股票批次同步
    batch_size = 100  # 每次查询100只股票

    for year in years:
        year_start = f"{year}0101"
        year_end = f"{year}1231"
        logger.info(f"  📡 获取 {year} 年的财务比率数据...")

        for i in range(0, len(stock_codes), batch_size):
            batch_codes = stock_codes[i:i + batch_size]
            ts_codes_str = ",".join(batch_codes)

            try:
                # 核心 API 调用: 传入 100 只股票的代码
                df = await asyncio.to_thread(
                    self.pro.fina_indicator,
                    ts_code=ts_codes_str,  # ← 关键: 逗号分隔的 100 个股票代码
                    start_date=year_start,
                    end_date=year_end,
                    fields="ts_code,ann_date,end_date,debt_to_assets,current_ratio,quick_ratio,roe,roa"
                )

                if df.empty:
                    continue

                logger.info(f"    📊 {year} 年 批次 {i//batch_size + 1}: 返回 {len(df)} 条记录")

                # 批量写入数据库
                from pymongo import UpdateOne
                operations = []
                for _, row in df.iterrows():
                    record = row.to_dict()
                    # 过滤掉 NaN 值
                    filtered_record = {k: v for k, v in record.items()
                                     if pd.notna(v) and k in ['ts_code', 'ann_date', 'end_date',
                                                               'debt_to_assets', 'current_ratio',
                                                               'quick_ratio', 'roe', 'roa']}
                    if 'ts_code' in filtered_record and 'end_date' in filtered_record:
                        operations.append(
                            UpdateOne(
                                {"ts_code": filtered_record["ts_code"], "end_date": filtered_record["end_date"]},
                                {"$set": {**filtered_record, "synced_at": datetime.now()}},
                                upsert=True  # ← 关键: 避免重复插入
                            )
                        )

                if operations:
                    result = await db.mdvaes_financial_ratios.bulk_write(operations, ordered=False)
                    synced += result.upserted_count
                    updated += result.modified_count
                    logger.info(f"    ✅ 新增 {result.upserted_count} 条, 更新 {result.modified_count} 条")

            except Exception as e:
                logger.error(f"    ❌ {year} 年 批次 {i//batch_size + 1} 同步失败: {e}")
                skipped += 1

    logger.info(f"  ✅ 财务比率同步完成: 新增 {synced} 条, 更新 {updated} 条, 跳过 {skipped} 个批次")
    return {"synced": synced, "updated": updated, "skipped": skipped}
```

### 6.4 执行示例

**假设**: 16,179 只股票，同步 2020-2023 年数据

```
总批次数 = ceil(16179 / 100) × 4 年 = 162 × 4 = 648 次 API 调用

执行过程:
├─ 2020年: 162 批次 (每批 100 只股票)
├─ 2021年: 162 批次
├─ 2022年: 162 批次
└─ 2023年: 162 批次

数据去重:
  唯一键: {ts_code, end_date}
  例如: 000001.SZ + 20231231 = 唯一标识
  相同数据重复调用会被更新而非插入
```

---

## 📊 完整计算示例

### 输入数据

```
股票: 平安银行 (000001.SZ)
日期: 2024-01-15

历史 EPS:
  2020: 1.40 元
  2021: 1.73 元
  2022: 2.20 元
  2023: 2.25 元

市场数据:
  当前 PE: 3.76
  10年期国债利率: 2.56%

财务比率:
  debt_to_assets: 91.55%
  roe: 10.24%
```

### 计算过程

#### Step 1: EPS 预测

```
增长率 = (2.25 / 1.40)^(1/3) - 1 = 17.13%

预测:
  2024: 2.25 × 1.1713^1 = 2.64 元
  2025: 2.25 × 1.1713^2 = 3.09 元
  2026: 2.25 × 1.1713^3 = 3.62 元
  2027: 2.25 × 1.1713^4 = 4.24 元
  2028: 2.25 × 1.1713^5 = 4.96 元
```

#### Step 2: 增长指标

```
对数回归: ln(EPS) = 0.158 × year
增长率: exp(0.158) - 1 = 17.13%
R²: 1.000 (完美拟合)
CAGR: (2.25/1.40)^(1/3) - 1 = 17.13%
```

#### Step 3: 估值计算

```
① PEG = 2.25 × 0.1713 × 1.0 × (1 - 0.5×0.0256) = 0.38 元
② PE  = 2.25 × 3.76 × 1.1713 × 0.8 = 7.92 元
③ PB  = 2.25 × 1.5 = 3.38 元
④ DCF ≈ 38.41 元

加权 = 0.4×0.38 + 0.3×7.92 + 0.15×3.38 + 0.15×38.41
     = 0.15 + 2.38 + 0.51 + 5.76
     = 8.80 元

风险调整 = 8.80 × (1 - 0.1×1.0) = 8.80 × 0.9 = 7.92 元
```

#### Step 4: 估值区间

```
置信度 = max(1.0 - 0.1, 0.3) = 0.9
边际值 = 7.92 × (1 - 0.9) × 0.2 = 0.16 元

区间: [7.76, 8.08] 元
```

### 最终结果

```
内在价值: 7.92 元
估值区间: [7.76, 8.08] 元
交易信号: HOLD (持有)
```

---

## 🔗 相关文件索引

| 文件 | 功能 |
|------|------|
| `app/services/mdvaes_data_reader.py` | EPS 预测数据读取 |
| `app/services/growth_calculator.py` | 增长指标计算 |
| `app/services/valuation_calculator.py` | 估值结果计算 |
| `app/services/mdvaes_service.py` | 估值服务编排 |
| `app/services/mdvaes_data_sync_service.py` | 数据同步服务 |
| `app/domain/mdvaes.py` | 领域模型定义 |

---

## 📝 附录

### A. Tushare API 相关

| 接口 | 用途 | 文档 ID |
|------|------|----------|
| `stock_basic` | 获取股票列表 | - |
| `fina_indicator` | 财务指标 | 33 |
| `report_rc` | 分析师盈利预测 | 292 |
| `pe_daily_basic` | 每日基本面 | - |
| `yv_ts` | 国债收益率曲线 | - |

### B. 数据库表结构

| 表名 | 唯一键 | 说明 |
|------|--------|------|
| `mdvaes_analyst_forecasts` | ts_code + report_date + org_name | 分析师预测 |
| `mdvaes_eps_history` | ts_code + end_date | EPS 历史 |
| `mdvaes_financial_ratios` | ts_code + end_date | 财务比率 |
| `mdvaes_pe_history` | ts_code + trade_date | PE 历史 |
| `mdvaes_bond_rate` | trade_date + curve_term | 国债收益率 |

---

**文档结束**
