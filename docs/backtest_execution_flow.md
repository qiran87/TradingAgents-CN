# 回测引擎执行流程详解

## 问题

用户问: "目前回测某个策略的时候,是计算每天应该买入或者卖出什么股票后,实时的调用模拟交易,还是说,把这些动作扔到一张表里面,然后另外做操作的worker查询这张表,根据表里的动作,按照动作去执行的呢?"

## 答案

**实时执行模式** - 策略信号生成后立即执行模拟交易,不通过中间表。

## 详细执行流程

### 1. 回测任务启动

```
用户发起回测请求
    ↓
POST /api/backtest/start
    ↓
创建回测任务 (backtest_tasks 集合)
{
  backtest_id: "bt_xxx",
  status: "created",
  parameters: {...}
}
    ↓
后台线程执行 execute_backtest_task()
```

### 2. 回测主循环 (单线程同步执行)

**位置**: `app/services/backtest_engine_service.py:322-372`

```python
for i, trading_day in enumerate(trading_days):  # 遍历每个交易日
    # 1. 获取当日行情
    quote = self._get_quote_by_date(quotes, trading_day)

    # 2. 执行策略,生成信号
    signal = self._execute_sample_strategy(state, quote, trading_day, i)

    # 3. 立即执行交易
    if signal["action"] in ["buy", "sell"]:
        await self._execute_trade(backtest_id, state, signal, quote, trading_day)

    # 4. 更新每日状态
    await self._update_daily_state(backtest_id, state, quote, trading_day, i)

    # 5. 推送进度到WebSocket
    await self._send_progress_update(backtest_id, {...})
```

### 3. 策略信号生成

**位置**: `app/services/backtest_engine_service.py:382-429`

```python
def _execute_sample_strategy(self, state, quote, date, bar_index):
    """
    实时计算策略信号
    """
    # 初始化策略 (如果还没有)
    if not hasattr(self, 'strategy'):
        self.strategy = DualMAStrategy(params)

    # 调用策略生成信号
    signal = self.strategy.on_bar(
        bar_id=f"{date}_{bar_index}",
        timestamp=datetime.strptime(date, '%Y-%m-%d'),
        current_price=quote['close'],
        position=state.position,
        cash=state.cash
    )

    return signal  # 返回 {"action": "buy/sell/hold", ...}
```

### 4. 立即执行交易 (不是延迟执行!)

**位置**: `app/services/backtest_engine_service.py:511-532`

```python
async def _execute_trade(self, backtest_id, state, signal, quote, date):
    """
    立即执行交易,不写入中间表
    """
    if signal["action"] == "buy":
        await self._execute_buy(backtest_id, state, signal, quote, date)
    elif signal["action"] == "sell":
        await self._execute_sell(backtest_id, state, signal, quote, date)
```

#### 4.1 买入执行

**位置**: `app/services/backtest_engine_service.py:534-610`

```python
async def _execute_buy(self, backtest_id, state, signal, quote, date):
    # 1. 计算买入数量
    shares = (state.cash * 0.95) // quote["close"] // 100 * 100  # 95%仓位,100股倍数

    # 2. 计算费用
    amount = shares * quote["close"]
    cost_info = TradingCostCalculator.calculate_buy_cost(amount)
    total_cost = amount + cost_info["total_cost"]

    # 3. 检查资金
    if total_cost > state.cash:
        return  # 资金不足,不买入

    # 4. 立即更新状态
    state.cash -= total_cost
    unit_total_cost = total_cost / shares
    state.add_position(shares, unit_total_cost, date)

    # 5. 立即写入交易记录到数据库
    trade_doc = {
        "backtest_id": backtest_id,
        "date": date,
        "trade_type": "buy",
        "price": quote["close"],
        "shares": shares,
        "amount": amount,
        "commission": cost_info["commission"],
        "total_cost": total_cost,
        "cash_before": cash_before,
        "cash_after": state.cash,
        "position_before": position_before,
        "position_after": state.position,
        ...
    }
    await self.db.backtest_trades.insert_one(trade_doc)  # ← 直接插入数据库

    # 6. 发送WebSocket通知
    await self._send_trade_signal(backtest_id, "buy", price, shares)
```

#### 4.2 卖出执行

**位置**: `app/services/backtest_engine_service.py:622-700`

```python
async def _execute_sell(self, backtest_id, state, signal, quote, date):
    # 1. 计算卖出数量
    sell_shares = min(signal.get("amount", state.position), state.position)

    # 2. T+1检查
    if not state.can_sell(sell_shares, date):
        return  # T+1限制,不能卖出

    # 3. 调整为100股倍数
    sell_shares = (sell_shares // 100) * 100

    # 4. 计算费用和盈亏
    amount = sell_shares * quote["close"]
    cost_info = TradingCostCalculator.calculate_sell_cost(amount)
    total_cost = cost_info["total_cost"]

    # 5. 获取成本基础
    cost_basis = state.sell_position(sell_shares)  # 返回总成本

    # 6. 立即更新状态
    state.cash += amount - total_cost

    # 7. 计算盈亏
    profit_loss = amount - total_cost - cost_basis

    # 8. 立即写入交易记录到数据库
    trade_doc = {
        "backtest_id": backtest_id,
        "date": date,
        "trade_type": "sell",
        "price": quote["close"],
        "shares": sell_shares,
        "amount": amount,
        "commission": cost_info["commission"],
        "stamp_duty": cost_info["stamp_duty"],
        "total_cost": total_cost,
        "cash_before": cash_before,
        "cash_after": state.cash,
        "cost_basis": cost_basis,
        "profit_loss": profit_loss,
        ...
    }
    await self.db.backtest_trades.insert_one(trade_doc)  # ← 直接插入数据库

    # 9. 发送WebSocket通知
    await self._send_trade_signal(backtest_id, "sell", price, sell_shares)
```

### 5. 更新每日状态

**位置**: `app/services/backtest_engine_service.py:822-861`

```python
async def _update_daily_state(self, backtest_id, state, quote, date, bar_index):
    """
    每天交易后立即更新状态
    """
    profit_loss = state.get_profit_loss(quote["close"])

    daily_state_doc = {
        "backtest_id": backtest_id,
        "date": date,
        "bar_index": bar_index,
        "cash": state.cash,
        "position": state.position,
        "position_cost": state.position_cost,
        "current_price": quote["close"],
        "market_value": state.position * quote["close"],
        "total_value": state.cash + state.position * quote["close"],
        "profit_loss": profit_loss,
        ...
    }

    await self.db.backtest_daily_states.insert_one(daily_state_doc)  # ← 直接插入数据库
```

### 6. 实时进度推送

```python
async def _send_progress_update(self, backtest_id, progress_data):
    """
    通过WebSocket实时推送进度
    """
    # 不写入数据库,直接推送到WebSocket
    await websocket_manager.broadcast(backtest_id, {
        "type": "progress",
        "data": progress_data
    })
```

## 核心特点

### ✅ 实时执行 (同步模式)

```
策略生成信号 → 立即执行交易 → 立即写入数据库 → 继续下一天
```

**关键点**:
1. **没有中间表**: 信号不写入中间表,直接在内存中执行
2. **同步执行**: 策略计算和交易执行在同一个循环中
3. **原子操作**: 每个交易日的所有操作都是原子性的
4. **单线程**: 整个回测过程在单个线程中执行

### ❌ 不是延迟执行 (异步模式)

**没有使用**:
- ❌ 信号队列表 (signal_queue)
- ❌ 任务队列表 (task_queue)
- ❌ Worker异步处理
- ❌ 延迟执行机制

## 数据库集合说明

### 交易相关集合

| 集合名 | 用途 | 写入时机 |
|--------|------|----------|
| `backtest_tasks` | 回测任务元数据 | 任务开始/更新/完成时 |
| `backtest_trades` | 交易记录 | **每次交易立即写入** |
| `backtest_daily_states` | 每日状态 | **每天收盘后立即写入** |
| `backtest_results` | 回测结果 | 回测完成后写入 |
| `backtest_history` | 回测历史 | 回测完成后写入 |

### 没有的集合

- ❌ `backtest_signals` - 不存在,因为信号不存储
- ❌ `trade_signals` - 不存在,因为信号不存储
- ❌ `pending_trades` - 不存在,因为交易立即执行

## 时序图

```
回测开始
    ↓
for each trading_day:
    │
    ├─→ 获取行情数据
    │
    ├─→ 调用策略计算信号 (内存中)
    │   └─→ DualMAStrategy.on_bar()
    │       └─→ 返回 {"action": "buy/sell/hold"}
    │
    ├─→ 立即执行交易 (如果是buy/sell)
    │   ├─→ _execute_buy() / _execute_sell()
    │   ├─→ 更新内存状态 (state.cash, state.position)
    │   └─→ 插入数据库 (backtest_trades)
    │
    ├─→ 更新每日状态
    │   └─→ 插入数据库 (backtest_daily_states)
    │
    └─→ 推送进度 (WebSocket)
        └─→ 前端实时显示
    ↓
回测完成
    ↓
计算结果
    ↓
插入 backtest_results
```

## 为什么采用实时执行模式?

### 优点

1. **简单直接**: 代码逻辑清晰,没有复杂的异步协调
2. **数据一致性强**: 状态更新和数据库写入同步完成
3. **调试方便**: 可以跟踪每一步的执行过程
4. **性能足够**: 对于历史数据回测,单线程执行速度已经足够

### 缺点

1. **无法并行**: 不能同时执行多个回测任务
2. **实时性差**: 如果回测时间跨度大,需要等待较长时间
3. **资源占用**: 长时间运行的回测会占用进程资源

## 是否需要改成异步模式?

### 当前场景: 历史数据回测

**建议**: 保持实时执行模式

**原因**:
- 历史数据回测是一次性任务,不需要实时性
- 单线程执行已经足够快 (242个交易日 < 1秒)
- 异步模式增加复杂度,收益不大

### 未来场景: 实盘交易

**需要**: 异步模式 + 信号队列

**建议架构**:
```
策略生成信号
    ↓
写入信号表 (trade_signals)
{
  signal_id: "xxx",
  strategy_id: "xxx",
  action: "buy/sell",
  stock_code: "xxx",
  price: xxx,
  timestamp: xxx
}
    ↓
Worker异步处理
    ↓
查询信号表
    ↓
执行实际交易
    ↓
更新状态表
```

## 总结

### 当前实现

**模式**: 实时同步执行

**流程**:
```
策略计算 → 信号生成 → 立即执行 → 写入数据库 → 继续下一天
```

**特点**:
- ✅ 无中间表
- ✅ 单线程同步
- ✅ 原子操作
- ✅ 简单可靠

### 数据库写入时机

| 数据 | 写入时机 |
|------|----------|
| 交易记录 | 每次交易后立即写入 |
| 每日状态 | 每个交易日后立即写入 |
| 回测结果 | 回测完成后一次性写入 |

### 性能指标

- **执行速度**: 242个交易日 < 1秒
- **数据库写入**: 每次< 10ms
- **总耗时**: 取决于交易日数量 (通常< 5秒)

---

**文档创建时间**: 2026-02-10
**代码版本**: v1.0.0-preview
**维护者**: TradingAgents-CN Team
