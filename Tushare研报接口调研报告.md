# Tushare 研报接口调研报告

## 📋 调研目标

调研 Tushare Pro API 是否提供股票历史研报数据获取能力,包括券商评级、目标价、盈利预测等信息,为 TradingAgents-CN 平台功能扩展提供数据源参考。

---

## 🔍 调研结论

### 核心发现

**Tushare Pro 提供券商研报盈利预测数据接口**

- ✅ Tushare 提供 `report_rc` 接口获取券商研报数据
- ✅ 数据包含: 卖方评级、目标价、盈利预测(EPS/PE)、机构信息
- ✅ 历史数据从 **2010 年** 开始,覆盖面广
- ⚠️ 需要 **8000 积分** 正式权限才能高频调用
- ❌ 当前 TradingAgents-CN 平台 **未集成** 此接口

---

## 📊 Tushare 研报接口详解

### 1. 接口基本信息

#### 接口名称
**`report_rc`** - 券商盈利预测数据

#### 官方文档
- **接口地址**: https://tushare.pro/document/2?doc_id=292
- **数据分类**: 股票数据 > 特色数据
- **数据来源**: Tushare Pro 官方整理

#### 接口描述
获取券商（卖方）每天研报的盈利预测数据,包括目标价、评级、财务预测等关键信息。

---

### 2. 接口参数

#### 输入参数

| 参数名 | 类型 | 必填 | 说明 | 示例 |
|--------|------|------|------|------|
| `ts_code` | str | N | 股票代码 (支持单只或批量) | "000001.SZ" |
| `report_date` | str | N | 研报日期 | "20250203" |
| `start_date` | str | N | 起始日期 | "20240101" |
| `end_date` | str | N | 终止日期 | "20241231" |
| `org_name` | str | N | 机构名称 | "中信证券" |
| `year` | str | N | 年份 | "2024" |

**注意事项**:
- 输入参数为空时返回所有股票的最新数据
- `report_date` 与 `start_date/end_date` 二选一
- 支持 `ts_code` 批量查询 (用逗号分隔)

#### 输出字段

| 字段名 | 说明 | 数据类型 | 示例 |
|--------|------|----------|------|
| `ts_code` | 股票代码 | str | "000001.SZ" |
| `name` | 股票名称 | str | "平安银行" |
| `report_date` | 研报发布日期 | str | "20250203" |
| `report_title` | 报告标题 | str | "平安银行:息差改善,资产质量优化" |
| `report_type` | 报告类型 | str | "公司研究" |
| `classify` | 报告分类 | str | "银行业" |
| `org_name` | 机构名称 | str | "中信证券" |
| `author_name` | 作者姓名 | str | "肖斐斐" |
| `quarter` | 预测报告期 | str | "2024Q4" |
| `eps` | 预测每股收益(元) | float | 2.15 |
| `pe` | 预测市盈率 | float | 6.5 |
| `rating` | 卖方评级 | str | "买入" |
| `max_price` | 预测最高目标价 | float | 16.50 |
| `min_price` | 预测最低目标价 | float | 14.80 |

---

### 3. 数据覆盖范围

#### 时间范围
- **起始时间**: 2010 年
- **更新频率**: 每日 19:00-22:00 更新当日数据
- **历史深度**: 约 14 年历史数据

#### 空间范围
- **覆盖市场**: 沪深 A 股全市场
- **覆盖股票**: 约 5000+ 只股票
- **覆盖机构**: 约 50+ 家主要券商

#### 数据量级预估
- **日增量**: 约 100-200 条/天
- **年总量**: 约 30,000-50,000 条/年
- **累计总量**: 约 400,000+ 条历史记录

---

### 4. 权限与限制

#### 积分要求

| 权限类型 | 积分要求 | 调用频率 | 适用场景 |
|---------|---------|---------|---------|
| **试用权限** | 120 积分 | 10 次/天 | 开发测试 |
| **正式权限** | 8000 积分 | 100,000 次/天 | 生产环境 |

**注意事项**:
- 试用权限适合开发验证
- 生产环境必须获取正式权限
- 积分获取方式: https://tushare.pro/register

#### 调用限制

| 限制类型 | 限制值 | 说明 |
|---------|--------|------|
| **单次返回** | 最多 3000 条 | 超过需分页 |
| **请求频率** | 200-1000 次/分 | 根据积分等级 |
| **并发限制** | 2 个线程 | 同时请求数 |

#### 数据更新策略
- **实时性**: T+1 (当日研报当晚更新)
- **批量同步**: 建议凌晨 2-4 点执行
- **增量更新**: 每日拉取最新 1-3 天数据

---

### 5. 评级体系说明

#### Tushare 评级标准

Tushare 的 `rating` 字段返回券商的原始评级文本,常见的评级词汇包括:

**买入类评级**:
- `买入` - 强烈推荐购买
- `增持` - 建议增加仓位
- `强烈推荐` - 最高评级

**持有类评级**:
- `持有` - 建议持有
- `中性` - 观望态度
- `观望` - 不建议操作

**卖出类评级**:
- `减持` - 建议减少仓位
- `卖出` - 建议卖出
- `回避` - 不推荐投资

**注意事项**:
- 不同券商的评级词汇可能不同
- 建议在应用层建立评级标准化映射表
- 可参考 Akshare 调研报告中的评级标准化方案

---

## 💻 代码示例

### 1. 基础调用示例

```python
import tushare as ts

# 设置 Token (首次调用)
ts.set_token("YOUR_TUSHARE_TOKEN")
pro = ts.pro_api()

# 1. 查询单只股票的最新研报
df = pro.report_rc(ts_code="000001.SZ")

# 2. 查询指定日期的研报
df = pro.report_rc(report_date="20250203")

# 3. 查询指定机构的所有研报
df = pro.report_rc(org_name="中信证券")

# 4. 查询日期范围内的研报
df = pro.report_rc(
    start_date="20240101",
    end_date="20241231"
)

# 5. 批量查询多只股票
df = pro.report_rc(ts_code="000001.SZ,000002.SZ,600036.SH")
```

---

### 2. 数据处理示例

```python
import pandas as pd
import tushare as ts
from datetime import datetime, timedelta

def fetch_reports(stock_code: str, days: int = 90) -> pd.DataFrame:
    """
    获取指定股票的研报数据

    Args:
        stock_code: 股票代码 (如 "000001.SZ")
        days: 获取最近 N 天的数据

    Returns:
        研报数据 DataFrame
    """
    pro = ts.pro_api()

    # 计算日期范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # 调用接口
    df = pro.report_rc(
        ts_code=stock_code,
        start_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d")
    )

    # 数据清洗
    if df is not None and not df.empty:
        # 转换日期格式
        df["report_date"] = pd.to_datetime(df["report_date"])

        # 计算潜在收益率
        if "max_price" in df.columns:
            df["potential_return"] = (
                (df["max_price"] - df.get("current_price", 0)) /
                df.get("current_price", 1) * 100
            ).round(2)

        # 排序 (最新优先)
        df = df.sort_values("report_date", ascending=False)

    return df


# 使用示例
reports = fetch_reports("000001.SZ", days=90)

# 筛选买入评级
buy_reports = reports[reports["rating"] == "买入"]

# 计算平均目标价
avg_target_price = reports["max_price"].mean()

print(f"研报总数: {len(reports)}")
print(f"平均目标价: {avg_target_price:.2f}")
print(f"买入评级: {len(buy_reports)}")
```

---

### 3. 与 MongoDB 集成示例

```python
import tushare as ts
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
from typing import List, Dict

class TushareReportService:
    """Tushare 研报服务"""

    def __init__(self, db: AsyncIOMotorDatabase, token: str):
        self.db = db
        self.collection = db.stock_research_reports
        ts.set_token(token)
        self.pro = ts.pro_api()

    async def fetch_and_save(self, stock_code: str) -> Dict:
        """
        获取并保存研报数据

        Args:
            stock_code: 股票代码 (如 "000001.SZ")

        Returns:
            保存结果统计
        """
        # 获取数据
        df = self.pro.report_rc(ts_code=stock_code)

        if df.empty:
            return {"fetched": 0, "saved": 0}

        reports = df.to_dict("records")
        saved_count = 0

        for report in reports:
            try:
                # 检查是否已存在 (去重)
                existing = await self.collection.find_one({
                    "ts_code": report["ts_code"],
                    "org_name": report["org_name"],
                    "report_date": report["report_date"]
                })

                if not existing:
                    # 转换数据格式
                    doc = {
                        "ts_code": report["ts_code"],
                        "stock_name": report.get("name", ""),
                        "report_date": datetime.strptime(
                            report["report_date"],
                            "%Y%m%d"
                        ),
                        "org_name": report.get("org_name", ""),
                        "analyst": report.get("author_name", ""),
                        "rating": report.get("rating", ""),
                        "max_price": report.get("max_price"),
                        "min_price": report.get("min_price"),
                        "eps": report.get("eps"),
                        "pe": report.get("pe"),
                        "report_title": report.get("report_title", ""),
                        "quarter": report.get("quarter", ""),
                        "data_source": "tushare",
                        "created_at": datetime.utcnow(),
                        "updated_at": datetime.utcnow(),
                        "is_valid": True
                    }

                    # 插入数据库
                    await self.collection.insert_one(doc)
                    saved_count += 1

            except Exception as e:
                print(f"保存研报失败: {e}")
                continue

        return {
            "fetched": len(reports),
            "saved": saved_count
        }


# 使用示例
import asyncio
from app.core.database import get_database

async def main():
    db = get_database()
    service = TushareReportService(db, "YOUR_TOKEN")

    result = await service.fetch_and_save("000001.SZ")
    print(f"获取 {result['fetched']} 条, 保存 {result['saved']} 条")

# asyncio.run(main())
```

---

## 📊 与 Akshare 接口对比

| 对比维度 | Tushare `report_rc` | Akshare `stock_research_report_em` |
|---------|---------------------|-----------------------------------|
| **数据来源** | Tushare 官方整理 | 东方财富网 |
| **接口稳定性** | ✅ 官方维护,稳定可靠 | ⚠️ 爬虫采集,可能失效 |
| **历史深度** | ✅ 2010 年至今 | ⚠️ 约 1-2 年 |
| **数据字段** | ✅ 丰富 (含盈利预测) | ✅ 丰富 (含研报 URL) |
| **更新频率** | ✅ 每日更新 | ✅ 每日更新 |
| **权限要求** | ⚠️ 需 8000 积分 | ✅ 完全免费 |
| **调用限制** | ⚠️ 有频率限制 | ⚠️ 需控制频率防封 |
| **数据准确性** | ✅ 结构化数据 | ✅ 结构化数据 |
| **研报全文** | ❌ 不提供 | ✅ 提供研报 PDF 链接 |
| **机构覆盖** | ✅ 主流券商 | ✅ 全市场券商 |

**选择建议**:
- **生产环境**: 优先选择 **Tushare** (稳定性高)
- **开发测试**: 可用 **Akshare** (免费无门槛)
- **完整方案**: **两者结合** (Tushare 为主, Akshare 补充)

---

## 🏗️ 集成方案建议

### 1. 数据库设计

参考 Akshare 调研报告中的数据库设计,稍作调整以兼容 Tushare 数据:

```javascript
// MongoDB 集合: stock_research_reports
{
  "_id": ObjectId("..."),
  "ts_code": "000001.SZ",  // Tushare 标准代码
  "stock_code": "000001",   // 统一股票代码
  "stock_name": "平安银行",
  "report_date": ISODate("2025-02-03T00:00:00Z"),
  "org_name": "中信证券",
  "analyst": "肖斐斐",
  "rating": "买入",
  "rating_code": "BUY",  // 标准化评级
  "max_price": 16.50,
  "min_price": 14.80,
  "eps": 2.15,           // 每股收益预测
  "pe": 6.5,             // 市盈率预测
  "report_title": "平安银行:息差改善...",
  "quarter": "2024Q4",   // 预测报告期
  "data_source": "tushare",  // 数据来源标记
  "created_at": ISODate("2025-02-04T10:30:00Z"),
  "updated_at": ISODate("2025-02-04T10:30:00Z"),
  "is_valid": true
}
```

---

### 2. 后端服务实现

#### 文件结构

```
app/
├── services/
│   └── tushare_report_service.py  # Tushare 研报服务 (新增)
├── worker/
│   └── tushare_report_sync.py     # Tushare 同步任务 (新增)
└── models/
    └── research_report.py          # 统一研报模型 (已存在)
```

#### 核心服务类

**文件**: `app/services/tushare_report_service.py`

```python
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import tushare as ts
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.config import settings

class TushareReportService:
    """Tushare 研报服务"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.stock_research_reports

        # 初始化 Tushare API
        token = self._get_token_from_db()
        ts.set_token(token)
        self.pro = ts.pro_api()

    def _get_token_from_db(self) -> str:
        """从数据库获取 Token"""
        # TODO: 从 llm_providers 集合读取
        return settings.TUSHARE_TOKEN

    async def sync_stock_reports(
        self,
        ts_code: str,
        days: int = 90
    ) -> Dict:
        """
        同步单只股票的研报

        Args:
            ts_code: Tushare 股票代码 (如 "000001.SZ")
            days: 获取最近 N 天

        Returns:
            同步结果统计
        """
        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 调用 Tushare API
        import pandas as pd
        df = self.pro.report_rc(
            ts_code=ts_code,
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d")
        )

        if df.empty:
            return {"fetched": 0, "saved": 0}

        reports = df.to_dict("records")
        saved_count = 0

        for report in reports:
            try:
                # 去重检查
                existing = await self.collection.find_one({
                    "ts_code": report["ts_code"],
                    "org_name": report["org_name"],
                    "report_date": datetime.strptime(
                        report["report_date"],
                        "%Y%m%d"
                    )
                })

                if not existing:
                    # 数据转换
                    doc = self._convert_to_doc(report)
                    await self.collection.insert_one(doc)
                    saved_count += 1

            except Exception as e:
                print(f"保存失败: {e}")
                continue

        return {
            "ts_code": ts_code,
            "fetched": len(reports),
            "saved": saved_count
        }

    def _convert_to_doc(self, report: Dict) -> Dict:
        """转换 Tushare 数据为 MongoDB 文档"""
        return {
            "ts_code": report["ts_code"],
            "stock_code": report["ts_code"].split(".")[0],
            "stock_name": report.get("name", ""),
            "report_date": datetime.strptime(
                report["report_date"],
                "%Y%m%d"
            ),
            "org_name": report.get("org_name", ""),
            "analyst": report.get("author_name", ""),
            "rating": report.get("rating", ""),
            "max_price": report.get("max_price"),
            "min_price": report.get("min_price"),
            "eps": report.get("eps"),
            "pe": report.get("pe"),
            "report_title": report.get("report_title", ""),
            "quarter": report.get("quarter", ""),
            "data_source": "tushare",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "is_valid": True
        }
```

---

### 3. 定时同步任务

**文件**: `app/worker/tushare_report_sync.py`

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.tushare_report_service import TushareReportService
from app.core.database import get_database

class TushareReportSync:
    """Tushare 研报同步任务"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.service = None

    async def sync_all_stocks(self):
        """全量同步所有股票研报"""
        db = get_database()
        self.service = TushareReportService(db)

        # 获取股票列表
        cursor = db.stock_basic_info.find(
            {"list_status": "L"},
            {"ts_code": 1}
        )

        stocks = await cursor.to_list(length=5000)
        total_saved = 0

        for stock in stocks:
            ts_code = stock["ts_code"]

            result = await self.service.sync_stock_reports(ts_code, days=7)
            total_saved += result["saved"]

            print(f"✅ {ts_code}: 新增 {result['saved']} 条")

        print(f"\n🎉 同步完成! 总计新增 {total_saved} 条")

    async def sync_hot_stocks(self):
        """同步热门股票"""
        hot_stocks = [
            "000001.SZ",  # 平安银行
            "000002.SZ",  # 万科A
            "600036.SH",  # 招商银行
            "600519.SH"   # 贵州茅台
        ]

        db = get_database()
        self.service = TushareReportService(db)

        for ts_code in hot_stocks:
            result = await self.service.sync_stock_reports(ts_code, days=30)
            print(f"✅ {ts_code}: 新增 {result['saved']} 条")

    def start(self):
        """启动定时任务"""

        # 每周日凌晨 2 点全量同步
        self.scheduler.add_job(
            self.sync_all_stocks,
            "cron",
            day_of_week="sun",
            hour=2,
            minute=0,
            id="tushare_sync_all"
        )

        # 每日凌晨 1 点同步热门股票
        self.scheduler.add_job(
            self.sync_hot_stocks,
            "cron",
            hour=1,
            minute=0,
            id="tushare_sync_hot"
        )

        self.scheduler.start()
        print("✅ Tushare 研报同步任务已启动")
```

---

### 4. 配置更新

**文件**: `app/core/config.py`

在现有配置中添加 Tushare 研报同步配置:

```python
# Tushare 研报同步配置
TUSHARE_REPORT_SYNC_ENABLED: bool = Field(
    default=False,
    description="启用 Tushare 研报同步"
)
TUSHARE_REPORT_SYNC_CRON: str = Field(
    default="0 2 * * 0",
    description="同步 cron 表达式"
)
TUSHARE_REPORT_SYNC_DAYS: int = Field(
    default=7,
    description="同步天数"
)
```

---

## 🚀 实施步骤

### Phase 1: 环境准备 (1 天)

- [ ] 确认 Tushare Token 及积分等级
- [ ] 测试 API 调用 (试用权限)
- [ ] 创建 MongoDB 集合和索引 (复用现有设计)
- [ ] 评级标准化映射表 (复用现有)

### Phase 2: 服务开发 (2-3 天)

- [ ] 实现 `TushareReportService` 服务类
- [ ] 实现数据转换和去重逻辑
- [ ] 实现 `TushareReportSync` 定时任务
- [ ] 集成到现有同步系统
- [ ] 单元测试

### Phase 3: 测试验证 (1-2 天)

- [ ] 测试单股票同步
- [ ] 测试批量同步
- [ ] 验证数据准确性
- [ ] 性能测试 (响应时间、并发)
- [ ] 异常处理测试

### Phase 4: 上线部署 (1 天)

- [ ] 生产环境配置
- [ ] 监控告警配置
- [ ] 数据回填 (历史数据)
- [ ] 文档更新

---

## 📊 预期效果

### 数据规模预估

| 指标 | 预估值 |
|------|--------|
| **历史数据总量** | ~400,000 条 (2010-2025) |
| **年增量** | ~30,000-50,000 条/年 |
| **日增量** | ~100-200 条/天 |
| **存储空间** | ~200 MB (含索引) |

### 性能指标

| 操作 | 预期响应时间 |
|------|-------------|
| **单股票同步** | ~1-2 秒 |
| **全量同步** | ~2-3 小时 (5000 只股票) |
| **API 查询** | < 100ms |
| **共识评级计算** | < 200ms |

---

## ⚠️ 注意事项

### 权限与合规

1. **积分要求**:
   - 生产环境必须获取 8000 积分正式权限
   - 试用权限仅适合开发测试

2. **数据使用**:
   - 仅用于个人学习研究
   - 不得用于商业用途
   - 需遵守 Tushare 用户协议

3. **免责声明**:
   - 研报观点不代表平台立场
   - 投资决策需谨慎
   - 需在界面添加风险提示

### 技术注意事项

1. **速率限制**:
   - 严格控制调用频率
   - 实现指数退避重试机制
   - 监控剩余积分

2. **数据质量**:
   - Tushare 数据可能缺失研报 URL
   - 部分记录可能缺少目标价
   - 需要数据清洗和验证

3. **去重策略**:
   - 使用 `ts_code + org_name + report_date` 唯一键
   - 避免重复存储相同研报

4. **异常处理**:
   - API 调用失败重试机制
   - 网络超时处理
   - 数据格式异常处理

---

## 📚 参考资料

### 官方文档

- Tushare Pro: https://tushare.pro/
- 接口文档: https://tushare.pro/document/2?doc_id=292
- 积分规则: https://tushare.pro/document/1

### 相关文档

- Akshare 调研报告: `./研报估值功能调研报告.md`
- Tushare 配置指南: `./app/core/config.py`
- 数据库设计参考: MongoDB 最佳实践

---

## 🎯 总结

### 核心结论

✅ **Tushare Pro 提供完善的研报数据获取能力**

**主要优势**:
1. 数据来源可靠 (官方维护)
2. 历史数据丰富 (2010 年至今)
3. 数据结构完整 (评级 + 目标价 + 盈利预测)
4. 接口稳定 (官方 API)

**主要限制**:
1. 需要较高积分门槛 (8000 积分)
2. 调用频率有限制
3. 不提供研报原文链接

### 与现有系统的集成

**当前状态**:
- ✅ 平台已集成 Tushare (用于行情、财务数据)
- ✅ 有成熟的同步服务架构
- ❌ 未使用研报接口

**集成建议**:
1. **复用现有架构**: Tushare 同步服务、速率限制器
2. **统一数据模型**: 与 Akshare 研报共用 MongoDB 集合
3. **双数据源策略**: Tushare 为主, Akshare 补充

### 推荐优先级

**中优先级** (建议在核心功能稳定后实施)

**理由**:
1. ✅ 技术实现简单 (复用现有架构)
2. ✅ 数据价值高 (机构观点参考)
3. ⚠️ 需要额外积分成本 (8000 积分)
4. ⚠️ 非核心功能 (不影响系统运行)

### 实施建议

**分阶段实施**:
1. **Phase 1** (试用): 使用 120 积分试用权限验证可行性
2. **Phase 2** (正式): 升级到 8000 积分正式权限
3. **Phase 3** (优化): 结合 Akshare 实现双数据源

**成本评估**:
- 积分成本: 约 ¥2000-5000/年 (8000 积分)
- 开发成本: 约 3-5 人天
- 维护成本: 低 (官方维护)

---

**报告生成时间**: 2025-02-04
**调研人**: Claude Code AI Assistant
**版本**: v1.0
**数据来源**: Tushare Pro 官方文档
