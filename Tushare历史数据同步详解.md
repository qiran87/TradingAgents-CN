# Tushare 历史数据同步详解

## 📋 目录

1. [数据同步概述](#数据同步概述)
2. [同步的数据类型](#同步的数据类型)
3. [数据存储位置](#数据存储位置)
4. [数据结构详解](#数据结构详解)
5. [同步逻辑](#同步逻辑)
6. [查看和管理数据](#查看和管理数据)

---

## 数据同步概述

### 定时任务配置

Tushare 历史数据同步通过 APScheduler 定时任务自动执行：

```python
# app/main.py 中的定时任务配置

# 1. 基础信息同步（每天凌晨 2:00）
scheduler.add_job(
    run_tushare_basic_info_sync,
    CronTrigger(hour=2, minute=0),
    id="tushare_basic_info_sync"
)

# 2. 实时行情同步（交易时间每 5 分钟）
scheduler.add_job(
    run_tushare_quotes_sync,
    CronTrigger(day_of_week="mon-fri", hour="9-15", minute="*/5"),
    id="tushare_quotes_sync"
)

# 3. 历史数据同步（每天收盘后 16:00）
scheduler.add_job(
    run_tushare_historical_sync,
    CronTrigger(hour=16, minute=0),
    id="tushare_historical_sync"
)

# 4. 财务数据同步（每天凌晨 3:00）
scheduler.add_job(
    run_tushare_financial_sync,
    CronTrigger(hour=3, minute=0),
    id="tushare_financial_sync"
)
```

### 同步服务类

**文件位置**: `app/worker/tushare_sync_service.py`

**核心类**: `TushareSyncService`

```python
class TushareSyncService:
    """Tushare 数据同步服务"""

    def __init__(self):
        self.provider = TushareProvider()  # Tushare 数据提供者
        self.stock_service = get_stock_data_service()
        self.historical_service = None  # 历史数据服务
        self.news_service = None  # 新闻数据服务
        self.db = get_mongo_db()  # MongoDB 数据库

        # 同步配置
        self.batch_size = 100  # 批量处理大小
        self.rate_limiter = get_tushare_rate_limiter()  # 速率限制器
```

---

## 同步的数据类型

Tushare 定时任务会同步以下 **4 类数据**：

### 1️⃣ **股票基础信息** (`stock_basic_info`)

**同步时间**: 每天凌晨 2:00

**数据内容**:
- 股票代码、名称
- 市场类型（主板/创业板/科创板/北交所）
- 行业分类
- 上市日期
- 股票状态（上市/退市）

**同步函数**: `sync_stock_basic_info()`

**代码位置**: `app/worker/tushare_sync_service.py:75-224`

---

### 2️⃣ **实时行情数据** (`market_quotes`)

**同步时间**: 交易日 9:00-15:00，每 5 分钟

**数据内容**:
- 当前价格
- 涨跌额、涨跌幅
- 成交量、成交额
- 买卖价档

**同步函数**: `sync_realtime_quotes()`

**代码位置**: `app/worker/tushare_sync_service.py:228-424`

**策略**:
- 少量股票（≤10 只）：自动切换到 AKShare（避免浪费 Tushare 配额）
- 大量股票或全市场：使用 Tushare 批量接口

---

### 3️⃣ **历史数据** (`stock_daily_quotes`) ⭐

**同步时间**: 每天收盘后 16:00

**数据内容**:
- OHLCV 数据（开高低收成交量）
- 技术指标（均线、RSI 等）
- 复权数据

**同步函数**: `sync_historical_data()`

**代码位置**: `app/worker/tushare_sync_service.py:543-742`

**周期类型**:
- `daily` - 日线数据（默认）
- `weekly` - 周线数据
- `monthly` - 月线数据

---

### 4️⃣ **财务数据** (`stock_financials`)

**同步时间**: 每天凌晨 3:00

**数据内容**:
- 营业收入、净利润
- 资产负债表数据
- 现金流量表数据
- 财务指标（ROE、PE、PB 等）

**同步函数**: `sync_financial_data()`

**代码位置**: `app/worker/tushare_sync_service.py:838-949`

**默认获取**: 最近 20 期财报（约 5 年数据）

---

## 数据存储位置

### MongoDB 集合（表）

| 数据类型 | 集合名称 | 说明 |
|---------|---------|------|
| 股票基础信息 | `stock_basic_info` | 股票列表、基本信息 |
| 实时行情 | `market_quotes` | 最新市场行情 |
| **历史数据** | **`stock_daily_quotes`** | **OHLCV 历史数据 ⭐** |
| 财务数据 | `stock_financials` | 财务报表数据 |
| 分析任务 | `analysis_tasks` | 分析任务记录 |
| 用户数据 | `users` | 用户账号信息 |

### 数据库信息

```
数据库名: tradingagents
MongoDB 地址: mongodb://admin:tradingagents123@localhost:27017
认证数据库: admin
```

---

## 数据结构详解

### 🎯 历史数据集合 - `stock_daily_quotes`

这是您最关心的集合，存储所有股票的历史行情数据。

#### 集合结构

```javascript
{
  "_id": ObjectId("..."),

  // ========== 基础字段（必填） ==========
  "symbol": "000001",              // 股票代码（6位）
  "trade_date": "2025-02-04",     // 交易日期（YYYY-MM-DD）
  "period": "daily",               // 周期：daily/weekly/monthly
  "data_source": "tushare",        // 数据源：tushare/akshare/baostock

  // ========== OHLCV 数据 ==========
  "open": 12.45,                   // 开盘价
  "high": 12.58,                   // 最高价
  "low": 12.38,                    // 最低价
  "close": 12.50,                  // 收盘价
  "volume": 12345678,              // 成交量（股）
  "amount": 154321000.00,          // 成交额（元）

  // ========== 复权数据 ==========
  "adj_factor": 0.9876,            // 复权因子
  "adj_open": 12.29,               // 复权开盘价
  "adj_high": 12.42,               // 复权最高价
  "adj_low": 12.22,                // 复权最低价
  "adj_close": 12.34,              // 复权收盘价

  // ========== 技术指标（预计算） ==========
  "ma5": 12.45,                    // 5日均线
  "ma10": 12.38,                   // 10日均线
  "ma20": 12.32,                   // 20日均线
  "ma60": 12.28,                   // 60日均线
  "rsi": 58.6,                     // RSI指标
  "macd": {
    "dif": 0.12,                   // DIF线
    "dea": 0.10,                   // DEA线
    "bar": 0.02                    // 柱状图
  },

  // ========== 涨跌信息 ==========
  "change": 0.05,                  // 涨跌额
  "change_pct": 0.40,              // 涨跌幅（%）
  "turnover": 2.5,                 // 换手率（%）

  // ========== 元数据 ==========
  "market": "CN",                  // 市场类型
  "name": "平安银行",              // 股票名称
  "created_at": ISODate("2025-02-04T16:30:00Z"),  // 创建时间
  "updated_at": ISODate("2025-02-04T16:30:00Z")   // 更新时间
}
```

#### 索引设计

```javascript
// 1. 复合唯一索引（用于去重和快速更新）
db.stock_daily_quotes.createIndex({
  "symbol": 1,
  "trade_date": 1,
  "data_source": 1,
  "period": 1
}, { unique: true })

// 2. 股票代码索引
db.stock_daily_quotes.createIndex({ "symbol": 1 })

// 3. 交易日期索引
db.stock_daily_quotes.createIndex({ "trade_date": -1 })

// 4. 复合索引（常用查询）
db.stock_daily_quotes.createIndex({
  "symbol": 1,
  "trade_date": -1
})
```

#### 数据示例

**查询平安银行最近 10 天的日线数据**:

```javascript
db.stock_daily_quotes.find({
  "symbol": "000001",
  "period": "daily"
})
.sort({ "trade_date": -1 })
.limit(10)
```

**查询特定日期范围的数据**:

```javascript
db.stock_daily_quotes.find({
  "symbol": "000001",
  "trade_date": {
    "$gte": "2025-01-01",
    "$lte": "2025-02-04"
  }
})
.sort({ "trade_date": 1 })
```

**统计数据总量**:

```javascript
// 统计总记录数
db.stock_daily_quotes.countDocuments({})

// 统计不同周期数据量
db.stock_daily_quotes.aggregate([
  { "$group": { "_id": "$period", "count": { "$sum": 1 } } }
])

// 统计覆盖的股票数量
db.stock_daily_quotes.distinct("symbol").length

// 统计数据日期范围
db.stock_daily_quotes.aggregate([
  { "$group": {
    "_id": null,
    "min_date": { "$min": "$trade_date" },
    "max_date": { "$max": "$trade_date" }
  }}
])
```

---

### 📊 其他集合结构

#### 1. `stock_basic_info` - 股票基础信息

```javascript
{
  "_id": ObjectId,
  "code": "000001",              // 股票代码
  "name": "平安银行",            // 股票名称
  "industry": "银行",             // 行业
  "market": "主板",              // 市场
  "list_date": "19910403",       // 上市日期（YYYYMMDD）
  "status": "L",                 // 状态：L=上市, D=退市, P=暂停
  "category": "stock_cn",        // 分类

  // 市场信息
  "market_info": {
    "market": "CN",              // 市场代码
    "currency": "CNY"            // 货币
  }
}
```

#### 2. `market_quotes` - 实时行情

```javascript
{
  "_id": ObjectId,
  "symbol": "000001",
  "name": "平安银行",
  "price": 12.50,                // 当前价
  "change": 0.05,
  "change_pct": 0.40,
  "volume": 12345678,
  "amount": 154321000.00,
  "high": 12.58,
  "low": 12.38,
  "open": 12.45,
  "prev_close": 12.45,
  "timestamp": ISODate("2025-02-04T14:30:00Z")
}
```

#### 3. `stock_financials` - 财务数据

```javascript
{
  "_id": ObjectId,
  "symbol": "000001",
  "report_period": "2024Q3",     // 报告期
  "report_type": "quarterly",    // 报告类型：quarterly/annual

  // 利润表
  "revenue": 123456789000.00,    // 营业收入
  "net_profit": 45678900000.00,  // 净利润

  // 资产负债表
  "total_assets": 9876543210000.00,
  "total_liabilities": 8765432100000.00,

  // 现金流量表
  "operating_cash_flow": 34567890000.00,

  // 财务指标
  "roe": 12.5,                   // 净资产收益率（%）
  "pe": 8.5,                     // 市盈率
  "pb": 0.9,                     // 市净率

  "created_at": ISODate("2025-02-04T16:30:00Z")
}
```

---

## 同步逻辑

### 历史数据同步流程

```
定时任务触发（每天 16:00）
    ↓
1. 获取股票列表
    ├─ 从 stock_basic_info 查询所有 A 股
    ├─ 排除退市股票（status != "D"）
    └─ 获取约 5000+ 只股票
    ↓
2. 确定同步策略
    ├─ 增量模式（默认）：从最后日期+1天开始
    ├─ 全量模式：从 1990-01-01 开始
    └─ 自定义范围：指定 start_date 和 end_date
    ↓
3. 遍历股票列表
    for symbol in symbols:
        ├─ 速率限制（避免超 API 配额）
        ├─ 调用 Tushare API: daily()
        ├─ 获取 DataFrame 数据
        ├─ 保存到 stock_daily_quotes 集合
        └─ 更新进度
    ↓
4. 完成统计
    ├─ 成功股票数
    ├─ 失败股票数
    ├─ 总记录数
    └─ 耗时统计
```

### 核心代码逻辑

**文件**: `app/worker/tushare_sync_service.py:543-742`

```python
async def sync_historical_data(
    self,
    symbols: List[str] = None,      # 股票代码列表
    start_date: str = None,         # 起始日期
    end_date: str = None,           # 结束日期
    incremental: bool = True,       # 是否增量同步
    all_history: bool = False,      # 是否全量同步
    period: str = "daily",          # 周期
    job_id: str = None
) -> Dict[str, Any]:
    """
    同步历史数据

    策略：
    1. 获取股票列表（排除退市股票）
    2. 确定同步日期范围
    3. 遍历每只股票
    4. 调用 Tushare API 获取数据
    5. 保存到 MongoDB
    """

    # 1. 获取股票列表
    if symbols is None:
        cursor = self.db.stock_basic_info.find({
            "$and": [
                {
                    "$or": [
                        {"market_info.market": "CN"},
                        {"category": "stock_cn"},
                        {"market": {"$in": ["主板", "创业板", "科创板", "北交所"]}}
                    ]
                },
                {
                    "$or": [
                        {"status": {"$ne": "D"}},  # 排除退市
                        {"status": {"$exists": False}}
                    ]
                }
            ]
        })
        symbols = [doc["code"] async for doc in cursor]

    # 2. 确定结束日期
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d')

    # 3. 遍历股票列表
    for i, symbol in enumerate(symbols):
        try:
            # 速率限制
            await self.rate_limiter.acquire()

            # 确定起始日期
            if incremental:
                symbol_start_date = await self._get_last_sync_date(symbol)
            elif all_history:
                symbol_start_date = "1990-01-01"
            else:
                symbol_start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

            # 调用 API
            df = await self.provider.get_historical_data(
                symbol,
                symbol_start_date,
                end_date,
                period=period
            )

            # 保存数据
            if df is not None and not df.empty:
                records_saved = await self._save_historical_data(
                    symbol,
                    df,
                    period=period
                )
                stats["total_records"] += records_saved

        except Exception as e:
            stats["error_count"] += 1
            logger.error(f"❌ {symbol} 同步失败: {e}")

    return stats
```

### 增量同步逻辑

增量同步会自动获取每只股票的最后日期：

```python
async def _get_last_sync_date(self, symbol: str) -> str:
    """获取最后同步日期"""

    # 从 stock_daily_quotes 查询最后日期
    latest_date = await self.historical_service.get_latest_date(symbol, "tushare")

    if latest_date:
        # 返回最后日期的下一天（避免重复）
        last_date_obj = datetime.strptime(latest_date, '%Y-%m-%d')
        next_date = last_date_obj + timedelta(days=1)
        return next_date.strftime('%Y-%m-%d')
    else:
        # 如果没有历史数据，从上市日期开始
        stock_info = await self.db.stock_basic_info.find_one(
            {"code": symbol},
            {"list_date": 1}
        )

        if stock_info and stock_info.get("list_date"):
            list_date = stock_info["list_date"]
            # 处理不同格式：20100101 或 2010-01-01
            if len(list_date) == 8 and list_date.isdigit():
                return f"{list_date[:4]}-{list_date[4:6]}-{list_date[6:]}"
            else:
                return list_date

        # 默认从 1990 年开始
        return "1990-01-01"
```

---

## 查看和管理数据

### 使用 Web 界面查看

```bash
# 启动 Mongo Express
./start-db-ui.sh
# 选择选项 1（Mongo Express）

# 浏览器访问
http://localhost:8082
```

**查看历史数据**:
1. 登录后点击 `tradingagents` 数据库
2. 点击 `stock_daily_quotes` 集合
3. 可以看到所有历史数据（默认显示 20 条）

**常用查询**（在 Mongo Express 中）:

```javascript
// 查询某只股票最近数据
{ "symbol": "000001" }

// 按日期排序
{ "symbol": "000001" }
排序: trade_date (降序)

// 日期范围查询
{
  "symbol": "000001",
  "trade_date": {
    "$gte": "2025-01-01",
    "$lte": "2025-02-04"
  }
}
```

### 使用命令行查看

```bash
# 连接 MongoDB
mongosh mongodb://admin:tradingagents123@localhost:27017/tradingagents?authSource=admin

# 切换数据库
use tradingagents

# 查看集合统计
db.stock_daily_quotes.countDocuments()

# 查看数据量
db.stock_daily_quotes.estimatedDocumentCount()

# 查看索引
db.stock_daily_quotes.getIndexes()

# 查询示例
```

#### 查询特定股票数据

```javascript
// 平安银行最近 10 天
db.stock_daily_quotes.find({
  "symbol": "000001",
  "period": "daily"
})
.sort({ "trade_date": -1 })
.limit(10)
.pretty()

// 万科最近一个月
db.stock_daily_quotes.find({
  "symbol": "000002",
  "trade_date": { "$gte": "2025-01-01" }
})
.sort({ "trade_date": 1 })
.pretty()
```

#### 统计分析

```javascript
// 统计每只股票的数据量
db.stock_daily_quotes.aggregate([
  { "$group": {
    "_id": "$symbol",
    "count": { "$sum": 1 },
    "min_date": { "$min": "$trade_date" },
    "max_date": { "$max": "$trade_date" }
  }},
  { "$sort": { "count": -1 } }
])

// 统计数据来源分布
db.stock_daily_quotes.aggregate([
  { "$group": {
    "_id": "$data_source",
    "count": { "$sum": 1 }
  }}
])

// 统计周期分布
db.stock_daily_quotes.aggregate([
  { "$group": {
    "_id": "$period",
    "count": { "$sum": 1 }
  }}
])

// 查看数据覆盖范围
db.stock_daily_quotes.aggregate([
  { "$group": {
    "_id": null,
    "total_symbols": { "$addToSet": "$symbol" },
    "min_date": { "$min": "$trade_date" },
    "max_date": { "$max": "$trade_date" }
  }},
  { "$project": {
    "symbol_count": { "$size": "$total_symbols" },
    "min_date": 1,
    "max_date": 1
  }}
])
```

### 手动触发同步

```bash
# 进入项目目录
cd /Users/qiran/LLM_Proj/LS_Proj/zp_ls/TradingAgents-CN

# 激活虚拟环境
source venv/bin/activate

# 方式一：使用脚本手动同步
python scripts/manual_sync.py --type historical --incremental true

# 方式二：在 Python 代码中调用
python -c "
import asyncio
from app.worker.tushare_sync_service import get_tushare_sync_service

async def manual_sync():
    service = await get_tushare_sync_service()
    result = await service.sync_historical_data(
        symbols=['000001', '000002'],  # 指定股票
        incremental=True,
        period='daily'
    )
    print(result)

asyncio.run(manual_sync())
"
```

---

## 📊 数据量估算

### 历史数据量计算

**假设**:
- A 股数量：约 5000 只
- 每只股票每年交易日：约 250 天
- 历史数据：从 1990 年至今（约 35 年）

**计算**:
```
总记录数 = 5000 只 × 250 天/年 × 35 年
         ≈ 43,750,000 条记录
```

**存储空间估算**（每条约 500 字节）:
```
总空间 = 43,750,000 条 × 500 字节
       ≈ 21.9 GB
```

**实际**:
- 考虑到股票退市、IPO 等因素
- 考虑到不同周期（日线/周线/月线）
- 考虑到多数据源（tushare/akshare/baostock）
- 预估实际数据量: **10-15 GB**

### 定期数据增长

**每日增量**:
```
每日新增记录 = 5000 只 × 1 天/天
             = 5,000 条记录/天

每日新增空间 = 5,000 条 × 500 字节
              ≈ 2.5 MB/天

每月新增空间 ≈ 75 MB/月
每年新增空间 ≈ 900 MB/年
```

---

## 🎯 关键要点总结

### 1. **核心集合**
- **`stock_daily_quotes`** - 存储所有历史 OHLCV 数据
- 包含日线、周线、月线数据
- 支持多数据源（tushare/akshare/baostock）

### 2. **同步策略**
- **增量同步**（默认）：从最后日期+1天开始
- **全量同步**：从上市日期或 1990 年开始
- **智能同步**：自动去重（唯一索引）

### 3. **数据字段**
- **基础字段**: symbol, trade_date, period, data_source
- **OHLCV**: open, high, low, close, volume, amount
- **复权数据**: adj_factor, adj_open, adj_high, adj_low, adj_close
- **技术指标**: ma5/10/20/60, rsi, macd
- **涨跌信息**: change, change_pct, turnover

### 4. **存储优化**
- **复合唯一索引**: 自动去重和快速更新
- **时间索引**: 快速范围查询
- **批量写入**: 每 100 条一批

### 5. **性能监控**
- 速率限制器（避免超 API 配额）
- 批量处理（提高效率）
- 进度跟踪（实时监控）

---

## 🔍 快速查询示例

### 查看数据覆盖情况

```javascript
// 1. 查看数据总量
db.stock_daily_quotes.countDocuments()

// 2. 查看覆盖的股票数量
db.stock_daily_quotes.distinct("symbol").length

// 3. 查看日期范围
db.stock_daily_quotes.aggregate([
  { "$group": {
    "_id": null,
    "min_date": { "$min": "$trade_date" },
    "max_date": { "$max": "$trade_date" }
  }}
])
```

### 查看特定股票数据

```javascript
// 1. 查看最近数据
db.stock_daily_quotes.find({
  "symbol": "000001"
})
.sort({ "trade_date": -1 })
.limit(5)
.pretty()

// 2. 查看最近一周
db.stock_daily_quotes.find({
  "symbol": "000001",
  "trade_date": { "$gte": "2025-01-28" }
})
.sort({ "trade_date": 1 })
.pretty()

// 3. 统计数据量
db.stock_daily_quotes.countDocuments({
  "symbol": "000001"
})
```

### 数据质量检查

```javascript
// 1. 检查缺失日期
db.stock_daily_quotes.aggregate([
  { "$match": { "symbol": "000001" } },
  { "$group": {
    "_id": null,
    "dates": { "$push": "$trade_date" },
    "count": { "$sum": 1 }
  }}
])

// 2. 检查重复数据
db.stock_daily_quotes.aggregate([
  { "$group": {
    "_id": {
      "symbol": "$symbol",
      "trade_date": "$trade_date",
      "data_source": "$data_source",
      "period": "$period"
    },
    "count": { "$sum": 1 }
  }},
  { "$match": { "count": { "$gt": 1 } } }
])

// 3. 检查数据完整性
db.stock_daily_quotes.find({
  "symbol": "000001",
  "trade_date": "2025-02-04"
}, {
  open: 1, high: 1, low: 1, close: 1,
  volume: 1, amount: 1
})
```

---

## 📚 相关文档

- **系统架构文档.md**: 完整的数据库设计说明
- **数据库查看指南.md**: 数据库查询和管理工具
- **API 文档**: http://localhost:8000/docs（后端启动后访问）

---

**文档维护**: 随项目演进持续更新
**最后更新**: 2025-02-04
