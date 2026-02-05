<template>
  <div class="backtest-control-panel">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">
        <el-icon><TrendCharts /></el-icon>
        回测引擎
      </h1>
      <p class="page-description">
        执行股票回测任务，实时查看进度和持仓
      </p>
    </div>

    <!-- 参数配置卡片 -->
    <el-card class="config-card" shadow="never">
      <template #header>
        <span class="card-title">
          <el-icon><Setting /></el-icon>
          回测参数配置
        </span>
      </template>

      <el-form :model="form" label-width="120px" label-position="left">
        <!-- 股票代码 -->
        <el-form-item label="股票代码">
          <el-input
            v-model="form.stock_code"
            placeholder="请输入股票代码（如 000001.SZ）"
            clearable
          >
            <template #append>
              <el-button @click="handleSearchStock">搜索</el-button>
            </template>
          </el-input>
        </el-form-item>

        <!-- 日期范围 -->
        <el-form-item label="回测日期范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            :disabled-date="disabledDate"
          />
        </el-form-item>

        <!-- 初始资金 -->
        <el-form-item label="初始资金">
          <el-input-number
            v-model="form.initial_capital"
            :min="10000"
            :max="10000000"
            :step="10000"
            :precision="2"
            controls-position="right"
          />
          <span class="unit-label">元</span>
        </el-form-item>

        <!-- 策略选择 -->
        <el-form-item label="策略">
          <el-select v-model="form.strategy_id" placeholder="选择策略">
            <el-option label="买入持有策略" value="dual_ma" />
            <el-option label="双均线策略" value="buy_and_hold" />
          </el-select>
        </el-form-item>

        <!-- 操作按钮 -->
        <el-form-item>
          <el-button
            type="primary"
            :loading="backtestStore.startingBacktest"
            :disabled="!canStartBacktest"
            @click="handleStartBacktest"
            size="large"
          >
            <el-icon><VideoPlay /></el-icon>
            启动回测
          </el-button>
          <el-button
            v-if="backtestStore.isRunning"
            type="warning"
            @click="handleInterruptBacktest"
            size="large"
          >
            <el-icon><VideoPause /></el-icon>
            暂停回测
          </el-button>
          <el-button
            v-if="backtestStore.isPaused"
            type="success"
            @click="handleContinueBacktest"
            size="large"
          >
            <el-icon><VideoPlay /></el-icon>
            继续回测
          </el-button>
          <el-button
            v-if="backtestStore.currentBacktestId"
            type="danger"
            @click="handleAbortBacktest"
            size="large"
          >
            <el-icon><CircleClose /></el-icon>
            放弃回测
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 执行进度卡片 -->
    <el-card v-if="backtestStore.currentBacktestId" class="progress-card" shadow="never">
      <template #header>
        <span class="card-title">
          <el-icon><DataLine /></el-icon>
          执行进度
        </span>
      </template>

      <!-- 进度条 -->
      <div class="progress-section">
        <div class="progress-label">
          <span>进度：{{ backtestStore.progress.toFixed(2) }}%</span>
          <span>{{ backtestStore.currentBarIndex }} / {{ backtestStore.totalBars }}</span>
        </div>
        <el-progress
          :percentage="backtestStore.progress"
          :status="progressStatus"
          :stroke-width="20"
        />
      </div>

      <!-- 当前日期 -->
      <div v-if="backtestStore.currentDate" class="current-date">
        <el-icon><Calendar /></el-icon>
        当前日期：{{ backtestStore.currentDate }}
      </div>

      <!-- 状态标签 -->
      <div class="status-tags">
        <el-tag :type="statusTagType" size="large">
          {{ statusText }}
        </el-tag>
        <el-tag v-if="backtestStore.wsConnected" type="success" size="large">
          <el-icon><Connection /></el-icon>
          实时连接中
        </el-tag>
        <el-tag v-else type="danger" size="large">
          <el-icon><Connection /></el-icon>
          连接断开
        </el-tag>
      </div>
    </el-card>

    <!-- 实时持仓卡片 -->
    <el-card v-if="backtestStore.hasPosition" class="position-card" shadow="never">
      <template #header>
        <span class="card-title">
          <el-icon><Wallet /></el-icon>
          实时持仓
        </span>
      </template>

      <el-row :gutter="16">
        <el-col :span="6">
          <div class="metric-item">
            <div class="metric-label">总资产</div>
            <div class="metric-value">{{ formatCurrency(backtestStore.totalValue) }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-item">
            <div class="metric-label">现金</div>
            <div class="metric-value">{{ formatCurrency(backtestStore.cash) }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-item">
            <div class="metric-label">市值</div>
            <div class="metric-value">{{ formatCurrency(backtestStore.marketValue) }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-item">
            <div class="metric-label">盈亏</div>
            <div
              class="metric-value"
              :class="backtestStore.profitLoss >= 0 ? 'profit' : 'loss'"
            >
              {{ formatCurrency(backtestStore.profitLoss) }}
              ({{ backtestStore.profitLossPct.toFixed(2) }}%)
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 错误提示 -->
    <el-alert
      v-if="backtestStore.startError || backtestStore.statusError"
      type="error"
      :title="backtestStore.startError || backtestStore.statusError || '未知错误'"
      :closable="false"
      show-icon
      class="error-alert"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { useBacktestEngineStore } from '@/stores/backtestEngine'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  TrendCharts,
  Setting,
  VideoPlay,
  VideoPause,
  CircleClose,
  DataLine,
  Calendar,
  Connection,
  Wallet
} from '@element-plus/icons-vue'

// Store
const backtestStore = useBacktestEngineStore()

// 表单数据
const form = ref({
  stock_code: '000001.SZ',
  start_date: '',
  end_date: '',
  initial_capital: 100000,
  strategy_id: 'dual_ma',
  strategy_params: {}
})

const dateRange = ref<string[]>([])

// 计算属性
const canStartBacktest = computed(() => {
  return form.value.stock_code &&
         dateRange.value?.length === 2 &&
         form.value.initial_capital > 0
})

const progressStatus = computed(() => {
  if (backtestStore.isCompleted) return 'success'
  if (backtestStore.isFailed) return 'exception'
  return undefined
})

const statusTagType = computed(() => {
  if (backtestStore.isRunning) return 'warning'
  if (backtestStore.isPaused) return 'info'
  if (backtestStore.isCompleted) return 'success'
  if (backtestStore.isFailed) return 'danger'
  return 'info'
})

const statusText = computed(() => {
  const statusMap: Record<string, string> = {
    created: '已创建',
    running: '运行中',
    paused: '已暂停',
    completed: '已完成',
    failed: '失败',
    aborted: '已放弃'
  }
  return statusMap[backtestStore.backtestStatus?.status || ''] || '未知'
})

// 方法
function disabledDate(time: Date) {
  // 禁用未来日期
  return time.getTime() > Date.now()
}

async function handleStartBacktest() {
  if (!canStartBacktest.value) {
    ElMessage.warning('请完善回测参数')
    return
  }

  // 更新表单数据
  form.value.start_date = dateRange.value[0]
  form.value.end_date = dateRange.value[1]

  try {
    await backtestStore.startBacktest(form.value)
    ElMessage.success('回测任务已启动')
  } catch (error: any) {
    ElMessage.error(error?.message || '启动失败')
  }
}

async function handleInterruptBacktest() {
  try {
    await ElMessageBox.confirm('确认暂停回测任务？', '提示', {
      type: 'warning'
    })
    await backtestStore.interruptBacktest()
    ElMessage.success('回测已暂停')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error?.message || '暂停失败')
    }
  }
}

async function handleContinueBacktest() {
  try {
    await backtestStore.continueBacktest()
    ElMessage.success('回测已继续')
  } catch (error: any) {
    ElMessage.error(error?.message || '继续失败')
  }
}

async function handleAbortBacktest() {
  try {
    await ElMessageBox.confirm('确认放弃回测任务？此操作不可恢复！', '警告', {
      type: 'error',
      confirmButtonText: '确认放弃',
      cancelButtonText: '取消'
    })
    await backtestStore.abortBacktest()
    ElMessage.success('回测任务已放弃')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error?.message || '放弃失败')
    }
  }
}

function handleSearchStock() {
  // TODO: 实现股票搜索功能
  ElMessage.info('股票搜索功能开发中...')
}

function formatCurrency(value: number): string {
  return `¥${value.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`
}

// 生命周期
onUnmounted(() => {
  backtestStore.cleanup()
})
</script>

<style scoped lang="scss">
.backtest-control-panel {
  padding: 20px;

  .page-header {
    margin-bottom: 20px;

    .page-title {
      font-size: 24px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 10px;
      margin: 0 0 10px 0;
    }

    .page-description {
      color: #606266;
      margin: 0;
    }
  }

  .config-card,
  .progress-card,
  .position-card {
    margin-bottom: 20px;

    .card-title {
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }

  .unit-label {
    margin-left: 10px;
    color: #909399;
  }

  .progress-section {
    margin-bottom: 20px;

    .progress-label {
      display: flex;
      justify-content: space-between;
      margin-bottom: 10px;
      font-weight: 500;
    }
  }

  .current-date {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 20px;
    font-size: 16px;
    font-weight: 500;
  }

  .status-tags {
    display: flex;
    gap: 10px;
  }

  .metric-item {
    text-align: center;
    padding: 15px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;

    .metric-label {
      color: #909399;
      margin-bottom: 8px;
    }

    .metric-value {
      font-size: 20px;
      font-weight: 600;

      &.profit {
        color: #f56c6c;
      }

      &.loss {
        color: #67c23a;
      }
    }
  }

  .error-alert {
    margin-bottom: 20px;
  }
}
</style>
