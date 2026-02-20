# 后端 API 分析

## API 架构概述

后端基于 FastAPI 框架构建，采用 RESTful API 设计风格，使用异步编程模式（async/await）处理请求。所有 API 路由都在定义时包含 `/api` 前缀，遵循项目的路由注册约定。

## 路由注册约定

**重要**: 路由必须在定义时包含 `/api` 前缀，而不是在 `include_router` 时添加。

```python
# ✅ 正确 - 在 router 定义时添加 prefix
router = APIRouter(prefix="/api/backtest", tags=["backtest-engine"])

# 在 main.py 中注册时不添加 prefix 参数
app.include_router(backtest_engine.router, tags=["backtest-engine"])

# ❌ 错误 - 不要这样做
# app.include_router(router, prefix="/api")  # 会导致路径重复
```

## API 路由模块

### 1. 回测引擎 API

**文件位置**: `app/routers/backtest_engine.py`

**路由前缀**: `/api/backtest`

#### 1.1 启动回测

```python
POST /api/backtest/start
```

**请求体**:
```python
class StartBacktestRequest(BaseModel):
    stock_code: str              # 股票代码（如 000001.SZ）
    start_date: str              # 起始日期 YYYY-MM-DD
    end_date: str                # 结束日期 YYYY-MM-DD
    initial_capital: float       # 初始资金
    strategy_id: str = "dual_ma" # 策略ID
    strategy_params: dict = {}   # 策略参数
```

**响应**:
```python
{
    "success": true,
    "data": {
        "backtest_id": "bt_20240205_143055_123456",
        "status": "created"
    },
    "timestamp": "2024-02-05T14:30:55.123456"
}
```

#### 1.2 暂停回测

```python
POST /api/backtest/{backtest_id}/interrupt
```

**响应**:
```python
{
    "success": true,
    "data": {"message": "回测已暂停"},
    "timestamp": "2024-02-05T14:35:22.123456"
}
```

#### 1.3 继续回测

```python
POST /api/backtest/{backtest_id}/continue
```

#### 1.4 查询回测状态

```python
GET /api/backtest/{backtest_id}/status
```

**响应**:
```python
{
    "success": true,
    "data": {
        "backtest_id": "bt_20240205_143055_123456",
        "status": "running",
        "parameters": {...},
        "execution_info": {
            "current_bar_index": 150,
            "total_bars": 500,
            "current_date": "2024-01-15",
            "progress": 30.0,
            "elapsed_time": 45.2
        },
        "created_at": "2024-02-05T14:30:55.123456",
        "updated_at": "2024-02-05T14:35:40.123456"
    }
}
```

#### 1.5 放弃回测

```python
DELETE /api/backtest/{backtest_id}
```

#### 1.6 获取回测结果

```python
GET /api/backtest/{backtest_id}/results
```

**响应**:
```python
{
    "success": true,
    "data": {
        "backtest_id": "bt_20240205_143055_123456",
        "return_metrics": {
            "total_return": 0.1523,
            "annual_return": 0.1825,
            "cumulative_returns": [...],
            "daily_returns": [...]
        },
        "risk_metrics": {
            "max_drawdown": -0.0842,
            "volatility": 0.1523,
            "downside_volatility": 0.0956,
            "var_95": -0.0234
        },
        "risk_adjusted_metrics": {
            "sharpe_ratio": 1.23,
            "sortino_ratio": 1.56,
            "calmar_ratio": 2.17
        },
        "trading_stats": {
            "total_trades": 25,
            "winning_trades": 15,
            "losing_trades": 10,
            "win_rate": 0.6,
            "avg_profit": 0.0345,
            "avg_loss": -0.0212,
            "profit_loss_ratio": 1.63
        },
        "equity_curve": {
            "dates": ["2024-01-01", "2024-01-02", ...],
            "total_assets": [100000, 101234, ...],
            "cash": [50000, 49876, ...],
            "position_value": [50000, 51358, ...]
        }
    }
}
```

#### 1.7 获取交易明细

```python
GET /api/backtest/{backtest_id}/trades?page=1&page_size=50
```

**响应**:
```python
{
    "success": true,
    "data": {
        "trades": [...],
        "count": 50,
        "pagination": {
            "page": 1,
            "page_size": 50,
            "total": 125,
            "total_pages": 3
        }
    }
}
```

#### 1.8 获取资金曲线

```python
GET /api/backtest/{backtest_id}/equity-curve
```

#### 1.9 触发结果计算

```python
POST /api/backtest/{backtest_id}/calculate-results
```

#### 1.10 WebSocket 进度推送

```python
WS /api/backtest/ws/{backtest_id}/progress?token=xxx
```

**消息类型**:
```python
# 连接确认
{
    "type": "connected",
    "data": {
        "backtest_id": "bt_20240205_143055_123456",
        "status": "running",
        "execution_info": {...}
    }
}

# 进度更新
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
    }
}

# 持仓更新
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
    }
}

# 交易信号
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
    }
}

# 错误消息
{
    "type": "error",
    "data": {
        "backtest_id": "bt_20240205_143055_123456",
        "error": {
            "code": "INSUFFICIENT_DATA",
            "message": "数据不足：需要至少26个交易日的数据"
        }
    }
}
```

### 2. 策略管理 API

**文件位置**: `app/routers/strategies.py`

**路由前缀**: `/api/strategies`

#### 2.1 获取所有策略

```python
GET /api/strategies
```

**响应**:
```python
{
    "success": true,
    "data": [
        {
            "strategy_id": "dual_ma",
            "name": "双均线策略",
            "description": "基于快慢均线的交叉信号进行交易...",
            "category": "trend",
            "parameters": [
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
        },
        {
            "strategy_id": "rsi",
            "name": "RSI策略",
            "description": "基于RSI指标的超买超卖进行交易...",
            "category": "oscillation",
            "parameters": [...]
        }
    ]
}
```

#### 2.2 获取策略详情

```python
GET /api/strategies/{strategy_id}
```

#### 2.3 验证策略参数

```python
POST /api/strategies/{strategy_id}/validate
```

**请求体**:
```python
{
    "strategy_params": {
        "short_window": 5,
        "long_window": 20
    }
}
```

### 3. 保存参数 API

**文件位置**: `app/routers/saved_params.py`

**路由前缀**: `/api/saved-params`

#### 3.1 获取参数列表

```python
GET /api/saved-params
```

#### 3.2 创建保存参数

```python
POST /api/saved-params
```

**请求体**:
```python
{
    "name": "常用配置-平安银行",
    "description": "平安银行2024年回测配置",
    "params": {
        "stock_code": "000001.SZ",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "initial_capital": 100000.0,
        "min_purchase": 100,
        "strategy_id": "dual_ma",
        "strategy_params": {...}
    }
}
```

#### 3.3 更新保存参数

```python
PUT /api/saved-params/{id}
```

#### 3.4 删除保存参数

```python
DELETE /api/saved-params/{id}
```

### 4. 回测历史 API

**文件位置**: `app/routers/backtest_history.py`

**路由前缀**: `/api/backtest-history`

#### 4.1 获取历史记录列表

```python
GET /api/backtest-history?page=1&page_size=20
```

#### 4.2 保存回测到历史

```python
POST /api/backtest-history/save
```

#### 4.3 删除历史记录

```python
DELETE /api/backtest-history/{history_id}
```

#### 4.4 导出历史记录

```python
GET /api/backtest-history/{history_id}/export
```

### 5. 股票数据 API

**文件位置**: `app/routers/stocks.py`

**路由前缀**: `/api/stocks`

#### 5.1 搜索股票

```python
GET /api/stocks/search?q={query}&market={market}
```

#### 5.2 获取股票信息

```python
GET /api/stocks/{symbol}
```

**响应**:
```python
{
    "success": true,
    "data": {
        "symbol": "000001.SZ",
        "name": "平安银行",
        "market": "A股",
        "industry": "银行",
        "list_date": "1991-04-03"
    }
}
```

#### 5.3 获取股票列表

```python
GET /api/stocks?market={market}&page={page}&page_size={page_size}
```

### 6. 行情数据 API

**文件位置**: `app/routers/stock_data.py`

**路由前缀**: `/api/stock-data`

#### 6.1 获取 K 线数据

```python
GET /api/stock-data/quotes?symbol={symbol}&start_date={start}&end_date={end}
```

**响应**:
```python
{
    "success": true,
    "data": {
        "symbol": "000001.SZ",
        "quotes": [
            {
                "date": "2024-01-01",
                "open": 100.50,
                "high": 102.30,
                "low": 99.80,
                "close": 101.50,
                "volume": 12345678,
                "amount": 1254321000.00
            },
            ...
        ]
    }
}
```

#### 6.2 获取实时行情

```python
GET /api/stock-data/realtime?symbol={symbol}
```

### 7. 交易日历 API

**文件位置**: `app/routers/trading_calendar.py`

**路由前缀**: `/api/trading-calendar`

#### 7.1 获取交易日列表

```python
GET /api/trading-calendar/days?start_date={start}&end_date={end}
```

**响应**:
```python
{
    "success": true,
    "data": {
        "trading_days": ["2024-01-01", "2024-01-02", ...],
        "total_days": 244
    }
}
```

#### 7.2 判断是否交易日

```python
GET /api/trading-calendar/is-trading-day?date={date}
```

#### 7.3 获取下一个交易日

```python
GET /api/trading-calendar/next-trading-day?date={date}
```

### 8. 回测股票数据 API

**文件位置**: `app/routers/backtest_stock_data_v2.py`

**路由前缀**: `/api/backtest-data`

#### 8.1 获取回测数据

```python
GET /api/backtest-data/quotes?symbol={symbol}&start_date={start}&end_date={end}
```

**响应**:
```python
{
    "success": true,
    "data": {
        "symbol": "000001.SZ",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "total_count": 244,
        "quotes": [...]
    }
}
```

#### 8.2 检查数据完整性

```python
GET /api/backtest-data/check?symbol={symbol}&start_date={start}&end_date={end}
```

### 9. 用户认证 API

**文件位置**: `app/routers/auth_db.py`

**路由前缀**: `/api/auth`

#### 9.1 用户登录

```python
POST /api/auth/login
```

**请求体**:
```python
{
    "username": "user123",
    "password": "password123"
}
```

**响应**:
```python
{
    "success": true,
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer",
        "expires_in": 86400,
        "user": {
            "user_id": "user123",
            "username": "user123",
            "role": "user"
        }
    }
}
```

#### 9.2 用户注册

```python
POST /api/auth/register
```

#### 9.3 刷新 Token

```python
POST /api/auth/refresh
```

#### 9.4 用户注销

```python
POST /api/auth/logout
```

### 10. 导出功能 API

**文件位置**: `app/routers/backtest_export.py`

**路由前缀**: `/api/backtest-export`

#### 10.1 导出回测结果

```python
GET /api/backtest-export/{backtest_id}/excel
```

#### 10.2 导出交易明细

```python
GET /api/backtest-export/{backtest_id}/trades
```

#### 10.3 导出资金曲线

```python
GET /api/backtest-export/{backtest_id}/equity-curve
```

## API 设计模式

### 1. 统一响应格式

**成功响应**:
```python
from app.core.response import ok

return ok(data=result)
```

**错误响应**:
```python
from app.core.response import error

return error("错误信息")
```

### 2. 依赖注入

```python
from app.core.database import get_mongo_db

@router.get("/api/backtest/{backtest_id}/status")
async def get_backtest_status(
    backtest_id: str,
    db = Depends(get_mongo_db)
):
    task = await db.backtest_tasks.find_one({"backtest_id": backtest_id})
    return ok(data=task)
```

### 3. 异常处理

```python
from fastapi import HTTPException

try:
    result = await some_operation()
except BacktestNotFoundError as e:
    raise HTTPException(status_code=404, detail=e.message)
except Exception as e:
    logger.error(f"操作失败: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail=f"操作失败: {str(e)}")
```

### 4. 后台任务

```python
from fastapi import BackgroundTasks

@router.post("/api/backtest/start")
async def start_backtest(
    request: StartBacktestRequest,
    background_tasks: BackgroundTasks
):
    # 创建任务
    backtest_id = create_backtest_task(request)

    # 后台执行
    background_tasks.add_task(execute_backtest_task, backtest_id, parameters)

    return ok(data={"backtest_id": backtest_id})
```

## API 安全

### 1. JWT 认证

```python
from app.routers.auth_db import get_current_user

@router.get("/api/backtest/{backtest_id}/results")
async def get_backtest_results(
    backtest_id: str,
    current_user: dict = Depends(get_current_user)
):
    # current_user 包含用户信息
    user_id = current_user.get("sub")
```

### 2. 权限验证

```python
# 检查是否有权访问（只能访问自己的任务，或管理员可以访问所有）
if task.get("user_id") != current_user.get("sub") and not current_user.get("is_admin", False):
    raise HTTPException(status_code=403, detail="无权访问此回测结果")
```

## API 版本控制

当前所有 API 都在 `/api` 路径下，未来可以通过以下方式支持版本控制：

```python
# v1 API
router_v1 = APIRouter(prefix="/api/v1/backtest", tags=["backtest-v1"])

# v2 API
router_v2 = APIRouter(prefix="/api/v2/backtest", tags=["backtest-v2"])
```

## API 文档

FastAPI 自动生成交互式 API 文档：

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## API 调用示例

### Python 客户端

```python
import requests

# 启动回测
response = requests.post(
    "http://localhost:8000/api/backtest/start",
    json={
        "stock_code": "000001.SZ",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "initial_capital": 100000.0,
        "strategy_id": "dual_ma",
        "strategy_params": {
            "short_window": 5,
            "long_window": 20
        }
    },
    headers={"Authorization": "Bearer <token>"}
)

result = response.json()
backtest_id = result["data"]["backtest_id"]

# 查询状态
status = requests.get(
    f"http://localhost:8000/api/backtest/{backtest_id}/status",
    headers={"Authorization": "Bearer <token>"}
)
```

### JavaScript 客户端

```typescript
import axios from 'axios'

const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Authorization': `Bearer ${token}`
  }
})

// 启动回测
const { data } = await apiClient.post('/api/backtest/start', {
  stock_code: '000001.SZ',
  start_date: '2024-01-01',
  end_date: '2024-12-31',
  initial_capital: 100000.0,
  strategy_id: 'dual_ma',
  strategy_params: {
    short_window: 5,
    long_window: 20
  }
})

const backtestId = data.data.backtest_id

// 查询状态
const status = await apiClient.get(`/api/backtest/${backtestId}/status`)
```

---

### 11. MDVAES 估值 API

**文件位置**: `app/routers/mdvaes.py` (待创建)

**路由前缀**: `/api/mdvaes`

**状态**: 🚧 待实现（设计已完成，见 `docs/plans/2026-02-19-mdvaes-design.md`）

#### 11.1 计算股票估值

```python
POST /api/mdvaes/valuation
```

**状态**: 🚧 待实现

**请求体**:
```python
class MDVAESValuationRequest(BaseModel):
    symbol: str                          # 股票代码（如 000001.SZ）
    calculation_date: str = None         # 计算日期（YYYY-MM-DD），默认最新交易日
    params: MDVAESParams                 # MDVAES 参数对象

class MDVAESParams(BaseModel):
    preset: Optional[str] = None         # 预设名称（conservative/neutral/aggressive）
    forecast_years: Optional[int] = 5    # 预测年数（1-10）
    peg_base: Optional[float] = 1.0      # 基础 PEG 值（0.5-2.0）
    risk_adjustment: Optional[float] = 0.1 # 风险折价（0.0-0.3）
    anchor_weight: Optional[Dict] = None  # 多锚点权重
    signal_mode: Optional[str] = "valuation_range" # 信号模式
    safety_margin_buy: Optional[float] = 0.8   # 安全边际买入系数
    safety_margin_sell: Optional[float] = 1.2  # 安全边际卖出系数
```

**响应**:
```python
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
            "valuation_projection": {...},
            "water_level": {...},
            "multi_anchor_comparison": {...},
            "eps_trend": [...]
        }
    },
    "message": "success",
    "timestamp": "2024-01-15T10:30:00.000Z"
}
```

**错误码**:
| 错误码 | HTTP 状态 | 说明 |
|-------|----------|------|
| INVALID_PARAMS | 400 | 请求参数无效 |
| DATA_INSUFFICIENT | 404 | 数据不足，无法计算估值 |
| UNAUTHORIZED | 401 | Token 缺失或无效 |
| SUBSCRIPTION_REQUIRED | 403 | 需要订阅 MDVAES 功能 |

#### 11.2 获取参数定义

```python
GET /api/mdvaes/parameters
```

**状态**: 🚧 待实现

**响应**:
```python
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
            }
        ],
        "presets": {
            "conservative": {
                "forecast_years": 3,
                "peg_base": 0.8,
                "risk_adjustment": 0.15,
                "safety_margin_buy": 0.7,
                "safety_margin_sell": 1.15
            },
            "neutral": {
                "forecast_years": 5,
                "peg_base": 1.0,
                "risk_adjustment": 0.1,
                "safety_margin_buy": 0.8,
                "safety_margin_sell": 1.2
            },
            "aggressive": {
                "forecast_years": 7,
                "peg_base": 1.2,
                "risk_adjustment": 0.05,
                "safety_margin_buy": 0.9,
                "safety_margin_sell": 1.25
            }
        }
    },
    "message": "success",
    "timestamp": "2024-01-15T10:30:00.000Z"
}
```

#### 11.3 保存用户参数

```python
POST /api/mdvaes/user-params
```

**状态**: 🚧 待实现

**请求体**:
```python
class SaveUserParamsRequest(BaseModel):
    symbol: str              # 股票代码
    params: {
        "name": str,         # 参数配置名称
        "description": str,   # 参数配置描述
        "config": MDVAESParams # 参数配置
    }
```

**响应**:
```python
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

#### 11.4 获取用户参数

```python
GET /api/mdvaes/user-params/{symbol}
```

**状态**: 🚧 待实现

**路径参数**:
- `symbol`: 股票代码

**响应**:
```python
{
    "success": true,
    "data": {
        "params": [
            {
                "param_id": "param_1234567890",
                "name": "我的保守配置",
                "description": "适合长期投资",
                "config": {...},
                "created_at": "2024-01-10T10:00:00.000Z",
                "updated_at": "2024-01-15T10:30:00.000Z"
            }
        ]
    },
    "message": "success",
    "timestamp": "2024-01-15T10:30:00.000Z"
}
```

#### 11.5 获取估值历史

```python
GET /api/mdvaes/history/{symbol}
```

**状态**: 🚧 待实现

**路径参数**:
- `symbol`: 股票代码

**查询参数**:
- `days`: 查询天数（1-365），默认 30
- `start_date`: 起始日期（YYYY-MM-DD）
- `end_date`: 结束日期（YYYY-MM-DD）

**响应**:
```python
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
            }
        ]
    },
    "message": "success",
    "timestamp": "2024-01-15T10:30:00.000Z"
}
```

---

## API 设计模式

1. **创建路由文件**: `app/routers/new_feature.py`
2. **定义路由**:
   ```python
   router = APIRouter(prefix="/api/new-feature", tags=["new-feature"])
   ```
3. **实现端点**: 使用 async 函数
4. **依赖注入**: 使用 `Depends()` 注入服务
5. **注册路由**: 在 `app/main.py` 中注册
6. **错误处理**: 使用自定义异常类
7. **测试验证**: 使用 Swagger UI 测试
