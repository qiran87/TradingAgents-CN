# K线数据存储说明

## 🎯 快速回答

**问题**: 这个项目里,具体有哪张表会存K线?还是说每次K线都是实时计算的?

**答案**:
- ✅ **K线数据存储在数据库表中**,不是实时计算
- 📊 **主要表**: `stock_daily_quotes` (1557万+条记录)
- 📊 **次要表**: `stock_quotes` (用于临时/测试数据)
- 💾 **数据来源**: 定时从Tushare/AKShare等数据源同步

---

## 📊 K线数据表详解

### 1️⃣ `stock_daily_quotes` - 主要K线表

**用途**: 存储所有股票的日线K线数据

**数据量**: 15,578,263条记录 (1557万+)

**表结构**:
```javascript
{
  _id: ObjectId,
  symbol: "600000",              // 股票代码(6位)
  code: "600000",                // 股票代码
  full_symbol: "600000.SH",      // 完整代码
  market: "CN",                  // 市场类型
  trade_date: "1999-11-10",      // 交易日期
  period: "daily",               // 周期(日线)
  data_source: "akshare",        // 数据源

  // K线数据
  open: 10.50,                   // 开盘价
  high: 10.80,                   // 最高价
  low: 10.30,                    // 最低价
  close: 10.70,                  // 收盘价
  pre_close: 10.40,              // 昨收
  volume: 1740850.0,             // 成交量
  amount: 4859102000.0,          // 成交额
  change: 2.69,                  // 涨跌额
  pct_chg: 66.92,                // 涨跌幅%

  created_at: DateTime,           // 创建时间
  updated_at: DateTime,           // 更新时间
  version: 1                     // 版本
}
```

**数据范围**:
- 从1999年开始至今
- 覆盖A股所有股票
- 每天同步更新

---

### 2️⃣ `stock_quotes` - 临时/测试K线表

**用途**:
- 测试数据
- 临时存储
- 回测专用数据

**数据量**: 151条记录 (测试数据)

**表结构**:
```javascript
{
  _id: ObjectId,
  stock_code: "000001.SZ",      // 股票代码
  date: "2025-01-02",            // 交易日期

  // K线数据
  open: 9.9,                    // 开盘价
  high: 10.1,                   // 最高价
  low: 9.85,                    // 最低价
  close: 10.0,                  // 收盘价
  volume: 1000000,              // 成交量
  amount: 10000000.0            // 成交额
}
```

---

### 3️⃣ `market_quotes` - 实时行情表

**用途**:
- 实时行情数据
- 当前价格快照
- 最新的交易数据

**数据量**: 5,478条记录

**表结构**:
```javascript
{
  _id: ObjectId,
  symbol: "920000",             // 股票代码
  code: "920000",
  trade_date: "20260206",       // 交易日期

  // K线数据
  open: 18.85,
  high: 18.94,
  low: 18.71,
  close: 18.79,
  pre_close: 18.69,
  volume: 453647.0,
  amount: 8531625.0,
  pct_chg: 0.535,

  updated_at: DateTime
}
```

---

## 🔄 回测时的K线获取流程

### 完整数据流

```
用户发起回测请求
    ↓
POST /api/backtest/start
{
  "stock_code": "000001.SZ",
  "start_date": "2025-01-01",
  "end_date": "2025-12-31"
}
    ↓
BacktestEngine.run_backtest()
    ↓
_get_quotes()  // 获取K线
    ↓
BacktestStockDataService.get_quotes()
    ↓
1. 检查Redis缓存
   key: "stock_quotes:000001.SZ:2025-01-01:2025-12-31"
   ↓
2. 如果缓存命中 → 直接返回
   ↓
3. 如果缓存未命中 → 查询数据库
   ↓
   查询 stock_daily_quotes 集合:
   find({
     "symbol": {"$regex": "^000001"},
     "trade_date": {"$gte": "2025-01-01", "$lte": "2025-12-31"}
   }).sort("trade_date", 1)
   ↓
4. 返回K线数据数组
   [
     {trade_date: "2025-01-02", open: 10.0, close: 10.5, ...},
     {trade_date: "2025-01-03", open: 10.5, close: 10.7, ...},
     ...
   ]
   ↓
5. 写入Redis缓存 (TTL=1天)
   ↓
6. 回测引擎使用K线数据执行策略
```

---

## 💾 数据存储策略

### 三级缓存架构

```
Level 1: Redis缓存 (最快)
   ↓ 未命中
Level 2: MongoDB stock_daily_quotes (快)
   ↓ 未找到
Level 3: 实时API调用 (慢, Tushare/AKShare)
   ↓
写入MongoDB + 写入Redis
```

### 代码实现

**app/services/backtest_stock_data_service_v2.py:157-250**:

```python
async def get_quotes(self, stock_code, start_date, end_date):
    # 1. 检查Redis缓存
    cache_key = f"stock_quotes:{stock_code}:{start_date}:{end_date}"
    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)  # ✅ 缓存命中,直接返回

    # 2. 查询MongoDB
    cursor = db.stock_daily_quotes.find({
        "symbol": {"$regex": f"^{code_6}"},
        "trade_date": {"$gte": start_date, "$lte": end_date}
    }).sort("trade_date", 1)

    quotes = await cursor.to_list(length=3000)

    # 3. 如果MongoDB没有,实时获取
    if not quotes:
        quotes = await self._fetch_from_api(stock_code, start_date, end_date)
        # 存入MongoDB
        await db.stock_daily_quotes.insert_many(quotes)

    # 4. 写入Redis缓存
    await redis.setex(cache_key, 86400, json.dumps(quotes))  # 缓存1天

    return quotes
```

---

## 📈 数据同步机制

### 定时同步任务

**app/worker/tushare_sync_service.py**:
```python
# 每天收盘后自动同步
@scheduler.scheduled_job('cron', hour=16, minute=30)
async def sync_daily_data():
    """每天16:30同步当日K线数据"""
    for stock in all_stocks:
        quotes = await fetch_from_tushare(stock)
        await db.stock_daily_quotes.insert_many(quotes)
```

### 数据源优先级

```python
# 1. Tushare (专业,付费)
# 2. AKShare (免费,推荐)
# 3. BaoStock (免费)
```

---

## 🎯 实际使用示例

### 回测时获取K线

**回测请求**:
```python
# 1. 用户发起回测
POST /api/backtest/start
{
  "stock_code": "000001.SZ",
  "start_date": "2025-01-01",
  "end_date": "2025-07-31"
}
```

**后端处理**:
```python
# 2. 回测引擎获取K线
quotes = await _get_quotes(parameters)

# 3. 实际执行的SQL查询
db.stock_daily_quotes.find({
  "symbol": {"$regex": "^000001"},  # 匹配000001开头
  "trade_date": {
    "$gte": "2025-01-01",
    "$lte": "2025-07-31"
  }
}).sort("trade_date", 1)

# 4. 返回K线数组
quotes = [
  {"trade_date": "2025-01-02", "open": 10.0, "close": 10.5, ...},
  {"trade_date": "2025-01-03", "open": 10.5, "close": 10.7, ...},
  ...
]

# 5. 回测引擎遍历K线
for quote in quotes:
    signal = strategy.on_bar(current_price=quote['close'], ...)
```

---

## 🔍 查询K线数据

### 通过MongoDB直接查询

```python
# 查询某股票的K线
db.stock_daily_quotes.find({
  "symbol": "000001",
  "trade_date": {"$gte": "2025-01-01", "$lte": "2025-07-31"}
}).sort("trade_date", 1)

# 查询最新一条
db.stock_daily_quotes.find({
  "symbol": "000001"
}).sort("trade_date", -1).limit(1)
```

### 通过API查询

```python
# 前端API调用
GET /api/stocks/000001.SZ/quotes?start=2025-01-01&end=2025-07-31

# 返回
{
  "success": true,
  "data": [
    {"date": "2025-01-02", "open": 10.0, "high": 10.5, ...},
    ...
  ]
}
```

---

## 📝 总结

### K线数据存储方式

| 表名 | 用途 | 数据量 | 字段特点 |
|------|------|--------|----------|
| **stock_daily_quotes** | 主要K线表 | 1557万+ | symbol, trade_date, OHLCV |
| **stock_quotes** | 临时/测试 | 少量 | stock_code, date, OHLCV |
| **market_quotes** | 实时行情 | 5478 | 最新的快照数据 |

### 数据获取方式

**不是实时计算**,而是:
1. ✅ **存储在数据库** (`stock_daily_quotes`)
2. ✅ **Redis缓存加速** (1天TTL)
3. ✅ **定时同步更新** (每天收盘后)
4. ✅ **按需实时获取** (如果缓存未命中且数据库没有)

### 性能优化

```
首次查询: API → MongoDB → Redis → 用户
    ↓ 慢 (~1秒)

后续查询: Redis → 用户
    ↓ 快 (~10ms)

缓存过期: 重新从MongoDB加载
```

---

## 🎓 关键要点

1. **K线不是实时计算的**,而是从数据库读取
2. **主要存储在** `stock_daily_quotes` 表
3. **有Redis缓存**,提高读取速度
4. **定时同步**,保证数据新鲜度
5. **多级缓存**,确保高可用性

**代码位置**:
- 数据读取: `app/services/backtest_stock_data_service_v2.py:157-250`
- 数据同步: `app/worker/tushare_sync_service.py`
- 数据库表: `stock_daily_quotes` (1557万条记录)

希望这个说明能帮你完全理解K线数据的存储机制! 📚
