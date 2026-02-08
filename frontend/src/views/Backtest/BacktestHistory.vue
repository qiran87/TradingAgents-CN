<template>
  <div class="backtest-history">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">
        <el-icon><Clock /></el-icon>
        回测历史记录
      </h1>
      <p class="page-description">
        查看和管理回测历史记录
      </p>
    </div>

    <!-- 筛选和操作工具栏 -->
    <el-card class="filter-card" shadow="never">
      <el-form :model="filterForm" :inline="true" @submit.prevent="handleSearch">
        <!-- 搜索框 -->
        <el-form-item label="搜索">
          <el-input
            v-model="filterForm.search"
            placeholder="搜索记录名称或描述"
            clearable
            style="width: 240px"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <!-- 策略筛选 -->
        <el-form-item label="策略">
          <el-select
            v-model="filterForm.strategy_id"
            clearable
            placeholder="全部策略"
            style="width: 150px"
          >
            <el-option label="双均线策略" value="dual_ma" />
            <el-option label="买入持有策略" value="buy_and_hold" />
          </el-select>
        </el-form-item>

        <!-- 股票代码筛选 -->
        <el-form-item label="股票代码">
          <el-input
            v-model="filterForm.stock_code"
            placeholder="输入股票代码"
            clearable
            style="width: 150px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>

        <!-- ✅ 新增：时间区间筛选 -->
        <el-form-item label="回测日期">
          <el-date-picker
            v-model="filterForm.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            clearable
            style="width: 240px"
          />
        </el-form-item>

        <!-- ✅ 新增：初始资金范围筛选 -->
        <el-form-item label="初始资金">
          <el-input
            v-model="filterForm.initial_capital_min"
            placeholder="最小值"
            clearable
            style="width: 100px"
            type="number"
          >
            <template #append>元</template>
          </el-input>
          <span style="margin: 0 8px">-</span>
          <el-input
            v-model="filterForm.initial_capital_max"
            placeholder="最大值"
            clearable
            style="width: 100px"
            type="number"
          >
            <template #append>元</template>
          </el-input>
        </el-form-item>

        <!-- ✅ 新增：收益率范围筛选 -->
        <el-form-item label="收益率">
          <el-input
            v-model="filterForm.return_rate_min"
            placeholder="最小值"
            clearable
            style="width: 100px"
            type="number"
            step="0.01"
          >
            <template #append>%</template>
          </el-input>
          <span style="margin: 0 8px">-</span>
          <el-input
            v-model="filterForm.return_rate_max"
            placeholder="最大值"
            clearable
            style="width: 100px"
            type="number"
            step="0.01"
          >
            <template #append>%</template>
          </el-input>
        </el-form-item>

        <!-- 查询和重置按钮 -->
        <el-form-item>
          <el-button type="primary" @click="handleSearch" :loading="historyStore.listLoading">
            <el-icon><Search /></el-icon>
            查询
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>

        <!-- 视图切换 -->
        <el-form-item style="margin-left: auto">
          <el-button
            :type="historyStore.isRecycleBinView ? 'warning' : 'default'"
            @click="handleToggleRecycleBin"
          >
            <el-icon><Delete /></el-icon>
            {{ historyStore.isRecycleBinView ? '返回列表' : '回收站' }}
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- ✅ P2-4: 历史记录上限警告 -->
    <el-alert
      v-if="historyStats && historyStats.near_limit"
      :type="historyStats.usage_percent >= 100 ? 'error' : 'warning'"
      :closable="false"
      class="limit-alert"
      show-icon
    >
      <template #title>
        <div class="alert-content">
          <span>
            历史记录即将达到上限（{{ historyStats.current_count }}/{{ historyStats.limit }}条，已使用{{ historyStats.usage_percent }}%）
          </span>
          <span style="margin-left: 16px; font-size: 13px; color: #666;">
            {{ historyStats.user_type }}上限为{{ historyStats.limit }}条，剩余{{ historyStats.remaining }}条可用
          </span>
        </div>
      </template>
    </el-alert>

    <!-- 批量操作工具栏 -->
    <el-card v-if="historyStore.hasBatchSelection" class="toolbar-card" shadow="never">
      <div class="toolbar-content">
        <div class="toolbar-left">
          <el-checkbox
            :model-value="isAllSelected"
            :indeterminate="isIndeterminate"
            @change="handleSelectAll"
          >
            全选
          </el-checkbox>
          <span class="selected-count">已选择 {{ historyStore.selectedRecords.length }} 项</span>
        </div>
        <div class="toolbar-right">
          <el-button
            :disabled="!canBatchDelete"
            @click="handleBatchDelete"
            :loading="historyStore.deleteLoading"
          >
            <el-icon><Delete /></el-icon>
            批量删除
          </el-button>
          <el-button
            v-if="historyStore.isRecycleBinView"
            :disabled="!canBatchRestore"
            @click="handleBatchRestore"
            :loading="historyStore.deleteLoading"
          >
            <el-icon><RefreshLeft /></el-icon>
            批量恢复
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 历史记录列表 -->
    <el-card class="list-card" shadow="never">
      <template #header>
        <div class="list-header">
          <h3>
            {{ historyStore.isRecycleBinView ? '🗑️ 回收站' : '📊 历史记录' }}
            ({{ historyStore.total }} 条)
          </h3>
        </div>
      </template>

      <!-- 加载状态 -->
      <div v-loading="historyStore.listLoading" element-loading-text="加载中...">
        <!-- 空状态 -->
        <el-empty
          v-if="!historyStore.hasRecords && !historyStore.listLoading"
          :description="historyStore.isRecycleBinView ? '回收站为空' : '暂无历史记录'"
        />

        <!-- 记录列表 -->
        <div v-else class="records-list">
          <el-table
            :data="historyStore.records"
            stripe
            style="width: 100%"
            @selection-change="handleSelectionChange"
          >
            <!-- 选择列 -->
            <el-table-column type="selection" width="55" />

            <!-- 记录名称 -->
            <el-table-column prop="name" label="记录名称" min-width="180">
              <template #default="{ row }">
                <div class="record-name">
                  <el-link type="primary" @click="handleViewDetail(row.record_id)">
                    {{ row.name }}
                  </el-link>
                  <div class="record-tags">
                    <el-tag
                      v-for="tag in row.tags"
                      :key="tag"
                      size="small"
                      type="info"
                    >
                      {{ tag }}
                    </el-tag>
                  </div>
                </div>
              </template>
            </el-table-column>

            <!-- 股票代码 -->
            <el-table-column prop="parameters.stock_code" label="股票代码" width="120">
              <template #default="{ row }">
                <el-tag size="small">{{ row.parameters.stock_code }}</el-tag>
              </template>
            </el-table-column>

            <!-- 策略 -->
            <el-table-column prop="parameters.strategy_id" label="策略" width="120">
              <template #default="{ row }">
                {{ getStrategyName(row.parameters.strategy_id) }}
              </template>
            </el-table-column>

            <!-- 回测期间 -->
            <el-table-column label="回测期间" width="180">
              <template #default="{ row }">
                {{ row.parameters.start_date }} 至 {{ row.parameters.end_date }}
              </template>
            </el-table-column>

            <!-- 关键指标 -->
            <el-table-column label="总收益率" width="120">
              <template #default="{ row }">
                <span
                  :class="getReturnClass(row.metrics_snapshot.total_return)"
                >
                  {{ formatPercentage(row.metrics_snapshot.total_return) }}
                </span>
              </template>
            </el-table-column>

            <el-table-column label="最大回撤" width="120">
              <template #default="{ row }">
                <span class="negative">
                  {{ formatPercentage(row.metrics_snapshot.max_drawdown) }}
                </span>
              </template>
            </el-table-column>

            <el-table-column label="夏普比率" width="100">
              <template #default="{ row }">
                <span :class="getSharpeClass(row.metrics_snapshot.sharpe_ratio)">
                  {{ row.metrics_snapshot.sharpe_ratio.toFixed(2) }}
                </span>
              </template>
            </el-table-column>

            <el-table-column label="胜率" width="100">
              <template #default="{ row }">
                {{ formatPercentage(row.metrics_snapshot.win_rate) }}
              </template>
            </el-table-column>

            <!-- 创建时间 -->
            <el-table-column prop="created_at" label="创建时间" width="160">
              <template #default="{ row }">
                {{ formatDateTime(row.created_at) }}
              </template>
            </el-table-column>

            <!-- 操作按钮 -->
            <el-table-column label="操作" width="280" fixed="right">
              <template #default="{ row }">
                <div class="action-buttons">
                  <!-- 查看详情 -->
                  <el-button
                    type="primary"
                    size="small"
                    text
                    @click="handleViewDetail(row.record_id)"
                  >
                    <el-icon><View /></el-icon>
                    详情
                  </el-button>

                  <!-- 添加到对比 -->
                  <el-button
                    v-if="!historyStore.isRecycleBinView"
                    type="success"
                    size="small"
                    text
                    @click="handleAddToCompare(row.record_id)"
                    :disabled="!canAddToCompare"
                  >
                    <el-icon><Plus /></el-icon>
                    对比
                  </el-button>

                  <!-- 导出 -->
                  <el-dropdown @command="(format) => handleExport(row.record_id, format)">
                    <el-button type="info" size="small" text :loading="historyStore.exportLoading">
                      <el-icon><Download /></el-icon>
                      导出
                      <el-icon class="el-icon--right"><arrow-down /></el-icon>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="json">JSON</el-dropdown-item>
                        <el-dropdown-item command="excel">Excel</el-dropdown-item>
                        <el-dropdown-item command="pdf">PDF</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>

                  <!-- 删除/恢复 -->
                  <el-button
                    v-if="!historyStore.isRecycleBinView"
                    type="danger"
                    size="small"
                    text
                    @click="handleDelete(row.record_id, row.name)"
                    :loading="historyStore.deleteLoading"
                  >
                    <el-icon><Delete /></el-icon>
                    删除
                  </el-button>
                  <el-button
                    v-else
                    type="success"
                    size="small"
                    text
                    @click="handleRestore(row.record_id)"
                    :loading="historyStore.deleteLoading"
                  >
                    <el-icon><RefreshLeft /></el-icon>
                    恢复
                  </el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>

          <!-- 加载更多 -->
          <div v-if="historyStore.records.length > 0 && historyStore.records.length < historyStore.total" class="load-more">
            <el-button @click="handleLoadMore" :loading="historyStore.listLoading">
              加载更多 (剩余 {{ historyStore.total - historyStore.records.length }} 条)
            </el-button>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 对比栏 -->
    <el-card v-if="historyStore.compareRecordIds.length > 0" class="compare-bar" shadow="always">
      <div class="compare-bar-content">
        <div class="compare-bar-left">
          <span class="compare-label">已选择 {{ historyStore.compareRecordIds.length }} 条记录进行对比</span>
          <el-tag
            v-for="recordId in historyStore.compareRecordIds"
            :key="recordId"
            closable
            @close="handleRemoveFromCompare(recordId)"
            style="margin-left: 8px"
          >
            {{ getRecordName(recordId) }}
          </el-tag>
        </div>
        <div class="compare-bar-right">
          <el-button @click="handleClearCompare">清空</el-button>
          <el-button
            type="primary"
            :disabled="!historyStore.canCompare"
            @click="handleCompare"
            :loading="historyStore.compareLoading"
          >
            <el-icon><TrendCharts /></el-icon>
            开始对比
          </el-button>
        </div>
      </div>
    </el-card>

    <!-- 对比结果对话框 -->
    <el-dialog
      v-model="compareDialogVisible"
      title="回测结果对比"
      width="90%"
      top="5vh"
    >
      <div v-loading="historyStore.compareLoading">
        <div v-if="historyStore.compareResults" class="compare-results">
          <!-- 对比表格 -->
          <el-table :data="historyStore.compareResults.records" border>
            <el-table-column prop="name" label="记录名称" width="200" fixed="left" />
            <el-table-column label="股票代码" width="120">
              <template #default="{ row }">
                {{ row.parameters.stock_code }}
              </template>
            </el-table-column>
            <el-table-column label="策略" width="120">
              <template #default="{ row }">
                {{ getStrategyName(row.parameters.strategy_id) }}
              </template>
            </el-table-column>
            <el-table-column label="总收益率" width="120">
              <template #default="{ row }">
                <span :class="getReturnClass(row.metrics_snapshot.total_return)">
                  {{ formatPercentage(row.metrics_snapshot.total_return) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="最大回撤" width="120">
              <template #default="{ row }">
                <span class="negative">
                  {{ formatPercentage(row.metrics_snapshot.max_drawdown) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="夏普比率" width="100">
              <template #default="{ row }">
                <span :class="getSharpeClass(row.metrics_snapshot.sharpe_ratio)">
                  {{ row.metrics_snapshot.sharpe_ratio.toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="胜率" width="100">
              <template #default="{ row }">
                {{ formatPercentage(row.metrics_snapshot.win_rate) }}
              </template>
            </el-table-column>
            <el-table-column label="交易次数" width="100">
              <template #default="{ row }">
                {{ row.metrics_snapshot.total_trades }}
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      :title="currentRecord?.name || '历史记录详情'"
      width="80%"
      top="5vh"
    >
      <div v-loading="historyStore.detailLoading">
        <div v-if="historyStore.recordDetail" class="record-detail">
          <!-- 基本信息 -->
          <el-descriptions title="基本信息" :column="2" border>
            <el-descriptions-item label="记录名称">
              {{ historyStore.recordDetail.history.name }}
            </el-descriptions-item>
            <el-descriptions-item label="描述">
              {{ historyStore.recordDetail.history.description || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="股票代码">
              {{ historyStore.recordDetail.history.parameters.stock_code }}
            </el-descriptions-item>
            <el-descriptions-item label="策略">
              {{ getStrategyName(historyStore.recordDetail.history.parameters.strategy_id) }}
            </el-descriptions-item>
            <el-descriptions-item label="回测期间">
              {{ historyStore.recordDetail.history.parameters.start_date }} 至
              {{ historyStore.recordDetail.history.parameters.end_date }}
            </el-descriptions-item>
            <el-descriptions-item label="初始资金">
              ¥{{ historyStore.recordDetail.history.parameters.initial_capital?.toLocaleString() || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatDateTime(historyStore.recordDetail.history.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="标签">
              <el-tag
                v-for="tag in historyStore.recordDetail.history.tags"
                :key="tag"
                size="small"
                type="info"
                style="margin-right: 8px"
              >
                {{ tag }}
              </el-tag>
              <span v-if="!historyStore.recordDetail.history.tags?.length">-</span>
            </el-descriptions-item>
          </el-descriptions>

          <!-- 回测结果 -->
          <BacktestResults
            v-if="historyStore.recordDetail.results"
            :backtest-id="historyStore.recordDetail.history.backtest_id"
            style="margin-top: 20px"
          />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Clock,
  Search,
  Refresh,
  Delete,
  RefreshLeft,
  View,
  Plus,
  Download,
  TrendCharts,
  ArrowDown
} from '@element-plus/icons-vue'
import { useBacktestHistoryStore } from '@/stores/backtestHistory'
import { formatDateTime } from '@/utils/datetime'
import BacktestResults from '@/components/BacktestResults.vue'

// Store
const historyStore = useBacktestHistoryStore()

// ✅ P2-4: 历史记录统计信息
const historyStats = ref<{
  current_count: number
  limit: number
  remaining: number
  usage_percent: number
  near_limit: boolean
  is_admin: boolean
  user_type: string
} | null>(null)

// 筛选表单
const filterForm = ref({
  search: '',
  strategy_id: '',
  stock_code: '',
  dateRange: null as [string, string] | null,  // ✅ 新增：时间区间
  initial_capital_min: '',  // ✅ 新增：最小初始资金
  initial_capital_max: '',  // ✅ 新增：最大初始资金
  return_rate_min: '',      // ✅ 新增：最小收益率
  return_rate_max: ''       // ✅ 新增：最大收益率
})

// 对话框状态
const compareDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const currentRecord = ref<any>(null)

// 计算属性
const isAllSelected = computed(() => {
  return (
    historyStore.records.length > 0 &&
    historyStore.selectedRecords.length === historyStore.records.length
  )
})

const isIndeterminate = computed(() => {
  const selected = historyStore.selectedRecords.length
  const total = historyStore.records.length
  return selected > 0 && selected < total
})

const canAddToCompare = computed(() => {
  return historyStore.compareRecordIds.length < 3
})

const canBatchDelete = computed(() => {
  return historyStore.selectedRecords.length > 0
})

const canBatchRestore = computed(() => {
  return historyStore.selectedRecords.length > 0 && historyStore.isRecycleBinView
})

// 查询历史记录
const handleSearch = async () => {
  // 处理dateRange转换为start_date和end_date
  const filtersToUpdate = {
    ...filterForm.value,
    start_date: filterForm.value.dateRange?.[0] || '',
    end_date: filterForm.value.dateRange?.[1] || ''
  }
  delete filtersToUpdate.dateRange  // 移除dateRange字段

  historyStore.updateFilters(filtersToUpdate)
  await historyStore.fetchHistoryList(true)
}

// 重置筛选
const handleReset = async () => {
  filterForm.value = {
    search: '',
    strategy_id: '',
    stock_code: '',
    dateRange: null,
    initial_capital_min: '',
    initial_capital_max: '',
    return_rate_min: '',
    return_rate_max: ''
  }
  historyStore.resetFilters()
  await historyStore.fetchHistoryList(true)
}

// ✅ P2-4: 获取历史记录统计信息
const fetchHistoryStats = async () => {
  try {
    const response = await fetch('/api/backtest/history/stats', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    })
    if (response.ok) {
      const result = await response.json()
      if (result.success) {
        historyStats.value = result.data
      }
    }
  } catch (error) {
    console.error('获取历史记录统计失败:', error)
  }
}

// 切换回收站视图
const handleToggleRecycleBin = async () => {
  const show = !historyStore.isRecycleBinView
  await historyStore.toggleRecycleBin(show)
  ElMessage.success(show ? '已切换到回收站' : '已返回列表')
}

// 加载更多
const handleLoadMore = async () => {
  await historyStore.loadMore()
}

// 选择变化
const handleSelectionChange = (selection: any[]) => {
  // 清空旧选择
  historyStore.selectedRecords = []
  // 添加新选择
  selection.forEach(item => {
    historyStore.toggleRecordSelection(item.record_id)
  })
}

// 全选/取消全选
const handleSelectAll = () => {
  historyStore.toggleSelectAll()
}

// 批量删除
const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${historyStore.selectedRecords.length} 条记录吗？${historyStore.isRecycleBinView ? '此操作将永久删除这些记录！' : '记录将移至回收站。'}`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
        distinguishCancelAndClose: true
      }
    )

    const permanent = historyStore.isRecycleBinView
    await historyStore.batchDelete(historyStore.selectedRecords, permanent)
  } catch {
    // 用户取消
  }
}

// 批量恢复
const handleBatchRestore = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要恢复选中的 ${historyStore.selectedRecords.length} 条记录吗？`,
      '确认恢复',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    for (const recordId of historyStore.selectedRecords) {
      await historyStore.restoreHistory(recordId)
    }
  } catch {
    // 用户取消
  }
}

// 查看详情
const handleViewDetail = async (recordId: string) => {
  detailDialogVisible.value = true
  currentRecord.value = historyStore.records.find(r => r.record_id === recordId)
  await historyStore.fetchHistoryDetail(recordId)
}

// 添加到对比
const handleAddToCompare = (recordId: string) => {
  historyStore.addToCompare(recordId)
}

// 从对比列表移除
const handleRemoveFromCompare = (recordId: string) => {
  historyStore.removeFromCompare(recordId)
}

// 清空对比列表
const handleClearCompare = () => {
  historyStore.clearCompare()
}

// 开始对比
const handleCompare = async () => {
  if (!historyStore.canCompare) {
    ElMessage.warning('请选择2-3条记录进行对比')
    return
  }

  await historyStore.compareHistory()
  if (historyStore.compareResults) {
    compareDialogVisible.value = true
  }
}

// 导出
const handleExport = async (recordId: string, format: 'json' | 'excel' | 'pdf') => {
  try {
    await historyStore.exportHistory(recordId, format)
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

// 删除
const handleDelete = async (recordId: string, name: string) => {
  try {
    await ElMessageBox.confirm(
      `确定要将 "${name}" 移至回收站吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await historyStore.deleteHistory(recordId, false)
  } catch {
    // 用户取消
  }
}

// 恢复
const handleRestore = async (recordId: string) => {
  try {
    await ElMessageBox.confirm(
      '确定要恢复此记录吗？',
      '确认恢复',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'info'
      }
    )

    await historyStore.restoreHistory(recordId)
  } catch {
    // 用户取消
  }
}

// 获取策略名称
const getStrategyName = (strategyId: string) => {
  const strategyMap: Record<string, string> = {
    dual_ma: '双均线策略',
    buy_and_hold: '买入持有策略'
  }
  return strategyMap[strategyId] || strategyId
}

// 获取记录名称
const getRecordName = (recordId: string) => {
  const record = historyStore.records.find(r => r.record_id === recordId)
  return record?.name || recordId
}

// 格式化百分比
const formatPercentage = (value: number) => {
  return (value * 100).toFixed(2) + '%'
}

// 获取收益率样式类
const getReturnClass = (value: number) => {
  return value >= 0 ? 'positive' : 'negative'
}

// 获取夏普比率样式类
const getSharpeClass = (value: number) => {
  if (value >= 1) return 'positive'
  if (value >= 0) return 'neutral'
  return 'negative'
}

// 初始化
onMounted(async () => {
  await historyStore.fetchHistoryList(true)
  // ✅ P2-4: 加载历史记录统计信息
  await fetchHistoryStats()
})
</script>

<style scoped lang="scss">
.backtest-history {
  padding: 20px;

  .page-header {
    margin-bottom: 24px;

    .page-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 24px;
      font-weight: 600;
      color: var(--el-text-color-primary);
      margin: 0 0 8px 0;
    }

    .page-description {
      color: var(--el-text-color-regular);
      margin: 0;
    }
  }

  .filter-card {
    margin-bottom: 20px;
  }

  // ✅ P2-4: 上限警告样式
  .limit-alert {
    margin-bottom: 20px;

    .alert-content {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
    }
  }

  .toolbar-card {
    margin-bottom: 20px;

    .toolbar-content {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .toolbar-left {
        display: flex;
        align-items: center;
        gap: 16px;

        .selected-count {
          color: var(--el-text-color-regular);
          font-size: 14px;
        }
      }

      .toolbar-right {
        display: flex;
        gap: 8px;
      }
    }
  }

  .list-card {
    .list-header {
      h3 {
        margin: 0;
        font-size: 16px;
        font-weight: 600;
      }
    }

    .records-list {
      .record-name {
        .record-tags {
          margin-top: 4px;
          display: flex;
          gap: 4px;
          flex-wrap: wrap;
        }
      }

      .action-buttons {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }

      .load-more {
        margin-top: 20px;
        text-align: center;
      }
    }
  }

  .compare-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 1000;
    border-radius: 0;
    box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.1);

    .compare-bar-content {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .compare-bar-left {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;

        .compare-label {
          font-weight: 500;
          color: var(--el-text-color-primary);
        }
      }

      .compare-bar-right {
        display: flex;
        gap: 8px;
      }
    }
  }

  .compare-results {
    .el-table {
      margin-top: 16px;
    }
  }

  .record-detail {
    .el-descriptions {
      margin-bottom: 20px;
    }
  }

  // 指标数值样式
  .positive {
    color: #67c23a;
    font-weight: 500;
  }

  .negative {
    color: #f56c6c;
    font-weight: 500;
  }

  .neutral {
    color: #909399;
    font-weight: 500;
  }
}
</style>
