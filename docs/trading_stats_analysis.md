# 交易统计指标计算分析报告

## 问题描述

用户反馈"亏损交易次数"有问题,需要全面检查交易统计各指标的计算逻辑。

## 前端组件

### 位置
`frontend/src/components/BacktestResults.vue:151-208`

### 显示的指标
```vue
<!-- 第一行 -->
- total_trades: 总交易次数
- winning_trades: 盈利交易
- losing_trades: 亏损交易
- win_rate: 胜率

<!-- 第二行 -->
- avg_profit: 平均盈利
- avg_loss: 平均亏损
- profit_loss_ratio: 盈亏比
```

### API调用
```typescript
// frontend/src/components/BacktestResults.vue:359
const response = await backtestEngineApi.getBacktestResults(props.backtestId)
// API: GET /api/backtest/{backtestId}/results
```

## 后端计算逻辑

### 位置
`app/services/result_calculator.py:420-467`

### 计算流程

```python
def _calculate_trading_stats(self, trades: List[Dict]) -> Dict[str, Any]:
    # 1. 分离买卖交易
    buy_trades = [t for t in trades if t["trade_type"] == "buy"]
    sell_trades = [t for t in trades if t["trade_type"] == "sell"]

    # 2. 配对买卖交易计算盈亏
    paired_trades = self._pair_trades(buy_trades, sell_trades)

    # 3. 统计盈利和亏损交易
    winning_trades = [t for t in paired_trades if t["profit"] > 0]
    losing_trades = [t for t in paired_trades if t["profit"] < 0]

    # 4. 计算指标
    total_trades = len(paired_trades)
    win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
    avg_profit = float(np.mean([t["profit"] for t in winning_trades])) if winning_trades else 0.0
    avg_loss = float(np.mean([t["profit"] for t in losing_trades])) if losing_trades else 0.0
    profit_loss_ratio = abs(avg_profit / avg_loss) if avg_loss != 0 else 0.0
```

### 配对算法(_pair_trades)

**位置**: `app/services/result_calculator.py:469-542`

**逻辑**: FIFO(先进先出)
```python
def _pair_trades(buy_trades, sell_trades):
    # 1. 按日期排序
    buy_trades = sorted(buy_trades, key=lambda x: x["date"])
    sell_trades = sorted(sell_trades, key=lambda x: x["date"])

    # 2. 创建买入队列
    buy_queue = [{"trade": buy_trade, "remaining_shares": buy_trade["shares"]}

    # 3. 处理每笔卖出交易
    for sell_trade in sell_trades:
        while remaining_shares_to_sell > 0 and buy_queue:
            # 计算配对数量
            paired_shares = min(remaining_shares_to_sell, buy_shares_available)

            # 计算盈亏
            profit = (sell_trade["price"] - buy_trade["price"]) * paired_shares

            # 按比例分摊手续费
            buy_cost = buy_trade["total_cost"] * (paired_shares / buy_trade["shares"])
            sell_cost = sell_trade["total_cost"] * (paired_shares / sell_trade["shares"])

            profit -= (buy_cost + sell_cost)
```

## 发现的问题

### 问题1: total_cost字段含义不一致 ❌

**买入交易**:
```python
total_cost = amount + commission + stamp_duty + slippage
# 示例: 89667.0 + 22.42 + 0 + 0 = 89689.42
# 但实际存储的是: 89691.21 (有误差)
```

**卖出交易**:
```python
total_cost = commission + stamp_duty + slippage
# 示例: 22.09 + 88.37 + 0 = 110.46
# 实际存储: 112.23
```

**问题**: 买入的`total_cost`是总支出,卖出的`total_cost`是手续费,含义不一致!

在`_pair_trades`中使用时:
```python
buy_cost = buy_trade["total_cost"] * (paired_shares / buy_trade["shares"])
# 这里期望的是买入的总成本(包括成交金额+手续费)
# 但实际buy_trade["total_cost"]确实包含了成交金额
```

### 问题2: 未配对的交易不计入统计 ❌

**场景**: 回测任务 `bt_20260209_163805_895406`
- 买入交易: 1笔
- 卖出交易: 0笔
- **交易统计**: total_trades=0, winning_trades=0, losing_trades=0

**原因**:
```python
# 只有配对成功的交易才计入paired_trades
paired_trades = self._pair_trades(buy_trades, sell_trades)
total_trades = len(paired_trades)  # 如果没有卖出,这里就是0
```

**影响**: 未平仓的交易不会显示在统计中!

### 问题3: profit_loss字段计算错误 ❌

**位置**: `app/services/backtest_engine_service.py:669`

```python
profit_loss = amount - total_cost - (cost_basis * sell_shares)
```

**实际案例** (回测任务 `bt_20260209_170755_379753` 第一笔卖出):
```python
amount = 88371.0
total_cost = 112.23  # 卖出手续费
cost_basis = 89667.0  # 这个值应该是买入的总成本

# 计算
profit_loss = 88371.0 - 112.23 - 89667.0 = -1408.23 ✅ 正确
```

**但数据库中存储的是**: -726214441.23

**可能原因**:
1. `cost_basis`的值在某些情况下异常(可能是存储问题)
2. 或者有其他计算逻辑覆盖了这个值

### 问题4: _pair_trades中的profit计算有误 ❌

**位置**: `app/services/result_calculator.py:510-519`

```python
# 计算盈亏
profit = (sell_trade["price"] - buy_trade["price"]) * paired_shares

# 按比例分摊手续费
buy_cost_ratio = paired_shares / buy_trade["shares"]
buy_cost = buy_trade["total_cost"] * buy_cost_ratio  # ❌ 错误!
sell_cost_ratio = paired_shares / sell_trade["shares"]
sell_cost = sell_trade["total_cost"] * sell_cost_ratio  # ✅ 正确

profit -= (buy_cost + sell_cost)
```

**问题**:
- `buy_trade["total_cost"]` = amount + commission (包含了成交金额)
- 但价差部分已经计算了: `(sell_price - buy_price) * shares`
- 再减去`buy_cost`会重复扣减买入的成交金额!

**正确逻辑应该是**:
```python
# 方法1: 只扣减手续费
buy_fees = buy_trade["commission"] * buy_cost_ratio
sell_fees = sell_trade["commission"] + sell_trade["stamp_duty"]
profit = (sell_price - buy_price) * paired_shares - (buy_fees + sell_fees)

# 方法2: 使用收入-成本
revenue = sell_trade["amount"] - sell_trade["total_cost"]
cost = buy_trade["amount"] + buy_trade["commission"]
profit = (revenue - cost) * buy_cost_ratio
```

## 验证数据

### 测试用例1: 只有买入的回测
**回测ID**: `bt_20260209_163805_895406`
```
买入: 1笔
卖出: 0笔
交易统计: total_trades=0 ❌ 应该显示有1笔未平仓交易
```

### 测试用例2: 有完整买卖对的回测
**回测ID**: `bt_20260209_170755_379753`
```
买入: 4笔
卖出: 3笔
配对: 3对

交易统计:
- total_trades: 3 ✅
- winning_trades: 0 ✅
- losing_trades: 3 ✅
- avg_loss: -88567.53 ❌ 应该是约 -1428
```

## 修复建议

### 1. 修复_pair_trades中的profit计算

**文件**: `app/services/result_calculator.py:510-519`

**修改前**:
```python
profit = (sell_trade["price"] - buy_trade["price"]) * paired_shares
buy_cost = buy_trade["total_cost"] * buy_cost_ratio
sell_cost = sell_trade["total_cost"] * sell_cost_ratio
profit -= (buy_cost + sell_cost)
```

**修改后**:
```python
# 只计算价差盈亏,然后减去手续费
profit = (sell_trade["price"] - buy_trade["price"]) * paired_shares

# 计算手续费(不包含成交金额)
buy_fees = (buy_trade["total_cost"] - buy_trade["amount"]) * buy_cost_ratio
sell_fees = sell_trade["total_cost"]  # 卖出的total_cost本来就是纯手续费

profit -= (buy_fees + sell_fees)
```

### 2. 处理未平仓交易

**文件**: `app/services/result_calculator.py:420-467`

**建议**:
```python
# 配对交易
paired_trades = self._pair_trades(buy_trades, sell_trades)

# 未平仓的买入交易
unpaired_buy_trades = buy_trades[len(sell_trades):] if buy_trades else []

# 显示警告
if unpaired_buy_trades:
    logger.warning(f"有{len(unpaired_buy_trades)}笔未平仓交易未计入统计")

total_trades = len(paired_trades)
# 或者: total_trades = len(paired_trades) + len(unpaired_buy_trades)
```

### 3. 统一total_cost字段的含义

**建议**:
- 买入时:`total_cost`保持不变(amount + commission)
- 卖出时:`total_cost`改为amount + commission + stamp_duty + slippage
- 或者新增`total_fees`字段只存储手续费

### 4. 修复profit_loss存储异常

需要进一步调查为什么数据库中的`profit_loss`值异常,可能需要:
1. 检查是否有其他代码覆盖了这个字段
2. 检查MongoDB写入逻辑
3. 添加数据验证

## 总结

| 指标 | 状态 | 问题 |
|------|------|------|
| total_trades | ⚠️ | 未配对交易不计入 |
| winning_trades | ✅ | 依赖配对逻辑 |
| losing_trades | ✅ | 依赖配对逻辑 |
| win_rate | ✅ | 计算正确 |
| avg_profit | ❌ | 受profit计算错误影响 |
| avg_loss | ❌ | 受profit计算错误影响 |
| profit_loss_ratio | ❌ | 受profit计算错误影响 |

**最严重的问题**: `_pair_trades`中的profit计算错误,导致所有盈亏数据都不准确!

---

**分析时间**: 2026-02-10
**分析人员**: Claude AI
**优先级**: 🔴 高
