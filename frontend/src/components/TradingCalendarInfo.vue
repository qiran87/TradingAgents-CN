<template>
  <el-card class="trading-calendar-info" shadow="never">
    <template #header>
      <div class="card-header">
        <span>交易日历信息</span>
        <el-button
          v-if="!loading"
          link
          type="primary"
          @click="refreshInfo"
        >
          刷新
        </el-button>
        <el-icon v-else class="is-loading">
          <Loading />
        </el-icon>
      </div>
    </template>

    <div v-if="loading && !info" class="loading-container">
      <el-skeleton :rows="4" animated />
    </div>

    <div v-else-if="info" class="info-content">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="日期范围">
          {{ info.date_range.start_date }} ~ {{ info.date_range.end_date }}
        </el-descriptions-item>

        <el-descriptions-item label="交易日数">
          <el-tag type="success" size="small">
            {{ info.trading_days_count }}天
          </el-tag>
        </el-descriptions-item>

        <el-descriptions-item label="节假日">
          <el-tag type="warning" size="small">
            {{ info.holidays_count }}天
          </el-tag>
        </el-descriptions-item>

        <el-descriptions-item label="周末">
          <el-tag type="info" size="small">
            {{ info.weekends_count }}天
          </el-tag>
        </el-descriptions-item>

        <el-descriptions-item label="第一个交易日">
          {{ info.first_trading_day.date }}
          <el-tag
            v-if="info.first_trading_day.weekday"
            size="small"
            style="margin-left: 8px"
          >
            {{ info.first_trading_day.weekday }}
          </el-tag>
        </el-descriptions-item>

        <el-descriptions-item label="最后一个交易日">
          {{ info.last_trading_day.date }}
          <el-tag
            v-if="info.last_trading_day.weekday"
            size="small"
            style="margin-left: 8px"
          >
            {{ info.last_trading_day.weekday }}
          </el-tag>
        </el-descriptions-item>

        <el-descriptions-item label="交易日占比" :span="2">
          <div class="percentage-container">
            <el-progress
              :percentage="info.trading_day_percentage"
              :color="progressColor"
              :stroke-width="20"
            />
            <span class="percentage-text">
              {{ info.trading_day_percentage }}%
            </span>
          </div>
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <el-empty
      v-else
      description="暂无数据"
      :image-size="80"
    />
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { useTradingCalendarStore } from '@/stores/tradingCalendar'
import type { TradingCalendarInfo } from '@/api/tradingCalendar'

// ===================== Props =====================
interface Props {
  startDate: string               // 起始日期 YYYY-MM-DD
  endDate: string                 // 结束日期 YYYY-MM-DD
  autoLoad?: boolean              // 是否自动加载
}

const props = withDefaults(defineProps<Props>(), {
  autoLoad: true
})

// ===================== Store =====================
const tradingCalendarStore = useTradingCalendarStore()

// ===================== 状态 =====================
const info = ref<TradingCalendarInfo | null>(null)
const loading = ref<boolean>(false)

// ===================== 计算属性 =====================
/**
 * 进度条颜色
 */
const progressColor = computed(() => {
  if (!info.value) return '#409eff'

  const percentage = info.value.trading_day_percentage
  if (percentage >= 70) return '#67c23a'
  if (percentage >= 50) return '#e6a23c'
  return '#f56c6c'
})

// ===================== 方法 =====================
/**
 * 加载交易日历信息
 */
async function loadInfo() {
  if (!props.startDate || !props.endDate) {
    return
  }

  loading.value = true
  try {
    info.value = await tradingCalendarStore.getTradingCalendarInfo(
      props.startDate,
      props.endDate
    )
  } catch (error) {
    console.error('加载交易日历信息失败:', error)
    info.value = null
  } finally {
    loading.value = false
  }
}

/**
 * 刷新信息
 */
async function refreshInfo() {
  // 清除缓存
  tradingCalendarStore.clearCache()
  // 重新加载
  await loadInfo()
}

// ===================== 监听 =====================
// 监听日期范围变化
watch(
  () => [props.startDate, props.endDate],
  () => {
    if (props.autoLoad) {
      loadInfo()
    }
  },
  { immediate: true }
)

// ===================== 暴露方法 =====================
defineExpose({
  loadInfo,
  refreshInfo
})
</script>

<style scoped lang="scss">
.trading-calendar-info {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-weight: 500;
  }

  .loading-container {
    padding: 16px 0;
  }

  .info-content {
    :deep(.el-descriptions) {
      .el-descriptions__body {
        .el-descriptions__table {
          .el-descriptions__cell {
            padding: 12px 16px;
          }
        }
      }
    }

    .percentage-container {
      display: flex;
      align-items: center;
      gap: 16px;

      .el-progress {
        flex: 1;
      }

      .percentage-text {
        font-weight: 500;
        color: #409eff;
        min-width: 50px;
        text-align: right;
      }
    }
  }
}
</style>
