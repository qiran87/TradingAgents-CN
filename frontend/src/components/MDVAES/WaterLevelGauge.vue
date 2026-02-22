<template>
  <div class="water-level-gauge">
    <div ref="chartRef" class="gauge-chart" style="width: 100%; height: 300px"></div>
    <div class="gauge-status">
      <div class="status-item">
        <span class="label">当前价格:</span>
        <span class="value price">{{ currentPrice.toFixed(2) }}</span>
      </div>
      <div class="status-item">
        <span class="label">内在价值:</span>
        <span class="value intrinsic">{{ intrinsicValue.toFixed(2) }}</span>
      </div>
      <div class="status-item">
        <span class="label">估值区间:</span>
        <span class="value range">{{ lowerBound.toFixed(2) }} - {{ upperBound.toFixed(2) }}</span>
      </div>
      <div class="status-item">
        <span class="label">估值状态:</span>
        <span :class="['value', 'status', valuationStatus.class]">{{ valuationStatus.text }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

interface Props {
  currentPrice: number
  intrinsicValue: number
  lowerBound: number
  upperBound: number
}

const props = defineProps<Props>()

const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null

// 计算估值状态
const valuationStatus = computed(() => {
  const { currentPrice, lowerBound, upperBound } = props

  if (currentPrice < lowerBound) {
    return { text: '低估', class: 'undervalued' }
  } else if (currentPrice > upperBound) {
    return { text: '高估', class: 'overvalued' }
  } else {
    // 计算在区间中的位置百分比
    const range = upperBound - lowerBound
    const position = (currentPrice - lowerBound) / range

    if (position < 0.33) {
      return { text: '偏低', class: 'slightly-undervalued' }
    } else if (position > 0.67) {
      return { text: '偏高', class: 'slightly-overvalued' }
    } else {
      return { text: '合理', class: 'fair-valued' }
    }
  }
})

const initChart = () => {
  if (!chartRef.value) return

  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

const updateChart = () => {
  if (!chartInstance) return

  const { currentPrice, lowerBound, upperBound } = props

  // 计算指针位置（0-100）
  const range = upperBound - lowerBound
  // 将价格范围扩展20%以获得更好的显示效果
  const minPrice = lowerBound - range * 0.2
  const maxPrice = upperBound + range * 0.2
  const totalRange = maxPrice - minPrice
  const pointerPosition = ((currentPrice - minPrice) / totalRange) * 100

  // 根据估值状态选择颜色
  const statusColor = {
    undervalued: '#52c41a',
    slightly_undervalued: '#91cc75',
    fair_valued: '#fac858',
    slightly_overvalued: '#ee6666',
    overvalued: '#f5222d'
  }[valuationStatus.value.class] as string

  const option: EChartsOption = {
    series: [
      {
        type: 'gauge',
        startAngle: 180,
        endAngle: 0,
        min: minPrice,
        max: maxPrice,
        radius: '80%',
        center: ['50%', '65%'],
        splitNumber: 5,
        axisLine: {
          lineStyle: {
            width: 30,
            color: [
              [0.2, '#52c41a'],      // 低估区（绿色）
              [0.4, '#91cc75'],      // 偏低区（浅绿）
              [0.6, '#fac858'],      // 合理区（黄色）
              [0.8, '#ee6666'],      // 偏高区（浅红）
              [1, '#f5222d']         // 高估区（红色）
            ]
          }
        },
        pointer: {
          itemStyle: {
            color: statusColor
          },
          length: '60%',
          width: 6
        },
        axisTick: {
          length: 8,
          lineStyle: {
            color: 'auto',
            width: 1
          }
        },
        splitLine: {
          length: 20,
          lineStyle: {
            color: 'auto',
            width: 3
          }
        },
        axisLabel: {
          color: '#464646',
          fontSize: 12,
          distance: -50,
          formatter: (value: number) => value.toFixed(2)
        },
        detail: {
          valueAnimation: true,
          formatter: '{value}',
          color: statusColor,
          fontSize: 30,
          offsetCenter: [0, '20%']
        },
        title: {
          offsetCenter: [0, '50%'],
          fontSize: 16,
          color: '#666'
        },
        data: [
          {
            value: currentPrice,
            name: '当前价格'
          }
        ]
      }
    ]
  }

  chartInstance.setOption(option, true)
}

const handleResize = () => {
  chartInstance?.resize()
}

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  chartInstance?.dispose()
  window.removeEventListener('resize', handleResize)
})

watch(() => [props.currentPrice, props.lowerBound, props.upperBound], () => {
  updateChart()
})
</script>

<style scoped>
.water-level-gauge {
  padding: 20px;
  background: #fff;
  border-radius: 8px;
}

.gauge-chart {
  min-height: 300px;
}

.gauge-status {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
}

.status-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.status-item .label {
  color: #666;
  font-size: 14px;
}

.status-item .value {
  font-weight: 600;
  font-size: 15px;
}

.value.price {
  color: #5470c6;
}

.value.intrinsic {
  color: #91cc75;
}

.value.range {
  color: #666;
}

.value.status.undervalued {
  color: #52c41a;
}

.value.status.slightly-undervalued {
  color: #91cc75;
}

.value.status.fair-valued {
  color: #fac858;
}

.value.status.slightly-overvalued {
  color: #ee6666;
}

.value.status.overvalued {
  color: #f5222d;
}
</style>
