# 数据库结构分析

## 数据库架构概述

TradingAgents-CN 使用 MongoDB 作为主数据库，Redis 作为缓存和队列存储。数据库设计遵循文档型数据库的最佳实践，通过集合（Collection）组织不同业务领域的数据。

## MongoDB 数据库

### 数据库名称

```
tradingagents
```

### 集合列表

1. **backtest_tasks** - 回测任务
2. **backtest_daily_states** - 每日状态快照
3. **backtest_trades** - 交易记录
4. **backtest_results** - 回测结果
5. **stock_info** - 股票基本信息
6. **stock_quotes** - 股票行情数据
7. **trading_calendar** - 交易日历
8. **users** - 用户信息
9. **saved_params** - 保存的参数配置
10. **operation_logs** - 操作日志

## 核心集合详解

### 1. backtest_tasks (回测任务)

存储所有回测任务的基本信息和状态。

#### 索引设计

```javascript
// 主索引
db.backtest_tasks.createIndex({ "backtest_id": 1 }, { unique: true })

// 用户查询索引
db.backtest_tasks.createIndex({ "user_id": 1, "created_at": -1 })

// 状态查询索引
db.backtest_tasks.createIndex({ "status": 1, "created_at": -1 })
```

#### 文档结构

```javascript
{
  "_id": ObjectId("..."),
  "backtest_id": "bt_20240205_143055_123456",
  "user_id": "user123",
  "status": "running",  // created/running/paused/completed/failed/aborted

  // 回测参数
  "parameters": {
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

  // 执行信息
  "execution_info": {
    "current_bar_index": 150,
    "total_bars": 500,
    "current_date": "2024-01-15",
    "progress": 30.0,
    "start_time": ISODate("2024-02-05T14:30:55.123Z"),
    "elapsed_time": 45.2,
    "estimated_time_remaining": 105.6
  },

  // 错误信息（可选）
  "error": {
    "code": "INSUFFICIENT_DATA",
    "message": "数据不足：需要至少26个交易日的数据"
  },

  // 时间戳
  "created_at": ISODate("2024-02-05T14:30:55.123Z"),
  "updated_at": ISODate("2024-02-05T14:35:40.123Z")
}
```

### 2. backtest_daily_states (每日状态)

存储每个交易日的状态快照，用于资金曲线计算和回放。

#### 索引设计

```javascript
// 复合索引：回测ID + K线索引
db.backtest_daily_states.createIndex(
  { "backtest_id": 1, "bar_index": 1 },
  { unique: true }
)

// 日期查询索引
db.backtest_daily_states.createIndex(
  { "backtest_id": 1, "date": 1 }
)
```

#### 文档结构

```javascript
{
  "_id": ObjectId("..."),
  "backtest_id": "bt_20240205_143055_123456",
  "date": "2024-01-15",
  "bar_index": 150,

  // 资金状态
  "cash": 45123.45,
  "position": 500,
  "position_cost": 98.76,
  "current_price": 102.56,
  "market_value": 51280.00,
  "total_assets": 96403.45,

  // 收益指标
  "daily_return": 0.0123,
  "cumulative_return": 0.0345,
  "profit_loss": 1900.00,

  "created_at": ISODate("2024-02-05T14:35:40.123Z")
}
```

### 3. backtest_trades (交易记录)

存储所有交易明细，包括买入和卖出。

#### 索引设计

```javascript
// 回测ID查询
db.backtest_trades.createIndex({ "backtest_id": 1, "date": 1 })

// 类型查询
db.backtest_trades.createIndex({ "backtest_id": 1, "trade_type": 1 })
```

#### 文档结构

```javascript
{
  "_id": ObjectId("..."),
  "backtest_id": "bt_20240205_143055_123456",
  "date": "2024-01-15",
  "trade_type": "buy",  // buy/sell

  // 股票信息
  "stock_code": "000001.SZ",
  "stock_name": "平安银行",

  // 交易信息
  "price": 102.56,
  "shares": 500,
  "amount": 51280.00,

  // 费用明细
  "commission": 12.82,
  "stamp_duty": 0.0,
  "slippage": 0.0,
  "total_cost": 25.64,

  // 状态变化
  "cash_before": 50000.00,
  "cash_after": 45123.45,
  "position_before": 0,
  "position_after": 500,

  // 盈亏（卖出时）
  "cost_basis": null,
  "profit_loss": 0.0,

  // 交易信号
  "signal": {
    "action": "buy",
    "amount": 500,
    "reason": "金叉买入"
  },

  "created_at": ISODate("2024-02-05T14:35:40.123Z")
}
```

### 4. backtest_results (回测结果)

存储回测完成后的统计结果。

#### 索引设计

```javascript
// 唯一索引
db.backtest_results.createIndex({ "backtest_id": 1 }, { unique: true })

// 用户结果查询
db.backtest_results.createIndex({ "backtest_id": 1, "created_at": -1 })
```

#### 文档结构

```javascript
{
  "_id": ObjectId("..."),
  "backtest_id": "bt_20240205_143055_123456",

  // 收益指标
  "return_metrics": {
    "total_return": 0.1523,
    "annual_return": 0.1825,
    "cumulative_returns": [0.0012, 0.0023, ...],
    "daily_returns": [0.0012, 0.0011, ...]
  },

  // 风险指标
  "risk_metrics": {
    "max_drawdown": -0.0842,
    "volatility": 0.1523,
    "downside_volatility": 0.0956,
    "var_95": -0.0234
  },

  // 风险调整收益指标
  "risk_adjusted_metrics": {
    "sharpe_ratio": 1.23,
    "sortino_ratio": 1.56,
    "calmar_ratio": 2.17
  },

  // 交易统计
  "trading_stats": {
    "total_trades": 25,
    "winning_trades": 15,
    "losing_trades": 10,
    "win_rate": 0.6,
    "avg_profit": 0.0345,
    "avg_loss": -0.0212,
    "profit_loss_ratio": 1.63
  },

  // 资金曲线
  "equity_curve": {
    "dates": ["2024-01-01", "2024-01-02", ...],
    "total_assets": [100000, 101234, ...],
    "cash": [50000, 49876, ...],
    "position_value": [50000, 51358, ...]
  },

  "created_at": ISODate("2024-02-05T14:40:00.123Z")
}
```

### 5. stock_info (股票基本信息)

存储股票的基本信息。

#### 索引设计

```javascript
// 唯一索引
db.stock_info.createIndex({ "symbol": 1 }, { unique: true })

// 名称搜索
db.stock_info.createIndex({ "name": 1 })

// 市场筛选
db.stock_info.createIndex({ "market": 1, "symbol": 1 })
```

#### 文档结构

```javascript
{
  "_id": ObjectId("..."),
  "symbol": "000001.SZ",
  "name": "平安银行",
  "market": "A股",
  "exchange": "深圳证券交易所",
  "industry": "银行",
  "list_date": "1991-04-03",
  "updated_at": ISODate("2024-02-05T14:30:00.123Z")
}
```

### 6. stock_quotes (股票行情数据)

存储日线级别的行情数据。

#### 索引设计

```javascript
// 复合唯一索引
db.stock_quotes.createIndex(
  { "symbol": 1, "date": 1 },
  { unique: true }
)

// 日期范围查询
db.stock_quotes.createIndex({ "symbol": 1, "date": -1 })
```

#### 文档结构

```javascript
{
  "_id": ObjectId("..."),
  "symbol": "000001.SZ",
  "date": "2024-01-15",
  "open": 100.50,
  "high": 102.30,
  "low": 99.80,
  "close": 101.50,
  "volume": 12345678,
  "amount": 1254321000.00,
  "updated_at": ISODate("2024-01-16T00:00:00.000Z")
}
```

### 7. trading_calendar (交易日历)

存储交易日历信息，包括交易日和节假日。

#### 索引设计

```javascript
// 唯一索引
db.trading_calendar.createIndex({ "date": 1 }, { unique: true })

// 交易日标记
db.trading_calendar.createIndex({ "is_trading_day": 1, "date": 1 })
```

#### 文档结构

```javascript
{
  "_id": ObjectId("..."),
  "date": "2024-01-15",
  "is_trading_day": true,
  "is_holiday": false,
  "holiday_name": null,
  "created_at": ISODate("2024-01-01T00:00:00.000Z")
}
```

### 8. users (用户信息)

存储用户账户信息。

#### 索引设计

```javascript
// 唯一索引
db.users.createIndex({ "user_id": 1 }, { unique: true })
db.users.createIndex({ "username": 1 }, { unique: true })
db.users.createIndex({ "email": 1 }, { unique: true, sparse: true })
```

#### 文档结构

```javascript
{
  "_id": ObjectId("..."),
  "user_id": "user123",
  "username": "user123",
  "password_hash": "hashed_password",
  "email": "user@example.com",
  "role": "user",  // user/admin
  "is_active": true,
  "created_at": ISODate("2024-01-01T00:00:00.000Z"),
  "last_login": ISODate("2024-02-05T14:30:00.000Z")
}
```

### 9. saved_params (保存的参数)

存储用户保存的回测参数配置。

#### 索引设计

```javascript
// 用户查询
db.saved_params.createIndex({ "user_id": 1, "created_at": -1 })

// 默认参数查询
db.saved_params.createIndex({ "user_id": 1, "is_default": -1 })
```

#### 文档结构

```javascript
{
  "_id": ObjectId("..."),
  "id": "param_123456",
  "user_id": "user123",
  "name": "常用配置-平安银行",
  "description": "平安银行2024年回测配置",
  "usage_count": 5,
  "is_default": false,

  // 参数内容
  "params": {
    "stock_code": "000001.SZ",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "initial_capital": 100000.0,
    "min_purchase": 100,
    "strategy_id": "dual_ma",
    "strategy_params": {
      "short_window": 5,
      "long_window": 20
    }
  },

  "created_at": ISODate("2024-01-01T00:00:00.000Z"),
  "updated_at": ISODate("2024-02-05T14:30:00.000Z")
}
```

### 10. operation_logs (操作日志)

存储用户操作日志，用于审计和问题排查。

#### 索引设计

```javascript
// 用户操作查询
db.operation_logs.createIndex({ "user_id": 1, "created_at": -1 })

// 操作类型查询
db.operation_logs.createIndex({ "action": 1, "created_at": -1 })

// 资源查询
db.operation_logs.createIndex({ "resource_type": 1, "resource_id": 1 })
```

#### 文档结构

```javascript
{
  "_id": ObjectId("..."),
  "user_id": "user123",
  "action": "start_backtest",
  "resource_type": "backtest",
  "resource_id": "bt_20240205_143055_123456",
  "details": {
    "stock_code": "000001.SZ",
    "strategy_id": "dual_ma"
  },
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "created_at": ISODate("2024-02-05T14:30:55.123Z")
}
```

## Redis 数据结构

### Key 命名约定

```
{namespace}:{identifier}:{field}
```

### 1. 缓存 Keys

#### 股票信息缓存

```
stock:info:{symbol}
```

**示例**: `stock:info:000001.SZ`

**TTL**: 86400 秒（24小时）

#### 行情数据缓存

```
quotes:{symbol}:{start_date}:{end_date}
```

**示例**: `quotes:000001.SZ:2024-01-01:2024-12-31`

**TTL**: 3600 秒（1小时）

#### 交易日历缓存

```
trading_calendar:{year}
```

**示例**: `trading_calendar:2024`

**TTL**: 604800 秒（7天）

### 2. 队列 Keys

#### 分析队列

```
analysis_queue:user:{user_id}
analysis_queue:global
```

**数据结构**: List

**可见性超时**: 300 秒

#### 回测队列（未来扩展）

```
backtest_queue:user:{user_id}
backtest_queue:global
```

### 3. 进度跟踪 Keys

#### 回测进度

```
progress:backtest:{backtest_id}
```

**数据结构**: Hash

**字段**:
- current_bar: 当前K线索引
- total_bars: 总K线数
- progress: 进度百分比
- status: 当前状态

#### WebSocket 连接

```
websocket:backtest:{backtest_id}
```

**数据结构**: Set

存储连接的客户端 ID

### 4. Session Keys

#### 用户会话

```
session:{user_id}
```

**TTL**: 86400 秒（24小时）

#### 限流计数

```
rate_limit:{user_id}:{endpoint}
```

**TTL**: 60 秒

## 数据库设计原则

### 1. 索引策略

- **唯一索引**: 保证数据唯一性
- **复合索引**: 优化常用查询组合
- **时间索引**: 支持时间范围查询
- **稀疏索引**: 可选字段使用稀疏索引

### 2. 分片策略（未来扩展）

- **按用户ID分片**: `user_id`
- **按时间分片**: `created_at`
- **按股票分片**: `symbol`

### 3. TTL 策略

- **缓存数据**: 短期 TTL（小时级）
- **历史数据**: 长期保留
- **临时数据**: 自动过期

### 4. 数据归档

- **回测任务**: 完成后90天归档
- **操作日志**: 180天后归档
- **每日状态**: 与回测任务一同归档

## 数据一致性保证

### 1. 事务处理

对于关键操作使用 MongoDB 事务：

```python
async with await client.start_session() as session:
    async with session.start_transaction():
        # 创建任务
        await db.backtest_tasks.insert_one(task_doc, session=session)
        # 初始化状态
        await db.backtest_daily_states.insert_many(states, session=session)
```

### 2. 乐观锁

使用版本号控制并发更新：

```python
{
    "_id": ObjectId("..."),
    "version": 1,
    "data": {...}
}

# 更新时检查版本
db.collection.update_one(
    {"_id": id, "version": 1},
    {"$set": {"data": new_data, "version": 2}}
)
```

### 3. 缓存一致性

数据变更时清理缓存：

```python
# 更新股票信息
await db.stock_info.update_one({"symbol": symbol}, update_data)

# 清理缓存
await redis_client.delete(f"stock:info:{symbol}")
```

## 数据备份策略

### 1. 全量备份

- **频率**: 每天凌晨2点
- **保留**: 30天
- **工具**: mongodump

### 2. 增量备份

- **频率**: 每小时
- **保留**: 7天
- **工具**: MongoDB Oplog

### 3. Redis 备份

- **RDB**: 每小时快照
- **AOF**: 实时追加
- **保留**: 7天

## 性能优化

### 1. 查询优化

- 使用投影限制返回字段
- 使用 $slice 限制数组返回
- 使用聚合管道预计算

### 2. 写入优化

- 批量写入使用 insert_many
- 使用无序写入提高速度
- 合理设置 write concern

### 3. 索引优化

- 复合索引字段顺序很重要
- 避免过多索引影响写入性能
- 定期重建碎片化索引

## 监控指标

### 1. 连接池

```python
# MongoDB 连接池
"maxPoolSize": 100,
"minPoolSize": 10

# Redis 连接池
"max_connections": 50
```

### 2. 查询性能

- 慢查询日志（>100ms）
- 查询分析器使用情况
- 索引命中率

### 3. 存储空间

- 集合大小监控
- 索引大小监控
- 数据增长趋势

## 数据迁移

### 1. 版本迁移

```python
# 迁移脚本示例
async def migrate_v1_to_v2():
    # 添加新字段
    await db.backtest_tasks.update_many(
        {"new_field": {"$exists": False}},
        {"$set": {"new_field": default_value}}
    )
```

### 2. 数据修复

```python
# 修复损坏的数据
async def fix_corrupted_data():
    # 找出问题数据
    corrupted = await db.collection.find({"status": None}).to_list(None)

    # 批量修复
    for doc in corrupted:
        await db.collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"status": "unknown"}}
        )
```
