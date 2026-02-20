# MDVAES 估值模型技术设计文档

**创建日期**: 2026-02-19
**状态**: 草稿
**作者**: Claude Code

---

## Part 1: 业务需求

### 功能概述

MDVAES (Multi-Dimensional Value Anchoring Evaluation System) 是一个基于基本面分析的多维度价值锚定评估系统，用于计算股票内在价值并生成交易信号。

### 核心功能模块

#### 1. 核心估值模块
- **增长率透视**: 使用对数最小二乘法回归分析 EPS 增长率
- **R² 拟合优度**: 评估增长趋势的稳定性
- **宏观利率联动 PEG**: 基于无风险利率的动态 PEG 估值
- **多叉验证**: 结合 PE、PB、DCF 多种方法交叉验证

#### 2. 成长能力模块
- **CAGR 计算**: 复合年均增长率
- **增长质量**: 收入增长与利润增长的匹配度

#### 3. 风险评估模块
- **财务风险**: 资产负债率、流动比率、速动比率
- **现金流风险**: 经营现金流/净利润比率
- **压力测试**: 极端情况下的估值敏感性分析

#### 4. 可视化决策模块
- **估值推演图**: 未来估值区间预测
- **概率区间**: 不同置信水平下的估值范围
- **交易信号**: 买入/卖出/持有建议

### 用户故事

| 角色 | 故事 | 验收标准 |
|-----|------|---------|
| 量化研究员 | 配置估值模型参数并进行回测 | 能够保存参数模板，回测报告包含所有指标 |
| 个人投资者 | 查看股票的估值区间和交易信号 | 可视化图表清晰显示估值水位和买卖点 |
| 基金经理 | 对比不同股票的估值吸引力 | 支持多股票估值对比和排序 |

### 业务规则

1. **数据时效性**: 所有估值计算基于最新的财务数据和分析师预测
2. **更新频率**: 每日收盘后更新估值
3. **信号模式**:
   - 模式1（估值区间）: 价格 < 下限买入，价格 > 上限卖出
   - 模式2（安全边际）: 估值×80%买入，估值×120%卖出
4. **参数预设**: 保守/中性/激进三套预设参数
5. **历史回测**: 使用历史时间点的分析师预测（避免后见之明）

### 用户工作流程

```
1. 用户选择股票
   ↓
2. 系统加载最新财务数据
   ↓
3. 用户选择参数预设或自定义
   ↓
4. 系统实时计算估值
   ↓
5. 用户查看可视化图表
   ↓
6. 用户启动回测
   ↓
7. 系统生成回测报告
```

### 边界情况处理

| 情况 | 处理策略 |
|-----|---------|
| 分析师预测缺失 | 使用历史增长率外推 |
| 财务数据不足 | 显示警告，禁用相关计算 |
| 停牌股票 | 使用最近一日数据，标注停牌状态 |
| 新股上市 | 使用有限历史数据，降低预测可信度 |

---

## Part 2A: 后端技术设计

### 模块复用分析

#### ✅ 复用模块

| 模块 | 复用度 | 说明 |
|-----|-------|------|
| `BacktestEngine` | 100% | 完全复用现有回测引擎 |
| `BaseStrategy` | 100% | 继承基类实现 MDVAES 策略 |
| `StrategyRegistry` | 100% | 注册新策略 |
| `WebSocketManager` | 100% | 实时进度推送 |
| MongoDB 基础设施 | 100% | 数据存储 |

#### 🔧 修改模块

| 模块 | 修改内容 | 影响范围 |
|-----|---------|---------|
| 回测前端组件 | 添加 MDVAES 参数配置界面 | `BacktestControlPanel.vue` |
| 策略列表 | 添加 MDVAES 策略入口 | `StrategyList.vue` |

#### ➕ 新增模块

| 模块 | 职责 |
|-----|------|
| `MDVAESStrategy` | MDVAES 策略实现 |
| `MDVAESCalculator` | 核心估值计算逻辑 |
| `MDVAESDataReader` | 数据读取和聚合 |
| `MDVAESDataSyncService` | 定时数据同步 |
| `MDVAESVisualizer` | 可视化数据生成 |

---

### 技术架构

#### 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│                        API 层                                │
│  POST /api/backtest/start (strategy_id=mdvaes)              │
│  GET  /api/mdvaes/valuation?symbol=xxx                      │
│  GET  /api/mdvaes/parameters                                │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      服务层                                  │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ MDVAESService    │  │ MDVAESDataSync   │               │
│  │ - calculate()    │  │ - sync_daily()   │               │
│  │ - get_valuation()│  │                  │               │
│  └──────────────────┘  └──────────────────┘               │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      策略层                                  │
│  ┌──────────────────────────────────────────────────┐      │
│  │ MDVAESStrategy (extends BaseStrategy)            │      │
│  │ - on_bar()                                      │      │
│  │ - get_parameters_definition()                   │      │
│  └──────────────────────────────────────────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     计算层                                   │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ MDVAESCalculator │  │ GrowthCalculator  │               │
│  │ - eps_regression │  │ - calc_cagr()    │               │
│  │ - peg_valuation  │  │ - quality_score() │               │
│  │ - multi_anchor() │  │                  │               │
│  └──────────────────┘  └──────────────────┘               │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     数据层                                   │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ MDVAESDataReader │  │ MongoDB          │               │
│  │ - get_eps_hist() │  │ - analyst_fcsts  │               │
│  │ - get_pe_hist()  │  │ - eps_history    │               │
│  │ - get_bond_rate()│  │ - pe_history     │               │
│  └──────────────────┘  │ - bond_rate      │               │
│                       └──────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

---

### DDD 领域模型

#### 聚合根

```python
# app/domain/mdvaes.py

class MDVAESValuation(AggregateRoot):
    """MDVAES 估值聚合根"""

    def __init__(self, symbol: str, calculation_date: str):
        self.symbol = symbol
        self.calculation_date = calculation_date
        self.eps_forecast: List[EPSForecast] = []
        self.growth_metrics: Optional[GrowthMetrics] = None
        self.risk_metrics: Optional[RiskMetrics] = None
        self.valuation_result: Optional[ValuationResult] = None

    def calculate(self, params: MDVAESParams, data_reader: MDVAESDataReader):
        """执行估值计算"""
        # 1. 获取数据
        self.eps_forecast = data_reader.get_eps_forecast(
            self.symbol,
            self.calculation_date,
            params.forecast_years
        )

        # 2. 计算增长率
        self.growth_metrics = GrowthCalculator.calculate(self.eps_forecast)

        # 3. 计算风险指标
        self.risk_metrics = RiskCalculator.calculate(
            self.symbol,
            self.calculation_date,
            data_reader
        )

        # 4. 多锚点估值
        self.valuation_result = ValuationCalculator.calculate(
            self.growth_metrics,
            self.risk_metrics,
            params
        )
```

#### 实体

```python
class EPSForecast(Entity):
    """EPS 预测"""
    year: int
    eps_forecast: float
    forecast_date: str  # 预测发布日期
    analyst_count: int
    source: str  # analyst/historical_extrapolation

class GrowthMetrics(ValueObject):
    """增长指标"""
    cagr: float
    growth_rate: float
    r_squared: float
    growth_quality_score: float
    trend_stability: str  # stable/volatile/declining

class RiskMetrics(ValueObject):
    """风险指标"""
    debt_to_assets: float
    current_ratio: float
    quick_ratio: float
    cashflow_to_income: float
    risk_level: str  # low/medium/high

class ValuationResult(ValueObject):
    """估值结果"""
    intrinsic_value: float
    lower_bound: float
    upper_bound: float
    confidence: float
    valuation_method: dict  # 各方法估值
    signal: str  # buy/sell/hold
```

#### 值对象

```python
@dataclass(frozen=True)
class MDVAESParams(ValueObject):
    """MDVAES 参数"""
    # 预测参数
    forecast_years: int = 5
    min_forecast_count: int = 3

    # 估值参数
    peg_base: float = 1.0  # 基础 PEG
    peg_interest_sensitivity: float = 0.5  # 利率敏感度
    risk_adjustment: float = 0.1  # 风险折价

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

    # 预设
    preset: Optional[str] = None  # conservative/neutral/aggressive
```

---

### 数据库设计

#### 集合设计

```javascript
// 1. mdvaes_analyst_forecasts - 分析师盈利预测
{
  _id: ObjectId,
  ts_code: "000001.SZ",
  name: "平安银行",
  report_date: "2024-04-29",  // 研报日期
  quarter: "2024Q4",  // 预测报告期
  eps: 1.23,  // 预测EPS
  pe: 8.5,  // 预测PE
  rating: "买入",
  max_price: 15.5,
  min_price: 12.3,
  created_at: ISODate,
  synced_at: ISODate
}

// 索引
db.mdvaes_analyst_forecasts.createIndex({
  ts_code: 1,
  quarter: 1,
  report_date: -1
})

// 2. mdvaes_eps_history - EPS 历史数据
{
  _id: ObjectId,
  ts_code: "000001.SZ",
  ann_date: "2024-04-29",  // 公告日期
  end_date: "2023-12-31",  // 报告期
  eps: 2.15,  // 基本EPS
  dt_eps: 2.20,  // 稀释EPS
  updated_at: ISODate
}

// 3. mdvaes_pe_history - PE 历史数据
{
  _id: ObjectId,
  ts_code: "000001.SZ",
  trade_date: "2024-01-15",
  pe: 8.5,  // 静态PE
  pe_ttm: 8.8,  // TTM PE
  pb: 0.75,
  ps: 1.2,
  synced_at: ISODate
}

// 4. mdvaes_cashflow_data - 现金流数据
{
  _id: ObjectId,
  ts_code: "000001.SZ",
  ann_date: "2024-04-29",
  end_date: "2023-12-31",
  ocfps: 3.5,  // 经营现金流/股
  fcff_ps: 2.8,  // 自由现金流/股
  updated_at: ISODate
}

// 5. mdvaes_financial_ratios - 财务比率
{
  _id: ObjectId,
  ts_code: "000001.SZ",
  ann_date: "2024-04-29",
  end_date: "2023-12-31",
  debt_to_assets: 0.92,  // 资产负债率
  current_ratio: 1.05,  // 流动比率
  quick_ratio: 0.98,  // 速动比率
  roe: 0.12,  // ROE
  roa: 0.01,  // ROA
  updated_at: ISODate
}

// 6. mdvaes_bond_rate - 国债收益率
{
  _id: ObjectId,
  trade_date: "2024-01-15",
  curve_term: 10.0,  // 10年期
  yield: 2.75,  // 收益率(%)
  curve_type: "0",  // 到期收益率
  synced_at: ISODate
}

// 7. mdvaes_valuation_cache - 估值缓存
{
  _id: ObjectId,
  ts_code: "000001.SZ",
  calculation_date: "2024-01-15",
  params_hash: "abc123",  # 参数哈希
  intrinsic_value: 15.5,
  lower_bound: 12.5,
  upper_bound: 18.5,
  signal: "hold",
  confidence: 0.75,
  created_at: ISODate
}
```

#### 数据映射

| MDVAES 需求 | MongoDB 集合 | Tushare 接口 | 字段映射 |
|------------|-------------|-------------|---------|
| 分析师盈利预测 | `mdvaes_analyst_forecasts` | `report_rc` | `eps`→eps_forecast, `quarter`→forecast_period |
| 历史 EPS | `mdvaes_eps_history` | `fina_indicator` | `eps`→basic_eps |
| 历史 PE | `mdvaes_pe_history` | `daily_basic` | `pe_ttm`→pe_ratio |
| 经营现金流/股 | `mdvaes_cashflow_data` | `fina_indicator` | `ocfps`→operating_cashflow_per_share |
| 资产负债率 | `mdvaes_financial_ratios` | `fina_indicator` | `debt_to_assets` |
| 10年期国债收益率 | `mdvaes_bond_rate` | `yc_cb` | `yield`→bond_yield, `curve_term=10.0` |

---

### API 设计

#### 1. 获取估值

```python
GET /api/mdvaes/valuation
```

**请求参数**:
```json
{
  "symbol": "000001.SZ",
  "calculation_date": "2024-01-15",
  "params": {
    "preset": "neutral"
  }
}
```

**响应**:
```json
{
  "success": true,
  "data": {
    "symbol": "000001.SZ",
    "calculation_date": "2024-01-15",
    "current_price": 12.5,
    "valuation": {
      "intrinsic_value": 15.5,
      "lower_bound": 12.5,
      "upper_bound": 18.5,
      "confidence": 0.75
    },
    "signal": "hold",
    "growth_metrics": {
      "cagr": 0.15,
      "growth_rate": 0.12,
      "r_squared": 0.89,
      "quality_score": 0.8
    },
    "risk_metrics": {
      "debt_to_assets": 0.92,
      "current_ratio": 1.05,
      "risk_level": "medium"
    },
    "multi_anchor": {
      "peg": 15.5,
      "pe_historical": 14.8,
      "pb": 13.2,
      "dcf": 16.5
    },
    "charts": {
      "valuation_projection": {...},
      "water_level": {...},
      "multi_anchor_comparison": {...},
      "eps_trend": {...}
    }
  }
}
```

#### 2. 获取参数定义

```python
GET /api/mdvaes/parameters
```

**响应**:
```json
{
  "success": true,
  "data": {
    "parameters": [
      {
        "name": "forecast_years",
        "type": "int",
        "default": 5,
        "range": {"min": 1, "max": 10},
        "description": "预测年数",
        "required": true
      },
      {
        "name": "peg_base",
        "type": "float",
        "default": 1.0,
        "range": {"min": 0.5, "max": 2.0},
        "description": "基础PEG值",
        "required": true
      }
    ],
    "presets": {
      "conservative": {
        "peg_base": 0.8,
        "risk_adjustment": 0.15,
        "safety_margin_buy": 0.7
      },
      "neutral": {
        "peg_base": 1.0,
        "risk_adjustment": 0.1,
        "safety_margin_buy": 0.8
      },
      "aggressive": {
        "peg_base": 1.2,
        "risk_adjustment": 0.05,
        "safety_margin_buy": 0.9
      }
    }
  }
}
```

#### 3. 启动回测

```python
POST /api/backtest/start
```

**请求体**:
```json
{
  "stock_code": "000001.SZ",
  "start_date": "2020-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 100000,
  "strategy_id": "mdvaes",
  "strategy_params": {
    "preset": "neutral",
    "signal_mode": "valuation_range"
  }
}
```

---

### 详细接口规格 (OpenAPI 风格)

#### 1. POST /api/mdvaes/valuation

**接口描述**: 计算股票的 MDVAES 估值

**请求方式**: `POST`

**请求头**:
```
Content-Type: application/json
Authorization: Bearer <access_token>
```

**请求参数**:

| 参数名 | 类型 | 位置 | 必填 | 说明 | 示例值 |
|-------|------|------|------|------|--------|
| symbol | string | body | 是 | 股票代码（带后缀） | `"000001.SZ"` |
| calculation_date | string | body | 否 | 计算日期（YYYY-MM-DD），默认为最新交易日 | `"2024-01-15"` |
| params | object | body | 是 | MDVAES 参数对象 | - |
| params.preset | string | body | 否 | 预设名称（conservative/neutral/aggressive/custom） | `"neutral"` |
| params.forecast_years | integer | body | 否 | 预测年数（1-10），preset 为 custom 时必填 | `5` |
| params.min_forecast_count | integer | body | 否 | 最小预测数量（1-10） | `3` |
| params.peg_base | number | body | 否 | 基础 PEG 值（0.5-2.0） | `1.0` |
| params.peg_interest_sensitivity | number | body | 否 | 利率敏感度（0.0-1.0） | `0.5` |
| params.risk_adjustment | number | body | 否 | 风险折价（0.0-0.3） | `0.1` |
| params.anchor_weight | object | body | 否 | 多锚点权重 | - |
| params.anchor_weight.peg | number | body | 否 | PEG 权重（0.0-1.0） | `0.4` |
| params.anchor_weight.pe_historical | number | body | 否 | 历史 PE 权重（0.0-1.0） | `0.3` |
| params.anchor_weight.pb | number | body | 否 | PB 权重（0.0-1.0） | `0.15` |
| params.anchor_weight.dcf | number | body | 否 | DCF 权重（0.0-1.0） | `0.15` |
| params.signal_mode | string | body | 否 | 信号模式（valuation_range/safety_margin） | `"valuation_range"` |
| params.safety_margin_buy | number | body | 否 | 安全边际买入系数（0.5-0.95） | `0.8` |
| params.safety_margin_sell | number | body | 否 | 安全边际卖出系数（1.05-1.5） | `1.2` |

**请求示例**:
```json
{
  "symbol": "000001.SZ",
  "calculation_date": "2024-01-15",
  "params": {
    "preset": "neutral",
    "forecast_years": 5,
    "peg_base": 1.0,
    "risk_adjustment": 0.1,
    "anchor_weight": {
      "peg": 0.4,
      "pe_historical": 0.3,
      "pb": 0.15,
      "dcf": 0.15
    },
    "signal_mode": "valuation_range"
  }
}
```

**响应字段说明**:

| 字段路径 | 类型 | 说明 |
|---------|------|------|
| success | boolean | 请求是否成功 |
| data.symbol | string | 股票代码 |
| data.calculation_date | string | 计算日期 |
| data.current_price | number | 当前价格 |
| data.valuation | object | 估值结果 |
| data.valuation.intrinsic_value | number | 内在价值 |
| data.valuation.lower_bound | number | 估值下限 |
| data.valuation.upper_bound | number | 估值上限 |
| data.valuation.confidence | number | 置信度（0.0-1.0） |
| data.valuation.valuation_method | object | 各方法估值结果 |
| data.valuation.valuation_method.peg | number | PEG 方法估值 |
| data.valuation.valuation_method.pe_historical | number | 历史 PE 方法估值 |
| data.valuation.valuation_method.pb | number | PB 方法估值 |
| data.valuation.valuation_method.dcf | number | DCF 方法估值 |
| data.signal | string | 交易信号（buy/sell/hold） |
| data.growth_metrics | object | 增长指标 |
| data.growth_metrics.cagr | number | 复合年均增长率 |
| data.growth_metrics.growth_rate | number | 增长率 |
| data.growth_metrics.r_squared | number | R² 拟合优度 |
| data.growth_metrics.growth_quality_score | number | 增长质量评分（0.0-1.0） |
| data.growth_metrics.trend_stability | string | 趋势稳定性（stable/volatile/declining） |
| data.risk_metrics | object | 风险指标 |
| data.risk_metrics.debt_to_assets | number | 资产负债率（0.0-1.0） |
| data.risk_metrics.current_ratio | number | 流动比率 |
| data.risk_metrics.quick_ratio | number | 速动比率 |
| data.risk_metrics.cashflow_to_income | number | 现金流/利润比率 |
| data.risk_metrics.risk_level | string | 风险等级（low/medium/high） |
| data.multi_anchor | object | 多锚点估值结果 |
| data.multi_anchor.peg | number | PEG 锚点估值 |
| data.multi_anchor.pe_historical | number | 历史 PE 锚点估值 |
| data.multi_anchor.pb | number | PB 锚点估值 |
| data.multi_anchor.dcf | number | DCF 锚点估值 |
| data.charts | object | 图表数据 |
| data.charts.valuation_projection | object | 估值推演图数据 |
| data.charts.water_level | object | 水位仪表盘数据 |
| data.charts.multi_anchor_comparison | object | 多锚点对比图数据 |
| data.charts.eps_trend | array | EPS 趋势图数据 |
| message | string | 响应消息（成功时为 "success"） |
| timestamp | string | 响应时间戳（ISO 8601） |

**成功响应示例** (200 OK):
```json
{
  "success": true,
  "data": {
    "symbol": "000001.SZ",
    "calculation_date": "2024-01-15",
    "current_price": 12.5,
    "valuation": {
      "intrinsic_value": 15.5,
      "lower_bound": 12.5,
      "upper_bound": 18.5,
      "confidence": 0.75,
      "valuation_method": {
        "peg": 15.5,
        "pe_historical": 14.8,
        "pb": 13.2,
        "dcf": 16.5
      }
    },
    "signal": "hold",
    "growth_metrics": {
      "cagr": 0.15,
      "growth_rate": 0.12,
      "r_squared": 0.89,
      "growth_quality_score": 0.8,
      "trend_stability": "stable"
    },
    "risk_metrics": {
      "debt_to_assets": 0.92,
      "current_ratio": 1.05,
      "quick_ratio": 0.98,
      "cashflow_to_income": 1.2,
      "risk_level": "medium"
    },
    "multi_anchor": {
      "peg": 15.5,
      "pe_historical": 14.8,
      "pb": 13.2,
      "dcf": 16.5
    },
    "charts": {
      "valuation_projection": {
        "dates": ["2024-01-15", "2025-01-15", "2026-01-15"],
        "lower_bound": [12.5, 13.8, 15.2],
        "intrinsic_value": [15.5, 17.1, 18.8],
        "upper_bound": [18.5, 20.4, 22.4]
      },
      "water_level": {
        "current_price": 12.5,
        "lower_bound": 12.5,
        "upper_bound": 18.5,
        "intrinsic_value": 15.5,
        "position": 0.0
      },
      "multi_anchor_comparison": {
        "methods": ["PEG估值", "历史PE", "PB估值", "DCF估值"],
        "values": [15.5, 14.8, 13.2, 16.5]
      },
      "eps_trend": [
        {"year": 2019, "eps": 1.8, "forecast": false},
        {"year": 2020, "eps": 2.0, "forecast": false},
        {"year": 2021, "eps": 2.3, "forecast": false},
        {"year": 2024, "eps": 2.8, "forecast": true},
        {"year": 2025, "eps": 3.2, "forecast": true}
      ]
    }
  },
  "message": "success",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**错误响应**:

| HTTP 状态码 | 错误类型 | 错误码 | 说明 |
|------------|---------|-------|------|
| 400 | BadRequest | INVALID_PARAMS | 请求参数无效 |
| 400 | BadRequest | MISSING_REQUIRED_FIELD | 缺少必填字段 |
| 400 | BadRequest | INVALID_SYMBOL | 股票代码格式错误 |
| 400 | BadRequest | INVALID_DATE | 日期格式错误 |
| 400 | BadRequest | PARAM_OUT_OF_RANGE | 参数超出范围 |
| 401 | Unauthorized | UNAUTHORIZED | 未认证（Token 缺失或无效） |
| 403 | Forbidden | INSUFFICIENT_PERMISSIONS | 权限不足 |
| 403 | Forbidden | SUBSCRIPTION_REQUIRED | 需要订阅该功能 |
| 404 | NotFound | STOCK_NOT_FOUND | 股票不存在 |
| 404 | NotFound | DATA_INSUFFICIENT | 数据不足，无法计算 |
| 429 | TooManyRequests | RATE_LIMIT_EXCEEDED | 超出速率限制 |
| 500 | InternalServerError | CALCULATION_ERROR | 估值计算错误 |
| 500 | InternalServerError | DATABASE_ERROR | 数据库错误 |
| 503 | ServiceUnavailable | SERVICE_UNAVAILABLE | 服务暂时不可用 |

**错误响应示例**:
```json
{
  "success": false,
  "message": "数据不足：该股票缺少至少 3 年的 EPS 历史数据",
  "error": {
    "code": "DATA_INSUFFICIENT",
    "details": {
      "symbol": "000001.SZ",
      "available_years": 2,
      "required_years": 3
    }
  },
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**权限要求**:
- 需要有效的 JWT Token
- 用户订阅级别：Basic 及以上

**速率限制**:
- 每 user: 10 次/分钟
- 全局: 100 次/分钟

---

#### 2. GET /api/mdvaes/parameters

**接口描述**: 获取 MDVAES 参数定义和预设配置

**请求方式**: `GET`

**请求头**:
```
Authorization: Bearer <access_token>
```

**请求参数**: 无

**响应字段说明**:

| 字段路径 | 类型 | 说明 |
|---------|------|------|
| success | boolean | 请求是否成功 |
| data.parameters | array | 参数定义列表 |
| data.parameters[].name | string | 参数名称 |
| data.parameters[].type | string | 参数类型（int/float/string/boolean） |
| data.parameters[].default | any | 默认值 |
| data.parameters[].range | object | 取值范围（仅数值类型） |
| data.parameters[].range.min | number | 最小值 |
| data.parameters[].range.max | number | 最大值 |
| data.parameters[].description | string | 参数描述 |
| data.parameters[].required | boolean | 是否必填 |
| data.parameters[].group | string | 参数分组（预测/估值/风险/信号） |
| data.presets | object | 预设参数配置 |
| data.presets.conservative | object | 保守预设参数 |
| data.presets.neutral | object | 中性预设参数 |
| data.presets.aggressive | object | 激进预设参数 |

**成功响应示例** (200 OK):
```json
{
  "success": true,
  "data": {
    "parameters": [
      {
        "name": "forecast_years",
        "type": "int",
        "default": 5,
        "range": {"min": 1, "max": 10},
        "description": "EPS 预测年数",
        "required": true,
        "group": "预测参数"
      },
      {
        "name": "peg_base",
        "type": "float",
        "default": 1.0,
        "range": {"min": 0.5, "max": 2.0},
        "description": "PEG 估值的基础倍数",
        "required": true,
        "group": "估值参数"
      },
      {
        "name": "risk_adjustment",
        "type": "float",
        "default": 0.1,
        "range": {"min": 0.0, "max": 0.3},
        "description": "根据风险等级的估值折价比例",
        "required": true,
        "group": "估值参数"
      },
      {
        "name": "signal_mode",
        "type": "string",
        "default": "valuation_range",
        "description": "交易信号模式",
        "required": true,
        "group": "信号参数",
        "enum": ["valuation_range", "safety_margin"]
      }
    ],
    "presets": {
      "conservative": {
        "forecast_years": 3,
        "peg_base": 0.8,
        "risk_adjustment": 0.15,
        "safety_margin_buy": 0.7,
        "safety_margin_sell": 1.15,
        "anchor_weight": {
          "peg": 0.5,
          "pe_historical": 0.3,
          "pb": 0.1,
          "dcf": 0.1
        }
      },
      "neutral": {
        "forecast_years": 5,
        "peg_base": 1.0,
        "risk_adjustment": 0.1,
        "safety_margin_buy": 0.8,
        "safety_margin_sell": 1.2,
        "anchor_weight": {
          "peg": 0.4,
          "pe_historical": 0.3,
          "pb": 0.15,
          "dcf": 0.15
        }
      },
      "aggressive": {
        "forecast_years": 7,
        "peg_base": 1.2,
        "risk_adjustment": 0.05,
        "safety_margin_buy": 0.9,
        "safety_margin_sell": 1.25,
        "anchor_weight": {
          "peg": 0.35,
          "pe_historical": 0.25,
          "pb": 0.2,
          "dcf": 0.2
        }
      }
    }
  },
  "message": "success",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**权限要求**:
- 需要有效的 JWT Token
- 所有用户级别可访问

**速率限制**:
- 每 user: 20 次/分钟
- 全局: 200 次/分钟

---

#### 3. POST /api/mdvaes/user-params

**接口描述**: 保存用户自定义的 MDVAES 参数

**请求方式**: `POST`

**请求头**:
```
Content-Type: application/json
Authorization: Bearer <access_token>
```

**请求参数**:

| 参数名 | 类型 | 位置 | 必填 | 说明 | 示例值 |
|-------|------|------|------|------|--------|
| symbol | string | body | 是 | 股票代码 | `"000001.SZ"` |
| params | object | body | 是 | MDVAES 参数对象 | - |
| params.name | string | body | 是 | 参数配置名称 | `"我的保守配置"` |
| params.description | string | body | 否 | 参数配置描述 | `"适合长期投资"` |
| params.config | object | body | 是 | 参数配置（与 /valuation 的 params 相同） | - |

**请求示例**:
```json
{
  "symbol": "000001.SZ",
  "params": {
    "name": "我的保守配置",
    "description": "适合长期投资",
    "config": {
      "preset": "custom",
      "forecast_years": 3,
      "peg_base": 0.8,
      "risk_adjustment": 0.15,
      "signal_mode": "valuation_range",
      "anchor_weight": {
        "peg": 0.5,
        "pe_historical": 0.3,
        "pb": 0.1,
        "dcf": 0.1
      }
    }
  }
}
```

**响应字段说明**:

| 字段路径 | 类型 | 说明 |
|---------|------|------|
| success | boolean | 请求是否成功 |
| data.param_id | string | 参数配置 ID |
| data.symbol | string | 股票代码 |
| data.created_at | string | 创建时间 |

**成功响应示例** (201 Created):
```json
{
  "success": true,
  "data": {
    "param_id": "param_1234567890",
    "symbol": "000001.SZ",
    "created_at": "2024-01-15T10:30:00.000Z"
  },
  "message": "参数保存成功",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**权限要求**:
- 需要有效的 JWT Token
- 所有用户级别可访问

**速率限制**:
- 每 user: 10 次/分钟

---

#### 4. GET /api/mdvaes/user-params/{symbol}

**接口描述**: 获取用户保存的股票参数配置列表

**请求方式**: `GET`

**请求头**:
```
Authorization: Bearer <access_token>
```

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 | 示例值 |
|-------|------|------|------|--------|
| symbol | string | 是 | 股票代码 | `000001.SZ` |

**响应字段说明**:

| 字段路径 | 类型 | 说明 |
|---------|------|------|
| success | boolean | 请求是否成功 |
| data.params | array | 参数配置列表 |
| data.params[].param_id | string | 参数配置 ID |
| data.params[].name | string | 配置名称 |
| data.params[].description | string | 配置描述 |
| data.params[].config | object | 参数配置 |
| data.params[].created_at | string | 创建时间 |
| data.params[].updated_at | string | 更新时间 |

**成功响应示例** (200 OK):
```json
{
  "success": true,
  "data": {
    "params": [
      {
        "param_id": "param_1234567890",
        "name": "我的保守配置",
        "description": "适合长期投资",
        "config": {
          "preset": "custom",
          "forecast_years": 3,
          "peg_base": 0.8
        },
        "created_at": "2024-01-10T10:00:00.000Z",
        "updated_at": "2024-01-15T10:30:00.000Z"
      }
    ]
  },
  "message": "success",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**权限要求**:
- 需要有效的 JWT Token
- 只能获取自己保存的参数

**速率限制**:
- 每 user: 20 次/分钟

---

#### 5. GET /api/mdvaes/history/{symbol}

**接口描述**: 获取股票的历史估值记录

**请求方式**: `GET`

**请求头**:
```
Authorization: Bearer <access_token>
```

**路径参数**:

| 参数名 | 类型 | 必填 | 说明 | 示例值 |
|-------|------|------|------|--------|
| symbol | string | 是 | 股票代码 | `000001.SZ` |

**查询参数**:

| 参数名 | 类型 | 必填 | 说明 | 示例值 |
|-------|------|------|------|--------|
| days | integer | 否 | 查询天数（1-365），默认 30 | `30` |
| start_date | string | 否 | 起始日期（YYYY-MM-DD） | `"2024-01-01"` |
| end_date | string | 否 | 结束日期（YYYY-MM-DD） | `"2024-01-31"` |

**响应字段说明**:

| 字段路径 | 类型 | 说明 |
|---------|------|------|
| success | boolean | 请求是否成功 |
| data.symbol | string | 股票代码 |
| data.history | array | 历史估值记录 |
| data.history[].date | string | 日期 |
| data.history[].intrinsic_value | number | 内在价值 |
| data.history[].lower_bound | number | 估值下限 |
| data.history[].upper_bound | number | 估值上限 |
| data.history[].signal | string | 交易信号 |
| data.history[].current_price | number | 当前价格 |

**成功响应示例** (200 OK):
```json
{
  "success": true,
  "data": {
    "symbol": "000001.SZ",
    "history": [
      {
        "date": "2024-01-01",
        "intrinsic_value": 15.2,
        "lower_bound": 12.3,
        "upper_bound": 18.1,
        "signal": "hold",
        "current_price": 14.5
      },
      {
        "date": "2024-01-02",
        "intrinsic_value": 15.3,
        "lower_bound": 12.4,
        "upper_bound": 18.2,
        "signal": "hold",
        "current_price": 14.8
      }
    ]
  },
  "message": "success",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**权限要求**:
- 需要有效的 JWT Token
- 用户订阅级别：Basic 及以上

**速率限制**:
- 每 user: 10 次/分钟

---

#### 6. POST /api/backtest/start (扩展)

**接口描述**: 启动 MDVAES 策略回测（复用现有接口，扩展 strategy_id）

**请求方式**: `POST`

**请求头**:
```
Content-Type: application/json
Authorization: Bearer <access_token>
```

**请求参数** (MDVAES 特定):

| 参数名 | 类型 | 位置 | 必填 | 说明 | 示例值 |
|-------|------|------|------|------|--------|
| stock_code | string | body | 是 | 股票代码 | `"000001.SZ"` |
| start_date | string | body | 是 | 回测起始日期 | `"2020-01-01"` |
| end_date | string | body | 是 | 回测结束日期 | `"2024-12-31"` |
| initial_capital | number | body | 是 | 初始资金 | `100000` |
| strategy_id | string | body | 是 | 策略 ID，值为 `"mdvaes"` | `"mdvaes"` |
| strategy_params | object | body | 是 | 策略参数 | - |
| strategy_params.preset | string | body | 否 | 预设名称 | `"neutral"` |
| strategy_params.signal_mode | string | body | 否 | 信号模式 | `"valuation_range"` |
| strategy_params.safety_margin_buy | number | body | 否 | 安全边际买入系数 | `0.8` |
| strategy_params.safety_margin_sell | number | body | 否 | 安全边际卖出系数 | `1.2` |
| strategy_params.forecast_years | number | body | 否 | 预测年数 | `5` |
| strategy_params.peg_base | number | body | 否 | 基础 PEG | `1.0` |
| strategy_params.risk_adjustment | number | body | 否 | 风险折价 | `0.1` |

**请求示例**:
```json
{
  "stock_code": "000001.SZ",
  "start_date": "2020-01-01",
  "end_date": "2024-12-31",
  "initial_capital": 100000,
  "strategy_id": "mdvaes",
  "strategy_params": {
    "preset": "neutral",
    "signal_mode": "valuation_range"
  }
}
```

**响应** (与现有回测接口一致):
```json
{
  "success": true,
  "data": {
    "backtest_id": "bt_20240115_103000_123456",
    "status": "created"
  },
  "message": "回测任务已创建",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**权限要求**:
- 需要有效的 JWT Token
- 用户订阅级别：Pro 及以上

**速率限制**:
- 每 user: 5 次/小时

---

### 安全与性能

#### 1. 认证与授权

```python
from app.routers.auth_db import get_current_user

@router.get("/api/mdvaes/valuation")
async def get_valuation(
    symbol: str,
    current_user: dict = Depends(get_current_user)
):
    # 检查用户权限
    check_subscription_tier(current_user, "mdvaes")
    ...
```

#### 2. 缓存策略

```python
# 估值结果缓存（参数哈希）
cache_key = f"mdvaes:valuation:{symbol}:{params_hash}"
cached = await redis_client.get(cache_key)

if cached:
    return json.loads(cached)

# 计算估值
result = await calculator.calculate(...)
await redis_client.setex(cache_key, 3600, json.dumps(result))  # 1小时
```

#### 3. 查询优化

```python
# 使用投影减少数据传输
await db.mdvaes_eps_history.find(
    {"ts_code": symbol},
    {"_id": 0, "end_date": 1, "eps": 1}  # 只返回需要的字段
).sort("end_date", -1).limit(10).to_list(None)

# 复合索引优化查询
db.mdvaes_analyst_forecasts.create_index([
  ("ts_code", 1),
  ("quarter", 1),
  ("report_date", -1)
], background=True)
```

#### 4. 可观测性

```python
import time
from prometheus_client import Histogram, Counter

# 计算耗时
VALUATION_DURATION = Histogram(
    'mdvaes_valuation_duration_seconds',
    'Time spent calculating valuation'
)

VALUATION_REQUESTS = Counter(
    'mdvaes_valuation_requests_total',
    'Total valuation requests'
)

@VALUATION_DURATION.time()
async def calculate_valuation(...):
    VALUATION_REQUESTS.inc()
    ...
```

---

**Part 2A 完成，接下来是 Part 2B: 前端技术设计**

---

## Part 2B: 前端技术设计

### 模块复用分析

#### ✅ 复用组件

| 组件 | 复用度 | 说明 |
|-----|-------|------|
| `BacktestControlPanel.vue` | 80% | 复用参数配置框架，添加 MDVAES 特定参数 |
| `BacktestResults.vue` | 90% | 复用回测结果展示，添加 MDVAES 特有指标 |
| `TradingDayRangePicker.vue` | 100% | 完全复用 |
| `StockSelector.vue` | 100% | 完全复用 |
| `backtestEngine` Store | 85% | 复用回测状态管理，添加 MDVAES 特定状态 |
| `backtestEngine` API | 100% | 复用现有回测 API |

#### 🔧 修改组件

| 组件 | 修改内容 | 影响范围 |
|-----|---------|---------|
| `StrategyList.vue` | 添加 MDVAES 策略描述和入口 | 新增策略卡片 |
| `backtestEngine` Store | 扩展参数类型支持 MDVAES 参数 | 扩展 `strategy_params` 类型 |

#### ➕ 新增组件

| 组件 | 职责 |
|-----|------|
| `MDVAESParamsConfig.vue` | MDVAES 参数配置（预设选择 + 自定义滑块） |
| `MDVAESValuationPanel.vue` | 估值结果展示（指标 + 4种图表） |
| `ValuationProjectionChart.vue` | 估值推演图（ECharts） |
| `WaterLevelGauge.vue` | 水位仪表盘（ECharts） |
| `MultiAnchorComparison.vue` | 多锚点对比图（ECharts） |
| `EPSTrendChart.vue` | EPS 趋势图（ECharts） |
| `mdvaes` Store | MDVAES 估值状态管理 |

---

### 前端架构

#### 组件层次结构

```
┌─────────────────────────────────────────────────────────────┐
│                      路由层 (router/)                       │
│  /backtest/control → BacktestControlPanel.vue              │
│  /mdvaes/valuation → MDVAESValuationView.vue (新增)        │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      视图层 (views/)                        │
│  ┌──────────────────────────────────────────────────┐      │
│  │ MDVAESValuationView.vue (新增)                   │      │
│  │ - 顶部工具栏（股票选择、日期选择）                │      │
│  │ - 参数配置区（预设 + 自定义）                     │      │
│  │ - 估值结果展示区                                 │      │
│  │ - 图表展示区（4个图表）                           │      │
│  └──────────────────────────────────────────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     组件层 (components/)                    │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ MDVAESParamsConf  │  │ MDVAESValuationP │               │
│  │ ig.vue (新增)     │  │ anel.vue (新增)  │               │
│  │ - PresetSelector │  │ - MetricsDisplay │               │
│  │ - CustomSliders  │  │ - SignalBadge    │               │
│  └──────────────────┘  └──────────────────┘               │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ ValuationProject │  │ WaterLevelGauge  │               │
│  │ ionChart.vue     │  │ .vue             │               │
│  │ (新增)           │  │ (新增)           │               │
│  └──────────────────┘  └──────────────────┘               │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ MultiAnchorCompa │  │ EPSTrendChart    │               │
│  │ rison.vue        │  │ .vue             │               │
│  │ (新增)           │  │ (新增)           │               │
│  └──────────────────┘  └──────────────────┘               │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    状态层 (stores/)                         │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ mdvaes (新增)     │  │ backtestEngine   │               │
│  │ - valuation      │  │ (复用+扩展)      │               │
│  │ - parameters     │  │ - strategy_params │               │
│  │ - loading        │  │                  │               │
│  └──────────────────┘  └──────────────────┘               │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     API层 (api/)                           │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │ mdvaes.ts (新增) │  │ backtestEngine   │               │
│  │ - getValuation   │  │ .ts (复用)       │               │
│  │ - getParameters  │  │                  │               │
│  └──────────────────┘  └──────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

---

### 核心组件设计

#### 1. MDVAESParamsConfig.vue

**文件位置**: `frontend/src/components/MDVAESParamsConfig.vue`

**核心功能**:
- 预设参数选择（保守/中性/激进）
- 自定义参数滑块组
- 实时估值预览
- 参数重置和保存功能

**Props 接口**:
```typescript
interface Props {
  modelValue: MDVAESParams  // v-model 绑定
  symbol: string            // 股票代码
  disabled?: boolean        // 禁用状态
}
```

**组件结构**:
```vue
<template>
  <div class="mdvaes-params-config">
    <!-- 预设选择器 -->
    <el-radio-group v-model="localParams.preset" @change="onPresetChange">
      <el-radio-button label="conservative">保守</el-radio-button>
      <el-radio-button label="neutral">中性</el-radio-button>
      <el-radio-button label="aggressive">激进</el-radio-button>
      <el-radio-button label="custom">自定义</el-radio-button>
    </el-radio-group>

    <!-- 自定义参数滑块 -->
    <div v-if="localParams.preset === 'custom'" class="custom-params">
      <!-- 预测年数 -->
      <el-form-item label="预测年数">
        <el-slider
          v-model="localParams.forecast_years"
          :min="1"
          :max="10"
          :marks="{ 3: '3年', 5: '5年', 10: '10年' }"
          @change="onParamChange"
        />
      </el-form-item>

      <!-- 基础 PEG -->
      <el-form-item label="基础 PEG">
        <el-slider
          v-model="localParams.peg_base"
          :min="0.5"
          :max="2.0"
          :step="0.1"
          :marks="{ 0.8: '0.8', 1.0: '1.0', 1.5: '1.5' }"
          @change="onParamChange"
        />
      </el-form-item>

      <!-- 风险折价 -->
      <el-form-item label="风险折价">
        <el-slider
          v-model="localParams.risk_adjustment"
          :min="0"
          :max="0.3"
          :step="0.01"
          :marks="{ 0.05: '5%', 0.1: '10%', 0.2: '20%' }"
          @change="onParamChange"
        />
      </el-form-item>

      <!-- 多锚点权重 -->
      <el-form-item label="PEG 权重">
        <el-slider
          v-model="localParams.anchor_weight.peg"
          :min="0"
          :max="1"
          :step="0.05"
          @change="onParamChange"
        />
      </el-form-item>

      <!-- 其他锚点权重... -->
    </div>

    <!-- 实时估值预览 -->
    <div v-if="previewValuation" class="valuation-preview">
      <el-descriptions :column="3" border>
        <el-descriptions-item label="内在价值">
          {{ previewValuation.intrinsic_value.toFixed(2) }}
        </el-descriptions-item>
        <el-descriptions-item label="估值区间">
          {{ previewValuation.lower_bound.toFixed(2) }} -
          {{ previewValuation.upper_bound.toFixed(2) }}
        </el-descriptions-item>
        <el-descriptions-item label="信号">
          <el-tag :type="getSignalType(previewValuation.signal)">
            {{ getSignalText(previewValuation.signal) }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <!-- 操作按钮 -->
    <div class="actions">
      <el-button @click="handleReset">重置参数</el-button>
      <el-button type="primary" @click="handleSave">保存参数</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useMdvaesStore } from '@/stores/mdvaes'

interface Props {
  modelValue: MDVAESParams
  symbol: string
  disabled?: boolean
}

const props = defineProps<Props>()
const emit = defineEmits(['update:modelValue'])

const mdvaesStore = useMdvaesStore()

const localParams = ref<MDVAESParams>({ ...props.modelValue })
const previewValuation = ref<ValuationResult | null>(null)

// 预设变更
const onPresetChange = async (preset: string) => {
  if (preset === 'custom') return

  // 加载预设参数
  const presetParams = await mdvaesStore.getPresetParams(preset)
  localParams.value = { ...presetParams }
  emit('update:modelValue', localParams.value)

  // 更新估值预览
  await updatePreview()
}

// 参数变更（防抖）
let debounceTimer: NodeJS.Timeout | null = null
const onParamChange = () => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    emit('update:modelValue', localParams.value)
    updatePreview()
  }, 500)
}

// 更新估值预览
const updatePreview = async () => {
  try {
    const result = await mdvaesStore.calculateValuation(
      props.symbol,
      localParams.value
    )
    previewValuation.value = result.valuation
  } catch (error) {
    console.error('估值预览失败:', error)
  }
}

// 重置参数
const handleReset = () => {
  localParams.value = mdvaesStore.getDefaultParams()
  emit('update:modelValue', localParams.value)
  ElMessage.success('参数已重置')
}

// 保存参数
const handleSave = () => {
  // 调用保存参数 API
  mdvaesStore.saveUserParams(props.symbol, localParams.value)
  ElMessage.success('参数已保存')
}

// 监听外部变化
watch(() => props.modelValue, (newVal) => {
  localParams.value = { ...newVal }
}, { deep: true })

// 初始化
onMounted(() => {
  updatePreview()
})
</script>
```

---

#### 2. MDVAESValuationPanel.vue

**文件位置**: `frontend/src/components/MDVAESValuationPanel.vue`

**核心功能**:
- 估值结果概览（内在价值、区间、信号）
- 增长指标展示（CAGR、R²、质量评分）
- 风险指标展示（资产负债率、流动比率）
- 多锚点估值对比

**Props 接口**:
```typescript
interface Props {
  valuation: ValuationResult
  growthMetrics: GrowthMetrics
  riskMetrics: RiskMetrics
  multiAnchor: MultiAnchorResult
  currentPrice: number
}
```

**组件结构**:
```vue
<template>
  <div class="mdvaes-valuation-panel">
    <!-- 估值概览卡片 -->
    <el-card class="valuation-overview" shadow="hover">
      <template #header>
        <span class="card-title">估值结果</span>
        <el-tag :type="getSignalType(valuation.signal)" size="large">
          {{ getSignalText(valuation.signal) }}
        </el-tag>
      </template>

      <el-row :gutter="20">
        <el-col :span="8">
          <div class="metric-item">
            <div class="metric-label">内在价值</div>
            <div class="metric-value">
              {{ valuation.intrinsic_value.toFixed(2) }}
            </div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="metric-item">
            <div class="metric-label">估值区间</div>
            <div class="metric-value">
              {{ valuation.lower_bound.toFixed(2) }} -
              {{ valuation.upper_bound.toFixed(2) }}
            </div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="metric-item">
            <div class="metric-label">当前价格</div>
            <div class="metric-value" :class="getPriceClass()">
              {{ currentPrice.toFixed(2) }}
            </div>
            <div class="metric-sub">
              {{ getValuationStatus() }}
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- 估值水位可视化 -->
      <WaterLevelGauge
        :current-price="currentPrice"
        :lower-bound="valuation.lower_bound"
        :upper-bound="valuation.upper_bound"
        :intrinsic-value="valuation.intrinsic_value"
      />
    </el-card>

    <!-- 增长指标卡片 -->
    <el-card class="growth-metrics" shadow="hover">
      <template #header>
        <span class="card-title">成长能力</span>
      </template>

      <el-row :gutter="20">
        <el-col :span="6">
          <div class="metric-item">
            <div class="metric-label">CAGR</div>
            <div class="metric-value">
              {{ (growthMetrics.cagr * 100).toFixed(2) }}%
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-item">
            <div class="metric-label">增长率</div>
            <div class="metric-value">
              {{ (growthMetrics.growth_rate * 100).toFixed(2) }}%
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-item">
            <div class="metric-label">R² 拟合</div>
            <div class="metric-value">
              {{ growthMetrics.r_squared.toFixed(3) }}
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-item">
            <div class="metric-label">质量评分</div>
            <div class="metric-value">
              {{ (growthMetrics.growth_quality_score * 100).toFixed(0) }}分
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- EPS 趋势图 -->
      <EPSTrendChart :eps-data="epsData" />
    </el-card>

    <!-- 风险指标卡片 -->
    <el-card class="risk-metrics" shadow="hover">
      <template #header>
        <span class="card-title">风险评估</span>
        <el-tag :type="getRiskTagType(riskMetrics.risk_level)">
          {{ getRiskText(riskMetrics.risk_level) }}
        </el-tag>
      </template>

      <el-row :gutter="20">
        <el-col :span="6">
          <div class="metric-item">
            <div class="metric-label">资产负债率</div>
            <div class="metric-value">
              {{ (riskMetrics.debt_to_assets * 100).toFixed(2) }}%
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-item">
            <div class="metric-label">流动比率</div>
            <div class="metric-value">
              {{ riskMetrics.current_ratio.toFixed(2) }}
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-item">
            <div class="metric-label">速动比率</div>
            <div class="metric-value">
              {{ riskMetrics.quick_ratio.toFixed(2) }}
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-item">
            <div class="metric-label">现金流/利润</div>
            <div class="metric-value">
              {{ riskMetrics.cashflow_to_income.toFixed(2) }}
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 多锚点对比卡片 -->
    <el-card class="multi-anchor" shadow="hover">
      <template #header>
        <span class="card-title">多锚点估值</span>
      </template>

      <MultiAnchorComparison :multi-anchor="multiAnchor" />
    </el-card>

    <!-- 估值推演图卡片 -->
    <el-card class="valuation-projection" shadow="hover">
      <template #header>
        <span class="card-title">估值推演</span>
      </template>

      <ValuationProjectionChart :projection-data="projectionData" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import WaterLevelGauge from './WaterLevelGauge.vue'
import MultiAnchorComparison from './MultiAnchorComparison.vue'
import EPSTrendChart from './EPSTrendChart.vue'
import ValuationProjectionChart from './ValuationProjectionChart.vue'

interface Props {
  valuation: ValuationResult
  growthMetrics: GrowthMetrics
  riskMetrics: RiskMetrics
  multiAnchor: MultiAnchorResult
  currentPrice: number
  epsData?: EPSData[]
}

const props = defineProps<Props>()

// 信号类型映射
const getSignalType = (signal: string) => {
  const typeMap: Record<string, any> = {
    'buy': 'success',
    'sell': 'danger',
    'hold': 'warning'
  }
  return typeMap[signal] || 'info'
}

const getSignalText = (signal: string) => {
  const textMap: Record<string, string> = {
    'buy': '买入',
    'sell': '卖出',
    'hold': '持有'
  }
  return textMap[signal] || '未知'
}

// 价格状态
const getPriceClass = () => {
  const { currentPrice, valuation } = props
  if (currentPrice < valuation.lower_bound) return 'price-low'
  if (currentPrice > valuation.upper_bound) return 'price-high'
  return 'price-normal'
}

const getValuationStatus = () => {
  const { currentPrice, valuation } = props
  if (currentPrice < valuation.lower_bound) return '低估'
  if (currentPrice > valuation.upper_bound) return '高估'
  return '合理区间'
}

// 风险等级
const getRiskTagType = (level: string) => {
  const typeMap: Record<string, any> = {
    'low': 'success',
    'medium': 'warning',
    'high': 'danger'
  }
  return typeMap[level] || 'info'
}

const getRiskText = (level: string) => {
  const textMap: Record<string, string> = {
    'low': '低风险',
    'medium': '中等风险',
    'high': '高风险'
  }
  return textMap[level] || '未知'
}
</script>

<style scoped>
.mdvaes-valuation-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.metric-item {
  text-align: center;
  padding: 10px;
}

.metric-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 24px;
  font-weight: bold;
  color: #303133;
}

.metric-sub {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.price-low { color: #67C23A; }
.price-normal { color: #E6A23C; }
.price-high { color: #F56C6C; }
</style>
```

---

#### 3. ValuationProjectionChart.vue

**文件位置**: `frontend/src/components/ValuationProjectionChart.vue`

**核心功能**: 展示未来估值区间预测的折线图

**Props 接口**:
```typescript
interface Props {
  projectionData: {
    dates: string[]
    lower_bound: number[]
    intrinsic_value: number[]
    upper_bound: number[]
    current_price?: number[]
  }
}
```

**图表配置** (ECharts):
```typescript
const chartOption = computed(() => ({
  title: {
    text: '未来估值推演',
    left: 'center'
  },
  tooltip: {
    trigger: 'axis',
    formatter: (params: any) => {
      let result = params[0].axisValue + '<br/>'
      params.forEach((param: any) => {
        result += `${param.marker} ${param.seriesName}: ${param.value.toFixed(2)}<br/>`
      })
      return result
    }
  },
  legend: {
    data: ['估值下限', '内在价值', '估值上限', '当前价格'],
    bottom: 10
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '15%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    data: props.projectionData.dates,
    boundaryGap: false
  },
  yAxis: {
    type: 'value',
    name: '价格（元）'
  },
  series: [
    {
      name: '估值下限',
      type: 'line',
      data: props.projectionData.lower_bound,
      smooth: true,
      lineStyle: { color: '#67C23A', width: 2 },
      areaStyle: { opacity: 0.1 }
    },
    {
      name: '内在价值',
      type: 'line',
      data: props.projectionData.intrinsic_value,
      smooth: true,
      lineStyle: { color: '#409EFF', width: 3 }
    },
    {
      name: '估值上限',
      type: 'line',
      data: props.projectionData.upper_bound,
      smooth: true,
      lineStyle: { color: '#F56C6C', width: 2 },
      areaStyle: { opacity: 0.1 }
    },
    {
      name: '当前价格',
      type: 'line',
      data: props.projectionData.current_price || [],
      lineStyle: { color: '#E6A23C', type: 'dashed' }
    }
  ]
}))
```

---

#### 4. WaterLevelGauge.vue

**文件位置**: `frontend/src/components/WaterLevelGauge.vue`

**核心功能**: 仪表盘样式显示当前价格在估值区间中的位置

**Props 接口**:
```typescript
interface Props {
  currentPrice: number
  lowerBound: number
  upperBound: number
  intrinsicValue: number
}
```

**图表配置** (ECharts Gauge):
```typescript
const chartOption = computed(() => {
  const { currentPrice, lowerBound, upperBound, intrinsicValue } = props
  const range = upperBound - lowerBound
  const position = ((currentPrice - lowerBound) / range) * 100

  // 根据位置确定颜色
  let color = '#67C23A' // 绿色（低估）
  if (currentPrice > upperBound) {
    color = '#F56C6C' // 红色（高估）
  } else if (currentPrice > intrinsicValue) {
    color = '#E6A23C' // 橙色（偏高）
  }

  return {
    series: [
      {
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        min: lowerBound,
        max: upperBound,
        splitNumber: 10,
        itemStyle: { color },
        progress: { show: true, width: 30 },
        pointer: { show: false },
        axisLine: {
          lineStyle: {
            width: 30,
            color: [[1, '#E6EBF8']]
          }
        },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        detail: {
          valueAnimation: true,
          formatter: '{value}',
          fontSize: 20,
          offsetCenter: [0, '20%']
        },
        data: [{ value: currentPrice }]
      }
    ],
    graphic: [
      {
        type: 'text',
        left: 'center',
        top: '60%',
        style: {
          text: getWaterLevelText(),
          fontSize: 14,
          fill: '#606266'
        }
      }
    ]
  }
})

const getWaterLevelText = () => {
  const { currentPrice, lowerBound, upperBound } = props
  if (currentPrice < lowerBound) return '低估区（买入）'
  if (currentPrice > upperBound) return '高估区（卖出）'
  return '合理区间（持有）'
}
```

---

#### 5. MultiAnchorComparison.vue

**文件位置**: `frontend/src/components/MultiAnchorComparison.vue`

**核心功能**: 柱状图对比不同估值方法的结果

**Props 接口**:
```typescript
interface Props {
  multiAnchor: {
    peg: number
    pe_historical: number
    pb: number
    dcf: number
  }
}
```

**图表配置** (ECharts Bar):
```typescript
const chartOption = computed(() => ({
  title: {
    text: '多锚点估值对比',
    left: 'center'
  },
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'shadow' }
  },
  xAxis: {
    type: 'category',
    data: ['PEG估值', '历史PE', 'PB估值', 'DCF估值']
  },
  yAxis: {
    type: 'value',
    name: '估值（元）'
  },
  series: [
    {
      name: '估值结果',
      type: 'bar',
      data: [
        props.multiAnchor.peg,
        props.multiAnchor.pe_historical,
        props.multiAnchor.pb,
        props.multiAnchor.dcf
      ],
      itemStyle: {
        color: (params: any) => {
          const colors = ['#5470C6', '#91CC75', '#FAC858', '#EE6666']
          return colors[params.dataIndex]
        }
      },
      label: {
        show: true,
        position: 'top',
        formatter: (params: any) => params.value.toFixed(2)
      }
    }
  ]
}))
```

---

#### 6. EPSTrendChart.vue

**文件位置**: `frontend/src/components/EPSTrendChart.vue`

**核心功能**: 展示历史 EPS 数据和回归趋势线

**Props 接口**:
```typescript
interface Props {
  epsData: {
    year: number
    eps: number
    forecast?: boolean
  }[]
}
```

**图表配置** (ECharts Scatter + Line):
```typescript
const chartOption = computed(() => {
  const historicalData = props.epsData.filter(d => !d.forecast)
  const forecastData = props.epsData.filter(d => d.forecast)

  return {
    title: {
      text: 'EPS 趋势与拟合',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const param = params[0]
        return `${param.name}<br/>EPS: ${param.value[1].toFixed(2)}`
      }
    },
    legend: {
      data: ['历史EPS', '预测EPS', '趋势线'],
      bottom: 10
    },
    xAxis: {
      type: 'value',
      name: '年份',
      min: (dataMin: number) => Math.floor(dataMin)
    },
    yAxis: {
      type: 'value',
      name: 'EPS（元）'
    },
    series: [
      {
        name: '历史EPS',
        type: 'scatter',
        data: historicalData.map(d => [d.year, d.eps]),
        itemStyle: { color: '#409EFF' },
        symbolSize: 10
      },
      {
        name: '预测EPS',
        type: 'scatter',
        data: forecastData.map(d => [d.year, d.eps]),
        itemStyle: { color: '#67C23A' },
        symbolSize: 10
      },
      {
        name: '趋势线',
        type: 'line',
        data: calculateTrendLine(props.epsData),
        smooth: true,
        lineStyle: { color: '#E6A23C', type: 'dashed' },
        showSymbol: false
      }
    ]
  }
})

// 计算对数回归趋势线
const calculateTrendLine = (data: typeof props.epsData) => {
  // 对数最小二乘法回归
  const validData = data.filter(d => d.eps > 0)
  const n = validData.length

  let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0
  validData.forEach(d => {
    const x = d.year
    const y = Math.log(d.eps)
    sumX += x
    sumY += y
    sumXY += x * y
    sumX2 += x * x
  })

  const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX)
  const intercept = (sumY - slope * sumX) / n

  // 生成趋势线数据点
  const startYear = validData[0].year
  const endYear = validData[validData.length - 1].year + 5
  const trendData = []

  for (let year = startYear; year <= endYear; year++) {
    const logEPS = slope * year + intercept
    trendData.push([year, Math.exp(logEPS)])
  }

  return trendData
}
```

---

### Pinia Store 设计

#### mdvaes.ts

**文件位置**: `frontend/src/stores/mdvaes.ts`

**核心功能**: MDVAES 估值状态管理

```typescript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { mdvaesApi } from '@/api/mdvaes'
import type {
  MDVAESParams,
  ValuationResult,
  GrowthMetrics,
  RiskMetrics,
  MultiAnchorResult
} from '@/types/mdvaes'

export const useMdvaesStore = defineStore('mdvaes', () => {
  // 状态
  const currentValuation = ref<ValuationResult | null>(null)
  const currentGrowthMetrics = ref<GrowthMetrics | null>(null)
  const currentRiskMetrics = ref<RiskMetrics | null>(null)
  const currentMultiAnchor = ref<MultiAnchorResult | null>(null)
  const parameterDefinitions = ref<ParameterDefinition[]>([])
  const presetParams = ref<Record<string, MDVAESParams>>({})

  const loading = ref(false)
  const error = ref<string | null>(null)

  // 计算属性
  const hasValuation = computed(() => currentValuation.value !== null)
  const signal = computed(() => currentValuation.value?.signal || 'hold')
  const confidence = computed(() => currentValuation.value?.confidence || 0)

  // 操作
  async function fetchParameters() {
    loading.value = true
    try {
      const response = await mdvaesApi.getParameters()
      parameterDefinitions.value = response.data.parameters
      presetParams.value = response.data.presets
    } catch (err: any) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function calculateValuation(
    symbol: string,
    params: MDVAESParams,
    calculationDate?: string
  ) {
    loading.value = true
    error.value = null

    try {
      const response = await mdvaesApi.getValuation({
        symbol,
        calculation_date: calculationDate || new Date().toISOString().split('T')[0],
        params
      })

      currentValuation.value = response.data.valuation
      currentGrowthMetrics.value = response.data.growth_metrics
      currentRiskMetrics.value = response.data.risk_metrics
      currentMultiAnchor.value = response.data.multi_anchor

      return response.data
    } catch (err: any) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  function getPresetParams(preset: string): MDVAESParams {
    return presetParams.value[preset] || getDefaultParams()
  }

  function getDefaultParams(): MDVAESParams {
    return {
      forecast_years: 5,
      min_forecast_count: 3,
      peg_base: 1.0,
      peg_interest_sensitivity: 0.5,
      risk_adjustment: 0.1,
      anchor_weight: {
        peg: 0.4,
        pe_historical: 0.3,
        pb: 0.15,
        dcf: 0.15
      },
      signal_mode: 'valuation_range',
      safety_margin_buy: 0.8,
      safety_margin_sell: 1.2,
      preset: 'neutral'
    }
  }

  async function saveUserParams(symbol: string, params: MDVAESParams) {
    // 调用保存参数 API
    await mdvaesApi.saveUserParams(symbol, params)
  }

  function clearValuation() {
    currentValuation.value = null
    currentGrowthMetrics.value = null
    currentRiskMetrics.value = null
    currentMultiAnchor.value = null
    error.value = null
  }

  return {
    // 状态
    currentValuation,
    currentGrowthMetrics,
    currentRiskMetrics,
    currentMultiAnchor,
    parameterDefinitions,
    presetParams,
    loading,
    error,
    // 计算属性
    hasValuation,
    signal,
    confidence,
    // 操作
    fetchParameters,
    calculateValuation,
    getPresetParams,
    getDefaultParams,
    saveUserParams,
    clearValuation
  }
})
```

---

### API 集成

#### mdvaes.ts

**文件位置**: `frontend/src/api/mdvaes.ts`

```typescript
import axios from 'axios'
import type {
  MDVAESParams,
  ValuationResult,
  ParameterDefinition,
  PresetParams
} from '@/types/mdvaes'

const API_BASE = '/api/mdvaes'

export const mdvaesApi = {
  /**
   * 获取股票估值
   */
  async getValuation(request: {
    symbol: string
    calculation_date: string
    params: MDVAESParams
  }) {
    const response = await axios.post(`${API_BASE}/valuation`, request)
    return response.data
  },

  /**
   * 获取参数定义
   */
  async getParameters() {
    const response = await axios.get(`${API_BASE}/parameters`)
    return response.data
  },

  /**
   * 保存用户自定义参数
   */
  async saveUserParams(symbol: string, params: MDVAESParams) {
    const response = await axios.post(`${API_BASE}/user-params`, {
      symbol,
      params
    })
    return response.data
  },

  /**
   * 获取用户保存的参数
   */
  async getUserParams(symbol: string) {
    const response = await axios.get(`${API_BASE}/user-params/${symbol}`)
    return response.data
  },

  /**
   * 获取估值历史缓存
   */
  async getValuationHistory(symbol: string, days: number = 30) {
    const response = await axios.get(`${API_BASE}/history/${symbol}`, {
      params: { days }
    })
    return response.data
  }
}
```

---

### TypeScript 类型定义

#### mdvaes.ts

**文件位置**: `frontend/src/types/mdvaes.ts`

```typescript
/**
 * MDVAES 参数
 */
export interface MDVAESParams {
  forecast_years: number
  min_forecast_count: number
  peg_base: number
  peg_interest_sensitivity: number
  risk_adjustment: number
  anchor_weight: {
    peg: number
    pe_historical: number
    pb: number
    dcf: number
  }
  signal_mode: 'valuation_range' | 'safety_margin'
  safety_margin_buy: number
  safety_margin_sell: number
  preset?: 'conservative' | 'neutral' | 'aggressive' | 'custom'
}

/**
 * 估值结果
 */
export interface ValuationResult {
  intrinsic_value: number
  lower_bound: number
  upper_bound: number
  confidence: number
  valuation_method: {
    peg: number
    pe_historical: number
    pb: number
    dcf: number
  }
  signal: 'buy' | 'sell' | 'hold'
}

/**
 * 增长指标
 */
export interface GrowthMetrics {
  cagr: number
  growth_rate: number
  r_squared: number
  growth_quality_score: number
  trend_stability: 'stable' | 'volatile' | 'declining'
}

/**
 * 风险指标
 */
export interface RiskMetrics {
  debt_to_assets: number
  current_ratio: number
  quick_ratio: number
  cashflow_to_income: number
  risk_level: 'low' | 'medium' | 'high'
}

/**
 * 多锚点结果
 */
export interface MultiAnchorResult {
  peg: number
  pe_historical: number
  pb: number
  dcf: number
}

/**
 * 参数定义
 */
export interface ParameterDefinition {
  name: string
  type: 'int' | 'float' | 'string' | 'boolean'
  default: any
  range?: {
    min: number
    max: number
  }
  description: string
  required: boolean
}

/**
 * 预设参数
 */
export type PresetParams = Record<string, MDVAESParams>

/**
 * EPS 数据点
 */
export interface EPSData {
  year: number
  eps: number
  forecast?: boolean
}

/**
 * 估值推演数据
 */
export interface ValuationProjection {
  dates: string[]
  lower_bound: number[]
  intrinsic_value: number[]
  upper_bound: number[]
  current_price?: number[]
}

/**
 * 完整估值响应
 */
export interface ValuationResponse {
  symbol: string
  calculation_date: string
  current_price: number
  valuation: ValuationResult
  signal: string
  growth_metrics: GrowthMetrics
  risk_metrics: RiskMetrics
  multi_anchor: MultiAnchorResult
  charts: {
    valuation_projection: ValuationProjection
    water_level: any
    multi_anchor_comparison: any
    eps_trend: EPSData[]
  }
}
```

---

### 与现有回测框架集成

#### BacktestControlPanel.vue 扩展

**修改位置**: `frontend/src/views/Backtest/BacktestControlPanel.vue`

**扩展内容**:

```vue
<template>
  <!-- 现有内容保持不变，添加 MDVAES 特定配置 -->

  <!-- 策略参数配置区域 -->
  <div v-if="form.strategy_id === 'mdvaes'" class="mdvaes-config">
    <el-divider>MDVAES 估值参数</el-divider>

    <MDVAESParamsConfig
      v-model="form.strategy_params"
      :symbol="form.stock_code"
      :disabled="backtestStatus?.status === 'running'"
    />
  </div>
</template>

<script setup lang="ts">
import MDVAESParamsConfig from '@/components/MDVAESParamsConfig.vue'

// 扩展策略参数类型
interface StrategyParams {
  // 现有策略参数...
  [key: string]: any

  // MDVAES 特定参数
  preset?: 'conservative' | 'neutral' | 'aggressive' | 'custom'
  forecast_years?: number
  peg_base?: number
  // ... 其他 MDVAES 参数
}

const form = ref<{
  stock_code: string
  start_date: string
  end_date: string
  initial_capital: number
  min_purchase: number
  strategy_id: string
  strategy_params: StrategyParams
}>({
  // ... 现有字段
  strategy_id: '',
  strategy_params: {}
})

// 监听策略变更，加载默认参数
watch(() => form.value.strategy_id, async (newStrategyId) => {
  if (newStrategyId === 'mdvaes') {
    const mdvaesStore = useMdvaesStore()
    await mdvaesStore.fetchParameters()
    form.value.strategy_params = mdvaesStore.getDefaultParams()
  }
})
</script>
```

---

### 性能优化

#### 1. 组件懒加载

```typescript
// router/index.ts
const MDVAESValuationView = defineAsyncComponent(() =>
  import('@/views/MDVAES/MDVAESValuationView.vue')
)

const MDVAESParamsConfig = defineAsyncComponent(() =>
  import('@/components/MDVAESParamsConfig.vue')
)
```

#### 2. 图表防抖渲染

```typescript
import { debounce } from 'lodash-es'

const updateChart = debounce(() => {
  chartRef.value?.setOption(chartOption.value)
}, 300)
```

#### 3. 计算属性缓存

```typescript
// 使用 computed 缓存复杂计算
const valuationRange = computed(() => {
  return currentValuation.value?.upper_bound - currentValuation.value?.lower_bound || 0
})
```

#### 4. 虚拟滚动

```vue
<!-- 对于长列表使用虚拟滚动 -->
<el-table-v2
  :columns="columns"
  :data="largeDataList"
  :width="700"
  :height="400"
  fixed
/>
```

---

### UI/UX 设计

#### 设计系统一致性

1. **颜色规范**:
   - 买入信号: `#67C23A` (绿色)
   - 持有信号: `#E6A23C` (橙色)
   - 卖出信号: `#F56C6C` (红色)
   - 估值区间: 蓝色渐变 `#409EFF` → `#A0CFFF`

2. **间距规范**:
   - 组件间距: `20px` (gap)
   - 卡片内边距: `20px` (padding)
   - 表单项间距: `18px` (margin-bottom)

3. **字体规范**:
   - 标题: `18px` font-weight: 500
   - 数值: `24px` font-weight: bold
   - 标签: `14px` color: `#606266`

4. **响应式断点**:
   - `< 768px`: 单列布局
   - `768px - 1200px`: 两列布局
   - `> 1200px`: 三列布局

---

**Part 2B 完成，接下来是 Part 3: 跨领域关注点**

---

## Part 3: 跨领域关注点

### 前后端集成

#### 1. 数据同步流程

```
┌─────────────────────────────────────────────────────────────┐
│                        定时任务层                            │
│  APScheduler (每个交易日 16:30)                             │
│  ┌──────────────────────────────────────────────────┐      │
│  | daily_mdvaes_data_sync()                         │      │
│  | 1. 调用 MDVAESDataSyncService                    │      │
│  | 2. 从 Tushare 同步数据到 MongoDB                  │      │
│  | 3. 清理 Redis 缓存                               │      │
│  | 4. 记录同步日志                                  │      │
│  └──────────────────────────────────────────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      数据层                                  │
│  MongoDB Collections:                                       │
│  - mdvaes_analyst_forecasts (分析师预测)                     │
│  - mdvaes_eps_history (EPS 历史)                             │
│  - mdvaes_pe_history (PE 历史)                               │
│  - mdvaes_cashflow_data (现金流数据)                         │
│  - mdvaes_financial_ratios (财务比率)                        │
│  - mdvaes_bond_rate (国债收益率)                             │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                      API 层                                  │
│  GET /api/mdvaes/valuation                                   │
│  - 从 MongoDB 读取数据                                       │
│  - 调用 MDVAESCalculator 计算                                │
│  - 生成可视化图表数据                                        │
│  - 返回完整估值结果                                          │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                     前端层                                   │
│  MDVAESValuationPanel.vue                                    │
│  - 调用 mdvaesApi.getValuation()                             │
│  - 展示估值结果和图表                                        │
│  - 响应用户参数调整                                          │
└─────────────────────────────────────────────────────────────┘
```

#### 2. WebSocket 实时通信

**回测进度推送**:

```python
# 后端: app/services/backtest_engine_service.py

async def _update_progress(self, backtest_id: str, progress: float):
    """推送回测进度"""
    message = {
        "type": "progress",
        "data": {
            "backtest_id": backtest_id,
            "progress": progress,
            # MDVAES 特有数据
            "current_valuation": self._get_current_valuation(),
            "valuation_signal": self._get_current_signal()
        }
    }
    await self.websocket_manager.send_to_backtest(backtest_id, message)
```

**前端接收处理**:

```typescript
// stores/backtestEngine.ts

function handleWSMessage(message: WSMessage) {
  switch (message.type) {
    case 'progress':
      backtestStatus.value = { ...backtestStatus.value, execution_info: message.data }
      // MDVAES 特有处理
      if (message.data.current_valuation) {
        mdvaesStore.currentValuation = message.data.current_valuation
      }
      break
  }
}
```

#### 3. API 版本兼容性

**统一响应格式**:

```python
# app/core/response.py

def ok(data: Any = None, message: str = "success") -> JSONResponse:
    """统一成功响应"""
    return JSONResponse({
        "success": True,
        "data": data,
        "message": message,
        "timestamp": datetime.now().isoformat()
    })

def error(message: str, code: int = 400) -> JSONResponse:
    """统一错误响应"""
    return JSONResponse(
        {
            "success": False,
            "message": message,
            "timestamp": datetime.now().isoformat()
        },
        status_code=code
    )
```

**前端拦截器处理**:

```typescript
// api/axios.ts

axios.interceptors.response.use(
  (response) => {
    const { success, data, message } = response.data
    if (success) {
      return data
    } else {
      ElMessage.error(message || '请求失败')
      return Promise.reject(new Error(message))
    }
  },
  (error) => {
    if (error.response?.status === 401) {
      // Token 过期，跳转登录
      router.push('/login')
    }
    return Promise.reject(error)
  }
)
```

---

### 测试策略

#### 1. 单元测试

**后端单元测试** (pytest):

```python
# tests/services/test_mdvaes_calculator.py

import pytest
from app.services.mdvaes_calculator import MDVAESCalculator
from app.domain.mdvaes import MDVAESParams, GrowthMetrics, RiskMetrics

class TestMDVAESCalculator:
    """MDVAES 计算器单元测试"""

    @pytest.fixture
    def calculator(self):
        return MDVAESCalculator()

    @pytest.fixture
    def sample_params(self):
        return MDVAESParams(
            forecast_years=5,
            peg_base=1.0,
            risk_adjustment=0.1,
            anchor_weight={"peg": 0.4, "pe_historical": 0.3, "pb": 0.15, "dcf": 0.15}
        )

    @pytest.fixture
    def sample_growth_metrics(self):
        return GrowthMetrics(
            cagr=0.15,
            growth_rate=0.12,
            r_squared=0.89,
            growth_quality_score=0.8,
            trend_stability="stable"
        )

    @pytest.fixture
    def sample_risk_metrics(self):
        return RiskMetrics(
            debt_to_assets=0.92,
            current_ratio=1.05,
            quick_ratio=0.98,
            cashflow_to_income=1.2,
            risk_level="medium"
        )

    def test_peg_valuation(self, calculator, sample_growth_metrics, sample_params):
        """测试 PEG 估值"""
        eps = 2.5
        bond_rate = 0.0275  # 2.75%

        valuation = calculator.calc_peg_valuation(
            eps, sample_growth_metrics, bond_rate, sample_params
        )

        assert valuation > 0
        assert valuation == pytest.approx(eps * (1 + sample_growth_metrics.growth_rate) * sample_params.peg_base, rel=0.1)

    def test_multi_anchor_valuation(self, calculator, sample_growth_metrics, sample_risk_metrics, sample_params):
        """测试多锚点估值"""
        result = calculator.calc_multi_anchor(
            sample_growth_metrics,
            sample_risk_metrics,
            sample_params
        )

        assert "peg" in result
        assert "pe_historical" in result
        assert "pb" in result
        assert "dcf" in result
        assert all(v > 0 for v in result.values())

    def test_risk_adjustment(self, calculator, sample_risk_metrics):
        """测试风险折价计算"""
        base_value = 15.0
        risk_adjustment = 0.1

        adjusted_value = calculator.apply_risk_adjustment(
            base_value,
            sample_risk_metrics,
            risk_adjustment
        )

        # 中等风险应该折价 10%
        assert adjusted_value == pytest.approx(base_value * (1 - risk_adjustment), rel=0.01)

    def test_signal_generation(self, calculator):
        """测试交易信号生成"""
        current_price = 12.0
        lower_bound = 10.0
        upper_bound = 15.0

        signal = calculator.generate_signal(current_price, lower_bound, upper_bound)
        assert signal == "hold"

        # 低估
        signal = calculator.generate_signal(8.0, lower_bound, upper_bound)
        assert signal == "buy"

        # 高估
        signal = calculator.generate_signal(18.0, lower_bound, upper_bound)
        assert signal == "sell"
```

**前端单元测试** (Vitest):

```typescript
// components/__tests__/MDVAESParamsConfig.spec.ts

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import MDVAESParamsConfig from '../MDVAESParamsConfig.vue'
import { useMdvaesStore } from '@/stores/mdvaes'

describe('MDVAESParamsConfig', () => {
  let wrapper: any
  let mdvaesStore: any

  beforeEach(() => {
    const pinia = createPinia()
    mdvaesStore = useMdvaesStore(pinia)

    wrapper = mount(MDVAESParamsConfig, {
      props: {
        modelValue: {
          forecast_years: 5,
          peg_base: 1.0,
          preset: 'neutral'
        },
        symbol: '000001.SZ'
      },
      global: {
        plugins: [pinia]
      }
    })
  })

  it('正确渲染预设选择器', () => {
    const radioButtons = wrapper.findAll('.el-radio-button')
    expect(radioButtons).toHaveLength(4)
    expect(radioButtons[0].text()).toBe('保守')
    expect(radioButtons[1].text()).toBe('中性')
    expect(radioButtons[2].text()).toBe('激进')
    expect(radioButtons[3].text()).toBe('自定义')
  })

  it('选择预设时更新参数', async () => {
    const conservativeRadio = wrapper.findAll('.el-radio-button')[0]
    await conservativeRadio.trigger('click')

    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    const emittedParams = wrapper.emitted('update:modelValue')[0][0]
    expect(emittedParams.preset).toBe('conservative')
  })

  it('参数变更触发估值预览', async () => {
    const spy = vi.spyOn(mdvaesStore, 'calculateValuation')

    const slider = wrapper.find('.el-slider input[type="range"]')
    await slider.setValue(3)

    // 防抖后应该调用计算
    await new Promise(resolve => setTimeout(resolve, 600))
    expect(spy).toHaveBeenCalled()
  })
})
```

#### 2. 集成测试

**API 集成测试**:

```python
# tests/api/test_mdvaes_integration.py

import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
class TestMDVAESIntegration:
    """MDVAES API 集成测试"""

    async def test_valuation_flow(self, async_client: AsyncClient, test_token):
        """测试完整估值流程"""
        headers = {"Authorization": f"Bearer {test_token}"}

        # 1. 获取参数定义
        response = await async_client.get("/api/mdvaes/parameters", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert "parameters" in data["data"]
        assert "presets" in data["data"]

        # 2. 计算估值（使用中性预设）
        valuation_request = {
            "symbol": "000001.SZ",
            "calculation_date": "2024-01-15",
            "params": {
                "preset": "neutral"
            }
        }
        response = await async_client.post("/api/mdvaes/valuation", json=valuation_request, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert "valuation" in data["data"]
        assert "growth_metrics" in data["data"]
        assert "risk_metrics" in data["data"]
        assert data["data"]["valuation"]["intrinsic_value"] > 0

        # 3. 使用自定义参数计算估值
        custom_request = {
            "symbol": "000001.SZ",
            "calculation_date": "2024-01-15",
            "params": {
                "preset": "custom",
                "forecast_years": 3,
                "peg_base": 0.8,
                "risk_adjustment": 0.15
            }
        }
        response = await async_client.post("/api/mdvaes/valuation", json=custom_request, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        # 自定义参数应该产生不同结果
        assert data["data"]["valuation"]["confidence"] != valuation_request["confidence"]

    async def test_backtest_integration(self, async_client: AsyncClient, test_token):
        """测试回测集成"""
        headers = {"Authorization": f"Bearer {test_token}"}

        backtest_request = {
            "stock_code": "000001.SZ",
            "start_date": "2020-01-01",
            "end_date": "2024-12-31",
            "initial_capital": 100000,
            "strategy_id": "mdvaes",
            "strategy_params": {
                "preset": "neutral",
                "signal_mode": "valuation_range"
            }
        }

        # 启动回测
        response = await async_client.post("/api/backtest/start", json=backtest_request, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        backtest_id = data["data"]["backtest_id"]

        # 等待回测完成
        await asyncio.sleep(5)

        # 获取结果
        response = await async_client.get(f"/api/backtest/{backtest_id}/results", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert "return_metrics" in data["data"]
        assert "trading_stats" in data["data"]
```

#### 3. 端到端测试

**E2E 测试** (Playwright):

```typescript
// e2e/tests/mdvaes.spec.ts

import { test, expect } from '@playwright/test'

test.describe('MDVAES 估值流程', () => {
  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('http://localhost:8080/login')
    await page.fill('input[name="username"]', 'testuser')
    await page.fill('input[name="password"]', 'password123')
    await page.click('button[type="submit"]')
    await page.waitForURL('**/dashboard')
  })

  test('完整估值流程', async ({ page }) => {
    // 1. 导航到 MDVAES 估值页面
    await page.click('text=MDVAES 估值')
    await page.waitForURL('**/mdvaes/valuation')

    // 2. 选择股票
    await page.fill('input[placeholder="输入股票代码或名称"]', '000001.SZ')
    await page.click('.el-autocomplete-suggestion')

    // 3. 选择预设参数
    await page.click('label:has-text("中性")')

    // 4. 等待估值结果
    await page.waitForSelector('.mdvaes-valuation-panel')

    // 5. 验证估值结果
    const intrinsicValue = await page.textContent('.metric-item:has-text("内在价值") .metric-value')
    expect(parseFloat(intrinsicValue!)).toBeGreaterThan(0)

    // 6. 验证图表渲染
    const charts = await page.locator('canvas').count()
    expect(charts).toBeGreaterThanOrEqual(4)

    // 7. 切换到自定义参数
    await page.click('label:has-text("自定义")')

    // 8. 调整滑块
    const slider = page.locator('.el-slider').first
    await slider.click({ position: { x: 100, y: 0 } })

    // 9. 验证估值预览更新
    await page.waitForTimeout(600) // 防抖延迟
    const newIntrinsicValue = await page.textContent('.metric-item:has-text("内在价值") .metric-value')
    expect(newIntrinsicValue).not.toBe(intrinsicValue)
  })

  test('MDVAES 回测流程', async ({ page }) => {
    // 1. 导航到回测控制面板
    await page.goto('http://localhost:8080/backtest/control')

    // 2. 填写回测参数
    await page.fill('input[placeholder="股票代码"]', '000001.SZ')
    await page.fill('input[placeholder="开始日期"]', '2020-01-01')
    await page.fill('input[placeholder="结束日期"]', '2024-12-31')
    await page.fill('input[placeholder="初始资金"]', '100000')

    // 3. 选择 MDVAES 策略
    await page.click('.el-select-dropdown:has-text("MDVAES")')

    // 4. 配置策略参数
    await page.click('label:has-text("中性")')
    await page.click('label:has-text("估值区间")')

    // 5. 启动回测
    await page.click('button:has-text("开始回测")')

    // 6. 验证进度显示
    await page.waitForSelector('.el-progress-bar')
    await expect(page.locator('.el-progress-bar__text')).toContainText('%')

    // 7. 等待回测完成
    await page.waitForSelector('button:has-text("重新开始")', { timeout: 60000 })

    // 8. 验证结果显示
    await expect(page.locator('.backtest-results')).toBeVisible()
    const totalReturn = await page.textContent('.return-metrics:has-text("总收益率")')
    expect(parseFloat(totalReturn!)).toBeDefined()
  })
})
```

#### 4. 测试覆盖率目标

| 模块 | 单元测试覆盖率 | 集成测试覆盖率 | E2E 覆盖 |
|-----|-------------|-------------|---------|
| MDVAESCalculator | ≥ 90% | ≥ 70% | - |
| MDVAESStrategy | ≥ 85% | ≥ 70% | 核心流程 |
| MDVAESDataSyncService | ≥ 80% | ≥ 60% | - |
| API 端点 | ≥ 80% | ≥ 80% | 核心流程 |
| Vue 组件 | ≥ 80% | ≥ 60% | 核心交互 |
| Pinia Store | ≥ 85% | ≥ 70% | - |

---

### 部署与 DevOps

#### 1. 环境配置

**Docker Compose 配置**:

```yaml
# docker-compose.yml

version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - MONGODB_HOST=mongodb
      - REDIS_HOST=redis
      - TUSHARE_TOKEN=${TUSHARE_TOKEN}
      - DEBUG=false
    depends_on:
      - mongodb
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "8080:80"
    depends_on:
      - backend
    restart: unless-stopped

  mongodb:
    image: mongo:7.0
    ports:
      - "27017:27017"
    environment:
      - MONGO_INITDB_ROOT_USERNAME=admin
      - MONGO_INITDB_ROOT_PASSWORD=password
    volumes:
      - mongodb_data:/data/db
      - ./scripts/init-mongo.js:/docker-entrypoint-initdb.d/init-mongo.js
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  worker:
    build: ./backend
    command: python -m app.worker.mdvaes_sync_worker
    environment:
      - MONGODB_HOST=mongodb
      - REDIS_HOST=redis
      - TUSHARE_TOKEN=${TUSHARE_TOKEN}
    depends_on:
      - mongodb
      - redis
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

volumes:
  mongodb_data:
  redis_data:
```

#### 2. 数据库迁移脚本

```javascript
// scripts/init-mongo.js

// 创建 MDVAES 集合和索引
db = db.getSiblingDB('tradingagents');

// 分析师预测
db.createCollection('mdvaes_analyst_forecasts');
db.mdvaes_analyst_forecasts.createIndex({
  ts_code: 1,
  quarter: 1,
  report_date: -1
});

// EPS 历史
db.createCollection('mdvaes_eps_history');
db.mdvaes_eps_history.createIndex({
  ts_code: 1,
  end_date: -1
});

// PE 历史
db.createCollection('mdvaes_pe_history');
db.mdvaes_pe_history.createIndex({
  ts_code: 1,
  trade_date: -1
});

// 现金流数据
db.createCollection('mdvaes_cashflow_data');
db.mdvaes_cashflow_data.createIndex({
  ts_code: 1,
  end_date: -1
});

// 财务比率
db.createCollection('mdvaes_financial_ratios');
db.mdvaes_financial_ratios.createIndex({
  ts_code: 1,
  end_date: -1
});

// 国债收益率
db.createCollection('mdvaes_bond_rate');
db.mdvaes_bond_rate.createIndex({
  trade_date: -1,
  curve_term: 1
});

// 估值缓存
db.createCollection('mdvaes_valuation_cache');
db.mdvaes_valuation_cache.createIndex({
  ts_code: 1,
  calculation_date: -1,
  params_hash: 1
});

print('✅ MDVAES 数据库集合和索引创建完成');
```

#### 3. CI/CD 流程

**GitHub Actions 配置**:

```yaml
# .github/workflows/ci.yml

name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    services:
      mongodb:
        image: mongo:7.0
        env:
          MONGO_INITDB_ROOT_USERNAME: admin
          MONGO_INITDB_ROOT_PASSWORD: password
        ports:
          - 27017:27017
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov

      - name: Run tests
        env:
          MONGODB_HOST: localhost
          REDIS_HOST: localhost
        run: |
          cd backend
          pytest tests/ --cov=app --cov-report=xml --cov-report=html

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml

  frontend-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          cd frontend
          npm ci

      - name: Run linter
        run: |
          cd frontend
          npm run lint

      - name: Run tests
        run: |
          cd frontend
          npm run test:unit

      - name: Build
        run: |
          cd frontend
          npm run build

  e2e-tests:
    runs-on: ubuntu-latest
    needs: [backend-tests, frontend-tests]

    steps:
      - uses: actions/checkout@v3

      - name: Start services
        run: docker-compose up -d

      - name: Install Playwright
        run: |
          cd frontend
          npx playwright install --with-deps

      - name: Run E2E tests
        run: |
          cd frontend
          npm run test:e2e

      - name: Stop services
        run: docker-compose down
```

#### 4. 监控与日志

**日志结构化**:

```python
# app/core/logging.py

import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """结构化日志格式"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        if hasattr(record, 'mdvaes_context'):
            log_data.update(record.mdvaes_context)

        return json.dumps(log_data)

# 使用示例
logger = logging.getLogger(__name__)
logger.info("估值计算完成", extra={
    "mdvaes_context": {
        "symbol": "000001.SZ",
        "intrinsic_value": 15.5,
        "calculation_time": 0.23
    }
})
```

**Prometheus 指标**:

```python
# app/core/metrics.py

from prometheus_client import Counter, Histogram, Gauge

# 估值计算指标
VALUATION_REQUESTS = Counter(
    'mdvaes_valuation_requests_total',
    'Total valuation requests',
    ['symbol', 'preset']
)

VALUATION_DURATION = Histogram(
    'mdvaes_valuation_duration_seconds',
    'Valuation calculation duration',
    ['symbol']
)

VALUATION_ERRORS = Counter(
    'mdvaes_valuation_errors_total',
    'Total valuation errors',
    ['error_type']
)

# 数据同步指标
SYNC_DURATION = Histogram(
    'mdvaes_sync_duration_seconds',
    'Data sync duration',
    ['data_type']
)

SYNC_RECORDS = Gauge(
    'mdvaes_sync_records_total',
    'Total records in collections',
    ['collection_name']
)

# 使用示例
@VALUATION_DURATION.time()
def calculate_valuation(symbol: str, params: MDVAESParams):
    VALUATION_REQUESTS.labels(symbol=symbol, preset=params.preset).inc()
    try:
        # 计算逻辑
        pass
    except Exception as e:
        VALUATION_ERRORS.labels(error_type=type(e).__name__).inc()
        raise
```

---

### 文档与培训

#### 1. 用户文档

**MDVAES 使用指南**:

```markdown
# MDVAES 估值模型使用指南

## 什么是 MDVAES？

MDVAES（Multi-Dimensional Value Anchoring Evaluation System）是一个基于基本面分析的多维度价值锚定评估系统。

## 核心功能

### 1. 估值计算
- 增长率透视：使用对数最小二乘法回归分析 EPS 增长率
- R² 拟合优度：评估增长趋势的稳定性
- 宏观利率联动 PEG：基于无风险利率的动态 PEG 估值
- 多叉验证：结合 PE、PB、DCF 多种方法交叉验证

### 2. 成长能力分析
- CAGR 计算：复合年均增长率
- 增长质量：收入增长与利润增长的匹配度

### 3. 风险评估
- 财务风险：资产负债率、流动比率、速动比率
- 现金流风险：经营现金流/净利润比率
- 压力测试：极端情况下的估值敏感性分析

## 快速开始

### 查看股票估值

1. 进入"MDVAES 估值"页面
2. 输入股票代码（如：000001.SZ）
3. 选择参数预设（保守/中性/激进）或自定义参数
4. 查看估值结果和图表

### 启动回测

1. 进入"回测控制面板"
2. 填写回测参数（日期范围、初始资金等）
3. 选择策略为"MDVAES"
4. 配置 MDVAES 参数
5. 点击"开始回测"

## 参数说明

### 预设参数

| 预设 | 特点 | 适用场景 |
|-----|------|---------|
| 保守 | 低风险偏好，严格安全边际 | 退休账户、保守投资者 |
| 中性 | 平衡风险和收益 | 一般投资者 |
| 激进 | 高风险偏好，追求成长 | 成长型投资者 |

### 自定义参数

- **预测年数**：EPS 预测的年数（1-10年）
- **基础 PEG**：PEG 估值的基础倍数（0.5-2.0）
- **风险折价**：根据风险调整估值的比例（0-30%）
- **多锚点权重**：各估值方法的权重分配

## 交易信号

### 估值区间模式
- **买入**：价格 < 估值下限
- **持有**：估值下限 ≤ 价格 ≤ 估值上限
- **卖出**：价格 > 估值上限

### 安全边际模式
- **买入**：价格 ≤ 估值 × 安全边际买入系数（默认80%）
- **持有**：估值 × 80% < 价格 < 估值 × 120%
- **卖出**：价格 ≥ 估值 × 安全边际卖出系数（默认120%）

## 常见问题

**Q: 为什么显示"数据不足"？**
A: 该股票的历史财务数据或分析师预测数据不足，无法进行可靠的估值计算。

**Q: 估值结果的置信度是什么意思？**
A: 置信度反映估值结果的可信程度，基于 R² 拟合优度、数据完整性等计算。

**Q: 如何保存自定义参数？**
A: 调整参数后点击"保存参数"按钮，下次选择该股票时会自动加载。
```

#### 2. 开发者文档

**API 接口文档**:

```markdown
# MDVAES API 开发文档

## 认证

所有 API 请求需要在 Header 中携带 JWT Token：

```
Authorization: Bearer <token>
```

## 端点

### 获取估值

`POST /api/mdvaes/valuation`

**请求体**：
\`\`\`json
{
  "symbol": "000001.SZ",
  "calculation_date": "2024-01-15",
  "params": {
    "preset": "neutral"
  }
}
\`\`\`

**响应**：
\`\`\`json
{
  "success": true,
  "data": {
    "symbol": "000001.SZ",
    "valuation": { ... },
    "growth_metrics": { ... },
    "risk_metrics": { ... }
  }
}
\`\`\`

### 获取参数定义

`GET /api/mdvaes/parameters`

**响应**：
\`\`\`json
{
  "success": true,
  "data": {
    "parameters": [ ... ],
    "presets": { ... }
  }
}
\`\`\`

## 错误码

| 错误码 | 说明 |
|-------|------|
| 400 | 参数错误 |
| 401 | 未认证 |
| 403 | 权限不足 |
| 404 | 数据不存在 |
| 500 | 服务器错误 |
```

#### 3. 运维文档

**部署手册**:

```markdown
# MDVAES 部署手册

## 系统要求

- Docker 20.10+
- Docker Compose 2.0+
- 8GB RAM
- 50GB 磁盘空间

## 部署步骤

### 1. 环境准备

\`\`\`bash
# 克隆代码
git clone https://github.com/your-org/TradingAgents-CN.git
cd TradingAgents-CN

# 配置环境变量
cp .env.example .env
vi .env  # 填写 TUSHARE_TOKEN 等配置
\`\`\`

### 2. 构建镜像

\`\`\`bash
docker-compose build
\`\`\`

### 3. 启动服务

\`\`\`bash
docker-compose up -d
\`\`\`

### 4. 初始化数据库

\`\`\`bash
docker-compose exec backend python -m app.scripts.init_mdvaes_db
\`\`\`

### 5. 验证部署

\`\`\`bash
# 检查服务状态
docker-compose ps

# 检查日志
docker-compose logs -f backend

# 健康检查
curl http://localhost:8000/api/health
\`\`\`

## 数据同步

### 手动同步

\`\`\`bash
docker-compose exec worker python -m app.worker.manual_mdvaes_sync
\`\`\`

### 检查同步状态

\`\`\`bash
docker-compose exec backend python -m app.scripts.check_sync_status
\`\`\`

## 监控

### Prometheus 指标

- `http://localhost:8000/metrics`

### 日志

- 后端日志：`./logs/backend.log`
- Worker 日志：`./logs/worker.log`
- 前端日志：浏览器控制台

## 故障排查

### 数据同步失败

1. 检查 TUSHARE_TOKEN 是否有效
2. 检查网络连接
3. 查看同步日志

### 估值计算超时

1. 检查数据库连接
2. 检查 Redis 缓存
3. 增加计算超时时间

### 回测启动失败

1. 检查股票数据完整性
2. 检查参数配置
3. 查看回测日志
```

---

### 性能优化

#### 1. 缓存策略

**多级缓存架构**:

```
L1: 内存缓存 (应用内)
  ↓ miss
L2: Redis 缓存 (分布式)
  ↓ miss
L3: MongoDB (持久化)
```

**缓存实现**:

```python
# app/services/mdvaes_cache_service.py

from functools import lru_cache
from app.core.database import get_redis_client
import hashlib
import json

class MDVAESCacheService:
    """MDVAES 缓存服务"""

    def __init__(self):
        self.redis = None
        self.memory_cache = {}

    async def get_redis(self):
        if self.redis is None:
            self.redis = await get_redis_client()
        return self.redis

    def _get_params_hash(self, params: MDVAESParams) -> str:
        """生成参数哈希"""
        params_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(params_str.encode()).hexdigest()

    async def get_valuation(
        self,
        symbol: str,
        calculation_date: str,
        params: MDVAESParams
    ) -> Optional[ValuationResult]:
        """获取缓存的估值结果"""
        params_hash = self._get_params_hash(params)
        cache_key = f"mdvaes:valuation:{symbol}:{calculation_date}:{params_hash}"

        # L1: 内存缓存
        if cache_key in self.memory_cache:
            return self.memory_cache[cache_key]

        # L2: Redis 缓存
        redis = await self.get_redis()
        cached = await redis.get(cache_key)
        if cached:
            result = json.loads(cached)
            # 回填内存缓存
            self.memory_cache[cache_key] = result
            return result

        return None

    async def set_valuation(
        self,
        symbol: str,
        calculation_date: str,
        params: MDVAESParams,
        result: ValuationResult,
        ttl: int = 3600
    ):
        """缓存估值结果"""
        params_hash = self._get_params_hash(params)
        cache_key = f"mdvaes:valuation:{symbol}:{calculation_date}:{params_hash}"

        # L1: 内存缓存
        self.memory_cache[cache_key] = result

        # L2: Redis 缓存
        redis = await self.get_redis()
        await redis.setex(cache_key, ttl, json.dumps(result))

    async def invalidate_symbol(self, symbol: str):
        """使股票的所有缓存失效"""
        redis = await self.get_redis()
        pattern = f"mdvaes:valuation:{symbol}:*"
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)

        # 清空内存缓存
        keys_to_remove = [k for k in self.memory_cache.keys() if k.startswith(f"mdvaes:valuation:{symbol}:")]
        for key in keys_to_remove:
            del self.memory_cache[key]
```

#### 2. 数据库查询优化

**批量查询**:

```python
# app/services/mdvaes_data_reader.py

class MDVAESDataReader:
    """MDVAES 数据读取器 - 优化版"""

    async def get_eps_forecast_batch(
        self,
        symbols: List[str],
        target_year: int,
        current_date: str
    ) -> Dict[str, List[EPSForecast]]:
        """批量获取多只股票的 EPS 预测"""
        results = await self.db.mdvaes_analyst_forecasts.find({
            "ts_code": {"$in": symbols},
            "target_year": target_year,
            "forecast_date": {"$lte": current_date}
        }).to_list(None)

        # 按股票分组
        grouped = {}
        for r in results:
            symbol = r["ts_code"]
            if symbol not in grouped:
                grouped[symbol] = []
            grouped[symbol].append(EPSForecast.from_dict(r))

        return grouped

    async def get_financial_data_batch(
        self,
        symbols: List[str],
        end_date: str
    ) -> Dict[str, FinancialData]:
        """批量获取财务数据"""
        results = await self.db.mdvaes_financial_ratios.aggregate([
            {
                "$match": {
                    "ts_code": {"$in": symbols},
                    "end_date": {"$lte": end_date}
                }
            },
            {
                "$sort": {"ts_code": 1, "end_date": -1}
            },
            {
                "$group": {
                    "_id": "$ts_code",
                    "latest": {"$first": "$$ROOT"}
                }
            }
        ]).to_list(None)

        return {r["_id"]: FinancialData.from_dict(r["latest"]) for r in results}
```

**索引优化**:

```javascript
// 复合索引优化查询
db.mdvaes_analyst_forecasts.createIndex({
  ts_code: 1,
  target_year: 1,
  forecast_date: -1
});

// 覆盖索引（包含查询所需的所有字段）
db.mdvaes_eps_history.createIndex({
  ts_code: 1,
  end_date: -1,
  eps: 1,
  dt_eps: 1
});
```

#### 3. 前端性能优化

**虚拟滚动**:

```vue
<!-- 大数据量列表使用虚拟滚动 -->
<template>
  <el-table-v2
    :columns="columns"
    :data="largeDataList"
    :width="700"
    :height="400"
    fixed
    :estimated-row-height="50"
  />
</template>
```

**图表懒加载**:

```typescript
// 使用 Intersection Observer 实现图表懒加载
const chartRefs = ref<Map<string, HTMLElement>>(new Map())

const observeCharts = () => {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const chartId = entry.target.dataset.chartId
        renderChart(chartId)
        observer.unobserve(entry.target)
      }
    })
  }, { threshold: 0.1 })

  chartRefs.value.forEach((el, id) => {
    el.dataset.chartId = id
    observer.observe(el)
  })
}
```

**请求合并**:

```typescript
// 合并多个估值请求
export const mdvaesApi = {
  async batchGetValuation(requests: Array<{
    symbol: string
    calculation_date: string
    params: MDVAESParams
  }>) {
    const response = await axios.post(`${API_BASE}/valuation/batch`, {
      requests
    })
    return response.data
  }
}
```

---

### 安全与合规

#### 1. 数据隐私

**敏感数据加密**:

```python
# app/core/encryption.py

from cryptography.fernet import Fernet
import os

class EncryptionService:
    """加密服务"""

    def __init__(self):
        # 从环境变量读取密钥
        key = os.getenv('ENCRYPTION_KEY')
        if not key:
            raise ValueError("ENCRYPTION_KEY not set")
        self.cipher = Fernet(key.encode())

    def encrypt(self, data: str) -> str:
        """加密数据"""
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """解密数据"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()

# 使用示例
encryption = EncryptionService()

# 加密用户保存的参数
encrypted_params = encryption.encrypt(json.dumps(user_params))

# 存储到数据库
await db.mdvaes_user_params.insert_one({
  "user_id": user_id,
  "symbol": symbol,
  "encrypted_params": encrypted_params
})
```

#### 2. API 限流

**速率限制**:

```python
# app/core/rate_limit.py

from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

limiter = Limiter(key_func=get_remote_address)

# 应用到路由
@router.post("/api/mdvaes/valuation")
@limiter.limit("10/minute")  # 每分钟最多 10 次
async def get_valuation(
    request: Request,
    valuation_request: ValuationRequest,
    current_user: dict = Depends(get_current_user)
):
    # ... 业务逻辑
    pass

# VIP 用户限流更宽松
@limiter.limit("30/minute", key_func=lambda r: r.user.get("tier"))
async def get_valuation_vip(...):
    pass
```

#### 3. 审计日志

**操作审计**:

```python
# app/services/audit_service.py

class AuditService:
    """审计服务"""

    async def log_valuation_access(
        self,
        user_id: str,
        symbol: str,
        params: MDVAESParams,
        result: ValuationResult
    ):
        """记录估值访问日志"""
        await self.db.audit_logs.insert_one({
            "timestamp": datetime.utcnow(),
            "user_id": user_id,
            "action": "mdvaes_valuation",
            "resource": f"symbol:{symbol}",
            "params_hash": hashlib.md5(json.dumps(params).encode()).hexdigest(),
            "result": {
                "signal": result.signal,
                "intrinsic_value": result.intrinsic_value
            },
            "ip": self.get_client_ip(),
            "user_agent": self.get_user_agent()
        })

    async def log_backtest_start(
        self,
        user_id: str,
        backtest_id: str,
        params: dict
    ):
        """记录回测启动日志"""
        await self.db.audit_logs.insert_one({
            "timestamp": datetime.utcnow(),
            "user_id": user_id,
            "action": "backtest_start",
            "backtest_id": backtest_id,
            "strategy": "mdvaes",
            "params": params,
            "ip": self.get_client_ip()
        })
```

---

### 总结

MDVAES 估值模型的完整技术设计已完成，涵盖：

1. **Part 1: 业务需求** - 功能概述、用户故事、业务规则、边界情况
2. **Part 2A: 后端技术设计** - 模块复用、架构分层、DDD 领域模型、数据库设计、API 设计
3. **Part 2B: 前端技术设计** - 组件架构、核心组件、状态管理、API 集成、性能优化
4. **Part 3: 跨领域关注点** - 前后端集成、测试策略、部署运维、文档培训、性能优化、安全合规

**关键设计决策**：

| 决策点 | 选择 | 理由 |
|-------|------|------|
| 数据源 | Tushare 定时同步到 MongoDB | 避免重复网络调用，保证回测性能 |
| 避免后见之明 | 使用时间戳查询历史预测 | 确保回测真实性 |
| 参数配置 | 预设 + 自定义滑块 | 平衡易用性和灵活性 |
| 可视化 | 4 种 ECharts 图表 | 多维度展示估值结果 |
| 缓存策略 | 三级缓存（内存 → Redis → MongoDB） | 优化响应时间 |
| 测试覆盖 | 单元 ≥ 80%，集成 ≥ 70%，E2E 核心流程 | 保证代码质量 |

**下一步行动**：

1. 使用 `superpowers:writing-plans` 创建详细实施计划
2. 使用 `superpowers:using-git-worktrees` 创建隔离工作空间
3. 按照设计文档实现各模块
4. 持续运行测试确保质量
5. 完成后进行代码审查和集成测试

---

**文档版本**: v1.0
**最后更新**: 2026-02-19
**状态**: 待审查
