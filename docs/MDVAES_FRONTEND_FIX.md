# MDVAES 策略前端显示问题修复

## 问题描述

在网页上查看 MDVAES 策略的回测结果详情时，没有显示估值分析图表和决策数据。

## 问题原因

### 根本原因：认证缺失

前端调用估值历史 API 时使用了直接的 `fetch` 调用，而不是通过 `ApiClient`，导致请求没有携带认证令牌，API 返回 403 Forbidden 错误。

**问题代码 (BacktestResults.vue:461)：**
```javascript
const response = await fetch(`/api/backtest/${props.backtestId}/valuation-history`)
const data = await response.json()
```

### 次要问题：Motor 游标 project 方法

后端 API 使用了 Motor 的 `project()` 方法，这在某些情况下可能存在兼容性问题。

## 修复方案

### 1. 前端 API 调用修复

**文件：** `frontend/src/api/backtestEngine.ts`

**添加了：**
- `ValuationHistoryDataPoint` 接口定义
- `getValuationHistory()` 方法（使用 `ApiClient.get`）

```typescript
export interface ValuationHistoryDataPoint {
  date: string
  current_price: number
  intrinsic_value: number
  lower_bound: number
  upper_bound: number
  confidence: number
  signal: string
  valuation_method?: any
}

async getValuationHistory(backtestId: string) {
  return ApiClient.get<{
    backtest_id: string
    strategy_id: string
    total_count: number
    valuation_history: ValuationHistoryDataPoint[]
  }>(
    `/api/backtest/${backtestId}/valuation-history`
  )
}
```

**文件：** `frontend/src/components/BacktestResults.vue`

**修改了：**
- `loadValuationHistory()` 函数，使用 `backtestEngineApi.getValuationHistory()` 替代直接的 `fetch` 调用

```typescript
const loadValuationHistory = async () => {
  if (!props.backtestId || !isMDVAESStrategy.value) return

  valuationLoading.value = true
  try {
    const response = await backtestEngineApi.getValuationHistory(props.backtestId)
    if (response.success && response.data) {
      valuationHistory.value = response.data.valuation_history
    } else {
      console.warn('获取估值历史失败:', response.message)
    }
  } catch (err: any) {
    console.error('加载估值历史失败:', err)
  } finally {
    valuationLoading.value = false
  }
}
```

### 2. 后端数据验证

**文件：** `app/services/backtest_engine_service.py`

**验证了：**
- 估值数据正确保存到 `backtest_daily_states` 集合的 `valuation` 字段
- 数据包含：`intrinsic_value`, `lower_bound`, `upper_bound`, `confidence`, `signal`

**保存逻辑 (第787-803行)：**
```python
if signal and "metadata" in signal:
    metadata = signal["metadata"]
    if any(key in metadata for key in ["intrinsic_value", "lower_bound", "upper_bound", "confidence"]):
        daily_state_doc["valuation"] = {
            "intrinsic_value": metadata.get("intrinsic_value"),
            "lower_bound": metadata.get("lower_bound"),
            "upper_bound": metadata.get("upper_bound"),
            "confidence": metadata.get("confidence"),
            "signal": metadata.get("signal", signal.get("action")),
            "valuation_method": metadata.get("valuation_method"),
            ...
        }
```

### 3. 后端 API 修复

**文件：** `app/routers/backtest_history.py` (第 507-513 行)

**问题：** Motor 游标不支持 `.project()` 方法，导致 API 返回 500 错误

**修复：** 移除 `.project()` 调用，在数据格式化时手动选择字段

**修复前：**
```python
cursor = db.backtest_daily_states.find(
    {"backtest_id": backtest_id, "valuation": {"$exists": True}},
    sort=[("bar_index", 1)]
).project({
    "_id": 0,
    "date": 1,
    "current_price": 1,
    "valuation": 1
})
```

**修复后：**
```python
logger.info(f"🔍 查询估值历史: backtest_id={backtest_id}")
cursor = db.backtest_daily_states.find(
    {"backtest_id": backtest_id, "valuation": {"$exists": True}},
    sort=[("bar_index", 1)]
)

valuation_history = await cursor.to_list(length=None)
logger.info(f"✅ 查询到 {len(valuation_history)} 条估值记录")
```

**API 路径：** `GET /api/backtest/{backtest_id}/valuation-history`

**功能：**
- 查询 `backtest_daily_states` 集合
- 筛选有 `valuation` 字段的记录
- 返回格式化的估值历史数据

## 数据流程

```
用户查看回测结果
    ↓
BacktestResults.vue 组件
    ↓
调用 backtestEngineApi.getValuationHistory(backtestId)
    ↓
API 自动添加认证令牌
    ↓
后端 API: /api/backtest/{backtestId}/valuation-history
    ↓
查询 MongoDB backtest_daily_states 集合
    ↓
返回估值历史数据
    ↓
前端渲染图表:
  - ValuationProjectionChart (估值推演图)
  - WaterLevelGauge (估值水位仪表盘)
```

## 验证步骤

1. **启动后端服务：**
   ```bash
   ./venv/bin/python3 -m app
   ```

2. **启动前端服务：**
   ```bash
   cd frontend && npm run dev
   ```

3. **创建 MDVAES 策略回测：**
   - 进入回测控制面板
   - 选择 MDVAES 策略
   - 设置参数并启动回测

4. **查看结果详情：**
   - 回测完成后，点击查看详情
   - 应该看到以下内容：
     - 基本回测指标（收益、回撤等）
     - **MDVAES 估值分析** 区域
     - 估值推演图（价格 vs 估值区间）
     - 估值水位仪表盘

## 预期显示内容

### 估值推演图
- X轴：日期
- Y轴：价格
- 三条线：
  - 当前价格（蓝色实线）
  - 内在价值（绿色虚线）
  - 估值区间（阴影区域）

### 估值水位仪表盘
- 显示当前价格相对于估值区间的位置
- 颜色指示：
  - 绿色：价格低于下限（低估）
  - 黄色：价格在区间内（合理）
  - 红色：价格高于上限（高估）

## 文件修改清单

### 前端修改
- ✅ `frontend/src/api/backtestEngine.ts` - 添加 `getValuationHistory` 方法和类型定义
- ✅ `frontend/src/components/BacktestResults.vue` - 使用 API 客户端调用估值历史

### 后端修复
- ✅ `app/routers/backtest_history.py` (第 507-513 行) - 修复 Motor cursor `.project()` 问题
- ✅ `app/services/backtest_engine_service.py` - 估值数据保存逻辑正确

### 测试脚本
- ✅ `scripts/verify_valuation_api.py` - 验证数据结构正确
- ✅ `scripts/test_mdvaes_full.py` - 完整回测测试

## 总结

**问题 1：** 前端调用估值历史 API 时没有携带认证信息，导致 403 错误。
**解决方案：** 通过 `ApiClient` 调用 API，自动添加认证令牌。

**问题 2：** 后端 API 使用了 Motor 不支持的 `.project()` 方法，导致 500 错误。
**解决方案：** 移除 `.project()` 调用，在数据格式化时手动选择字段。

**修复文件：**
1. `frontend/src/api/backtestEngine.ts`
2. `frontend/src/components/BacktestResults.vue`
3. `app/routers/backtest_history.py`

**验证：** 修复后，MDVAES 策略回测结果详情应该正常显示估值分析图表和决策数据。

**测试结果：**
- ✅ API 返回正确的数据结构
- ✅ 包含所有必需字段 (date, current_price, intrinsic_value, lower_bound, upper_bound, confidence, signal)
- ✅ 日志显示 "✅ 查询到 10 条估值记录"
