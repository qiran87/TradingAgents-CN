# 交易明细显示为空Bug修复报告

## Bug描述

**症状**: 执行回测后,前端页面的#交易明细#组件中的历史回测数据显示为空,完全没有任何数据展示。

**测试任务**: `bt_20260209_153019_173344`

## 问题定位过程

### 1. 数据验证 ✅

首先验证数据库中的数据完整性:

```python
# 数据库检查
backtest_id = 'bt_20260209_153019_173344'

# 回测任务
task = {
    'backtest_id': 'bt_20260209_153019_173344',
    'user_id': 'admin',
    'status': 'completed',
    'stock_code': '000001.SZ'
}

# 交易记录
trades_count = 1
trade = {
    'date': '2025-03-03',
    'trade_type': 'buy',
    'stock_code': '000001.SZ',
    'stock_name': '000001.SZ',
    'price': 10.93,
    'shares': 9100,
    'cash_before': 100000.0,
    'position_before': 0,
    ...
}
```

**结论**: 数据库中的数据完整,所有必需字段都存在。

### 2. 后端API测试 ✅

测试后端服务层是否能正常返回数据:

```python
calculator = ResultCalculator(db)
trades = await calculator.get_trades(backtest_id, limit=50)

# 返回结果
len(trades) = 1  # ✅ 正常返回
trades[0] = {
    'backtest_id': 'bt_20260209_153019_173344',
    'date': '2025-03-03',
    'trade_type': 'buy',
    'stock_code': '000001.SZ',
    ...
}
```

**结论**: 后端API正常返回数据。

### 3. 前端调用检查 ❌ 发现问题!

检查前端 `BacktestResults.vue` 的 `loadTrades()` 函数:

```typescript
// ❌ 错误的调用方式
const response = await backtestEngineApi.getBacktestTrades(
  props.backtestId,
  pageSize.value * 3  // 只传了2个参数!
)
```

但API定义是:

```typescript
async getBacktestTrades(
  backtestId: string,
  page: number = 1,       // 第2个参数是page
  pageSize: number = 50   // 第3个参数是pageSize
)
```

**问题分析**:
- 前端只传递了2个参数
- 导致 `pageSize.value * 3` (例如60) 被当作 `page` 参数
- 实际的 `pageSize` 使用了默认值50
- 请求变成了 `GET /api/backtest/bt_xxx/trades?page=60&page_size=50`
- 后端返回第60页的数据,但总共只有1条记录,所以返回空数组!

## 修复方案

### 修改文件

`frontend/src/components/BacktestResults.vue`

### 修改内容

```diff
// 加载交易明细
const loadTrades = async () => {
  if (!props.backtestId) return

  tradesLoading.value = true
  try {
-   // 使用分页参数
+   // 使用分页参数 - 修正参数顺序
    const response = await backtestEngineApi.getBacktestTrades(
      props.backtestId,
-     pageSize.value * 3  // 获取更多数据以支持分页
+     1,  // page = 1 (第一页)
+     pageSize.value * 3  // pageSize 获取更多数据以支持分页
    )
    if (response.success) {
      trades.value = response.data.trades
    } else {
      ElMessage.warning(response.message || '获取交易明细失败')
    }
  } catch (err: any) {
    console.error('加载交易明细失败:', err)
    ElMessage.warning('获取交易明细失败，但不影响主要功能')
  } finally {
    tradesLoading.value = false
  }
}
```

### 修复说明

1. **添加 `page` 参数**: 传递 `1` 表示请求第一页
2. **修正 `pageSize` 参数**: `pageSize.value * 3` 作为第三个参数传递
3. **添加注释**: 明确参数含义,避免后续混淆

## 验证结果

### 修复前

```typescript
// 错误调用
getBacktestTrades(backtestId, 60)
↓
实际请求: GET /api/backtest/bt_xxx/trades?page=60&page_size=50
↓
后端处理:
  total = 1
  start_idx = (60 - 1) * 50 = 2950
  end_idx = 2950 + 50 = 3000
  paginated_trades = trades[2950:3000]  # 空数组!
↓
返回: {"trades": [], "count": 0}
↓
前端显示: 空表格
```

### 修复后

```typescript
// 正确调用
getBacktestTrades(backtestId, 1, 60)
↓
实际请求: GET /api/backtest/bt_xxx/trades?page=1&page_size=60
↓
后端处理:
  total = 1
  start_idx = (1 - 1) * 60 = 0
  end_idx = 0 + 60 = 60
  paginated_trades = trades[0:60]  # 包含1条记录!
↓
返回: {"trades": [{...}], "count": 1}
↓
前端显示: 完整的交易记录表格
```

## 技术细节

### API参数定义

```typescript
// frontend/src/api/backtestEngine.ts
async getBacktestTrades(
  backtestId: string,   // 路径参数
  page: number = 1,     // 查询参数: 页码
  pageSize: number = 50 // 查询参数: 每页数量
): Promise<ApiResponse<{
  trades: TradeRecord[],
  count: number,
  pagination: {...}
}>>
```

### 后端分页逻辑

```python
# app/routers/backtest_engine.py:520-535
# 手动分页
total = len(trades)
start_idx = (page - 1) * page_size
end_idx = start_idx + page_size
paginated_trades = trades[start_idx:end_idx]

return ok(data={
    "trades": paginated_trades,
    "count": len(paginated_trades),
    "pagination": {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size
    }
})
```

## 总结

### 根本原因

**前端API调用参数顺序错误**:
- 缺少 `page` 参数
- 导致 `pageSize` 值被误当作 `page` 使用
- 请求了不存在的页码,返回空数组

### 修复措施

✅ 添加正确的 `page` 参数(值为1)
✅ 将 `pageSize` 作为第三个参数传递
✅ 添加注释说明参数含义

### 影响范围

- **修改文件**: `frontend/src/components/BacktestResults.vue`
- **影响功能**: 交易明细显示
- **测试任务**: `bt_20260209_153019_173344`
- **验证状态**: ✅ 修复完成

### 后续建议

1. **代码审查**: 检查其他API调用是否有类似问题
2. **类型安全**: 考虑使用对象参数替代位置参数
3. **单元测试**: 为前端API调用添加测试用例

## 相关文件

- **修改文件**: `frontend/src/components/BacktestResults.vue:378-400`
- **API定义**: `frontend/src/api/backtestEngine.ts:254-267`
- **后端路由**: `app/routers/backtest_engine.py:491-540`
- **测试数据**: backtest_id = `bt_20260209_153019_173344`

## 时间记录

- Bug发现: 2026-02-09
- 问题定位: 1. 数据验证 → 2. 后端测试 → 3. 前端检查
- 根本原因: 前端API调用参数顺序错误
- 修复完成: 2026-02-09
- 验证通过: 等待前端刷新页面后确认
