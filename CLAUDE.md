# CLAUDE.md

本文档为 Claude Code (claude.ai/code) 提供项目开发指导。

## 📖 项目简介

TradingAgents-CN 是一个基于多智能体和大语言模型的股票分析学习平台，专注于中国股市（A股、港股、美股）。

**核心架构：**
- **后端**：FastAPI + Motor (异步MongoDB) + Redis
- **前端**：Vue 3 + TypeScript + Vite + Element Plus + Pinia
- **多智能体系统**：LangGraph 构建的分析师团队（市场分析师、基本面分析师、新闻分析师等）
- **数据源**：Tushare、AKShare、BaoStock，支持优先级和降级
- **部署**：Docker 多架构支持 (amd64/arm64)

---

## 🚀 快速开始

### 后端开发

```bash
# 启动后端服务器（自动重载）
./venv/bin/python3 -m app

# 使用系统 Python（不推荐，可能缺少依赖）
python3 -m app

# 初始化数据库索引
./venv/bin/python3 -m app.scripts.init_trading_calendar

# 同步股票数据
./venv/bin/python3 -m app.worker.tushare_sync_service
```

### 前端开发

```bash
cd frontend

# 安装依赖
npm install

# 开发服务器（热重载）
npm run dev

# 生产构建
npm run build

# 类型检查
npm run type-check

# 代码检查和格式化
npm run lint
npm run format
```

### Docker 部署

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 停止服务
docker-compose down

# 清理数据卷（警告：会删除数据）
docker-compose down -v
```

### 数据库操作

```bash
# 连接 MongoDB
mongosh mongodb://admin:password@localhost:27017/tradingagents

# 连接 Redis
redis-cli -h localhost -p 6379

# 清空 Redis 缓存（谨慎操作）
redis-cli FLUSHDB
```

---

## 🏗️ 核心架构

### 后端目录结构

```
app/
├── core/              # 核心配置
│   ├── config.py      # 从环境变量读取配置
│   ├── database.py    # MongoDB 初始化 (Motor), get_mongo_db()
│   └── response.py    # 统一响应格式: ok(data), error(msg)
├── models/            # Pydantic 数据模型
├── services/          # 业务逻辑层（通过依赖注入使用）
├── routers/           # FastAPI 路由定义
└── scripts/           # 独立工具脚本
```

### ⚠️ 关键模式：路由注册

**重要**：路由必须在定义时包含 `/api` 前缀，而不是在 `include_router` 时添加。

```python
# ✅ 正确 - 在 router 定义时添加 prefix
router = APIRouter(prefix="/api/backtest/strategies", tags=["backtest-strategies"])

# 在 main.py 中注册时不添加 prefix 参数
app.include_router(strategies_router.router, tags=["backtest-strategies"])

# ❌ 错误 - 不要这样做
# app.include_router(router, prefix="/api")  # 会导致路径重复
```

### 数据库访问模式

**始终使用依赖注入**：

```python
from app.core.database import get_mongo_db

def get_service(db = Depends(get_mongo_db)):
    return MyService(db)

# 在 service 中：
class MyService:
    def __init__(self, db):
        self.db = db
        self.collection = db.trading_calendar  # 直接访问 Motor 集合
```

### 统一响应格式

```python
from app.core.response import ok, error

# 成功响应
return ok(data)

# 错误响应
return error("错误信息")
```

### Redis 缓存模式

```python
from app.core.database import get_redis_client

# 获取 Redis 客户端
redis_client = await get_redis_client()

# 设置缓存（带 TTL）
await redis_client.set(key, value, ex=86400)  # 24小时

# 读取缓存
cached = await redis_client.get(key)
```

### 前端状态管理（Pinia）

```typescript
export const useMyStore = defineStore('my', () => {
  // 状态
  const data = ref([])
  const loading = ref(false)

  // 操作
  async function fetchData() {
    loading.value = true
    try {
      const response = await myApi.getData()
      data.value = response.data
    } finally {
      loading.value = false
    }
  }

  return { data, loading, fetchData }
})
```

---

## 📝 关键约定

### 日期格式
- **必须**使用 `YYYY-MM-DD` 字符串格式（例如："2024-01-15"）
- 不要在 API 响应中使用 Date 对象
- 前端使用 dayjs 进行日期操作

### 错误处理
- 后端：使用 `HTTPException` 抛出 API 错误
- 始终记录错误上下文：`logger.error(f"操作失败: {e}")`
- 前端：使用 Element Plus `ElMessage` 提示用户

### 异步操作
- 后端：所有数据库操作**必须**是异步的（使用 Motor，不是 pymongo）
- 前端：API 调用应该是异步的
- 不要混用同步和异步数据库操作

### 中文本地化
- 所有面向用户的字符串**必须**是中文
- 使用规范术语："股票"、"交易日"、"交易日历" 等
- 星期名称："周一"、"周二" 等

### 路由组织
- 路由按功能分组：`/api/backtest/*`、`/api/analysis/*` 等
- 使用 tags 标记 OpenAPI 文档：`tags=["功能名称"]`
- 遵循 RESTful 规范

---

## ⚠️ 常见错误

### 不要这样做：
- ❌ 直接使用 `pymongo`（应使用 `motor` 进行异步操作）
- ❌ 不使用依赖注入直接访问数据库
- ❌ 硬编码 API 基础 URL（应使用环境变量）
- ❌ 在 JSON 响应中使用 Python 的 `datetime` 对象
- ❌ 混用同步/异步数据库操作
- ❌ 在 `include_router()` 中添加 `/api` 前缀（应在 router 定义时添加）

### 必须这样做：
- ✅ 使用 `get_mongo_db()` 依赖注入
- ✅ 使用 Motor 异步方法（`async for`、`await collection.find()`）
- ✅ 使用 `datetime.strptime(date_str, "%Y-%m-%d")` 验证日期
- ✅ 缓存命中时使用 DEBUG 日志级别，不是 INFO
- ✅ 数据变更时清理 Redis 缓存
- ✅ 处理 MongoDB 查询中的 `None` 值

---

## 🔧 添加新功能

### 新增 API 端点

1. **创建 Pydantic 模型** - `app/models/feature_name.py`
2. **创建服务层** - `app/services/feature_service.py`（使用依赖注入）
3. **创建路由** - `app/routers/feature_name.py`：
   ```python
   router = APIRouter(prefix="/api/feature", tags=["feature"])

   @router.get("")
   async def get_feature(service: FeatureService = Depends(get_feature_service)):
       return ok(await service.get_data())
   ```
4. **注册路由** - `app/main.py`：
   ```python
   from app.routers import feature_name as feature_router
   app.include_router(feature_router.router, tags=["feature"])
   ```

### 新增前端组件

1. **创建 API 接口** - `frontend/src/api/feature.ts`
2. **创建 Pinia Store** - `frontend/src/stores/feature.ts`（如果需要）
3. **创建 Vue 组件** - `frontend/src/components/FeatureComponent.vue`
4. **使用 Composition API** - `<script setup lang="ts">`

---

## 🤖 多智能体分析系统

### 智能体类型（`tradingagents/agents/`）

- **分析师** (`analysts/`)：市场分析师、基本面分析师、新闻分析师、社交媒体分析师、中国股市分析师
- **研究员** (`researchers/`)：深度研究代理
- **风险管理** (`risk_mgmt/`)：风险评估代理
- **交易员** (`trader/`)：交易决策代理
- **管理者** (`managers/`)：投资组合管理代理

### 图结构（`tradingagents/graph/`）

- `trading_graph.py`：主要的 LangGraph 编排
- `conditional_logic.py`：代理间的决策路由
- `signal_processing.py`：市场信号处理
- `reflection.py`：代理反思和改进
- `propagation.py`：代理间的信息传播

### 集成点

- 后端 API 通过 `app/services/analysis_service.py` 调用 `TradingAgentsGraph`
- 通过 `RedisProgressTracker` 进行进度跟踪
- 结果存储在 MongoDB `analysis_tasks` 集合
- 通过 WebSocket/SSE 推送实时更新

---

## 📊 分析工作流程

### 股票分析请求流程

1. **请求提交** (`POST /api/analysis/analyze`)
   - 用户提交股票代码和分析参数
   - 在 MongoDB 中创建 `AnalysisTask`
   - 推送到 Redis 队列（带优先级）

2. **队列处理** (`app/services/queue_service.py`)
   - Worker 从 Redis 队列拉取任务
   - 执行并发限制（用户级和全局级）
   - 处理任务优先级和重试

3. **多智能体执行** (`TradingAgentsGraph`)
   - LangGraph 编排代理序列
   - 每个代理分析不同方面（技术面、基本面、新闻等）
   - 代理辩论并完善结论
   - 生成最终建议

4. **进度跟踪** (`RedisProgressTracker`)
   - 通过 Redis pub/sub 实时更新进度
   - 前端通过 WebSocket/SSE 接收更新
   - 进度包括：当前代理、阶段、百分比

5. **结果存储**
   - 完整分析存储在 MongoDB `analysis_tasks` 集合
   - 包含所有代理观点、辩论历史、最终建议
   - 可导出为 Markdown/Word/PDF 报告

### 队列系统详解

**Redis 队列结构：**
- 队列键：`analysis_queue:user:{user_id}`（用户队列）、`analysis_queue:global`（全局队列）
- 优先级：基于用户等级和请求类型
- 可见性超时：300秒（防止 worker 崩溃时任务丢失）
- 并发限制：
  - 默认用户：2个并发任务
  - 全局：10个并发任务
  - 可通过环境变量配置

**Worker 进程：**
- 位于 `app/worker/`（与 API 服务器分离的进程）
- 从队列拉取任务、执行分析、更新进度
- 可运行多个 worker 实例实现水平扩展
- 失败时自动重试（指数退避）

---

## 🔑 数据源优先级系统

数据源按市场类型设置优先级：
- **A股**：AKShare > BaoStock > Tushare（可在数据库中配置）
- **港股**：AKShare > Yahoo Finance
- **美股**：Finnhub > Alpha Vantage > Yahoo Finance

优先级存储在 MongoDB `data_sources_config` 集合，可通过 API `/api/config/data-sources` 修改。

---

## 🧪 测试

项目目前自动化测试有限。手动测试清单：
- 后端健康检查：`curl http://localhost:8000/api/health`
- API 文档：访问 `http://localhost:8000/docs`（Swagger UI）
- 前端构建：`cd frontend && npm run build`
- 数据库索引：检查日志中的 "✅ 数据库索引创建完成"
- 分析流程：通过 Web UI 提交分析请求，实时监控进度

---

## 🌍 环境变量

关键变量（见 `.env` 文件）：
- `MONGODB_HOST`、`MONGODB_PORT`、`MONGODB_USERNAME`、`MONGODB_PASSWORD`
- `REDIS_HOST`、`REDIS_PORT`
- `OPENAI_API_KEY`、`GOOGLE_API_KEY`、`DASHSCOPE_API_KEY`
- `DEBUG=true` 开发模式

---

## 📌 项目特定说明

- **交易日历**：使用简化的周末检测（非真实节假日）。生产环境应集成 Tushare/AKShare 节假日 API。
- **用户认证**：基于 JWT 的角色访问控制（RBAC）
- **实时更新**：WebSocket + SSE 双通道进度跟踪
- **多源数据**：MongoDB/Redis/文件三级缓存统一系统
- **定时任务**：基于 APScheduler 的 cron 数据同步
- **日志系统**：统一日志系统（`tradingagents/utils/logging_init.py`）- 使用 `get_logger()` 获取配置的 logger

---

## 🤖 LLM 提供商集成

系统支持动态 LLM 提供商配置：
1. 通过 Web UI 或 API 配置提供商（`/api/config/llm-providers`）
2. 配置存储在 MongoDB `llm_providers_config` 集合
3. 运行时根据模型能力选择
4. 失败时自动降级
5. 按提供商跟踪成本

### 添加新 LLM 提供商

1. 在 `tradingagents/llms/providers/` 实现提供商
2. 在 `tradingagents/llms/base.py` 注册
3. 在 MongoDB `llm_providers_config` 添加配置模式
4. 更新前端 LLM 配置页面

---

## 💡 快速参考：常见开发任务

### 调试分析问题

```bash
# 检查分析任务状态
mongosh mongodb://admin:password@localhost:27017/tradingagents
db.analysis_tasks.find({symbol: "000001.SZ"}).sort({created_at: -1}).limit(1)

# 检查 Redis 队列
redis-cli
LRANGE analysis_queue:global 0 10

# 查看 worker 日志
tail -f logs/worker.log

# 检查进度跟踪
redis-cli KEYS "progress:*"
```

### 添加新分析代理

1. 在 `tradingagents/agents/analysts/new_analyst.py` 创建代理文件
2. 实现代理类的 `__init__` 和 `analyze` 方法
3. 在 `tradingagents/graph/trading_graph.py` 将代理添加到图
4. 更新 `tradingagents/agents/utils/agent_states.py` 中的代理状态
5. 在 `tradingagents/graph/conditional_logic.py` 添加条件逻辑

### 修改数据源配置

```python
# 通过 API
curl -X PUT http://localhost:8000/api/config/data-sources \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "market": "A_stock",
    "sources": ["akshare", "baostock", "tushare"],
    "priorities": {"akshare": 1, "baostock": 2, "tushare": 3}
  }'

# 直接 MongoDB 更新
db.data_sources_config.updateOne(
  {market: "A_stock"},
  {$set: {sources: ["akshare", "baostock"], priorities: {akshare: 1, baostock: 2}}}
)
```

### 前端 API 集成

```typescript
// 在 frontend/src/api/ 添加新 API 方法
import axios from 'axios'

const API_BASE = '/api'

export const myNewApi = {
  async getData(params: Params) {
    const response = await axios.get(`${API_BASE}/feature`, { params })
    return response.data  // { success, data, message, timestamp }
  }
}

// 在组件中使用（带错误处理）
import { ElMessage } from 'element-plus'

try {
  const result = await myNewApi.getData(params)
  if (result.success) {
    // 处理成功
  }
} catch (error) {
  ElMessage.error('操作失败')
}
```

### 性能优化技巧

- **缓存失效**：更新股票数据时清理相关 Redis 键
  ```python
  await redis_client.delete(f"stock_info:{symbol}")
  await redis_client.delete(f"quotes:{symbol}")
  ```

- **数据库查询**：使用投影限制返回字段
  ```python
  await collection.find({"symbol": symbol}, {"_id": 0, "name": 1}).to_list(None)
  ```

- **批量操作**：使用 `insert_many()` 和 `bulk_write()` 进行批量操作
- **连接池**：Motor 自动处理，但可调整 `MONGODB_MIN_POOL_SIZE`

---

## 📚 相关文档

- [README.md](README.md) - 项目概述和安装指南
- [docs/BUILD_GUIDE.md](docs/BUILD_GUIDE.md) - Docker 构建指南
- [docs/llm/LLM_INTEGRATION_GUIDE.md](docs/llm/LLM_INTEGRATION_GUIDE.md) - LLM 集成指南
- [frontend/前端架构学习指南.md](frontend/前端架构学习指南.md) - 前端架构说明

---

## 🎓 学习资源

### 多智能体系统架构

1. **分析师团队** - 每个分析师关注不同维度
2. **LangGraph 编排** - 定义分析师之间的协作流程
3. **状态管理** - AgentState、InvestDebateState、RiskDebateState
4. **条件逻辑** - 根据市场情况动态选择分析师
5. **反思机制** - 分析师回顾和改进自己的判断

### 数据流架构

1. **统一缓存系统** - MongoDB/Redis/文件三级缓存
2. **数据源优先级** - 自动降级和重试
3. **实时行情** - WebSocket 推送最新价格
4. **历史数据** - 定时同步和补全

### 前端架构

1. **Vue 3 Composition API** - 更好的逻辑复用
2. **Pinia 状态管理** - 轻量级且类型安全
3. **Element Plus** - 企业级 UI 组件库
4. **TypeScript** - 类型安全和更好的 IDE 支持

---

**版本**：v1.0.0-preview

**最后更新**：2025年2月

**维护者**：TradingAgents-CN 开发团队
