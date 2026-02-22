<template>
  <div ref="chartRef" class="eps-trend-chart" style="width: 100%; height: 400px"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

interface EPSDataPoint {
  year: number | string  // 支持数字（年份）或字符串（月份，如 "2024-01"）
  eps: number
  is_forecast: boolean
}

interface Props {
  data: EPSDataPoint[]
}

const props = defineProps<Props>()

const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null

const initChart = () => {
  if (!chartRef.value) return

  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

const updateChart = () => {
  if (!chartInstance || !props.data || props.data.length === 0) return

  const years = props.data.map(d => d.year)
  const epsValues = props.data.map(d => d.eps)

  const option: EChartsOption = {
    title: {
      text: '估值预测 EPS 趋势图',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        const year = params[0].axisValue
        const title = typeof year === 'string' ? year : `${year}年`
        let tooltip = `<strong>${title}</strong><br/>`

        params.forEach((param: any) => {
          if (param.value != null) {
            const value = param.value.toFixed(2)
            tooltip += `${param.marker} EPS: ${value} 元<br/>`
          }
        })

        return tooltip
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: years,
      axisLabel: {
        formatter: (value: any) => {
          if (typeof value === 'string') {
            return value
          }
          return `${value}年`
        }
      }
    },
    yAxis: {
      type: 'value',
      name: 'EPS (元)',
      scale: true,
      axisLabel: {
        formatter: '{value}'
      }
    },
    series: [
      {
        name: '估值预测 EPS',
        type: 'bar',
        data: epsValues,
        itemStyle: {
          color: '#5470c6'
        },
        barMaxWidth: 40
      }
    ]
  }

  chartInstance.setOption(option)
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

watch(() => props.data, () => {
  updateChart()
}, { deep: true })
</script>

<style scoped>
.eps-trend-chart {
  min-height: 400px;
}
</style>
