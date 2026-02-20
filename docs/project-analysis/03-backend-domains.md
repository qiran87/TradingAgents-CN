# 后端领域模型分析

## 领域模型概述

后端使用 Pydantic 进行数据验证和序列化，定义了清晰的领域模型。这些模型覆盖了回测、策略、股票数据、用户认证等核心业务领域。

## 核心数据模型

### 1. 回测参数模型

**文件位置**: `app/models/backtest_params.py`

#### 1.1 SavedBacktestParams

保存的回测参数配置，用户可以保存常用配置以便复用。

```python
class SavedBacktestParams(BaseModel):
    """保存的回测参数"""
    id: Optional[str] = Field(None, description="参数ID")
    user_id: str = Field(..., description="用户ID")
    name: str = Field(..., min_length=1, max_length=50, description="参数名称")
    description: Optional[str] = Field(None, max_length=200, description="参数描述")

    # 回测参数
    start_date: str = Field(..., description="起始日期 YYYY-MM-DD")
    end_date: str = Field(..., description="结束日期 YYYY-MM-DD")
    initial_capital: float = Field(..., gt=0, description="初始资金")
    min_purchase: int = Field(..., ge=100, le=10000, description="最小购买量")
    stock_code: str = Field(..., description="股票代码")

    # 策略相关
    strategy_id: str = Field(..., description="策略ID")
    strategy_params: Dict[str, Any] = Field(default_factory=dict, description="策略参数")

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    usage_count: int = Field(default=0, description="使用次数")
    is_default: bool = Field(default=False, description="是否为默认参数")
```

**示例数据**:
```python
{
    "user_id": "user123",
    "name": "常用配置-平安银行",
    "description": "平安银行2024年回测配置",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "initial_capital": 100000.0,
    "min_purchase": 100,
    "stock_code": "000001.SZ",
    "strategy_id": "dual_ma",
    "strategy_params": {
        "short_window": 5,
        "long_window": 20
    }
}
```

#### 1.2 CreateSavedParamsRequest

创建保存参数的请求模型。

```python
class CreateSavedParamsRequest(BaseModel):
    """创建保存参数请求"""
    name: str = Field(..., min_length=1, max_length=50, description="参数名称")
    description: Optional[str] = Field(None, max_length=200, description="参数描述")
    params: Dict[str, Any] = Field(..., description="参数内容")
```

#### 1.3 UpdateSavedParamsRequest

更新保存参数的请求模型。

```python
class UpdateSavedParamsRequest(BaseModel):
    """更新保存参数请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="参数名称")
    description: Optional[str] = Field(None, max_length=200, description="参数描述")
    params: Optional[Dict[str, Any]] = Field(None, description="参数内容")
```

### 2. 策略领域模型

策略相关的数据结构主要定义在 `app/strategies/base.py` 中。

#### 2.1 策略参数定义

策略参数是策略配置的核心数据结构：

```python
List[Dict[str, Any]]  # 参数定义列表
```

**单个参数的结构**:
```python
{
    "name": "short_window",           # 参数名称
    "type": "int",                    # 参数类型 (int/float/str/select)
    "default_value": 5,               # 默认值
    "range": {"min": 2, "max": 60},   # 取值范围
    "description": "短期均线窗口",     # 描述
    "required": True                  # 是否必填
}
```

**示例参数定义**（双均线策略）:
```python
[
    {
        "name": "short_window",
        "type": "int",
        "default_value": 5,
        "range": {"min": 2, "max": 60},
        "description": "短期均线窗口",
        "required": True
    },
    {
        "name": "long_window",
        "type": "int",
        "default_value": 20,
        "range": {"min": 5, "max": 250},
        "description": "长期均线窗口",
        "required": True
    }
]
```

#### 2.2 交易信号模型

策略的 `on_bar` 方法返回交易信号：

```python
Dict[str, Any]
```

**信号结构**:
```python
{
    "action": "buy",              # 动作: buy/sell/hold
    "amount": 500,                # 交易股数
    "reason": "金叉买入"          # 原因说明
}
```

### 3. 回测引擎领域模型

回测引擎内部使用的数据结构，主要定义在 `app/services/backtest_engine_service.py`。

#### 3.1 BacktestState

回测状态类，维护回测过程中的所有状态。

```python
class BacktestState:
    """回测状态类"""

    def __init__(
        self,
        backtest_id: str,
        initial_capital: float,
        quotes: List[Dict],
        trading_days: List[str],
        parameters: Dict[str, Any] = None
    ):
        self.backtest_id = backtest_id
        self.initial_capital = initial_capital
        self.cash = initial_capital           # 可用现金
        self.position = 0                     # 持仓股数
        self.position_cost = 0.0              # 平均持仓成本
        self.quotes = quotes                  # 行情数据
        self.trading_days = trading_days      # 交易日列表
        self.parameters = parameters or {}    # 回测参数

        # T+1规则：持仓批次列表
        self.position_lots: List[Dict[str, Any]] = []
```

**核心方法**:
```python
# 添加持仓批次
def add_position(self, shares: int, cost: float, date: str)

# 检查是否可以卖出（T+1规则）
def can_sell(self, shares: int, current_date: str) -> bool

# 卖出持仓
def sell_position(self, shares: int) -> float

# 获取当前市值
def get_market_value(self, current_price: float) -> float

# 获取总资产
def get_total_assets(self, current_price: float) -> float

# 获取持仓盈亏
def get_profit_loss(self, current_price: float) -> float
```

#### 3.2 持仓批次模型

T+1 规则使用的持仓批次结构：

```python
{
    "shares": 500,           # 股数
    "cost": 98.76,          # 成本价
    "buy_date": "2024-01-15" # 买入日期
}
```

### 4. 回测任务领域模型

存储在 MongoDB 中的回测任务数据结构。

#### 4.1 回测任务文档

```python
{
    # 基本信息
    "backtest_id": "bt_20240205_143055_123456",
    "user_id": "user123",
    "status": "running",  # created/running/paused/completed/failed/aborted

    # 参数
    "parameters": {
        "stock_code": "000001.SZ",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "initial_capital": 100000.0,
        "strategy_id": "dual_ma",
        "strategy_params": {...}
    },

    # 执行信息
    "execution_info": {
        "current_bar_index": 150,
        "total_bars": 500,
        "current_date": "2024-01-15",
        "progress": 30.0,
        "start_time": "2024-02-05T14:30:55.123456",
        "elapsed_time": 45.2,
        "estimated_time_remaining": 105.6,
        "end_time": null,
        "final_value": null,
        "total_return": null
    },

    # 错误信息（如果有）
    "error": {
        "code": "INSUFFICIENT_DATA",
        "message": "数据不足：需要至少26个交易日的数据",
        "stack_trace": "..."
    },

    # 时间戳
    "created_at": "2024-02-05T14:30:55.123456",
    "updated_at": "2024-02-05T14:35:40.123456"
}
```

#### 4.2 每日状态文档

存储每个交易日的状态快照。

```python
{
    "backtest_id": "bt_20240205_143055_123456",
    "date": "2024-01-15",
    "bar_index": 150,

    # 资金状态
    "cash": 45123.45,
    "position": 500,
    "position_cost": 98.76,
    "current_price": 102.56,
    "market_value": 51280.00,
    "total_assets": 96403.45,

    # 收益指标
    "daily_return": 0.0123,
    "cumulative_return": 0.0345,
    "profit_loss": 1900.00,

    "created_at": "2024-02-05T14:35:40.123456"
}
```

#### 4.3 交易记录文档

每笔交易的详细信息。

```python
{
    "backtest_id": "bt_20240205_143055_123456",
    "date": "2024-01-15",
    "trade_type": "buy",  # buy/sell

    # 股票信息
    "stock_code": "000001.SZ",
    "stock_name": "平安银行",

    # 交易信息
    "price": 102.56,
    "shares": 500,
    "amount": 51280.00,

    # 费用明细
    "commission": 12.82,      # 佣金
    "stamp_duty": 0.0,       # 印花税（买入无）
    "slippage": 0.0,         # 滑点
    "total_cost": 25.64,     # 总费用

    # 状态变化
    "cash_before": 50000.00,
    "cash_after": 45123.45,
    "position_before": 0,
    "position_after": 500,

    # 盈亏（卖出时）
    "cost_basis": null,      # 成本基础（卖出时）
    "profit_loss": 0.0,      # 盈亏（卖出时）

    # 交易信号
    "signal": {
        "action": "buy",
        "amount": 500,
        "reason": "金叉买入"
    },

    "created_at": "2024-02-05T14:35:40.123456"
}
```

#### 4.4 回测结果文档

回测完成后的统计结果。

```python
{
    "backtest_id": "bt_20240205_143055_123456",

    # 收益指标
    "return_metrics": {
        "total_return": 0.1523,           # 总收益率
        "annual_return": 0.1825,          # 年化收益率
        "cumulative_returns": [...],      # 累计收益率序列
        "daily_returns": [...]            # 日收益率序列
    },

    # 风险指标
    "risk_metrics": {
        "max_drawdown": -0.0842,          # 最大回撤
        "volatility": 0.1523,             # 波动率
        "downside_volatility": 0.0956,    # 下行波动率
        "var_95": -0.0234                # 95% VaR
    },

    # 风险调整收益指标
    "risk_adjusted_metrics": {
        "sharpe_ratio": 1.23,             # 夏普比率
        "sortino_ratio": 1.56,            # 索提诺比率
        "calmar_ratio": 2.17              # 卡玛比率
    },

    # 交易统计
    "trading_stats": {
        "total_trades": 25,               # 总交易次数
        "winning_trades": 15,             # 盈利交易次数
        "losing_trades": 10,              # 亏损交易次数
        "win_rate": 0.6,                  # 胜率
        "avg_profit": 0.0345,             # 平均盈利
        "avg_loss": -0.0212,              # 平均亏损
        "profit_loss_ratio": 1.63         # 盈亏比
    },

    # 资金曲线
    "equity_curve": {
        "dates": ["2024-01-01", ...],     # 日期列表
        "total_assets": [100000, ...],    # 总资产
        "cash": [50000, ...],             # 现金
        "position_value": [50000, ...]    # 持仓市值
    },

    "created_at": "2024-02-05T14:40:00.123456"
}
```

### 5. 股票数据领域模型

#### 5.1 股票行情数据

```python
{
    "date": "2024-01-15",
    "open": 100.50,
    "high": 102.30,
    "low": 99.80,
    "close": 101.50,
    "volume": 12345678,          # 成交量（股）
    "amount": 1254321000.00      # 成交额（元）
}
```

#### 5.2 股票基本信息

```python
{
    "symbol": "000001.SZ",
    "name": "平安银行",
    "market": "A股",
    "exchange": "深圳证券交易所",
    "industry": "银行",
    "list_date": "1991-04-03",
    "updated_at": "2024-02-05T14:30:00.123456"
}
```

### 6. 用户认证领域模型

#### 6.1 用户文档

```python
{
    "user_id": "user123",
    "username": "user123",
    "password_hash": "hashed_password",
    "email": "user@example.com",
    "role": "user",  # user/admin
    "is_active": True,
    "created_at": "2024-01-01T00:00:00.000000",
    "last_login": "2024-02-05T14:30:00.000000"
}
```

#### 6.2 JWT Token Payload

```python
{
    "sub": "user123",         # 用户ID
    "username": "user123",
    "role": "user",
    "exp": 1707676800,        # 过期时间
    "iat": 1707590400         # 签发时间
}
```

### 7. 交易日历领域模型

#### 7.1 交易日历文档

```python
{
    "date": "2024-01-15",
    "is_trading_day": True,
    "is_holiday": False,
    "holiday_name": None,
    "created_at": "2024-01-01T00:00:00.000000"
}
```

### 8. WebSocket 消息领域模型

#### 8.1 进度更新消息

```python
{
    "type": "progress",
    "data": {
        "backtest_id": "bt_20240205_143055_123456",
        "status": "running",
        "progress": {
            "current_bar": 150,
            "total_bars": 500,
            "percentage": 30.0,
            "current_date": "2024-01-15",
            "elapsed_time": 45.2,
            "estimated_time_remaining": 105.6
        }
    },
    "timestamp": "2024-02-05T14:35:40.123456"
}
```

#### 8.2 持仓更新消息

```python
{
    "type": "position_update",
    "data": {
        "backtest_id": "bt_20240205_143055_123456",
        "position": {
            "cash": 45123.45,
            "position": 500,
            "position_cost": 98.76,
            "current_price": 102.56,
            "market_value": 51280.00,
            "total_assets": 96403.45,
            "profit_loss": 1900.00,
            "profit_loss_percentage": 3.85
        }
    },
    "timestamp": "2024-02-05T14:35:40.123456"
}
```

#### 8.3 交易信号消息

```python
{
    "type": "trade_signal",
    "data": {
        "backtest_id": "bt_20240205_143055_123456",
        "trade": {
            "type": "buy",
            "date": "2024-01-15",
            "price": 102.56,
            "shares": 500,
            "amount": 51280.00
        }
    },
    "timestamp": "2024-02-05T14:35:40.123456"
}
```

## 领域模型关系图

```
┌─────────────────────┐
│   BacktestTask      │
│  (回测任务)         │
├─────────────────────┤
│ - backtest_id       │
│ - user_id           │
│ - parameters        │──┐
│ - status            │  │
│ - execution_info    │  │
└─────────────────────┘  │
         │              │
         │              ▼
         │    ┌─────────────────────┐
         │    │   BacktestState     │
         │    │  (回测状态)         │
         │    ├─────────────────────┤
         │    │ - cash              │
         │    │ - position          │
         │    │ - position_lots     │
         │    │ - quotes            │
         │    └─────────────────────┘
         │              │
         ▼              ▼
┌─────────────────────┐  ┌─────────────────────┐
│  DailyState         │  │    TradeRecord      │
│ (每日状态)          │  │   (交易记录)        │
├─────────────────────┤  ├─────────────────────┤
│ - date              │  │ - date              │
│ - cash              │  │ - trade_type        │
│ - position          │  │ - price             │
│ - total_assets      │  │ - shares            │
└─────────────────────┘  │ - profit_loss       │
                         └─────────────────────┘
                                   │
                                   ▼
                         ┌─────────────────────┐
                         │  BacktestResults   │
                         │   (回测结果)       │
                         ├─────────────────────┤
                         │ - return_metrics    │
                         │ - risk_metrics      │
                         │ - trading_stats     │
                         │ - equity_curve      │
                         └─────────────────────┘
```

## 领域模型设计原则

### 1. 单一职责

每个模型只负责一个业务领域：
- `BacktestTask`: 回测任务管理
- `BacktestState`: 回测状态维护
- `TradeRecord`: 交易记录存储
- `BacktestResults`: 结果统计计算

### 2. 不可变性

一旦创建的记录不应修改：
- 交易记录创建后不可修改
- 每日状态快照不可修改
- 回测结果一旦计算完成不可修改

### 3. 完整性

所有关键操作都有完整记录：
- 交易记录包含交易前后状态
- 每日状态记录资金变化
- 回测结果记录计算过程

### 4. 可追溯性

所有数据都包含时间戳：
- `created_at`: 创建时间
- `updated_at`: 更新时间
- 交易记录包含交易时间

## 数据验证

### 1. Pydantic 验证

使用 Pydantic 进行自动数据验证：

```python
class BacktestParams(BaseModel):
    initial_capital: float = Field(..., gt=0, description="初始资金")
    min_purchase: int = Field(..., ge=100, le=10000, description="最小购买量")
    start_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
```

### 2. 业务逻辑验证

在服务层进行业务逻辑验证：

```python
# T+1 规则验证
if not state.can_sell(shares, current_date):
    raise InsufficientPositionError(...)

# 资金充足性验证
if total_cost > state.cash:
    raise InsufficientFundsError(required=total_cost, available=state.cash)
```

## 数据转换

### 1. MongoDB -> Python

```python
# 移除 MongoDB 的 _id 字段
task.pop("_id", None)

# 转换 datetime 为字符串
if "created_at" in doc:
    doc["created_at"] = doc["created_at"].isoformat()
```

### 2. Python -> MongoDB

```python
# 转换字符串为 datetime
doc["created_at"] = datetime.strptime(date_str, "%Y-%m-%d")
```

### 3. API 响应转换

```python
# 使用 Pydantic 模型序列化
from app.models.backtest_params import SavedBacktestParams

params = SavedBacktestParams(**mongo_doc)
return ok(data=params.dict())
```

## 领域模型扩展指南

### 1. 添加新模型

1. 创建模型文件: `app/models/new_feature.py`
2. 定义 Pydantic 模型
3. 添加字段验证规则
4. 添加示例数据

### 2. 扩展现有模型

1. 修改现有模型文件
2. 添加新字段（使用 Optional 保持向后兼容）
3. 更新验证规则
4. 更新示例和文档

### 3. 模型迁移

1. 备份现有数据
2. 添加新字段（设置默认值）
3. 更新代码逻辑
4. 验证数据完整性
