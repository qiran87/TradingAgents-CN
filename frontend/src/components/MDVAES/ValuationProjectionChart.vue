<template>
  <div class="valuation-projection-chart" style="width: 100%; height: 400px">
    <div v-if="!data || data.length === 0" class="empty-state">
      <el-empty description="暂无估值数据" />
    </div>
    <div v-else ref="chartRef" style="width: 100%; height: 100%"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

interface ValuationDataPoint {
  date: string
  current_price: number
  intrinsic_value: number
  lower_bound: number
  upper_bound: number
  signal?: string
}

interface Props {
  data: ValuationDataPoint[]
}

const props = defineProps<Props>()

// 调试：监听 props 变化
watch(() => props.data, (newData) => {
  console.log('[ValuationProjectionChart] props.data changed:', newData?.length, 'records')
  if (newData && newData.length > 0) {
    console.log('[ValuationProjectionChart] First record:', newData[0])
  }
}, { immediate: true, deep: true })

const chartRef = ref<HTMLDivElement>()
let chartInstance: echarts.ECharts | null = null

const initChart = () => {
  console.log('[ValuationProjectionChart] initChart called, chartRef.value:', chartRef.value)
  if (!chartRef.value) {
    console.error('[ValuationProjectionChart] chartRef.value is null!')
    return
  }

  try {
    chartInstance = echarts.init(chartRef.value)
    console.log('[ValuationProjectionChart] ECharts instance created:', chartInstance)
    updateChart()
  } catch (e) {
    console.error('[ValuationProjectionChart] Failed to init chart:', e)
  }
}

const updateChart = () => {
  console.log('[ValuationProjectionChart] updateChart called')
  console.log('[ValuationProjectionChart] chartInstance:', chartInstance)
  console.log('[ValuationProjectionChart] props.data:', props.data?.length)

  if (!chartInstance) {
    console.error('[ValuationProjectionChart] chartInstance is null!')
    return
  }
  if (!props.data || props.data.length === 0) {
    console.warn('[ValuationProjectionChart] No data available')
    return
  }

  const dates = props.data.map(d => d.date)
  const currentPrices = props.data.map(d => d.current_price)
  const intrinsicValues = props.data.map(d => d.intrinsic_value)
  const lowerBounds = props.data.map(d => d.lower_bound)
  const upperBounds = props.data.map(d => d.upper_bound)

  // 标记买卖点 - 使用 ECharts 兼容的格式
  const markPointData: any[] = []
  const markLineData: any[] = []

  props.data.forEach((d) => {
    if (d.signal === 'buy') {
      markPointData.push({
        name: '买',
        coord: [d.date, d.current_price],
        value: d.current_price,
        itemStyle: { color: '#52c41a' },
        label: {
          show: true,
          formatter: '买',
          fontSize: 10,
          position: 'top'
        }
      })
    } else if (d.signal === 'sell') {
      markLineData.push({
        name: '卖',
        xAxis: d.date,
        yAxis: d.current_price,
        lineStyle: { color: '#f5222d', type: 'solid', width: 2 },
        label: { show: true, formatter: '卖', fontSize: 10 }
      })
    }
  })

  const option: EChartsOption = {
    title: {
      text: '估值推演图',
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: (params: any) => {
        if (!Array.isArray(params)) return ''
        const date = params[0].axisValue
        let tooltip = `<strong>${date}</strong><br/>`

        params.forEach((param: any) => {
          tooltip += `${param.marker} ${param.seriesName}: ${param.value.toFixed(2)}<br/>`
        })

        return tooltip
      }
    },
    legend: {
      data: ['当前价格', '内在价值', '估值上限', '估值下限'],
      bottom: 10
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false
    },
    yAxis: {
      type: 'value',
      name: '价格',
      scale: true
    },
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      },
      {
        start: 0,
        end: 100,
        handleIcon: 'M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4c0-5-3.9-9.1-8.8-9.4Z M15.5,21.3 c-4.2,0-7.6-3.4-7.6-7.6s3.4-7.6,7.6-7.6s7.6,3.4,7.6,7.6S19.7,21.3,15.5,21.3z',
        handleSize: '80%',
        handleStyle: {
          color: '#fff',
          shadowBlur: 3,
          shadowColor: 'rgba(0, 0, 0, 0.6)',
          shadowOffsetX: 2,
          shadowOffsetY: 2
        }
      }
    ],
    series: [
      {
        name: '当前价格',
        type: 'line',
        data: currentPrices,
        smooth: true,
        lineStyle: {
          width: 2,
          color: '#5470c6'
        },
        itemStyle: {
          color: '#5470c6'
        },
        markPoint: {
          symbol: 'circle',
          symbolSize: 8,
          data: markPointData
        },
        markLine: {
          silent: false,
          symbol: ['none', 'none'],
          data: markLineData
        }
      },
      {
        name: '内在价值',
        type: 'line',
        data: intrinsicValues,
        smooth: true,
        lineStyle: {
          width: 2,
          type: 'dashed',
          color: '#91cc75'
        },
        itemStyle: {
          color: '#91cc75'
        }
      },
      {
        name: '估值上限',
        type: 'line',
        data: upperBounds,
        smooth: true,
        lineStyle: {
          width: 1,
          color: '#fac858'
        },
        itemStyle: {
          color: '#fac858'
        },
        areaStyle: {
          color: 'rgba(250, 200, 88, 0.1)'
        }
      },
      {
        name: '估值下限',
        type: 'line',
        data: lowerBounds,
        smooth: true,
        lineStyle: {
          width: 1,
          color: '#ee6666'
        },
        itemStyle: {
          color: '#ee6666'
        },
        areaStyle: {
          color: 'rgba(238, 102, 102, 0.1)'
        }
      }
    ]
  }

  console.log('[ValuationProjectionChart] Setting ECharts option with', dates.length, 'data points')
  console.log('[ValuationProjectionChart] markPointData:', markPointData.length, 'buy signals')
  console.log('[ValuationProjectionChart] markLineData:', markLineData.length, 'sell signals')

  try {
    chartInstance.setOption(option)
    console.log('[ValuationProjectionChart] Option set successfully')
  } catch (e) {
    console.error('[ValuationProjectionChart] Failed to set option:', e)
  }
}

const handleResize = () => {
  chartInstance?.resize()
}

onMounted(() => {
  console.log('[ValuationProjectionChart] onMounted called')
  nextTick(() => {
    console.log('[ValuationProjectionChart] nextTick, calling initChart')
    initChart()
  })
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  chartInstance?.dispose()
  window.removeEventListener('resize', handleResize)
})

watch(() => props.data, (newData) => {
  console.log('[ValuationProjectionChart] watch triggered, data length:', newData?.length)
  // 如果数据到达但图表实例不存在，需要等待 DOM 更新后重新初始化
  if (newData && newData.length > 0 && !chartInstance) {
    console.log('[ValuationProjectionChart] Data arrived but no chart instance, waiting for DOM update...')
    nextTick(() => {
      console.log('[ValuationProjectionChart] nextTick in watch, chartRef.value:', chartRef.value)
      if (chartRef.value) {
        console.log('[ValuationProjectionChart] DOM ready, initializing chart...')
        initChart()
      } else {
        console.error('[ValuationProjectionChart] chartRef.value still undefined after nextTick!')
      }
    })
  } else {
    updateChart()
  }
}, { deep: true })
</script>

<style scoped>
.valuation-projection-chart {
  min-height: 400px;
}
</style>
