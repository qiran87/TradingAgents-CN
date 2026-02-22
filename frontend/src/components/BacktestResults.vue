<template>
  <div class="backtest-results">
    <!-- 错误边界 -->
    <el-alert
      v-if="error"
      title="加载失败"
      type="error"
      :description="error"
      show-icon
      @close="error = ''"
      style="margin-bottom: 20px"
    />

    <el-card v-loading="loading" element-loading-text="加载中...">
      <!-- 头部信息 -->
      <template #header>
        <div class="header">
          <span class="title">回测结果分析</span>
          <div class="header-actions">
            <el-tag v-if="results" type="success">
              {{ formatPercentage(results.return_metrics.total_return) }}
            </el-tag>
            <!-- 导出按钮组 -->
            <el-button-group v-if="results" style="margin-left: 12px">
              <el-button
                type="primary"
                :loading="excelExportLoading"
                @click="handleExportExcel"
                size="small"
              >
                <el-icon><Download /></el-icon>
                导出Excel
              </el-button>
              <el-dropdown @command="handleExportCharts" size="small">
                <el-button type="success">
                  <el-icon><Picture /></el-icon>
                  导出图表
                  <el-icon class="el-icon--right"><arrow-down /></el-icon>
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="equity">资金曲线图</el-dropdown-item>
                    <el-dropdown-item command="drawdown">回撤图</el-dropdown-item>
                    <el-dropdown-item command="all">全部图表</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </el-button-group>
          </div>
        </div>
      </template>

      <!-- 空状态 -->
      <el-empty v-if="!results && !loading && !error" description="暂无回测结果" />

      <!-- 结果内容 -->
      <div v-if="results" class="results-content">
        <!-- 关键指标卡片 -->
        <el-row :gutter="20" class="metrics-section">
          <!-- 收益指标 -->
          <el-col :span="8">
            <el-card shadow="hover" class="metric-card">
              <template #header>
                <div class="card-header">
                  <el-icon><TrendCharts /></el-icon>
                  <span>收益指标</span>
                </div>
              </template>
              <div class="metric-list">
                <div class="metric-item">
                  <span class="label">总收益率</span>
                  <span class="value" :class="getReturnClass(results.return_metrics.total_return)">
                    {{ formatPercentage(results.return_metrics.total_return) }}
                  </span>
                </div>
                <div class="metric-item">
                  <span class="label">年化收益率</span>
                  <span class="value" :class="getReturnClass(results.return_metrics.annual_return)">
                    {{ formatPercentage(results.return_metrics.annual_return) }}
                  </span>
                </div>
              </div>
            </el-card>
          </el-col>

          <!-- 风险指标 -->
          <el-col :span="8">
            <el-card shadow="hover" class="metric-card">
              <template #header>
                <div class="card-header">
                  <el-icon><Warning /></el-icon>
                  <span>风险指标</span>
                </div>
              </template>
              <div class="metric-list">
                <div class="metric-item">
                  <span class="label">最大回撤</span>
                  <span class="value negative">
                    {{ formatPercentage(results.risk_metrics.max_drawdown) }}
                  </span>
                </div>
                <div class="metric-item">
                  <span class="label">波动率</span>
                  <span class="value">
                    {{ formatPercentage(results.risk_metrics.volatility) }}
                  </span>
                </div>
                <div class="metric-item">
                  <span class="label">VaR 95%</span>
                  <span class="value negative">
                    {{ formatPercentage(results.risk_metrics.var_95) }}
                  </span>
                </div>
              </div>
            </el-card>
          </el-col>

          <!-- 风险调整收益 -->
          <el-col :span="8">
            <el-card shadow="hover" class="metric-card">
              <template #header>
                <div class="card-header">
                  <el-icon><DataAnalysis /></el-icon>
                  <span>风险调整收益</span>
                </div>
              </template>
              <div class="metric-list">
                <div class="metric-item">
                  <span class="label">夏普比率</span>
                  <span class="value" :class="getSharpeClass(results.risk_adjusted_metrics.sharpe_ratio)">
                    {{ results.risk_adjusted_metrics.sharpe_ratio.toFixed(2) }}
                  </span>
                </div>
                <div class="metric-item">
                  <span class="label">索提诺比率</span>
                  <span class="value">
                    {{ results.risk_adjusted_metrics.sortino_ratio.toFixed(2) }}
                  </span>
                </div>
                <div class="metric-item">
                  <span class="label">卡玛比率</span>
                  <span class="value">
                    {{ results.risk_adjusted_metrics.calmar_ratio.toFixed(2) }}
                  </span>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 交易统计 -->
        <el-card shadow="hover" class="trading-stats-card">
          <template #header>
            <div class="card-header">
              <el-icon><List /></el-icon>
              <span>交易统计</span>
            </div>
          </template>
          <el-row :gutter="20">
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value">{{ results.trading_stats.total_trades }}</div>
                <div class="stat-label">总交易次数</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value success">{{ results.trading_stats.winning_trades }}</div>
                <div class="stat-label">盈利交易</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value danger">{{ results.trading_stats.losing_trades }}</div>
                <div class="stat-label">亏损交易</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item">
                <div class="stat-value" :class="getWinRateClass(results.trading_stats.win_rate)">
                  {{ formatPercentage(results.trading_stats.win_rate) }}
                </div>
                <div class="stat-label">胜率</div>
              </div>
            </el-col>
          </el-row>
          <el-divider />
          <el-row :gutter="20">
            <el-col :span="8">
              <div class="stat-item">
                <div class="stat-value success">¥{{ results.trading_stats.avg_profit.toFixed(2) }}</div>
                <div class="stat-label">平均盈利</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-item">
                <div class="stat-value danger">¥{{ results.trading_stats.avg_loss.toFixed(2) }}</div>
                <div class="stat-label">平均亏损</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-item">
                <div class="stat-value">{{ results.trading_stats.profit_loss_ratio.toFixed(2) }}</div>
                <div class="stat-label">盈亏比</div>
              </div>
            </el-col>
          </el-row>
        </el-card>

        <!-- 资金曲线图表 -->
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <el-icon><TrendCharts /></el-icon>
              <span>资金曲线</span>
            </div>
          </template>
          <div v-if="chartError" class="chart-error">
            <el-empty description="图表加载失败，请刷新页面重试" />
          </div>
          <div v-else ref="chartRef" class="chart-container"></div>
        </el-card>

        <!-- MDVAES 估值图表 (仅 MDVAES 策略显示) -->
        <template v-if="isMDVAESStrategy">
          <el-divider content-position="left">
            <span style="font-size: 16px; font-weight: 600;">MDVAES 估值分析</span>
          </el-divider>

          <!-- 调试信息 -->
          <el-alert type="info" :closable="false" style="margin-bottom: 10px">
            <div><strong>调试信息:</strong></div>
            <div>isMDVAESStrategy: {{ isMDVAESStrategy }}</div>
            <div>valuationHistory.length: {{ valuationHistory.length }}</div>
            <div>backtestId: {{ props.backtestId }}</div>
            <div v-if="valuationHistory.length > 0">
              <div>第一条数据: {{ JSON.stringify(valuationHistory[0]) }}</div>
            </div>
            <div v-else style="color: red;">
              <strong>⚠️ valuationHistory 为空！</strong>
            </div>
          </el-alert>

          <!-- 估值推演图和水位仪表盘 -->
          <el-row :gutter="20">
            <el-col :span="16">
              <el-card shadow="hover" class="chart-card">
                <template #header>
                  <div class="card-header">
                    <el-icon><TrendCharts /></el-icon>
                    <span>估值推演图</span>
                  </div>
                </template>
                <ValuationProjectionChart :data="valuationHistory" />
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="hover" class="chart-card">
                <template #header>
                  <div class="card-header">
                    <el-icon><DataAnalysis /></el-icon>
                    <span>估值水位</span>
                  </div>
                </template>
                <WaterLevelGauge
                  v-if="valuationHistory.length > 0"
                  :current-price="valuationHistory[valuationHistory.length - 1].current_price"
                  :intrinsic-value="valuationHistory[valuationHistory.length - 1].intrinsic_value"
                  :lower-bound="valuationHistory[valuationHistory.length - 1].lower_bound"
                  :upper-bound="valuationHistory[valuationHistory.length - 1].upper_bound"
                />
              </el-card>
            </el-col>
          </el-row>

          <!-- EPS 趋势图 -->
          <el-row :gutter="20">
            <el-col :span="24">
              <el-card shadow="hover" class="chart-card">
                <template #header>
                  <div class="card-header">
                    <el-icon><TrendCharts /></el-icon>
                    <span>EPS 趋势分析</span>
                  </div>
                </template>
                <EPSTrendChart :data="epsTrendData" />
              </el-card>
            </el-col>
          </el-row>
        </template>

        <!-- 交易明细 -->
        <el-card shadow="hover" class="trades-card">
          <template #header>
            <div class="card-header">
              <el-icon><Document /></el-icon>
              <span>交易明细 ({{ trades.length }} 笔)</span>
              <el-button text type="primary" @click="loadTrades">
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </div>
          </template>
          <el-table
            :data="paginatedTrades"
            stripe
            max-height="450"
            v-loading="tradesLoading"
            style="width: 100%"
          >
            <el-table-column prop="date" label="日期" width="110" fixed />
            <el-table-column label="类型" width="70" fixed>
              <template #default="{ row }">
                <el-tag :type="row.trade_type === 'buy' ? 'success' : 'danger'" size="small">
                  {{ row.trade_type === 'buy' ? '买入' : '卖出' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="stock_code" label="股票代码" width="110" />
            <el-table-column prop="stock_name" label="股票名称" width="120" />
            <el-table-column prop="price" label="成交价" width="90">
              <template #default="{ row }">
                ¥{{ row.price.toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column prop="shares" label="数量" width="80" />
            <el-table-column prop="amount" label="成交额" width="110">
              <template #default="{ row }">
                ¥{{ row.amount.toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column label="佣金" width="90">
              <template #default="{ row }">
                ¥{{ (row.commission || 0).toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column label="印花税" width="90">
              <template #default="{ row }">
                ¥{{ (row.stamp_duty || 0).toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column prop="cash_before" label="交易前现金" width="120">
              <template #default="{ row }">
                ¥{{ row.cash_before.toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column prop="position_before" label="交易前持仓" width="100" />
            <el-table-column label="盈亏金额" width="110">
              <template #default="{ row }">
                <span :style="{ color: getProfitLossColor(row.profit_loss, row.trade_type) }">
                  {{ row.trade_type === 'buy' ? '-' : (row.profit_loss >= 0 ? '+' : '') }}¥{{ (row.profit_loss || 0).toFixed(2) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="cash_after" label="交易后现金" width="120">
              <template #default="{ row }">
                ¥{{ row.cash_after.toFixed(2) }}
              </template>
            </el-table-column>
            <el-table-column prop="position_after" label="交易后持仓" width="100" />
            <el-table-column label="决策详情" min-width="250" fixed="right">
              <template #default="{ row }">
                <div v-if="row.signal && row.signal.reason" class="decision-reason">
                  {{ row.signal.reason }}
                </div>
                <div v-if="row.signal && row.signal.metadata" class="decision-metadata">
                  <el-popover
                    placement="left"
                    :width="400"
                    trigger="click"
                  >
                    <template #reference>
                      <el-button size="small" text type="primary">
                        <el-icon><InfoFilled /></el-icon>
                        详细参数
                      </el-button>
                    </template>
                    <div class="metadata-detail">
                      <div class="metadata-item">
                        <span class="metadata-label">内在价值:</span>
                        <span class="metadata-value">¥{{ formatNumber(row.signal.metadata.intrinsic_value) }}</span>
                      </div>
                      <div class="metadata-item">
                        <span class="metadata-label">估值下限:</span>
                        <span class="metadata-value">¥{{ formatNumber(row.signal.metadata.lower_bound) }}</span>
                      </div>
                      <div class="metadata-item">
                        <span class="metadata-label">估值上限:</span>
                        <span class="metadata-value">¥{{ formatNumber(row.signal.metadata.upper_bound) }}</span>
                      </div>
                      <div class="metadata-item">
                        <span class="metadata-label">置信度:</span>
                        <span class="metadata-value">{{ (row.signal.metadata.confidence * 100).toFixed(1) }}%</span>
                      </div>
                      <div v-if="row.signal.metadata.eps !== undefined" class="metadata-item">
                        <span class="metadata-label">EPS预测:</span>
                        <span class="metadata-value">¥{{ formatNumber(row.signal.metadata.eps) }}</span>
                      </div>
                      <el-divider style="margin: 8px 0;" />
                      <div class="metadata-title">各估值方法结果:</div>
                      <div v-if="row.signal.metadata.peg_value !== undefined" class="metadata-item">
                        <span class="metadata-label">PEG估值:</span>
                        <span class="metadata-value">¥{{ formatNumber(row.signal.metadata.peg_value) }}</span>
                      </div>
                      <div v-if="row.signal.metadata.pe_value !== undefined" class="metadata-item">
                        <span class="metadata-label">PE估值:</span>
                        <span class="metadata-value">¥{{ formatNumber(row.signal.metadata.pe_value) }}</span>
                      </div>
                      <div v-if="row.signal.metadata.pb_value !== undefined" class="metadata-item">
                        <span class="metadata-label">PB估值:</span>
                        <span class="metadata-value">¥{{ formatNumber(row.signal.metadata.pb_value) }}</span>
                      </div>
                      <div v-if="row.signal.metadata.dcf_value !== undefined" class="metadata-item">
                        <span class="metadata-label">DCF估值:</span>
                        <span class="metadata-value">¥{{ formatNumber(row.signal.metadata.dcf_value) }}</span>
                      </div>
                    </div>
                  </el-popover>
                </div>
                <div v-else class="no-decision-info">-</div>
              </template>
            </el-table-column>
          </el-table>

          <!-- 分页 -->
          <div class="pagination-container" v-if="trades.length > 0">
            <el-pagination
              v-model:current-page="currentPage"
              v-model:page-size="pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="trades.length"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="loadTrades"
              @current-change="handlePageChange"
            />
          </div>
        </el-card>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import {
  TrendCharts,
  Warning,
  DataAnalysis,
  List,
  Document,
  Refresh,
  Download,
  Picture,
  ArrowDown,
  InfoFilled
} from '@element-plus/icons-vue'
import { backtestEngineApi, type BacktestResults, type TradeRecord, type ValuationHistoryDataPoint } from '@/api/backtestEngine'
import { backtestExportApi, chartExportUtils } from '@/api/backtestExport'
import ValuationProjectionChart from '@/components/MDVAES/ValuationProjectionChart.vue'
import WaterLevelGauge from '@/components/MDVAES/WaterLevelGauge.vue'
import EPSTrendChart from '@/components/MDVAES/EPSTrendChart.vue'

interface Props {
  backtestId: string
}

const props = defineProps<Props>()

// 状态
const loading = ref(false)
const results = ref<BacktestResults | null>(null)
const trades = ref<TradeRecord[]>([])
const tradesLoading = ref(false)
const error = ref('')
const chartRef = ref<HTMLElement>()
const chartError = ref(false)
const excelExportLoading = ref(false)

// MDVAES 估值相关状态
const valuationHistory = ref<any[]>([])
const valuationLoading = ref(false)
const isMDVAESStrategy = ref(false)

// 从估值历史获取 EPS 趋势数据
// 注意：这是回测估值时使用的"预测 EPS"，不是历史财报 EPS
// 数据来源：
//   1. mdvaes_eps_history 表存储历史财报 EPS
//   2. 通过 CAGR 外推或分析师预测得到未来 EPS
//   3. 回测时使用 eps_forecasts[0]（第1年预测）作为估值假设
// 展示这个 EPS 可以让用户了解估值计算时使用的盈利假设
const epsTrendData = computed(() => {
  if (!valuationHistory.value || valuationHistory.value.length === 0) {
    return []
  }

  // 调试：检查 EPS 数据
  const validEpsCount = valuationHistory.value.filter(r => r.eps && r.eps !== 0).length
  const undefinedEpsCount = valuationHistory.value.filter(r => !r.eps).length
  const zeroEpsCount = valuationHistory.value.filter(r => r.eps === 0).length
  console.log(`[epsTrendData] 总记录数: ${valuationHistory.value.length}, 有效EPS: ${validEpsCount}, undefined: ${undefinedEpsCount}, 零值: ${zeroEpsCount}`)

  // 按月份分组，每月取最后一个交易日的数据
  const monthlyData: Record<string, { eps: number; date: string }> = {}

  valuationHistory.value.forEach((record) => {
    // 使用回测阶段存储的估值预测 EPS
    // 放宽过滤条件：只要 eps 存在且不为 null/undefined 就使用（允许 0 或负值）
    if (record.eps === null || record.eps === undefined) {
      return
    }

    const date = new Date(record.date)
    const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`

    // 使用每月最后一个数据点
    monthlyData[monthKey] = {
      eps: record.eps,
      date: record.date
    }
  })

  console.log(`[epsTrendData] 月度数据点数: ${Object.keys(monthlyData).length}`)

  // 如果没有数据，返回空数组
  if (Object.keys(monthlyData).length === 0) {
    console.warn(`[epsTrendData] ⚠️ 没有有效的 EPS 数据可显示`)
    return []
  }

  // 转换为数组并按日期排序
  return Object.entries(monthlyData)
    .map(([monthKey, data]) => {
      const [year, month] = monthKey.split('-').map(Number)
      return {
        year: year * 100 + month,
        month: monthKey,
        eps: data.eps
      }
    })
    .sort((a, b) => a.year - b.year)
    .map(item => ({
      year: item.month,
      eps: item.eps
    }))
})

// 交易明细分页
const currentPage = ref(1)
const pageSize = ref(20)
let chartInstance: echarts.ECharts | null = null

// 加载回测结果
const loadResults = async () => {
  if (!props.backtestId) return

  loading.value = true
  error.value = ''
  try {
    console.log('[BacktestResults] Loading results for backtestId:', props.backtestId)
    const response = await backtestEngineApi.getBacktestResults(props.backtestId)
    console.log('[BacktestResults] Response:', response)
    if (response.success) {
      results.value = response.data
      // 检查是否为 MDVAES 策略
      isMDVAESStrategy.value = response.data.strategy_id === 'mdvaes'
      console.log('[BacktestResults] strategy_id:', response.data.strategy_id, 'isMDVAES:', isMDVAESStrategy.value)
      await nextTick()
      await initChart()
      // 如果是 MDVAES 策略，加载估值历史
      if (isMDVAESStrategy.value) {
        console.log('[BacktestResults] Loading valuation history...')
        await loadValuationHistory()
      } else {
        console.log('[BacktestResults] Not MDVAES strategy, skipping valuation history')
      }
    } else {
      error.value = response.message || '获取回测结果失败'
      ElMessage.error(error.value)
    }
  } catch (err: any) {
    error.value = err.response?.data?.detail || err.message || '获取回测结果失败'
    ElMessage.error(error.value)
    console.error('加载回测结果失败:', err)
  } finally {
    loading.value = false
  }
}

// 加载估值历史数据
const loadValuationHistory = async () => {
  if (!props.backtestId || !isMDVAESStrategy.value) {
    console.log('[loadValuationHistory] Skipped - backtestId:', props.backtestId, 'isMDVAES:', isMDVAESStrategy.value)
    return
  }

  valuationLoading.value = true
  try {
    console.log('[loadValuationHistory] Fetching valuation history for:', props.backtestId)
    console.log('[loadValuationHistory] API URL:', `/api/backtest/${props.backtestId}/valuation-history`)

    const response = await backtestEngineApi.getValuationHistory(props.backtestId)

    console.log('[loadValuationHistory] ===== Full API Response =====')
    console.log('[loadValuationHistory] response:', response)
    console.log('[loadValuationHistory] response.success:', response.success)
    console.log('[loadValuationHistory] response.data:', response.data)
    console.log('[loadValuationHistory] response.data type:', typeof response.data)
    console.log('[loadValuationHistory] response.data.valuation_history:', response.data?.valuation_history)
    console.log('[loadValuationHistory] response.data.valuation_history type:', typeof response.data?.valuation_history)

    if (response.success && response.data) {
      valuationHistory.value = response.data.valuation_history || []
      console.log('[loadValuationHistory] ✅ Loaded', valuationHistory.value.length, 'valuation records')
      if (valuationHistory.value.length > 0) {
        console.log('[loadValuationHistory] First record:', valuationHistory.value[0])
      }
    } else {
      console.warn('[loadValuationHistory] ❌ Failed - response.success:', response.success)
      console.warn('[loadValuationHistory] ❌ Failed - response.data:', response.data)
      console.warn('[loadValuationHistory] ❌ Failed - response.message:', response.message)
    }
  } catch (err: any) {
    console.error('[loadValuationHistory] ❌❌ Error:', err)
    console.error('[loadValuationHistory] ❌❌ Error response:', err.response?.data)
    console.error('[loadValuationHistory] ❌❌ Error status:', err.response?.status)
    // 不显示错误提示，因为这是可选功能
  } finally {
    valuationLoading.value = false
  }
}

// 加载交易明细
const loadTrades = async () => {
  if (!props.backtestId) return

  tradesLoading.value = true
  try {
    // 使用分页参数 - 修正参数顺序
    const response = await backtestEngineApi.getBacktestTrades(
      props.backtestId,
      1,  // page = 1 (第一页)
      pageSize.value * 3  // pageSize 获取更多数据以支持分页
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

// 处理分页变化
const handlePageChange = (page: number) => {
  currentPage.value = page
  // 滚动到交易明细区域
  const tradesCard = document.querySelector('.trades-card')
  if (tradesCard) {
    tradesCard.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// 获取盈亏金额显示颜色
const getProfitLossColor = (profitLoss: number, tradeType: string) => {
  if (tradeType === 'buy') {
    return '#999' // 买入时显示灰色
  }
  if (profitLoss > 0) {
    return '#67C23A' // 盈利显示绿色
  } else if (profitLoss < 0) {
    return '#F56C6C' // 亏损显示红色
  } else {
    return '#999' // 不盈不亏显示灰色
  }
}

// 获取当前页的交易记录
const paginatedTrades = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return trades.value.slice(start, end)
})

// 初始化图表
const initChart = async () => {
  if (!chartRef.value || !results.value) return

  chartError.value = false

  try {
    // 销毁旧实例
    if (chartInstance) {
      chartInstance.dispose()
    }

    // 创建新实例
    chartInstance = echarts.init(chartRef.value)

    const equityCurve = results.value.equity_curve

    const option: echarts.EChartsOption = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        }
      },
      legend: {
        data: ['总资产', '现金', '持仓市值'],
        top: 10
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: equityCurve.dates,
        axisLabel: {
          rotate: 45,
          formatter: (value: string) => {
            // 只显示月-日
            const parts = value.split('-')
            return `${parts[1]}-${parts[2]}`
          }
        }
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: (value: number) => {
            return '¥' + value.toFixed(0)
          }
        }
      },
      series: [
        {
          name: '总资产',
          type: 'line',
          data: equityCurve.total_assets,
          smooth: true,
          lineStyle: {
            width: 2
          },
          itemStyle: {
            color: '#409EFF'
          }
        },
        {
          name: '现金',
          type: 'line',
          data: equityCurve.cash,
          smooth: true,
          lineStyle: {
            width: 1,
            type: 'dashed'
          },
          itemStyle: {
            color: '#67C23A'
          }
        },
        {
          name: '持仓市值',
          type: 'line',
          data: equityCurve.position_value,
          smooth: true,
          lineStyle: {
            width: 1,
            type: 'dashed'
          },
          itemStyle: {
            color: '#E6A23C'
          }
        }
      ]
    }

    chartInstance.setOption(option)
  } catch (err) {
    console.error('初始化图表失败:', err)
    chartError.value = true
    ElMessage.warning('资金曲线图表加载失败，但不影响其他功能')
  }
}

// 格式化百分比
const formatPercentage = (value: number) => {
  return (value * 100).toFixed(2) + '%'
}

// 格式化数字（保留2位小数）
const formatNumber = (value: number | undefined) => {
  if (value === undefined || value === null) return '-'
  return value.toFixed(2)
}

// 导出Excel
const handleExportExcel = async () => {
  if (!props.backtestId) {
    ElMessage.warning('回测ID不存在')
    return
  }

  excelExportLoading.value = true
  try {
    await backtestExportApi.downloadExcel(props.backtestId)
    ElMessage.success('Excel导出成功')
  } catch (err: any) {
    console.error('导出Excel失败:', err)
    const errorMsg = err.response?.data?.detail || err.message || '导出Excel失败'
    ElMessage.error(errorMsg)
  } finally {
    excelExportLoading.value = false
  }
}

// 导出图表
const handleExportCharts = async (command: string) => {
  if (!props.backtestId) {
    ElMessage.warning('回测ID不存在')
    return
  }

  try {
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')

    if (command === 'equity') {
      // 导出资金曲线图
      chartExportUtils.exportEChartsToPNG(
        'equity-chart',
        `equity_curve_${props.backtestId}_${timestamp}`
      )
      ElMessage.success('资金曲线图导出成功')
    } else if (command === 'drawdown') {
      // 导出回撤图
      chartExportUtils.exportEChartsToPNG(
        'drawdown-chart',
        `drawdown_${props.backtestId}_${timestamp}`
      )
      ElMessage.success('回撤图导出成功')
    } else if (command === 'all') {
      // 导出所有图表
      chartExportUtils.exportMultipleCharts([
        {
          chartId: 'equity-chart',
          filename: `equity_curve_${props.backtestId}_${timestamp}`
        },
        {
          chartId: 'drawdown-chart',
          filename: `drawdown_${props.backtestId}_${timestamp}`
        }
      ])
      ElMessage.success('全部图表导出成功')
    }
  } catch (err: any) {
    console.error('导出图表失败:', err)
    ElMessage.error('导出图表失败')
  }
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

// 获取胜率样式类
const getWinRateClass = (value: number) => {
  if (value >= 0.6) return 'positive'
  if (value >= 0.5) return 'neutral'
  return 'negative'
}

// 监听 backtestId 变化
watch(() => props.backtestId, async () => {
  await loadResults()
  loadTrades()
  // loadValuationHistory 会在 loadResults 内部根据策略类型调用
})

// 组件挂载
onMounted(() => {
  loadResults()
  loadTrades()

  // 响应式调整图表大小
  window.addEventListener('resize', () => {
    if (chartInstance) {
      chartInstance.resize()
    }
  })
})

// 组件卸载
onUnmounted(() => {
  if (chartInstance) {
    chartInstance.dispose()
  }
  window.removeEventListener('resize', () => {})
})
</script>

<style scoped lang="scss">
.backtest-results {
  padding: 20px;

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .title {
      font-size: 18px;
      font-weight: bold;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 12px;
    }
  }

  .results-content {
    .metrics-section {
      margin-bottom: 20px;
    }

    .metric-card {
      .card-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: bold;
      }

      .metric-list {
        .metric-item {
          display: flex;
          justify-content: space-between;
          padding: 12px 0;
          border-bottom: 1px solid #f0f0f0;

          &:last-child {
            border-bottom: none;
          }

          .label {
            color: #606266;
            font-size: 14px;
          }

          .value {
            font-weight: bold;
            font-size: 16px;

            &.positive {
              color: #67c23a;
            }

            &.negative {
              color: #f56c6c;
            }

            &.neutral {
              color: #909399;
            }
          }
        }
      }
    }

    .trading-stats-card {
      margin-bottom: 20px;

      .stat-item {
        text-align: center;
        padding: 10px 0;

        .stat-value {
          font-size: 28px;
          font-weight: bold;
          margin-bottom: 8px;

          &.success {
            color: #67c23a;
          }

          &.danger {
            color: #f56c6c;
          }

          &.positive {
            color: #67c23a;
          }

          &.negative {
            color: #f56c6c;
          }
        }

        .stat-label {
          color: #909399;
          font-size: 14px;
        }
      }
    }

    .chart-card {
      margin-bottom: 20px;

      .chart-error {
        height: 400px;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .chart-container {
        width: 100%;
        height: 400px;
      }
    }

    .trades-card {
      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 8px;
        font-weight: bold;
      }

      .pagination-container {
        margin-top: 20px;
        display: flex;
        justify-content: center;
      }

      // 决策详情样式
      .decision-reason {
        font-size: 13px;
        color: #606266;
        line-height: 1.5;
        max-width: 250px;
        word-break: break-all;
      }

      .decision-metadata {
        margin-top: 4px;
      }

      .no-decision-info {
        color: #c0c4cc;
        font-size: 13px;
      }
    }
  }
}
</style>

<style lang="scss">
// 元数据详情弹出框样式（全局生效）
.metadata-detail {
  .metadata-title {
    font-weight: 600;
    color: #303133;
    margin-bottom: 8px;
    font-size: 14px;
  }

  .metadata-item {
    display: flex;
    justify-content: space-between;
    padding: 6px 0;
    border-bottom: 1px dashed #e4e7ed;

    &:last-child {
      border-bottom: none;
    }

    .metadata-label {
      color: #909399;
      font-size: 13px;
    }

    .metadata-value {
      color: #303133;
      font-size: 13px;
      font-weight: 500;
    }
  }
}
</style>
