# 测试策略分析

## 测试现状概述

TradingAgents-CN 项目目前自动化测试覆盖有限，主要通过手动测试验证功能。项目缺乏完整的单元测试、集成测试和端到端测试体系。

## 测试环境

### 1. 开发环境测试

```bash
# 后端开发服务器
python -m app

# 前端开发服务器
cd frontend && npm run dev

# 访问 API 文档进行测试
open http://localhost:8000/docs
```

### 2. 测试数据库

```bash
# 使用独立的测试数据库
export MONGODB_DATABASE=tradingagents_test
export REDIS_DB=1
```

## 手动测试清单

### 1. 后端健康检查

```bash
# 测试健康检查端点
curl http://localhost:8000/api/health

# 预期响应
{
  "status": "healthy",
  "timestamp": "2024-02-05T14:30:00.000Z"
}
```

### 2. API 文档测试

访问 `http://localhost:8000/docs` 进行以下测试：

- **回测启动**: `POST /api/backtest/start`
- **回测状态**: `GET /api/backtest/{backtest_id}/status`
- **策略列表**: `GET /api/strategies`
- **股票搜索**: `GET /api/stocks/search`

### 3. 数据库索引测试

```bash
# 检查数据库索引创建
python -m app.scripts.init_trading_calendar

# 验证日志
# 查看日志中的 "✅ 数据库索引创建完成"
```

### 4. 分析流程测试

```bash
# 1. 提交分析请求
curl -X POST http://localhost:8000/api/analysis/analyze \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "000001.SZ",
    "analysis_type": "comprehensive"
  }'

# 2. 监控进度
# 通过 WebSocket 连接实时查看进度

# 3. 查看结果
# 等待分析完成后查看结果
```

## 测试策略

### 1. 单元测试策略

#### 测试框架选择

```python
# pytest + pytest-asyncio
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
```

#### 策略测试

```python
# tests/test_strategies.py
from app.strategies.dual_ma import DualMAStrategy
from datetime import datetime

def test_dual_ma_initialization():
    params = {"short_window": 5, "long_window": 20}
    strategy = DualMAStrategy(params)
    assert strategy.short_window == 5
    assert strategy.long_window == 20

def test_dual_ma_signal_generation():
    params = {"short_window": 5, "long_window": 20}
    strategy = DualMAStrategy(params)

    # 添加历史数据
    for i in range(30):
        strategy.on_bar(
            bar_id=f"bar_{i}",
            timestamp=datetime.now(),
            current_price=100 + i,
            position=0,
            cash=100000
        )

    # 测试信号生成
    signal = strategy.on_bar(
        bar_id="bar_30",
        timestamp=datetime.now(),
        current_price=130,
        position=0,
        cash=100000
    )

    assert signal["action"] in ["buy", "sell", "hold"]
    assert "amount" in signal
    assert "reason" in signal
```

#### 服务测试

```python
# tests/test_services.py
from app.services.result_calculator import ResultCalculator
from motor.motor_asyncio import AsyncIOMotorClient

@pytest.mark.asyncio
async def test_result_calculator():
    # 创建测试数据库
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.tradingagents_test

    # 准备测试数据
    await db.backtest_daily_states.insert_many([
        {"date": "2024-01-01", "total_assets": 100000, ...},
        {"date": "2024-01-02", "total_assets": 101000, ...},
    ])

    # 测试结果计算
    calculator = ResultCalculator(db)
    results = await calculator.calculate_and_save_results("bt_test")

    assert results["return_metrics"]["total_return"] > 0
    assert results["trading_stats"]["total_trades"] >= 0
```

### 2. 集成测试策略

#### API 集成测试

```python
# tests/test_api_integration.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_backtest_flow():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 1. 启动回测
        response = await ac.post(
            "/api/backtest/start",
            json={
                "stock_code": "000001.SZ",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "initial_capital": 100000.0,
                "strategy_id": "dual_ma"
            }
        )
        assert response.status_code == 200
        backtest_id = response.json()["data"]["backtest_id"]

        # 2. 查询状态
        response = await ac.get(f"/api/backtest/{backtest_id}/status")
        assert response.status_code == 200
        status = response.json()["data"]["status"]
        assert status in ["created", "running", "completed"]

        # 3. 等待完成
        await asyncio.sleep(5)

        # 4. 获取结果
        response = await ac.get(f"/api/backtest/{backtest_id}/results")
        assert response.status_code == 200
        results = response.json()["data"]
        assert "return_metrics" in results
```

#### 数据库集成测试

```python
# tests/test_database.py
import pytest
from motor.motor_asyncio import AsyncIOMotorClient

@pytest.mark.asyncio
async def test_database_operations():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.tradingagents_test

    # 测试插入
    result = await db.test_collection.insert_one({"name": "test"})
    assert result.inserted_id is not None

    # 测试查询
    doc = await db.test_collection.find_one({"name": "test"})
    assert doc is not None

    # 测试更新
    await db.test_collection.update_one(
        {"name": "test"},
        {"$set": {"value": 100}}
    )

    # 测试删除
    await db.test_collection.delete_one({"name": "test"})
```

### 3. 端到端测试策略

#### 回测流程 E2E 测试

```python
# tests/test_e2e.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_complete_backtest_flow():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # 1. 用户登录
        response = await ac.post(
            "/api/auth/login",
            json={"username": "test", "password": "test"}
        )
        token = response.json()["data"]["access_token"]

        # 2. 启动回测
        response = await ac.post(
            "/api/backtest/start",
            headers={"Authorization": f"Bearer {token}"},
            json={...}
        )
        backtest_id = response.json()["data"]["backtest_id"]

        # 3. 监控进度
        while True:
            response = await ac.get(
                f"/api/backtest/{backtest_id}/status",
                headers={"Authorization": f"Bearer {token}"}
            )
            status = response.json()["data"]["status"]
            if status == "completed":
                break
            await asyncio.sleep(1)

        # 4. 验证结果
        response = await ac.get(
            f"/api/backtest/{backtest_id}/results",
            headers={"Authorization": f"Bearer {token}"}
        )
        results = response.json()["data"]
        assert results["return_metrics"]["total_return"] is not None
```

### 4. 前端测试策略

#### 组件测试

```typescript
// tests/components/BacktestControlPanel.spec.ts
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import BacktestControlPanel from '@/views/Backtest/BacktestControlPanel.vue'

describe('BacktestControlPanel', () => {
  it('renders properly', () => {
    const wrapper = mount(BacktestControlPanel)
    expect(wrapper.text()).toContain('股票回测')
  })

  it('validates form inputs', async () => {
    const wrapper = mount(BacktestControlPanel)
    const form = wrapper.findComponent({ name: 'ElForm' })

    // 测试必填字段
    expect(form.vm.stock_code).toBe('000001.SZ')
    expect(form.vm.initial_capital).toBe(100000)
  })
})
```

#### Store 测试

```typescript
// tests/stores/backtestEngine.spec.ts
import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useBacktestEngineStore } from '@/stores/backtestEngine'

describe('BacktestEngineStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts with empty state', () => {
    const store = useBacktestEngineStore()
    expect(store.currentBacktestId).toBeNull()
    expect(store.backtestStatus).toBeNull()
  })

  it('updates status correctly', async () => {
    const store = useBacktestEngineStore()
    await store.fetchBacktestStatus('bt_test')
    expect(store.backtestStatus).not.toBeNull()
  })
})
```

## 测试用例设计

### 1. 回测引擎测试用例

| 用例ID | 测试场景 | 输入 | 预期输出 |
|--------|----------|------|----------|
| BE-001 | 正常回测流程 | 有效参数 | 回测成功，有结果 |
| BE-002 | 无效股票代码 | 999999.SZ | 返回错误 |
| BE-003 | 日期范围错误 | start > end | 返回错误 |
| BE-004 | 资金不足 | initial_capital < 1000 | 返回错误 |
| BE-005 | 策略参数无效 | strategy_params = {} | 使用默认参数 |
| BE-006 | T+1 规则验证 | 当日买入当日卖出 | 卖出失败 |
| BE-007 | 交易费用计算 | 买入10000元 | 费用≈27元 |

### 2. 策略测试用例

| 用例ID | 测试场景 | 输入 | 预期输出 |
|--------|----------|------|----------|
| ST-001 | 双均线金叉 | 5日均线上穿20日均线 | 买入信号 |
| ST-002 | 双均线死叉 | 5日均线下穿20日均线 | 卖出信号 |
| ST-003 | RSI超卖 | RSI < 30 | 买入信号 |
| ST-004 | RSI超买 | RSI > 70 | 卖出信号 |
| ST-005 | 数据不足 | 历史数据<窗口 | 持有信号 |

### 3. API 测试用例

| 用例ID | 测试场景 | HTTP方法 | 端点 | 预期状态码 |
|--------|----------|----------|------|------------|
| API-001 | 健康检查 | GET | /api/health | 200 |
| API-002 | 启动回测 | POST | /api/backtest/start | 200 |
| API-003 | 查询状态 | GET | /api/backtest/{id}/status | 200 |
| API-004 | 无效回测ID | GET | /api/backtest/invalid/status | 404 |
| API-005 | 未认证请求 | GET | /api/backtest/{id}/results | 401 |

## 测试数据准备

### 1. Mock 数据

```python
# tests/fixtures/data.py
import pytest

@pytest.fixture
def sample_stock_data():
    return [
        {"date": "2024-01-01", "open": 100, "close": 101, ...},
        {"date": "2024-01-02", "open": 101, "close": 102, ...},
        # ... 更多数据
    ]

@pytest.fixture
def sample_backtest_params():
    return {
        "stock_code": "000001.SZ",
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "initial_capital": 100000.0,
        "strategy_id": "dual_ma",
        "strategy_params": {
            "short_window": 5,
            "long_window": 20
        }
    }
```

### 2. 测试数据库

```python
@pytest.fixture
async def test_db():
    # 创建测试数据库
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.tradingagents_test

    yield db

    # 清理
    await client.drop_database("tradingagents_test")
    client.close()
```

## 持续集成策略

### 1. GitHub Actions 配置

```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      mongodb:
        image: mongo:5.0
        ports:
          - 27017:27017

      redis:
        image: redis:7.0
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio

      - name: Run tests
        run: pytest tests/
```

### 2. 测试覆盖率

```bash
# 安装覆盖率工具
pip install pytest-cov

# 运行测试并生成覆盖率报告
pytest --cov=app --cov-report=html

# 查看报告
open htmlcov/index.html
```

## 测试改进建议

### 1. 建立测试框架

- 使用 pytest 作为测试框架
- 配置测试数据库
- 编写测试 fixtures
- 建立测试数据生成器

### 2. 增加测试覆盖

- 核心业务逻辑单元测试
- API 集成测试
- 前端组件测试
- E2E 测试

### 3. 测试自动化

- CI/CD 集成
- 自动运行测试
- 测试报告生成
- 覆盖率监控

### 4. 性能测试

- 压力测试
- 负载测试
- 响应时间测试

## 常见测试场景

### 1. 回测中断恢复

```python
@pytest.mark.asyncio
async def test_backtest_interrupt_resume():
    # 1. 启动回测
    # 2. 中断回测
    # 3. 恢复回测
    # 4. 验证结果
    pass
```

### 2. 并发回测

```python
@pytest.mark.asyncio
async def test_concurrent_backtests():
    # 同时启动多个回测任务
    # 验证资源竞争
    # 验证数据隔离
    pass
```

### 3. 数据异常处理

```python
@pytest.mark.asyncio
async def test_missing_data_handling():
    # 测试数据缺失时的处理
    # 验证错误提示
    # 验证优雅降级
    pass
```

## 调试测试

### 1. 使用断点调试

```python
import pdb

def test_something():
    pdb.set_trace()  # 设置断点
    result = some_function()
    assert result == expected
```

### 2. 查看日志

```bash
# 查看测试日志
pytest tests/ -v -s

# 查看详细输出
pytest tests/ -vv --log-cli-level=DEBUG
```

### 3. 使用测试数据库

```bash
# 启动测试数据库
docker-compose -f docker-compose.test.yml up -d

# 运行测试
pytest tests/ --test-db-url=mongodb://localhost:27017/test
```

## 测试最佳实践

### 1. 测试隔离

- 每个测试独立运行
- 使用独立的测试数据库
- 清理测试数据

### 2. 测试命名

- 使用描述性的测试名称
- 遵循约定：test_<功能>_<场景>

### 3. 断言明确

- 使用具体的断言消息
- 验证关键业务逻辑
- 检查边界条件

### 4. Mock 外部依赖

- Mock 外部 API 调用
- Mock 数据库连接
- Mock 文件系统操作
