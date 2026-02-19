<template>
  <div class="mdvaes-valuation-panel">
    <!-- 错误提示 -->
    <el-alert
      v-if="mdvaesStore.hasError"
      type="error"
      :title="mdvaesStore.error ?? '计算失败'"
      :closable="false"
      style="margin-bottom: 16px"
    />

    <!-- 估值结果卡片 -->
    <el-row :gutter="16">
      <!-- 内在价值卡片 -->
      <el-col :span="8">
        <el-card class="valuation-card intrinsic-card">
          <div class="card-content">
            <div class="card-label">内在价值</div>
            <div class="card-value">
              ¥{{ formatValue(valuation?.intrinsic_value) }}
            </div>
            <div class="card-sub" v-if="valuation">
              <el-tag :type="signalType" size="small">
                {{ signalText }}
              </el-tag>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 估值下限 -->
      <el-col :span="8">
        <el-card class="valuation-card lower-card">
          <div class="card-content">
            <div class="card-label">估值下限</div>
            <div class="card-value">
              ¥{{ formatValue(valuation?.lower_bound) }}
            </div>
            <div class="card-sub">
              安全买入价
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 估值上限 -->
      <el-col :span="8">
        <el-card class="valuation-card upper-card">
          <div class="card-content">
            <div class="card-label">估值上限</div>
            <div class="card-value">
              ¥{{ formatValue(valuation?.upper_bound) }}
            </div>
            <div class="card-sub">
              合理卖出价
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 置信度和估值方法明细 -->
    <el-row :gutter="16" style="margin-top: 16px">
      <!-- 置信度 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>估值置信度</span>
          </template>
          <div class="confidence-container">
            <el-progress
              :percentage="confidencePercent"
              :color="confidenceColor"
              :stroke-width="20"
            />
            <div class="confidence-value">
              {{ confidencePercent }}% {{ confidenceText }}
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 估值方法明细 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>多锚点估值明细</span>
          </template>
          <div class="methods-container">
            <div class="method-row" v-for="(value, method) in valuationMethods" :key="method">
              <span class="method-name">{{ methodNames[method as keyof typeof methodNames] }}</span>
              <span class="method-value">¥{{ formatValue(value) }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 增长指标 -->
    <el-row :gutter="16" style="margin-top: 16px" v-if="growthMetrics">
      <el-col :span="24">
        <el-card>
          <template #header>
            <span>增长指标</span>
          </template>
          <div class="growth-metrics">
            <div class="metric-item">
              <div class="metric-label">CAGR (复合年均增长率)</div>
              <div class="metric-value">{{ formatPercent(growthMetrics.cagr) }}</div>
            </div>
            <div class="metric-item">
              <div class="metric-label">增长率</div>
              <div class="metric-value">{{ formatPercent(growthMetrics.growth_rate) }}</div>
            </div>
            <div class="metric-item">
              <div class="metric-label">R² 拟合优度</div>
              <div class="metric-value">{{ growthMetrics.r_squared.toFixed(3) }}</div>
            </div>
            <div class="metric-item">
              <div class="metric-label">增长质量</div>
              <div class="metric-value">{{ (growthMetrics.growth_quality_score * 100).toFixed(0) }}分</div>
            </div>
            <div class="metric-item">
              <div class="metric-label">趋势稳定性</div>
              <div class="metric-value">
                <el-tag :type="trendStabilityType" size="small">
                  {{ trendStabilityText }}
                </el-tag>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- EPS 预测图表 -->
    <el-row style="margin-top: 16px" v-if="epsForecasts.length > 0">
      <el-col :span="24">
        <el-card>
          <template #header>
            <span>EPS 预测趋势</span>
          </template>
          <div ref="chartRef" style="width: 100%; height: 300px"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useMdvaesStore } from '@/stores/mdvaes'
import * as echarts from 'echarts'

const mdvaesStore = useMdvaesStore()

// 图表引用
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

// 计算属性
const valuation = computed(() => mdvaesStore.valuation)
const growthMetrics = computed(() => mdvaesStore.growthMetrics)
const epsForecasts = computed(() => mdvaesStore.epsForecasts)

const signalType = computed(() => mdvaesStore.signalType)

const signalText = computed(() => {
  const signal = valuation.value?.signal
  if (signal === 'buy') return '买入信号'
  if (signal === 'sell') return '卖出信号'
  return '持有信号'
})

const confidencePercent = computed(() => {
  return Math.round((valuation.value?.confidence ?? 0) * 100)
})

const confidenceColor = computed(() => {
  const confidence = valuation.value?.confidence ?? 0
  if (confidence >= 0.8) return '#67c23a'
  if (confidence >= 0.6) return '#e6a23c'
  return '#f56c6c'
})

const confidenceText = computed(() => {
  const confidence = valuation.value?.confidence ?? 0
  if (confidence >= 0.8) return '高置信'
  if (confidence >= 0.6) return '中等置信'
  return '低置信'
})

const valuationMethods = computed(() => {
  return valuation.value?.valuation_method ?? {}
})

const methodNames = {
  peg: 'PEG 估值',
  pe_historical: '历史PE',
  pb: 'PB 估值',
  dcf: 'DCF 估值'
}

const trendStabilityType = computed(() => {
  const stability = growthMetrics.value?.trend_stability
  if (stability === 'stable') return 'success'
  if (stability === 'volatile') return 'warning'
  return 'danger'
})

const trendStabilityText = computed(() => {
  const stability = growthMetrics.value?.trend_stability
  if (stability === 'stable') return '稳定'
  if (stability === 'volatile') return '波动'
  return '衰退'
})

// 方法
function formatValue(value?: number) {
  if (value === undefined || value === null) return '--'
  return value.toFixed(2)
}

function formatPercent(value: number) {
  return (value * 100).toFixed(2) + '%'
}

// 初始化图表
function initChart() {
  if (!chartRef.value || epsForecasts.value.length === 0) return

  chart = echarts.init(chartRef.value, 'light', { renderer: 'svg' })

  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const p = params[0]
        return `${p.name}年<br/>EPS预测: ¥${p.value.toFixed(2)}`
      }
    },
    xAxis: {
      type: 'category',
      data: epsForecasts.value.map(f => f.year + '年'),
      axisLabel: {
        rotate: 45
      }
    },
    yAxis: {
      type: 'value',
      name: 'EPS (元)',
      axisLabel: {
        formatter: '¥{value}'
      }
    },
    series: [{
      name: 'EPS预测',
      type: 'bar',
      data: epsForecasts.value.map(f => f.eps_forecast),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#83bff6' },
          { offset: 1, color: '#188df0' }
        ])
      },
      label: {
        show: true,
        position: 'top',
        formatter: '¥{c}'
      }
    }],
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    }
  }

  chart.setOption(option)
}

// 监听 EPS 预测变化，更新图表
watch(epsForecasts, () => {
  if (chart) {
    chart.dispose()
  }
  nextTick(() => {
    initChart()
  })
}, { deep: true })

onMounted(() => {
  initChart()
})
</script>

<style scoped>
.mdvaes-valuation-panel {
  width: 100%;
}

.valuation-card {
  border-radius: 8px;
}

.intrinsic-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.lower-card {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.upper-card {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.card-content {
  text-align: center;
  color: white;
  padding: 10px 0;
}

.card-label {
  font-size: 14px;
  opacity: 0.9;
  margin-bottom: 8px;
}

.card-value {
  font-size: 28px;
  font-weight: bold;
  margin-bottom: 8px;
}

.card-sub {
  font-size: 12px;
  opacity: 0.8;
}

.confidence-container {
  padding: 10px 0;
}

.confidence-value {
  text-align: center;
  margin-top: 16px;
  font-size: 14px;
  font-weight: 500;
}

.methods-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.method-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.method-name {
  color: #606266;
}

.method-value {
  font-weight: 500;
  color: #303133;
}

.growth-metrics {
  display: flex;
  justify-content: space-around;
  flex-wrap: wrap;
  gap: 16px;
}

.metric-item {
  text-align: center;
  min-width: 100px;
}

.metric-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
</style>
