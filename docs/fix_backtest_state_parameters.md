# 修复BacktestState缺少parameters属性的错误

## 问题描述

**错误日志**:
```python
{"time": "2026-02-10 01:02:11", "name": "app.services.backtest_engine_service", "level": "ERROR", "message": "❌ 回测任务执行失败: bt_20260209_170211_722518, 错误: 'BacktestState' object has no attribute 'parameters'"}
```

## 错误原因

在 `app/services/backtest_engine_service.py:403` 中,`_execute_sample_strategy` 方法尝试访问 `state.parameters`:

```python
def _execute_sample_strategy(...):
    # 获取策略参数
    strategy_params = state.parameters.get('strategy_params', {})
    ...
```

但是 `BacktestState` 类的 `__init__` 方法中没有定义 `parameters` 属性:

```python
class BacktestState:
    def __init__(
        self,
        backtest_id: str,
        initial_capital: float,
        quotes: List[Dict],
        trading_days: List[str]
    ):
        self.backtest_id = backtest_id
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.position = 0
        self.position_cost = 0.0
        self.quotes = quotes
        self.trading_days = trading_days
        # ❌ 缺少 self.parameters = parameters
```

## 修复方案

### 1. 修改 BacktestState 类定义

**文件**: `app/services/backtest_engine_service.py:138-157`

**修改前**:
```python
def __init__(
    self,
    backtest_id: str,
    initial_capital: float,
    quotes: List[Dict],
    trading_days: List[str]
):
    self.backtest_id = backtest_id
    self.initial_capital = initial_capital
    self.cash = initial_capital
    self.position = 0
    self.position_cost = 0.0
    self.quotes = quotes
    self.trading_days = trading_days
    self.position_lots: List[Dict[str, Any]] = []
```

**修改后**:
```python
def __init__(
    self,
    backtest_id: str,
    initial_capital: float,
    quotes: List[Dict],
    trading_days: List[str],
    parameters: Dict[str, Any] = None  # ✅ 添加parameters参数
):
    self.backtest_id = backtest_id
    self.initial_capital = initial_capital
    self.cash = initial_capital
    self.position = 0
    self.position_cost = 0.0
    self.quotes = quotes
    self.trading_days = trading_days
    self.parameters = parameters or {}  # ✅ 保存parameters
    self.position_lots: List[Dict[str, Any]] = []
```

### 2. 修改 BacktestState 初始化调用

**文件**: `app/services/backtest_engine_service.py:310-316`

**修改前**:
```python
state = BacktestState(
    backtest_id=backtest_id,
    initial_capital=parameters["initial_capital"],
    quotes=quotes,
    trading_days=trading_days
)
```

**修改后**:
```python
state = BacktestState(
    backtest_id=backtest_id,
    initial_capital=parameters["initial_capital"],
    quotes=quotes,
    trading_days=trading_days,
    parameters=parameters  # ✅ 传入完整参数
)
```

## 修复验证

### 1. 重启后端服务

```bash
./restart_backend.sh
```

**验证**:
```bash
curl http://localhost:8000/api/health
```

**预期输出**:
```json
{"success":true,"data":{"status":"ok","version":"v1.0.0-preview"}}
```

### 2. 创建新的回测任务

通过前端或API创建回测任务:
```json
{
  "stock_code": "000001.SZ",
  "start_date": "2025-01-02",
  "end_date": "2025-07-31",
  "initial_capital": 100000,
  "strategy_id": "dual_ma",
  "strategy_params": {
    "short_period": 5,
    "long_period": 20
  }
}
```

**预期结果**:
- 回测任务应该成功执行
- 日志中应该看到: `✅ 初始化双均线策略: short_window=5, long_window=20`
- 不应该再出现 `'BacktestState' object has no attribute 'parameters'` 错误

## 技术细节

### 为什么需要 parameters 属性?

双均线策略需要从 `state.parameters` 中获取策略参数:

```python
# app/services/backtest_engine_service.py:403-409
def _execute_sample_strategy(...):
    # 获取策略参数
    strategy_params = state.parameters.get('strategy_params', {})

    # 兼容不同的参数名称
    short_window = strategy_params.get('short_window',
                   strategy_params.get('short_period', 5))
    long_window = strategy_params.get('long_window',
                   strategy_params.get('long_period', 20))
```

### parameters 的结构

```python
parameters = {
    "stock_code": "000001.SZ",
    "start_date": "2025-01-02",
    "end_date": "2025-07-31",
    "initial_capital": 100000,
    "strategy_id": "dual_ma",
    "strategy_params": {
        "short_period": 5,
        "long_period": 20
    }
}
```

## 相关文件

- `app/services/backtest_engine_service.py:138-157` - BacktestState类定义
- `app/services/backtest_engine_service.py:310-316` - BacktestState初始化
- `app/services/backtest_engine_service.py:403-409` - 使用state.parameters的代码

## 修复时间

- **发现时间**: 2026-02-10 01:02:11
- **修复时间**: 2026-02-10 01:03:00
- **验证时间**: 2026-02-10 01:03:52

## 修复状态

✅ 已修复并验证

---

**修复人员**: Claude AI
**相关issue**: 回测任务执行失败错误
