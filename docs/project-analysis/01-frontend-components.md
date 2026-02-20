# 前端组件分析

## 组件架构概述

前端采用 Vue 3 Composition API + TypeScript 开发，使用 Element Plus 作为 UI 框架，Pinia 进行状态管理。整体采用模块化设计，按功能领域划分组件。

## 核心组件目录结构

```
frontend/src/
├── components/              # 可复用组件
│   ├── Layout/             # 布局组件
│   ├── Global/             # 全局组件
│   ├── Sync/               # 数据同步相关
│   └── Dashboard/          # 仪表盘组件
├── views/                  # 页面视图
│   └── Backtest/           # 回测相关页面
├── stores/                 # Pinia 状态管理
├── api/                    # API 接口封装
└── router/                 # 路由配置
```

## 1. 回测模块组件（重点）

### 1.1 BacktestControlPanel.vue

**文件位置**: `frontend/src/views/Backtest/BacktestControlPanel.vue`

**核心功能**:
- 回测参数设置（日期范围、初始资金、最小购买量、股票代码）
- 策略选择和参数配置
- 回测操作控制（开始、暂停、继续、重新）
- 实时持仓/现金预览
- 回测结果展示

**关键状态**:
```typescript
const form = ref({
  stock_code: '000001.SZ',
  start_date: '',
  end_date: '',
  initial_capital: 100000,
  min_purchase: 100,
  strategy_id: '',
  strategy_params: {}
})

// 确认状态
const paramsConfirmed = ref(false)
const strategyConfirmed = ref(false)
```

**关键方法**:
- `handleStartBacktest()`: 启动回测任务
- `handleInterruptBacktest()`: 暂停回测
- `handleContinueBacktest()`: 继续回测
- `handleConfirmParams()`: 确认回测参数
- `handleConfirmStrategy()`: 确认策略选择

**依赖的 Store**:
```typescript
const backtestStore = useBacktestEngineStore()
```

### 1.2 BacktestHistory.vue

**文件位置**: `frontend/src/views/Backtest/BacktestHistory.vue`

**核心功能**:
- 历史回测记录列表
- 回测结果对比
- 导出功能
- 详情查看

### 1.3 StrategyList.vue

**文件位置**: `frontend/src/views/Backtest/StrategyList.vue`

**核心功能**:
- 展示所有可用策略（内置和自定义）
- 策略详情查看
- 策略分类筛选

### 1.4 BacktestResults.vue

**文件位置**: `frontend/src/components/BacktestResults.vue`

**核心功能**:
- 收益指标展示（总收益率、年化收益率）
- 风险指标展示（最大回撤、波动率、夏普比率）
- 交易统计展示（胜率、盈亏比）
- 资金曲线图表
- 交易明细列表

## 2. 通用组件

### 2.1 TradingDayRangePicker.vue

**文件位置**: `frontend/src/components/TradingDayRangePicker.vue`

**核心功能**:
- 交易日范围选择
- 自动跳过非交易日
- 显示交易日统计
- 快捷选项（最近1月、3月、6月、1年）

**Props**:
```typescript
interface Props {
  showStats?: boolean       // 显示统计信息
  showQuickOptions?: boolean // 显示快捷选项
}
```

### 2.2 StockSelector.vue

**文件位置**: `frontend/src/components/StockSelector.vue`

**核心功能**:
- 股票代码/名称搜索
- 市场标识（A股、港股、美股）
- 自动补全
- 市场前缀提示

**Props**:
```typescript
interface Props {
  showMarket?: boolean      // 显示市场标识
  placeholder?: string      // 占位符
}
```

### 2.3 TradingDayPicker.vue

**文件位置**: `frontend/src/components/TradingDayPicker.vue`

**核心功能**:
- 单个交易日选择
- 自动过滤非交易日
- 节假日高亮

### 2.4 StockInfoCard.vue

**文件位置**: `frontend/src/components/StockInfoCard.vue`

**核心功能**:
- 股票基本信息展示
- 实时行情显示
- 涨跌幅颜色标识

## 3. 布局组件

### 3.1 SidebarMenu.vue

**文件位置**: `frontend/src/components/Layout/SidebarMenu.vue`

**核心功能**:
- 侧边栏导航菜单
- 路由跳转
- 菜单折叠/展开

### 3.2 AppFooter.vue

**文件位置**: `frontend/src/components/Layout/AppFooter.vue`

**核心功能**:
- 页面底部信息
- 版本显示
- 版权信息

### 3.3 HeaderActions.vue

**文件位置**: `frontend/src/components/Layout/HeaderActions.vue`

**核心功能**:
- 顶部操作按钮
- 用户信息展示
- 通知入口

## 4. 全局组件

### 4.1 MarketSelector.vue

**文件位置**: `frontend/src/components/Global/MarketSelector.vue`

**核心功能**:
- 市场选择（A股、港股、美股）
- 全局市场状态管理

### 4.2 MultiMarketStockSearch.vue

**文件位置**: `frontend/src/components/Global/MultiMarketStockSearch.vue`

**核心功能**:
- 跨市场股票搜索
- 统一搜索接口
- 市场自动识别

### 4.3 GlobalNotification.vue

**文件位置**: `frontend/src/components/Global/GlobalNotification.vue`

**核心功能**:
- 全局通知组件
- 多种通知类型（成功、警告、错误）
- 自动消失

### 4.4 GlobalConfirm.vue

**文件位置**: `frontend/src/components/Global/GlobalConfirm.vue`

**核心功能**:
- 全局确认对话框
- 异步操作确认

## 5. 数据同步组件

### 5.1 SyncControl.vue

**文件位置**: `frontend/src/components/Sync/SyncControl.vue`

**核心功能**:
- 数据同步控制
- 同步进度显示
- 同步任务管理

### 5.2 DataSourceStatus.vue

**文件位置**: `frontend/src/components/Sync/DataSourceStatus.vue`

**核心功能**:
- 数据源状态监控
- 健康检查结果
- 优先级配置

### 5.3 SyncHistory.vue

**文件位置**: `frontend/src/components/Sync/SyncHistory.vue`

**核心功能**:
- 同步历史记录
- 同步结果查看
- 失败重试

## 6. 状态管理（Pinia Stores）

### 6.1 backtestEngine.ts

**文件位置**: `frontend/src/stores/backtestEngine.ts`

**核心状态**:
```typescript
// 回测任务ID
const currentBacktestId = ref<string | null>(null)

// 回测状态
const backtestStatus = ref<BacktestStatus | null>(null)

// 实时持仓
const currentPosition = ref<PositionInfo | null>(null)

// WebSocket连接
const ws = ref<WebSocket | null>(null)
const wsConnected = ref(false)

// 进度历史
const progressHistory = ref<Array<{ date: string; value: number }>>([])

// 交易历史
const tradeHistory = ref<Array<any>>([])
```

**核心方法**:
```typescript
async function startBacktest(request: StartBacktestRequest)
async function interruptBacktest(backtestId?: string)
async function continueBacktest(backtestId?: string)
async function fetchBacktestStatus(backtestId?: string)
function connectWebSocket(backtestId: string)
function disconnectWebSocket()
```

**计算属性**:
```typescript
const isRunning = computed(() => backtestStatus.value?.status === 'running')
const isPaused = computed(() => backtestStatus.value?.status === 'paused')
const isCompleted = computed(() => backtestStatus.value?.status === 'completed')
const progress = computed(() => backtestStatus.value?.execution_info?.progress ?? 0)
```

### 6.2 strategy.ts

**文件位置**: `frontend/src/stores/strategy.ts`

**核心功能**:
- 策略列表管理
- 策略元数据缓存
- 策略参数定义

### 6.3 backtestHistory.ts

**文件位置**: `frontend/src/stores/backtestHistory.ts`

**核心功能**:
- 历史记录管理
- 对比功能
- 导出功能

### 6.4 auth.ts

**文件位置**: `frontend/src/stores/auth.ts`

**核心功能**:
- 用户登录状态
- Token 管理
- 权限验证

### 6.5 tradingCalendar.ts

**文件位置**: `frontend/src/stores/tradingCalendar.ts`

**核心功能**:
- 交易日历缓存
- 交易日查询
- 节假日判断

### 6.6 stockData.ts

**文件位置**: `frontend/src/stores/stockData.ts`

**核心功能**:
- 股票数据缓存
- 行情数据管理
- K线数据

## 7. API 接口封装

### 7.1 backtestEngine.ts

**文件位置**: `frontend/src/api/backtestEngine.ts`

**核心接口**:
```typescript
export const backtestEngineApi = {
  async startBacktest(request: StartBacktestRequest)
  async interruptBacktest(backtestId: string)
  async continueBacktest(backtestId: string)
  async getBacktestStatus(backtestId: string)
  async abortBacktest(backtestId: string)
  async getBacktestResults(backtestId: string)
  async getBacktestTrades(backtestId: string, page: number, pageSize: number)
  async getEquityCurve(backtestId: string)
  getWebSocketUrl(backtestId: string): string
}
```

**TypeScript 类型定义**:
```typescript
// 启动回测请求
export interface StartBacktestRequest {
  stock_code: string
  start_date: string
  end_date: string
  initial_capital: number
  strategy_id?: string
  strategy_params?: Record<string, any>
}

// 回测状态
export interface BacktestStatus {
  backtest_id: string
  status: 'created' | 'running' | 'paused' | 'completed' | 'failed' | 'aborted'
  parameters: StartBacktestRequest
  execution_info: ExecutionInfo
  error?: ErrorInfo
  created_at: string
  updated_at: string
}

// 持仓信息
export interface PositionInfo {
  cash: number
  position: number
  position_cost: number
  current_price: number
  market_value: number
  total_value: number
  profit_loss: number
  profit_loss_pct: number
}

// WebSocket 消息
export interface WSMessage {
  type: 'connected' | 'progress' | 'position' | 'trade' | 'completed' | 'error' | 'pong'
  data?: any
  timestamp?: string
}
```

### 7.2 strategies.ts

**文件位置**: `frontend/src/api/strategies.ts`

**核心接口**:
```typescript
export const strategiesApi = {
  async getStrategies(): Promise<Strategy[]>
  async getStrategyDetail(strategyId: string): Promise<Strategy>
  async validateStrategyParams(strategyId: string, params: any): Promise<ValidationResult>
}
```

### 7.3 savedParams.ts

**文件位置**: `frontend/src/api/savedParams.ts`

**核心接口**:
```typescript
export const savedParamsApi = {
  async getParamsList(): Promise<SavedBacktestParams[]>
  async getParams(id: string): Promise<SavedBacktestParams>
  async createParams(data: CreateParamsRequest): Promise<SavedBacktestParams>
  async updateParams(id: string, data: UpdateParamsRequest): Promise<SavedBacktestParams>
  async deleteParams(id: string): Promise<void>
  async useParams(id: string): Promise<void>
}
```

## 8. 组件通信模式

### 8.1 父子组件通信

```vue
<!-- 父组件 -->
<template>
  <TradingDayRangePicker
    v-model:start-date="form.start_date"
    v-model:end-date="form.end_date"
    :show-stats="true"
    :show-quick-options="true"
  />
</template>
```

### 8.2 Store 状态共享

```typescript
// 任何组件都可以访问
const backtestStore = useBacktestEngineStore()

// 读取状态
console.log(backtestStore.progress)

// 调用方法
await backtestStore.startBacktest(params)
```

### 8.3 WebSocket 消息处理

```typescript
// 在 backtestEngine Store 中处理
ws.value.onmessage = (event) => {
  const message: WSMessage = JSON.parse(event.data)
  handleWSMessage(message)
}

function handleWSMessage(message: WSMessage) {
  switch (message.type) {
    case 'progress':
      // 更新进度
      backtestStatus.value = { ...backtestStatus.value, execution_info: message.data }
      break
    case 'position':
      // 更新持仓
      currentPosition.value = message.data
      break
    case 'trade':
      // 记录交易
      tradeHistory.value.push(message.data)
      break
  }
}
```

## 9. 前端路由设计

```typescript
// router/index.ts
const routes = [
  {
    path: '/backtest',
    component: Layout,
    children: [
      {
        path: 'control',
        name: 'BacktestControl',
        component: () => import('@/views/Backtest/BacktestControlPanel.vue')
      },
      {
        path: 'history',
        name: 'BacktestHistory',
        component: () => import('@/views/Backtest/BacktestHistory.vue')
      },
      {
        path: 'strategies',
        name: 'StrategyList',
        component: () => import('@/views/Backtest/StrategyList.vue')
      }
    ]
  }
]
```

## 10. 组件最佳实践

### 10.1 组件设计原则

1. **单一职责**: 每个组件只负责一个功能
2. **Props 验证**: 使用 TypeScript 定义明确的 Props 类型
3. **事件命名**: 使用 kebab-case 命名自定义事件
4. **样式隔离**: 使用 scoped 样式避免污染

### 10.2 状态管理模式

1. **本地状态**: 使用 ref/reactive
2. **共享状态**: 使用 Pinia Store
3. **服务端状态**: 通过 API 获取后存入 Store

### 10.3 错误处理

```typescript
try {
  await backtestStore.startBacktest(params)
  ElMessage.success('回测启动成功')
} catch (error) {
  ElMessage.error(error?.message || '启动失败')
}
```

## 11. 性能优化

### 11.1 组件懒加载

```typescript
const BacktestResults = defineAsyncComponent(() => import('@/components/BacktestResults.vue'))
```

### 11.2 计算属性缓存

```typescript
const filteredStrategies = computed(() => {
  return strategies.value.filter(s => {
    return matchCategory && matchSearch
  })
})
```

### 11.3 WebSocket 连接管理

```typescript
// 组件卸载时清理
onUnmounted(() => {
  backtestStore.cleanup()
})
```

## 12. 添加新组件的步骤

1. **创建组件文件**: `frontend/src/components/NewComponent.vue`
2. **定义 Props 接口**: 明确输入参数
3. **实现组件逻辑**: 使用 Composition API
4. **添加样式**: 使用 scoped 样式
5. **导出组件**: 在需要的地方导入使用
6. **类型定义**: 在 `api/` 目录下定义相关类型
7. **Store 集成**: 如需共享状态，创建对应的 Store

## 13. 关键依赖版本

```json
{
  "vue": "^3.3.0",
  "typescript": "^5.0.0",
  "vite": "^4.4.0",
  "element-plus": "^2.3.0",
  "pinia": "^2.1.0",
  "vue-router": "^4.2.0",
  "axios": "^1.4.0",
  "echarts": "^5.4.0"
}
```

## 14. 开发建议

1. **使用 TypeScript**: 严格的类型检查减少错误
2. **组件拆分**: 复杂组件拆分为多个小组件
3. **样式规范**: 统一使用 Element Plus 的设计规范
4. **状态管理**: 合理使用 Pinia，避免过度使用全局状态
5. **错误处理**: 统一使用 ElMessage 提示用户
6. **代码复用**: 提取公共逻辑到 composables
