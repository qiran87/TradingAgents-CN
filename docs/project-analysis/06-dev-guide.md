# 开发指南

## 开发环境搭建

### 1. 后端开发环境

#### 系统要求

- Python 3.10+
- MongoDB 4.4+
- Redis 6.0+

#### 安装步骤

```bash
# 1. 克隆项目
git clone <repository-url>
cd TradingAgents-CN

# 2. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入必要的配置

# 5. 初始化数据库
python -m app.scripts.init_trading_calendar

# 6. 启动开发服务器
python -m app
```

#### 配置文件

`.env` 文件示例：

```ini
# MongoDB
MONGODB_HOST=localhost
MONGODB_PORT=27017
MONGODB_USERNAME=admin
MONGODB_PASSWORD=password
MONGODB_DATABASE=tradingagents

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# API Keys
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_api_key
DASHSCOPE_API_KEY=your_dashscope_api_key

# 数据源
TUSHARE_TOKEN=your_tushare_token

# 应用配置
DEBUG=true
LOG_LEVEL=INFO
```

### 2. 前端开发环境

#### 系统要求

- Node.js 18+
- npm 9+

#### 安装步骤

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 配置环境变量
cp .env.example .env.development

# 4. 启动开发服务器
npm run dev
```

#### 前端环境变量

`frontend/.env.development` 示例：

```ini
# API 基础 URL
VITE_API_BASE_URL=http://localhost:8000

# WebSocket URL
VITE_WS_BASE_URL=ws://localhost:8000

# 其他配置
VITE_APP_TITLE=TradingAgents-CN
```

### 3. Docker 开发环境

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 停止服务
docker-compose down
```

## 添加新策略

### 步骤 1: 创建策略文件

在 `app/strategies/` 目录下创建新策略文件：

```python
# app/strategies/new_strategy.py
from typing import Dict, Any, List
from datetime import datetime
from app.strategies.base import BaseStrategy

class NewStrategy(BaseStrategy):
    """新策略"""

    def __init__(self, params: Dict[str, Any]):
        super().__init__(params)
        # 初始化策略参数
        self.param1 = self.get_parameter("param1", default_value)

    def get_parameters_definition(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "param1",
                "type": "int",
                "default_value": 10,
                "range": {"min": 1, "max": 100},
                "description": "参数1描述",
                "required": True
            }
        ]

    def get_strategy_id(self) -> str:
        return "new_strategy"

    def get_strategy_name(self) -> str:
        return "新策略"

    def get_strategy_description(self) -> str:
        return "策略详细描述"

    def get_strategy_category(self) -> str:
        return "trend"  # trend/oscillation/momentum

    def on_bar(
        self,
        bar_id: str,
        timestamp: datetime,
        current_price: float,
        position: int,
        cash: float
    ) -> Dict[str, Any]:
        """
        处理单个K线数据

        Args:
            bar_id: K线ID
            timestamp: 时间戳
            current_price: 当前价格
            position: 当前持仓（股数）
            cash: 当前现金（元）

        Returns:
            交易信号
        """
        # 实现策略逻辑
        if should_buy:
            return {
                "action": "buy",
                "amount": 100,
                "reason": "买入原因"
            }
        elif should_sell:
            return {
                "action": "sell",
                "amount": position,
                "reason": "卖出原因"
            }

        return {"action": "hold", "amount": 0, "reason": "无信号"}
```

### 步骤 2: 注册策略

在 `app/main.py` 中注册策略：

```python
from app.strategies.registry import StrategyRegistry
from app.strategies.new_strategy import NewStrategy

# 注册策略
StrategyRegistry.register("new_strategy", NewStrategy)
```

### 步骤 3: 添加前端支持

在 `frontend/src/views/Backtest/BacktestControlPanel.vue` 中添加策略配置：

```typescript
const strategies = ref([
  // ... 现有策略
  {
    id: 'new_strategy',
    name: '新策略',
    description: '策略详细描述',
    is_builtin: true,
    category: 'trend',
    parameters: [
      {
        name: 'param1',
        label: '参数1',
        type: 'number',
        min: 1,
        max: 100,
        step: 1,
        default: 10
      }
    ]
  }
])
```

## 添加新 API 端点

### 步骤 1: 创建数据模型

在 `app/models/` 目录下创建 Pydantic 模型：

```python
# app/models/new_feature.py
from pydantic import BaseModel, Field
from typing import Optional

class NewFeatureRequest(BaseModel):
    """新功能请求"""
    name: str = Field(..., min_length=1, max_length=50, description="名称")
    description: Optional[str] = Field(None, max_length=200, description="描述")

class NewFeatureResponse(BaseModel):
    """新功能响应"""
    id: str
    name: str
    created_at: str
```

### 步骤 2: 创建服务层

在 `app/services/` 目录下创建服务：

```python
# app/services/new_feature_service.py
from typing import Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

class NewFeatureService:
    """新功能服务"""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def create_item(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建项目"""
        # 实现业务逻辑
        result = await self.db.new_collection.insert_one(data)
        return {"id": str(result.inserted_id), **data}

# 依赖注入
_new_feature_service = None

def get_new_feature_service(db: AsyncIOMotorDatabase) -> NewFeatureService:
    global _new_feature_service
    if _new_feature_service is None:
        _new_feature_service = NewFeatureService(db)
    return _new_feature_service
```

### 步骤 3: 创建路由

在 `app/routers/` 目录下创建路由：

```python
# app/routers/new_feature.py
from fastapi import APIRouter, Depends
from app.core.database import get_mongo_db
from app.core.response import ok
from app.services.new_feature_service import get_new_feature_service
from app.models.new_feature import NewFeatureRequest, NewFeatureResponse

router = APIRouter(prefix="/api/new-feature", tags=["new-feature"])

@router.post("", response_model=dict)
async def create_item(
    request: NewFeatureRequest,
    db = Depends(get_mongo_db),
    service = Depends(get_new_feature_service)
):
    """创建项目"""
    result = await service.create_item(request.dict())
    return ok(data=result)
```

### 步骤 4: 注册路由

在 `app/main.py` 中注册路由：

```python
from app.routers import new_feature as new_feature_router

app.include_router(new_feature_router.router, tags=["new-feature"])
```

### 步骤 5: 添加前端 API

在 `frontend/src/api/` 目录下创建 API 文件：

```typescript
// frontend/src/api/newFeature.ts
import { ApiClient } from './request'

export interface NewFeatureRequest {
  name: string
  description?: string
}

export interface NewFeatureResponse {
  id: string
  name: string
  created_at: string
}

export const newFeatureApi = {
  async createItem(request: NewFeatureRequest) {
    return ApiClient.post<NewFeatureResponse>(
      '/api/new-feature',
      request
    )
  }
}
```

## 添加新前端组件

### 步骤 1: 创建组件文件

```vue
<!-- frontend/src/components/NewComponent.vue -->
<template>
  <div class="new-component">
    <h3>{{ title }}</h3>
    <p>{{ description }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Props {
  title: string
  description?: string
}

const props = withDefaults(defineProps<Props>(), {
  description: '默认描述'
})

// 组件逻辑
const title = computed(() => props.title)
</script>

<style scoped lang="scss">
.new-component {
  padding: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
}
</style>
```

### 步骤 2: 使用组件

```vue
<template>
  <div>
    <NewComponent
      title="组件标题"
      description="组件描述"
    />
  </div>
</template>

<script setup lang="ts">
import NewComponent from '@/components/NewComponent.vue'
</script>
```

## 调试技巧

### 后端调试

#### 1. 使用日志

```python
import logging

logger = logging.getLogger(__name__)

logger.info("信息日志")
logger.warning("警告日志")
logger.error("错误日志", exc_info=True)
```

#### 2. 使用断点调试

```bash
# 使用 VS Code 调试
# 在 launch.json 中配置：
{
  "name": "Python: FastAPI",
  "type": "debugpy",
  "request": "launch",
  "module": "uvicorn",
  "args": ["app:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
}
```

#### 3. 使用 Swagger UI

访问 `http://localhost:8000/docs` 进行 API 测试。

### 前端调试

#### 1. 使用浏览器开发工具

- Console: 查看日志和错误
- Network: 查看网络请求
- Vue DevTools: 查看组件状态

#### 2. 添加调试日志

```typescript
console.log('调试信息', data)
console.warn('警告信息', warning)
console.error('错误信息', error)
```

#### 3. 使用 Vue DevTools

```bash
# 安装 Vue DevTools 浏览器扩展
# Chrome/Edge: Vue.js devtools
```

## 测试

### 后端测试

#### 单元测试

```python
# tests/test_strategies.py
import pytest
from app.strategies.dual_ma import DualMAStrategy

def test_dual_ma_strategy():
    params = {"short_window": 5, "long_window": 20}
    strategy = DualMAStrategy(params)

    # 测试参数定义
    param_defs = strategy.get_parameters_definition()
    assert len(param_defs) == 2

    # 测试策略ID
    assert strategy.get_strategy_id() == "dual_ma"
```

#### 集成测试

```python
# tests/test_api.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_start_backtest():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(
            "/api/backtest/start",
            json={
                "stock_code": "000001.SZ",
                "start_date": "2024-01-01",
                "end_date": "2024-12-31",
                "initial_capital": 100000.0,
                "strategy_id": "dual_ma"
            }
        )
        assert response.status_code == 200
```

### 前端测试

#### 组件测试

```typescript
// tests/components/NewComponent.spec.ts
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import NewComponent from '@/components/NewComponent.vue'

describe('NewComponent', () => {
  it('renders properly', () => {
    const wrapper = mount(NewComponent, {
      props: {
        title: '测试标题'
      }
    })
    expect(wrapper.text()).toContain('测试标题')
  })
})
```

## 代码规范

### Python 代码规范

#### 1. 命名规范

- 类名: PascalCase
- 函数名: snake_case
- 常量: UPPER_CASE
- 私有成员: _leading_underscore

#### 2. 类型注解

```python
from typing import Dict, List, Optional

def process_data(data: Dict[str, Any]) -> Optional[List[str]]:
    """处理数据"""
    # 实现
    pass
```

#### 3. 文档字符串

```python
def calculate_metrics(data: List[float]) -> Dict[str, float]:
    """
    计算指标

    Args:
        data: 数据列表

    Returns:
        包含各种指标的字典

    Raises:
        ValueError: 数据为空时抛出
    """
```

### TypeScript 代码规范

#### 1. 命名规范

- 接口/类型: PascalCase
- 函数/变量: camelCase
- 常量: UPPER_CASE
- 组件: PascalCase

#### 2. 类型定义

```typescript
interface UserData {
  id: string
  name: string
  email?: string
}

function processUser(user: UserData): void {
  // 实现
}
```

#### 3. 注释规范

```typescript
/**
 * 处理用户数据
 * @param user 用户数据
 * @returns 处理结果
 */
function processUser(user: UserData): Result {
  // 实现
}
```

## 性能优化

### 后端优化

#### 1. 数据库查询优化

```python
# 使用投影限制返回字段
await db.collection.find({"field": "value"}, {"_id": 0, "name": 1}).to_list(None)

# 使用索引
db.collection.create_index([("field", 1)])
```

#### 2. 缓存优化

```python
# 使用 Redis 缓存
cached = await redis_client.get(key)
if cached:
    return json.loads(cached)

# 计算结果
result = await expensive_operation()

# 缓存结果
await redis_client.set(key, json.dumps(result), ex=3600)
```

#### 3. 异步处理

```python
# 使用异步操作
async def process_data():
    # 并发执行多个异步操作
    results = await asyncio.gather(
        operation1(),
        operation2(),
        operation3()
    )
    return results
```

### 前端优化

#### 1. 组件懒加载

```typescript
const BacktestResults = defineAsyncComponent(() =>
  import('@/components/BacktestResults.vue')
)
```

#### 2. 计算属性缓存

```typescript
const filteredData = computed(() => {
  return data.value.filter(item => item.active)
})
```

#### 3. 防抖和节流

```typescript
import { debounce } from 'lodash-es'

const search = debounce((query: string) => {
  // 执行搜索
}, 300)
```

## 部署

### Docker 部署

#### 1. 构建镜像

```bash
# 构建后端镜像
docker build -t tradingagents-backend:latest .

# 构建前端镜像
docker build -t tradingagents-frontend:latest -f frontend/Dockerfile .
```

#### 2. 启动服务

```bash
docker-compose up -d
```

### 生产环境配置

#### 1. 环境变量

```ini
# 生产环境
DEBUG=false
LOG_LEVEL=WARNING

# 使用强密码
MONGODB_PASSWORD=<strong_password>
REDIS_PASSWORD=<strong_password>
```

#### 2. 反向代理

```nginx
# Nginx 配置
location /api {
    proxy_pass http://backend:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}

location /ws {
    proxy_pass http://backend:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

## 常见问题

### 1. 数据库连接失败

**问题**: MongoDB 连接超时

**解决**:
- 检查 MongoDB 是否运行
- 检查连接字符串是否正确
- 检查网络连接

### 2. 策略参数验证失败

**问题**: 参数验证不通过

**解决**:
- 检查参数定义是否正确
- 检查参数类型是否匹配
- 检查参数范围是否合理

### 3. WebSocket 连接断开

**问题**: WebSocket 频繁断开

**解决**:
- 检查心跳机制
- 增加超时时间
- 检查网络稳定性
