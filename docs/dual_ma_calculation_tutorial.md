# 双均线策略计算教程 - 项目实战版

## 📚 目录
1. [策略初始化](#1-策略初始化)
2. [价格数据传入](#2-价格数据传入)
3. [均线计算核心代码](#3-均线计算核心代码)
4. [完整流程演示](#4-完整流程演示)
5. [实战案例分析](#5-实战案例分析)

---

## 1. 策略初始化

### 🎯 从哪里开始?

回测启动后,会调用 `BacktestEngine` 的 `run_backtest()` 方法:

```python
# app/services/backtest_engine_service.py:220-425

async def run_backtest(
    self,
    backtest_id: str,
    stock_code: str,
    start_date: str,
    end_date: str,
    initial_capital: float,
    strategy_id: str,
    strategy_params: dict
):
    """
    执行回测任务
    """
    # 1. 获取历史K线数据
    quotes = await self._get_stock_data(stock_code, start_date, end_date)

    # 2. 初始化回测状态
    state = BacktestState(
        backtest_id=backtest_id,
        initial_capital=initial_capital,
        quotes=quotes,
        trading_days=trading_days
    )

    # 3. 执行回测循环
    for i, trading_day in enumerate(trading_days):
        quote = self._get_quote_by_date(quotes, trading_day)

        # ← 关键: 调用策略生成信号
        signal = self._execute_sample_strategy(state, quote, trading_day, i)

        # 4. 执行交易
        if signal["action"] in ["buy", "sell"]:
            await self._execute_trade(backtest_id, state, signal, quote, trading_day)
```

### 📌 策略初始化细节

```python
# app/services/backtest_engine_service.py:379-429

def _execute_sample_strategy(self, state, quote, date, bar_index):
    """
    执行双均线策略
    """
    # ← 第一次调用时初始化策略
    if not hasattr(self, 'strategy'):
        # 1. 获取策略参数
        strategy_params = state.parameters.get('strategy_params', {})

        # 2. 兼容不同参数名称
        short_window = strategy_params.get('short_window',
                       strategy_params.get('short_period', 5))
        long_window = strategy_params.get('long_window',
                       strategy_params.get('long_period', 20))

        # 3. 创建策略实例
        params = {
            'short_window': short_window,  # = 5
            'long_window': long_window     # = 20
        }
        self.strategy = DualMAStrategy(params)  # ← 这里!

        logger.info(f"✅ 初始化双均线策略: short_window={short_window}, long_window={long_window}")

    # 4. 每天调用策略
    signal = self.strategy.on_bar(...)
    return signal
```

**DualMAStrategy初始化**:

```python
# app/strategies/dual_ma.py:16-20

class DualMAStrategy(BaseStrategy):
    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        self.short_window = self.get_parameter("short_window", 5)   # = 5
        self.long_window = self.get_parameter("long_window", 20)   # = 20
        self.price_history = []  # ← 空列表,用于存储价格历史
```

---

## 2. 价格数据传入

### 📊 数据流向

```
MongoDB数据库
    ↓
_get_stock_data() 获取K线
    ↓
quotes = [{date: '2025-01-02', close: 10.50}, ...]
    ↓
for each trading_day:
    quote = get_quote(trading_day)  # 取当天K线
    current_price = quote['close']   # ← 取收盘价
    ↓
strategy.on_bar(current_price=current_price, ...)
    ↓
self.price_history.append(current_price)  # ← 添加到历史
```

### 🔍 详细代码

```python
# app/services/backtest_engine_service.py:318-341

for i, trading_day in enumerate(trading_days):
    # 1. 获取当天行情
    quote = self._get_quote_by_date(quotes, trading_day)
    # quote = {
    #     'date': '2025-01-02',
    #     'open': 10.40,
    #     'high': 10.60,
    #     'low': 10.30,
    #     'close': 10.50,  ← 使用这个!
    #     'volume': 1000000
    # }

    # 2. 调用策略
    signal = self._execute_sample_strategy(
        state=state,
        quote=quote,           # ← 传入整条K线
        date=trading_day,
        bar_index=i
    )
```

```python
# app/services/backtest_engine_service.py:419-427

# 3. 在策略方法中提取收盘价
timestamp = datetime.strptime(date, '%Y-%m-%d')
signal = self.strategy.on_bar(
    bar_id=f"{date}_{bar_index}",
    timestamp=timestamp,
    current_price=quote['close'],  # ← 提取收盘价
    position=state.position,
    cash=state.cash
)
```

```python
# app/strategies/dual_ma.py:75-76

# 4. 策略接收并存储价格
def on_bar(self, bar_id, timestamp, current_price, position, cash):
    self.price_history.append(current_price)  # ← 添加到列表
    # 第一次调用: price_history = [10.50]
    # 第二次调用: price_history = [10.50, 10.70]
    # 第三次调用: price_history = [10.50, 10.70, 10.60]
    # ...
```

---

## 3. 均线计算核心代码

### 📐 5日均线计算

```python
# app/strategies/dual_ma.py:83

# 计算短期均线 (5日)
short_ma = sum(self.price_history[-self.short_window:]) / self.short_window
#            ↑                                   ↑
#            求和                                 除以5
```

**详细拆解**:

```python
# 假设已经有25天的价格数据
self.price_history = [
    10.50,  # Day 1
    10.70,  # Day 2
    10.60,  # Day 3
    10.90,  # Day 4
    11.00,  # Day 5
    ...
    10.80,  # Day 24
    11.20   # Day 25 (最新)
]

# Python切片操作
last_5_prices = self.price_history[-5:]  # 取最后5个
#              = [10.30, 10.50, 10.80, 11.00, 11.20]

# 计算MA5
short_ma = sum(last_5_prices) / 5
#         = (10.30 + 10.50 + 10.80 + 11.00 + 11.20) / 5
#         = 54.80 / 5
#         = 10.96
```

### 📐 20日均线计算

```python
# app/strategies/dual_ma.py:86

# 计算长期均线 (20日)
long_ma = sum(self.price_history[-self.long_window:]) / self.long_window
#           ↑                                   ↑
#           求和                                 除以20
```

**详细拆解**:

```python
# 使用相同的price_history (25天数据)
self.price_history = [
    10.50,  # Day 1
    ...
    11.20   # Day 25
]

# Python切片操作
last_20_prices = self.price_history[-20:]  # 取最后20个
#               = [Day 6到Day 25的所有价格]

# 计算MA20
long_ma = sum(last_20_prices) / 20
#        = (最近20天价格之和) / 20
#        ≈ 10.85 (假设)
```

### 📐 前一天均线计算

```python
# app/strategies/dual_ma.py:90-91

# 前一个短期和长期均线
if len(self.price_history) > self.long_window:
    prev_short_ma = sum(self.price_history[-self.short_window-1:-1]) / self.short_window
    #                                  ↑ -5-1=-6       ↑ -1(不包含)
    #                                  = [Day 20到Day 24的5个价格]

    prev_long_ma = sum(self.price_history[-self.long_window-1:-1]) / self.long_window
    #                                 ↑ -20-1=-21      ↑ -1(不包含)
    #                                 = [Day 5到Day 24的20个价格]
```

**详细拆解**:

```python
# 当前是Day 25,price_history有25个元素

# 计算Day 24的MA5 (前一天的短期均线)
prev_short_ma = sum(self.price_history[-6:-1]) / 5
#               = sum([10.30, 10.50, 10.80, 11.00, 11.20][-6:-1]) / 5
#               = sum([Day 20, Day 21, Day 22, Day 23, Day 24的价格]) / 5
#               = (不包括Day 25,包括Day 24的前5天)
```

---

## 4. 完整流程演示

### 🎬 场景设置

**回测任务**:
- 股票: 000001.SZ
- 时间: 2025-01-02 至 2025-01-31
- 策略: 双均线 (short=5, long=20)

### 📅 Day 1-4: 数据积累期

```python
# Day 1 (2025-01-02)
quote = {'close': 10.50}
signal = strategy.on_bar(current_price=10.50, ...)

# 策略内部:
self.price_history.append(10.50)
# price_history = [10.50]
len(price_history) = 1 < long_window(20)

return {"action": "hold", "reason": "数据积累中"}
```

```python
# Day 2 (2025-01-03)
quote = {'close': 10.70}
signal = strategy.on_bar(current_price=10.70, ...)

self.price_history.append(10.70)
# price_history = [10.50, 10.70]
len(price_history) = 2 < 20

return {"action": "hold", "reason": "数据积累中"}
```

```python
# Day 3-4 同样...
# price_history = [10.50, 10.70, 10.60, 10.30]
len(price_history) = 4 < 20

return {"action": "hold", "reason": "数据积累中"}
```

### 📅 Day 5-19: 可以计算MA5,但不能计算MA20

```python
# Day 5 (2025-01-08)
quote = {'close': 11.00}
signal = strategy.on_bar(current_price=11.00, ...)

self.price_history.append(11.00)
# price_history = [10.50, 10.70, 10.60, 10.30, 11.00]
len(price_history) = 5

# 可以计算MA5
short_ma = sum([10.50, 10.70, 10.60, 10.30, 11.00]) / 5
         = 54.10 / 5
         = 10.82

# 但不能计算MA20 (需要至少20天数据)
len(price_history) = 5 < 20

return {"action": "hold", "reason": "数据积累中"}
```

```python
# Day 6-19 依此类推...
# Day 19:
# price_history有19个元素
# MA5可以计算
# MA20还不能计算
```

### 📅 Day 20: 可以计算MA20了!

```python
# Day 20 (2025-01-29)
quote = {'close': 10.90}
signal = strategy.on_bar(current_price=10.90, ...)

self.price_history.append(10.90)
# price_history = [10.50, 10.70, ..., 10.90]  # 20个元素
len(price_history) = 20

# 1. 计算当前均线
short_ma = sum(price_history[-5:]) / 5
         = sum([Day 16, Day 17, Day 18, Day 19, Day 20]) / 5
         = (10.30 + 10.50 + 10.80 + 11.00 + 10.90) / 5
         = 53.50 / 5
         = 10.70

long_ma = sum(price_history[-20:]) / 20
        = sum(Day 1到Day 20的所有价格) / 20
        = 215.00 / 20  (假设)
        = 10.75

# 2. 计算前一天均线 (Day 19)
prev_short_ma = sum(price_history[-6:-1]) / 5
             = sum(Day 15到Day 19的价格) / 5
             = 10.68

prev_long_ma = sum(price_history[-21:-1]) / 20
            # ❌ 索引-21不存在!只有20个元素

# 检查条件
if len(self.price_history) > self.long_window:  # 20 > 20 ❌
    # 不满足,无法判断金叉/死叉

return {"action": "hold", "reason": "无交易信号"}
```

### 📅 Day 21: 第一次可以判断金叉/死叉!

```python
# Day 21 (2025-01-30)
quote = {'close': 11.10}
signal = strategy.on_bar(current_price=11.10, ...)

self.price_history.append(11.10)
# price_history = [10.50, ..., 11.10]  # 21个元素
len(price_history) = 21

# 1. 计算当前均线 (Day 21)
short_ma = sum(price_history[-5:]) / 5
         = sum([Day 17, Day 18, Day 19, Day 20, Day 21]) / 5
         = (10.50 + 10.80 + 11.00 + 10.90 + 11.10) / 5
         = 54.30 / 5
         = 10.86

long_ma = sum(price_history[-20:]) / 20
        = sum(Day 2到Day 21的价格) / 20
        = 10.78

# 2. 计算前一天均线 (Day 20)
prev_short_ma = sum(price_history[-6:-1]) / 5
             = sum(Day 16到Day 20的价格) / 5
             = 10.70

prev_long_ma = sum(price_history[-21:-1]) / 20
            = sum(Day 1到Day 20的价格) / 20
            = 10.75

# 3. 判断金叉
if prev_short_ma <= prev_long_ma and short_ma > long_ma:
    # 10.70 <= 10.75 ✅
    # 10.86 > 10.78 ✅
    return {"action": "buy", "amount": 9000, "reason": "金叉: 短期均线(10.86)上穿长期均线(10.78)"}

# ✨ 金叉买入!
```

---

## 5. 实战案例分析

### 📊 真实回测案例

使用回测任务 `bt_20260209_153019_173344`:

**参数**:
- stock_code: 000001.SZ
- start_date: 2025-02-03
- end_date: 2025-12-31
- short_window: 5
- long_window: 20

**修复前的问题**:
```python
# 修复前: 只买不卖
2025-03-03: 买入 9100股 @ ¥10.93
原因: "初始买入"
之后永远持有...
```

**修复后的预期**:

```python
# 修复后: 正确执行双均线策略

# Day 20 (数据积累完成)
price_history长度 = 20
MA5 = 10.95
MA20 = 10.80
状态: 观望

# Day 25 (假设)
price_history长度 = 25
前一日: MA5=10.82, MA20=10.85  (短期 < 长期)
当前:   MA5=10.92, MA20=10.88  (短期 > 长期)
判断: ✨ 金叉!
操作: 买入

# Day 60 (假设,价格下跌)
price_history长度 = 60
前一日: MA5=11.05, MA20=10.95  (短期 > 长期)
当前:   MA5=10.85, MA20=10.98  (短期 < 长期)
判断: 💀 死叉!
操作: 卖出
```

### 🔍 调试验证方法

**1. 添加日志输出**:

```python
# app/strategies/dual_ma.py (修改版)

def on_bar(self, bar_id, timestamp, current_price, position, cash):
    self.price_history.append(current_price)

    if len(self.price_history) < self.long_window:
        return {"action": "hold", "amount": 0, "reason": "数据积累中"}

    # 计算均线
    short_ma = sum(self.price_history[-self.short_window:]) / self.short_window
    long_ma = sum(self.price_history[-self.long_window:]) / self.long_window

    # ← 添加日志
    logger.debug(f"Day {len(self.price_history)}: price={current_price:.2f}, "
                f"MA5={short_ma:.2f}, MA20={long_ma:.2f}")

    if len(self.price_history) > self.long_window:
        prev_short_ma = sum(self.price_history[-self.short_window-1:-1]) / self.short_window
        prev_long_ma = sum(self.price_history[-self.long_window-1:-1]) / self.long_window

        # ← 添加日志
        logger.debug(f"  前一日: MA5={prev_short_ma:.2f}, MA20={prev_long_ma:.2f}")

        # 判断金叉
        if prev_short_ma <= prev_long_ma and short_ma > long_ma:
            logger.info(f"✨ 金叉! MA5从{prev_short_ma:.2f}涨到{short_ma:.2f}, "
                       f"MA20从{prev_long_ma:.2f}涨到{long_ma:.2f}")
            ...

        # 判断死叉
        elif prev_short_ma >= prev_long_ma and short_ma < long_ma:
            logger.info(f"💀 死叉! MA5从{prev_short_ma:.2f}跌到{short_ma:.2f}, "
                       f"MA20从{prev_long_ma:.2f}跌到{long_ma:.2f}")
            ...
```

**2. 查看日志**:

```bash
# 运行回测后查看日志
tail -f logs/app.log | grep "MA5\|金叉\|死叉"
```

**3. 手动验证**:

从数据库读取价格数据,手动计算均线,验证策略是否正确:

```python
# 读取某天的数据
quotes = db.stock_quotes.find({
    'stock_code': '000001.SZ',
    'date': {'$lte': '2025-03-10'}
}).sort('date', 1).limit(25)

prices = [q['close'] for q in quotes]

# 手动计算MA5和MA20
MA5 = sum(prices[-5:]) / 5
MA20 = sum(prices[-20:]) / 20

print(f"MA5: {MA5:.2f}")
print(f"MA20: {MA20:.2f}")
```

---

## 📝 总结

### 核心代码位置

1. **策略初始化**: `app/strategies/dual_ma.py:16-20`
2. **价格数据传入**: `app/strategies/dual_ma.py:75-76`
3. **MA5计算**: `app/strategies/dual_ma.py:83`
4. **MA20计算**: `app/strategies/dual_ma.py:86`
5. **前一日MA计算**: `app/strategies/dual_ma.py:90-91`
6. **金叉判断**: `app/strategies/dual_ma.py:94-103`
7. **死叉判断**: `app/strategies/dual_ma.py:106-112`

### 计算公式

```python
# 5日均线
MA5 = sum(最近5天收盘价) / 5

# 20日均线
MA20 = sum(最近20天收盘价) / 20

# 前一天5日均线
MA5_昨天 = sum(倒数第2到第6天的收盘价) / 5

# 前一天20日均线
MA20_昨天 = sum(倒数第2到第21天的收盘价) / 20
```

### Python切片技巧

```python
prices = [p1, p2, p3, ..., pn]  # n个价格

# 取最后5个
prices[-5:]      # [p(n-4), p(n-3), p(n-2), p(n-1), pn]

# 取倒数第2到第6个
prices[-6:-1]    # [p(n-5), p(n-4), p(n-3), p(n-2), p(n-1)]

# 取最后20个
prices[-20:]     # [p(n-19), ..., pn]
```

这就是当前项目中双均线策略的完整计算流程! 🎓
