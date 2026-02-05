<template>
  <el-card class="stock-info-card" v-loading="loading">
    <!-- 卡片标题 -->
    <template #header>
      <div class="card-header">
        <span class="card-title">股票信息</span>
        <el-tag v-if="stockInfo" :type="getMarketType(stockInfo.market)" size="small">
          {{ stockInfo.market }}
        </el-tag>
      </div>
    </template>

    <!-- 错误提示 -->
    <el-alert
      v-if="error"
      type="error"
      :title="error"
      :closable="false"
      show-icon
    />

    <!-- 无数据提示 -->
    <el-empty
      v-else-if="!stockInfo"
      description="请选择股票查看详细信息"
      :image-size="80"
    />

    <!-- 股票信息内容 -->
    <div v-else class="stock-info-content">
      <!-- 基本信息 -->
      <div class="info-section">
        <h4 class="section-title">基本信息</h4>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">股票代码</span>
            <span class="info-value code">{{ stockInfo.stock_code }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">股票名称</span>
            <span class="info-value">{{ stockInfo.stock_name }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">上市市场</span>
            <span class="info-value">{{ stockInfo.market }}</span>
          </div>
          <div class="info-item" v-if="stockInfo.industry">
            <span class="info-label">所属行业</span>
            <span class="info-value">{{ stockInfo.industry }}</span>
          </div>
          <div class="info-item" v-if="stockInfo.list_date">
            <span class="info-label">上市日期</span>
            <span class="info-value">{{ stockInfo.list_date }}</span>
          </div>
        </div>
      </div>

      <el-divider />

      <!-- 数据统计信息 -->
      <div class="info-section">
        <h4 class="section-title">数据统计</h4>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">数据范围</span>
            <span class="info-value">
              {{ stockInfo.data_range.first_date || '-' }} ~
              {{ stockInfo.data_range.last_date || '-' }}
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">数据完整性</span>
            <span class="info-value">
              <el-progress
                :percentage="stockInfo.data_completeness"
                :color="getCompletenessColor(stockInfo.data_completeness)"
                :stroke-width="8"
                :show-text="true"
              />
            </span>
          </div>
          <div class="info-item">
            <span class="info-label">总交易日数</span>
            <span class="info-value number">{{ stockInfo.total_trading_days }} 天</span>
          </div>
          <div class="info-item" v-if="stockInfo.last_updated">
            <span class="info-label">最后更新</span>
            <span class="info-value">{{ stockInfo.last_updated }}</span>
          </div>
        </div>
      </div>

      <!-- 数据可用性检查 -->
      <el-divider v-if="showDataAvailability && dateRange" />

      <div class="info-section" v-if="showDataAvailability && dateRange">
        <h4 class="section-title">
          数据可用性
          <el-tooltip content="检查指定日期范围内的数据是否完整" placement="top">
            <el-icon><QuestionFilled /></el-icon>
          </el-tooltip>
        </h4>

        <!-- 检查按钮 -->
        <div class="availability-check">
          <el-button
            type="primary"
            size="small"
            @click="checkAvailability"
            :loading="availabilityChecking"
          >
            检查可用性
          </el-button>
          <span class="date-range-text">
            {{ dateRange.start }} 至 {{ dateRange.end }}
          </span>
        </div>

        <!-- 检查结果 -->
        <div v-if="availabilityResult" class="availability-result">
          <el-alert
            :type="availabilityResult.is_available ? 'success' : 'warning'"
            :closable="false"
            show-icon
          >
            <template #title>
              <span v-if="availabilityResult.is_available">
                数据可用（覆盖率 {{ dataCoverage }}%）
              </span>
              <span v-else>
                数据不完整（覆盖率 {{ dataCoverage }}%）
              </span>
            </template>
          </el-alert>

          <!-- 详细信息 -->
          <div class="availability-details" v-if="availabilityResult">
            <div class="detail-item">
              <span class="detail-label">覆盖率</span>
              <span class="detail-value">{{ dataCoverage }}%</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">缺失交易日</span>
              <span class="detail-value warning">
                {{ availabilityResult.missing_dates.length }} 天
              </span>
            </div>
            <div class="detail-item" v-if="availabilityResult.first_available_date">
              <span class="detail-label">首个可用日期</span>
              <span class="detail-value">{{ availabilityResult.first_available_date }}</span>
            </div>
            <div class="detail-item" v-if="availabilityResult.last_available_date">
              <span class="detail-label">最后可用日期</span>
              <span class="detail-value">{{ availabilityResult.last_available_date }}</span>
            </div>
          </div>

          <!-- 缺失日期列表（仅显示前10个） -->
          <el-collapse v-if="availabilityResult.missing_dates.length > 0" class="missing-dates">
            <el-collapse-item title="查看缺失日期" name="missing">
              <el-tag
                v-for="date in availabilityResult.missing_dates.slice(0, 10)"
                :key="date"
                size="small"
                type="danger"
                class="missing-date-tag"
              >
                {{ date }}
              </el-tag>
              <span v-if="availabilityResult.missing_dates.length > 10" class="more-dates">
                ...还有 {{ availabilityResult.missing_dates.length - 10 }} 个
              </span>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElCard, ElTag, ElAlert, ElEmpty, ElDivider, ElButton, ElProgress, ElTooltip, ElIcon, ElCollapse, ElCollapseItem, ElMessage } from 'element-plus'
import { QuestionFilled } from '@element-plus/icons-vue'
import { useStockDataStore } from '@/stores/stockData'
import type { StockInfo, DataAvailabilityInfo } from '@/api/stockData'

interface Props {
  stockCode: string                    // 股票代码
  showDataAvailability?: boolean       // 是否显示数据可用性
  dateRange?: {                        // 日期范围
    start: string
    end: string
  }
}

const props = withDefaults(defineProps<Props>(), {
  showDataAvailability: false
})

const stockDataStore = useStockDataStore()
const stockInfo = ref<StockInfo | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const availabilityResult = ref<DataAvailabilityInfo | null>(null)
const availabilityChecking = ref(false)

// 计算数据覆盖率百分比
const dataCoverage = computed(() => {
  if (!availabilityResult.value) return 0
  return Math.round(availabilityResult.value.coverage * 100)
})

// 监听股票代码变化
watch(() => props.stockCode, async (newCode) => {
  if (newCode) {
    await loadStockInfo(newCode)
  } else {
    stockInfo.value = null
    error.value = null
  }
}, { immediate: true })

// 加载股票信息
async function loadStockInfo(stockCode: string) {
  loading.value = true
  error.value = null

  try {
    const info = await stockDataStore.fetchStockInfo(stockCode, true)
    stockInfo.value = info
  } catch (err: any) {
    error.value = err?.message || '加载股票信息失败'
    console.error('加载股票信息失败:', err)
  } finally {
    loading.value = false
  }
}

// 检查数据可用性
async function checkAvailability() {
  if (!props.stockCode || !props.dateRange) {
    ElMessage.warning('请先选择股票和日期范围')
    return
  }

  availabilityChecking.value = true

  try {
    const result = await stockDataStore.checkDataAvailability(
      props.stockCode,
      props.dateRange.start,
      props.dateRange.end
    )
    availabilityResult.value = result

    if (result.is_available) {
      ElMessage.success('数据可用')
    } else {
      ElMessage.warning(`数据不完整，覆盖率仅 ${dataCoverage.value}%`)
    }
  } catch (err: any) {
    ElMessage.error(err?.message || '检查数据可用性失败')
    console.error('检查数据可用性失败:', err)
  } finally {
    availabilityChecking.value = false
  }
}

// 获取市场标签类型
function getMarketType(market: string): string {
  if (market === '深圳') return 'primary'
  if (market === '上海') return 'success'
  if (market === '香港') return 'warning'
  return 'info'
}

// 获取数据完整性颜色
function getCompletenessColor(completeness: number): string {
  if (completeness >= 95) return '#67c23a'
  if (completeness >= 80) return '#e6a23c'
  return '#f56c6c'
}
</script>

<style scoped>
.stock-info-card {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.stock-info-content {
  padding: 10px 0;
}

.info-section {
  margin-bottom: 10px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #606266;
  margin: 0 0 15px 0;
  display: flex;
  align-items: center;
  gap: 5px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.info-label {
  font-size: 12px;
  color: #909399;
}

.info-value {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.info-value.code {
  font-family: 'Courier New', monospace;
  color: #409eff;
  font-weight: 600;
}

.info-value.number {
  color: #67c23a;
  font-weight: 600;
}

.availability-check {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
}

.date-range-text {
  font-size: 13px;
  color: #909399;
}

.availability-result {
  margin-top: 15px;
}

.availability-details {
  margin-top: 15px;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-label {
  font-size: 13px;
  color: #909399;
}

.detail-value {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.detail-value.warning {
  color: #e6a23c;
  font-weight: 600;
}

.missing-dates {
  margin-top: 15px;
}

.missing-date-tag {
  margin-right: 5px;
  margin-bottom: 5px;
}

.more-dates {
  font-size: 12px;
  color: #909399;
  margin-left: 5px;
}

@media (max-width: 768px) {
  .info-grid {
    grid-template-columns: 1fr;
  }

  .availability-details {
    grid-template-columns: 1fr;
  }
}
</style>
