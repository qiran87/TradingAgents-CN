# 第三方依赖分析

## 依赖管理概述

项目使用 Python 的 `poetry` 或 `pip` 管理后端依赖，使用 `npm` 管理前端依赖。后端依赖定义在 `requirements.txt` 或 `pyproject.toml` 中，前端依赖定义在 `frontend/package.json` 中。

## 后端依赖（Python）

### 核心框架

#### FastAPI (0.104.0+)

**用途**: Web 框架，构建 RESTful API

**主要功能**:
- 异步请求处理
- 自动生成 API 文档（Swagger/ReDoc）
- Pydantic 数据验证
- 依赖注入系统
- WebSocket 支持

**关键使用**:
```python
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/backtest", tags=["backtest"])

@router.post("/start")
async def start_backtest(
    request: StartBacktestRequest,
    db = Depends(get_mongo_db)
):
    return ok(data=...)
```

#### Motor (3.3.0+)

**用途**: MongoDB 异步驱动

**主要功能**:
- 异步 MongoDB 操作
- 连接池管理
- GridFS 支持
- Aggregation Framework

**关键使用**:
```python
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient(mongodb_url)
db = client.tradingagents

# 异步查询
task = await db.backtest_tasks.find_one({"backtest_id": backtest_id})
```

#### Pydantic (2.5.0+)

**用途**: 数据验证和序列化

**主要功能**:
- 类型检查
- 数据验证
- JSON 序列化
- 自动生成 JSON Schema

**关键使用**:
```python
from pydantic import BaseModel, Field

class StartBacktestRequest(BaseModel):
    stock_code: str = Field(..., description="股票代码")
    initial_capital: float = Field(..., gt=0, description="初始资金")
```

### 数据源集成

#### Tushare (1.2.73+)

**用途**: A股数据源

**主要功能**:
- 股票基本信息
- 历史行情数据
- 财务数据
- 宏观经济数据

**使用示例**:
```python
import tushare as ts

pro = ts.pro_api(token)
df = pro.daily(ts_code="000001.SZ", start_date="20240101", end_date="20241231")
```

#### AKShare (1.12.0+)

**用途**: 多市场数据源（主要）

**主要功能**:
- A股数据
- 港股数据
- 美股数据
- 宏观经济数据
- 新闻资讯

**使用示例**:
```python
import akshare as ak

# A股行情
df = ak.stock_zh_a_hist(symbol="000001", period="daily")

# 港股行情
df = ak.stock_hk_hist(symbol="00700", period="daily")
```

#### BaoStock (0.8.8+)

**用途**: A股备用数据源

**主要功能**:
- 免费A股数据
- 历史行情
- 财务数据

**使用示例**:
```python
import baostock as bs

bs.login()
df = bs.query_history_k_data_plus("sz.000001", "date,open,high,low,close")
bs.logout()
```

### 异步任务

#### APScheduler (3.10.0+)

**用途**: 定时任务调度

**主要功能**:
- Cron 调度
- 间隔调度
- 异步任务支持
- 任务持久化

**使用示例**:
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@scheduler.scheduled_job('cron', hour=2, minute=0)
async def daily_sync():
    await sync_stock_data()
```

### Redis 客户端

#### Redis (5.0.0+)

**用途**: Redis 同步客户端（用于简单操作）

**使用示例**:
```python
import redis

r = redis.Redis(host='localhost', port=6379, db=0)
r.set('key', 'value', ex=3600)
```

#### Aioredis (2.0.0+)

**用途**: Redis 异步客户端

**主要功能**:
- 异步操作
- 连接池
- 发布订阅

**使用示例**:
```python
import aioredis

redis = await aioredis.from_url("redis://localhost")
await redis.set("key", "value", ex=3600)
```

### 认证与安全

#### PyJWT (2.8.0+)

**用途**: JWT Token 生成和验证

**使用示例**:
```python
import jwt

# 生成 Token
token = jwt.encode({"sub": "user123"}, secret, algorithm="HS256")

# 验证 Token
payload = jwt.decode(token, secret, algorithms=["HS256"])
```

#### Passlib (1.7.4+)

**用途**: 密码哈希

**使用示例**:
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 哈希密码
hashed = pwd_context.hash(password)

# 验证密码
is_valid = pwd_context.verify(password, hashed)
```

### 多智能体系统

#### LangGraph (0.0.20+)

**用途**: 多智能体编排

**主要功能**:
- 状态图定义
- 智能体路由
- 条件逻辑
- 反思机制

**使用示例**:
```python
from langgraph.graph import StateGraph

graph = StateGraph(AgentState)
graph.add_node("market_analyst", market_analyst_node)
graph.add_edge("market_analyst", "fundamental_analyst")
```

#### LangChain (0.1.0+)

**用途**: LLM 应用框架

**主要功能**:
- LLM 抽象
- Prompt 模板
- 工具调用
- 记忆管理

#### OpenAI (1.0.0+)

**用途**: OpenAI API 客户端

**使用示例**:
```python
from openai import OpenAI

client = OpenAI(api_key=api_key)
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}]
)
```

### 数据处理

#### NumPy (1.26.0+)

**用途**: 数值计算

**主要功能**:
- 数组操作
- 数学函数
- 统计分析

**使用示例**:
```python
import numpy as np

returns = np.array([0.01, 0.02, -0.01, 0.03])
volatility = np.std(returns) * np.sqrt(252)
```

#### Pandas (2.1.0+)

**用途**: 数据分析

**主要功能**:
- DataFrame 操作
- 时间序列处理
- 数据清洗

**使用示例**:
```python
import pandas as pd

df = pd.DataFrame({
    'date': pd.date_range('2024-01-01', periods=100),
    'close': np.random.randn(100).cumsum() + 100
})
```

### HTTP 客户端

#### HTTPX (0.25.0+)

**用途**: 异步 HTTP 客户端

**主要功能**:
- 异步请求
- HTTP/2 支持
- 连接池

**使用示例**:
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get("https://api.example.com/data")
```

### 日志

#### Python Loguru (0.7.0+)

**用途**: 日志库（可选）

**使用示例**:
```python
from loguru import logger

logger.info("处理回测任务: {}", backtest_id)
logger.error("处理失败: {}", error)
```

### 日期时间

#### Python-dateutil (2.8.0+)

**用途**: 日期解析

**使用示例**:
```python
from dateutil import parser

date = parser.parse("2024-01-15")
```

## 前端依赖（JavaScript/TypeScript）

### 核心框架

#### Vue (3.3.0+)

**用途**: 前端框架

**主要功能**:
- Composition API
- 响应式系统
- 组件化开发

#### Vue Router (4.2.0+)

**用途**: 路由管理

**使用示例**:
```typescript
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [...]
})
```

#### Pinia (2.1.0+)

**用途**: 状态管理

**使用示例**:
```typescript
import { defineStore } from 'pinia'

export const useBacktestStore = defineStore('backtest', () => {
  const data = ref([])
  async function fetchData() {
    // ...
  }
  return { data, fetchData }
})
```

### UI 框架

#### Element Plus (2.3.0+)

**用途**: UI 组件库

**主要组件**:
- el-button
- el-form
- el-table
- el-card
- el-dialog
- el-message

**使用示例**:
```vue
<template>
  <el-button type="primary" @click="handleClick">点击</el-button>
</template>
```

#### Element Plus Icons Vue (2.1.0+)

**用途**: 图标库

**使用示例**:
```vue
<template>
  <el-icon><TrendCharts /></el-icon>
</template>

<script setup>
import { TrendCharts } from '@element-plus/icons-vue'
</script>
```

### HTTP 客户端

#### Axios (1.6.0+)

**用途**: HTTP 请求库

**使用示例**:
```typescript
import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 10000
})

const response = await apiClient.get('/data')
```

### 图表库

#### ECharts (5.4.0+)

**用途**: 数据可视化

**使用示例**:
```typescript
import * as echarts from 'echarts'

const chart = echarts.init(document.getElementById('chart'))
chart.setOption({
  xAxis: { type: 'category', data: ['Mon', 'Tue', 'Wed'] },
  yAxis: { type: 'value' },
  series: [{ type: 'line', data: [150, 230, 224] }]
})
```

### 工具库

#### Day.js (1.11.0+)

**用途**: 日期处理

**使用示例**:
```typescript
import dayjs from 'dayjs'

const date = dayjs('2024-01-15').format('YYYY-MM-DD')
```

#### Lodash-es (4.17.0+)

**用途**: 工具函数

**使用示例**:
```typescript
import { debounce, throttle } from 'lodash-es'

const debouncedFn = debounce(() => {
  // ...
}, 300)
```

### 开发工具

#### Vite (4.4.0+)

**用途**: 构建工具

**主要功能**:
- 快速热更新
- 原生 ES 模块
- TypeScript 支持

#### TypeScript (5.0.0+)

**用途**: 类型系统

#### ESLint (8.50.0+)

**用途**: 代码检查

#### Prettier (3.0.0+)

**用途**: 代码格式化

## 依赖版本管理

### 后端依赖版本策略

- **精确版本**: 核心框架使用精确版本
- **范围版本**: 工具库使用范围版本
- **定期更新**: 每月检查安全更新

### 前端依赖版本策略

- **^ 前缀**: 允许次版本更新
- **~ 前缀**: 允许补丁更新
- **锁定文件**: 使用 package-lock.json

## 依赖安全

### 安全扫描

```bash
# Python 安全扫描
pip safety check

# JavaScript 安全扫描
npm audit

# 修复安全问题
npm audit fix
```

### 定期更新

```bash
# Python 依赖更新
pip list --outdated

# JavaScript 依赖更新
npm outdated
npm update
```

## 依赖最佳实践

### 1. 最小化原则

- 只引入需要的依赖
- 避免重复功能的库
- 定期清理未使用的依赖

### 2. 版本锁定

- 生产环境使用锁定版本
- 开发环境可以使用范围版本
- 使用 requirements.txt 锁定

### 3. 安全意识

- 定期检查安全漏洞
- 及时更新有漏洞的依赖
- 使用官方或可信的源

### 4. 文档记录

- 记录为什么引入某个依赖
- 记录依赖的使用场景
- 记录依赖的已知问题

## 新增依赖流程

### 1. 评估需求

- 明确需要的功能
- 检查现有依赖是否可以满足
- 评估维护活跃度

### 2. 选择依赖

- 选择活跃维护的
- 选择文档完善的
- 选择社区支持好的

### 3. 测试验证

- 在开发环境测试
- 检查兼容性
- 检查性能影响

### 4. 文档更新

- 更新 requirements.txt
- 更新 CLAUDE.md
- 更新相关文档

## 常见问题

### 1. 依赖冲突

**问题**: 不同依赖需要不同版本的同一个库

**解决**:
- 使用虚拟环境隔离
- 调整依赖版本
- 使用依赖替换

### 2. 依赖过大

**问题**: 打包后体积过大

**解决**:
- 使用 Tree Shaking
- 按需导入
- 考虑替代方案

### 3. 安全漏洞

**问题**: 依赖存在安全漏洞

**解决**:
- 及时更新
- 使用安全扫描工具
- 关注安全公告
