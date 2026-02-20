# 架构模式分析

## 架构模式概述

TradingAgents-CN 项目采用多种架构模式，包括分层架构、微服务架构、事件驱动架构、策略模式等。这些模式的组合使用，使得系统具有良好的可扩展性、可维护性和可测试性。

## 1. 分层架构

### 1.1 三层架构

```
┌─────────────────────────────────────────────┐
│          表现层 (Presentation)              │
│  - Vue Components                           │
│  - API Routers                              │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│          业务逻辑层 (Business)               │
│  - Services                                 │
│  - Strategies                               │
│  - Business Rules                           │
└────────────────┬────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────┐
│          数据访问层 (Data Access)            │
│  - MongoDB Operations                       │
│  - Redis Operations                         │
│  - External API Calls                       │
└─────────────────────────────────────────────┘
```

**特点**:
- 职责分离：每层只负责自己的职责
- 依赖单向：上层依赖下层，下层不依赖上层
- 易于测试：可以逐层测试

### 1.2 后端分层

```python
# 路由层 (Routers)
@router.post("/api/backtest/start")
async def start_backtest(request, db=Depends(get_mongo_db)):
    # 只负责接收请求、返回响应
    pass

# 服务层 (Services)
class BacktestEngine:
    async def execute_backtest(self, backtest_id, parameters):
        # 实现业务逻辑
        pass

# 数据层 (Database/Cache)
await db.backtest_tasks.insert_one(document)
```

### 1.3 前端分层

```vue
<!-- 视图层 -->
<template>
  <BacktestResults :data="resultData" />
</template>

<!-- 逻辑层 -->
<script setup>
const backtestStore = useBacktestEngineStore()
const resultData = computed(() => backtestStore.results)
</script>

<!-- 数据层 -->
import { backtestEngineApi } from '@/api/backtestEngine'
```

## 2. 微服务架构

### 2.1 服务拆分

```
┌─────────────────────────────────────────────┐
│              API Gateway                    │
│         (Nginx / FastAPI Router)           │
└─────────────────┬───────────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
    ▼             ▼             ▼
┌────────┐  ┌──────────┐  ┌──────────┐
│ Backtest│  │ Analysis │  │   Data   │
│Service │  │ Service  │  │ Service  │
└────────┘  └──────────┘  └──────────┘
```

### 2.2 服务通信

- **同步通信**: HTTP/REST API
- **异步通信**: WebSocket、Redis Queue
- **事件通信**: Redis Pub/Sub

### 2.3 服务独立部署

```yaml
# docker-compose.yml
services:
  backend:
    image: tradingagents-backend
    ports:
      - "8000:8000"

  worker:
    image: tradingagents-worker
    command: python -m app.worker
```

## 3. 事件驱动架构

### 3.1 事件类型

```python
# 回测事件
BACKTEST_STARTED = "backtest.started"
BACKTEST_PROGRESS = "backtest.progress"
BACKTEST_COMPLETED = "backtest.completed"
BACKTEST_ERROR = "backtest.error"

# 交易事件
TRADE_SIGNAL = "trade.signal"
POSITION_UPDATE = "position.update"

# 系统事件
DATA_SYNCED = "data.synced"
USER_LOGGED_IN = "user.logged_in"
```

### 3.2 事件发布

```python
class WebSocketManager:
    async def publish_event(self, event_type: str, data: dict):
        message = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        await self.broadcast(message)
```

### 3.3 事件订阅

```typescript
// 前端订阅事件
ws.onmessage = (event) => {
  const message = JSON.parse(event.data)
  switch (message.type) {
    case 'backtest.progress':
      handleProgress(message.data)
      break
    case 'trade.signal':
      handleTradeSignal(message.data)
      break
  }
}
```

## 4. 策略模式 (Strategy Pattern)

### 4.1 策略接口

```python
class BaseStrategy(ABC):
    @abstractmethod
    def on_bar(self, bar_id, timestamp, current_price, position, cash):
        """策略核心逻辑"""
        pass

    @abstractmethod
    def get_parameters_definition(self):
        """参数定义"""
        pass
```

### 4.2 具体策略

```python
class DualMAStrategy(BaseStrategy):
    def on_bar(self, bar_id, timestamp, current_price, position, cash):
        # 双均线策略实现
        pass

class RSIStrategy(BaseStrategy):
    def on_bar(self, bar_id, timestamp, current_price, position, cash):
        # RSI 策略实现
        pass
```

### 4.3 策略上下文

```python
class BacktestEngine:
    def __init__(self, strategy: BaseStrategy):
        self.strategy = strategy

    def execute_backtest(self):
        # 使用策略
        signal = self.strategy.on_bar(...)
```

### 4.4 策略注册

```python
class StrategyRegistry:
    _strategies = {}

    @classmethod
    def register(cls, strategy_id: str, strategy_class: Type[BaseStrategy]):
        cls._strategies[strategy_id] = strategy_class

    @classmethod
    def get_strategy(cls, strategy_id: str, params: dict) -> BaseStrategy:
        strategy_class = cls._strategies[strategy_id]
        return strategy_class(params)
```

## 5. 工厂模式 (Factory Pattern)

### 5.1 策略工厂

```python
class StrategyFactory:
    @staticmethod
    def create_strategy(strategy_id: str, params: dict) -> BaseStrategy:
        if strategy_id == "dual_ma":
            return DualMAStrategy(params)
        elif strategy_id == "rsi":
            return RSIStrategy(params)
        else:
            raise ValueError(f"Unknown strategy: {strategy_id}")
```

### 5.2 服务工厂

```python
def get_backtest_engine_service() -> BacktestEngine:
    global _instance
    if _instance is None:
        db = get_mongo_db()
        _instance = BacktestEngine(db)
    return _instance
```

## 6. 单例模式 (Singleton Pattern)

### 6.1 数据库连接单例

```python
_mongo_client: AsyncIOMotorClient = None

def get_mongo_db() -> AsyncIOMotorDatabase:
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncIOMotorClient(mongodb_url)
    return _mongo_client.tradingagents
```

### 6.2 Redis 连接单例

```python
_redis_client: redis.Redis = None

async def get_redis_client():
    global _redis_client
    if _redis_client is None:
        _redis_client = await aioredis.from_url(redis_url)
    return _redis_client
```

## 7. 观察者模式 (Observer Pattern)

### 7.1 WebSocket 连接管理

```python
class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, backtest_id: str):
        await websocket.accept()
        if backtest_id not in self.active_connections:
            self.active_connections[backtest_id] = []
        self.active_connections[backtest_id].append(websocket)

    async def disconnect(self, websocket: WebSocket, backtest_id: str):
        self.active_connections[backtest_id].remove(websocket)

    async def broadcast(self, backtest_id: str, message: dict):
        for connection in self.active_connections.get(backtest_id, []):
            await connection.send_json(message)
```

### 7.2 进度监听

```python
class ProgressListener:
    def __init__(self, backtest_id: str):
        self.backtest_id = backtest_id

    async def on_progress(self, progress: float):
        await websocket_manager.broadcast(self.backtest_id, {
            "type": "progress",
            "data": {"progress": progress}
        })

    async def on_trade(self, trade: dict):
        await websocket_manager.broadcast(self.backtest_id, {
            "type": "trade",
            "data": trade
        })
```

## 8. 仓储模式 (Repository Pattern)

### 8.1 数据仓储

```python
class BacktestTaskRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.backtest_tasks

    async def find_by_id(self, backtest_id: str):
        return await self.collection.find_one({"backtest_id": backtest_id})

    async def save(self, task: dict):
        await self.collection.insert_one(task)

    async def update(self, backtest_id: str, updates: dict):
        await self.collection.update_one(
            {"backtest_id": backtest_id},
            {"$set": updates}
        )
```

### 8.2 使用仓储

```python
class BacktestService:
    def __init__(self, repository: BacktestTaskRepository):
        self.repository = repository

    async def create_task(self, parameters: dict):
        task = self._build_task(parameters)
        await self.repository.save(task)
        return task
```

## 9. 命令模式 (Command Pattern)

### 9.1 回测命令

```python
class BacktestCommand:
    def __init__(self, backtest_id: str, parameters: dict):
        self.backtest_id = backtest_id
        self.parameters = parameters

    async def execute(self):
        engine = BacktestEngine(db)
        await engine.execute_backtest(self.backtest_id, self.parameters)
```

### 9.2 命令调用

```python
async def execute_backtest_task(backtest_id: str, parameters: dict):
    command = BacktestCommand(backtest_id, parameters)
    await command.execute()
```

## 10. 模板方法模式 (Template Method)

### 10.1 回测执行模板

```python
class BacktestEngine:
    async def execute_backtest(self, backtest_id: str, parameters: dict):
        # 模板方法定义执行流程
        await self._initialize(backtest_id, parameters)
        await self._execute_loop(backtest_id)
        await self._finalize(backtest_id)

    async def _execute_loop(self, backtest_id: str):
        # 子步骤可以重写
        for i, trading_day in enumerate(trading_days):
            signal = await self._generate_signal(backtest_id, trading_day)
            await self._execute_trade(backtest_id, signal)
            await self._update_state(backtest_id, trading_day)
```

## 11. 责任链模式 (Chain of Responsibility)

### 11.1 数据源责任链

```python
class DataSourceHandler:
    def __init__(self):
        self.next_handler = None

    def set_next(self, handler):
        self.next_handler = handler
        return handler

    async def handle(self, request: dict):
        if self.can_handle(request):
            return self.fetch_data(request)
        elif self.next_handler:
            return await self.next_handler.handle(request)
        else:
            raise Exception("No data source available")

# 使用链
akshare = AKShareHandler()
baostock = BaoStockHandler()
akshare.set_next(baostock)

data = await akshare.handle({"symbol": "000001.SZ"})
```

## 12. 装饰器模式 (Decorator Pattern)

### 12.1 缓存装饰器

```python
def cached(ttl: int = 3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{args}:{kwargs}"
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

            result = await func(*args, **kwargs)
            await redis_client.set(cache_key, json.dumps(result), ex=ttl)
            return result
        return wrapper
    return decorator

@cached(ttl=3600)
async def get_stock_info(symbol: str):
    return await db.stock_info.find_one({"symbol": symbol})
```

### 12.2 日志装饰器

```python
def log_execution(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        logger.info(f"开始执行: {func.__name__}")
        try:
            result = await func(*args, **kwargs)
            logger.info(f"执行成功: {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"执行失败: {func.__name__}, 错误: {e}")
            raise
    return wrapper
```

## 13. 依赖注入模式 (Dependency Injection)

### 13.1 构造器注入

```python
class BacktestService:
    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        redis: redis.Redis,
        websocket_manager: WebSocketManager
    ):
        self.db = db
        self.redis = redis
        self.websocket_manager = websocket_manager
```

### 13.2 FastAPI 依赖注入

```python
def get_backtest_service(db = Depends(get_mongo_db)) -> BacktestService:
    return BacktestService(db, redis_client, websocket_manager)

@router.post("/api/backtest/start")
async def start_backtest(
    request: StartBacktestRequest,
    service: BacktestService = Depends(get_backtest_service)
):
    return await service.start_backtest(request)
```

## 14. 状态模式 (State Pattern)

### 14.1 回测状态

```python
class BacktestState:
    def __init__(self, backtest_id: str):
        self.backtest_id = backtest_id
        self.status = "created"

    def start(self):
        self.status = "running"

    def pause(self):
        if self.status == "running":
            self.status = "paused"

    def resume(self):
        if self.status == "paused":
            self.status = "running"

    def complete(self):
        self.status = "completed"

    def fail(self):
        self.status = "failed"
```

## 15. 构建者模式 (Builder Pattern)

### 15.1 回测参数构建器

```python
class BacktestParamsBuilder:
    def __init__(self):
        self.params = {
            "stock_code": "",
            "start_date": "",
            "end_date": "",
            "initial_capital": 100000,
            "strategy_id": "dual_ma",
            "strategy_params": {}
        }

    def with_stock(self, stock_code: str):
        self.params["stock_code"] = stock_code
        return self

    def with_date_range(self, start_date: str, end_date: str):
        self.params["start_date"] = start_date
        self.params["end_date"] = end_date
        return self

    def with_strategy(self, strategy_id: str, params: dict):
        self.params["strategy_id"] = strategy_id
        self.params["strategy_params"] = params
        return self

    def build(self) -> dict:
        return self.params.copy()

# 使用
params = (BacktestParamsBuilder()
    .with_stock("000001.SZ")
    .with_date_range("2024-01-01", "2024-12-31")
    .with_strategy("dual_ma", {"short_window": 5, "long_window": 20})
    .build())
```

## 架构最佳实践

### 1. 关注点分离

- 每个模块只负责一个功能
- 避免模块间过度耦合
- 使用接口定义边界

### 2. 依赖倒置

- 高层模块不依赖低层模块
- 都依赖抽象（接口）
- 使用依赖注入

### 3. 开闭原则

- 对扩展开放
- 对修改关闭
- 使用策略模式、工厂模式

### 4. 单一职责

- 每个类只有一个变化的原因
- 功能拆分到独立的类
- 保持类的简洁

### 5. 接口隔离

- 定义小而专注的接口
- 客户端不依赖不需要的方法
- 使用类型提示

## 架构演进方向

### 1. 微服务化

- 将大服务拆分为小服务
- 每个服务独立部署
- 服务间通过 API 通信

### 2. 事件驱动

- 更多使用事件驱动架构
- 减少同步调用
- 提高系统解耦

### 3. 领域驱动设计

- 按业务领域划分模块
- 定义清晰的边界上下文
- 使用通用语言
