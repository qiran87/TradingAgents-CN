<template>
  <div class="trading-day-range-picker">
    <el-date-picker
      v-model="dateRange"
      type="daterange"
      range-separator="至"
      start-placeholder="开始日期"
      end-placeholder="结束日期"
      :disabled="disabled"
      :clearable="clearable"
      @change="handleDateRangeChange"
      format="YYYY-MM-DD"
      value-format="YYYY-MM-DD"
      style="width: 100%"
    />

    <!-- 自然日统计信息 -->
    <div v-if="showStats && totalDays > 0" class="trading-days-stats">
      <span class="stats-text">
        <el-icon><Calendar /></el-icon>
        共 <strong>{{ totalDays }}</strong> 个自然日
        <span v-if="estimatedYears">，约 <strong>{{ estimatedYears }}</strong> 年</span>
      </span>
    </div>

    <!-- 快捷选项 -->
    <div v-if="showQuickOptions" class="quick-options">
      <el-button
        v-for="option in quickOptions"
        :key="option.value"
        link
        type="primary"
        size="small"
        @click="selectQuickOption(option.value)"
      >
        {{ option.label }}
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { Calendar } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

// ===================== Props =====================
interface Props {
  startDate?: string               // 开始日期 YYYY-MM-DD
  endDate?: string                 // 结束日期 YYYY-MM-DD
  disabled?: boolean               // 是否禁用
  clearable?: boolean              // 是否可清空
  showStats?: boolean              // 是否显示统计
  showQuickOptions?: boolean       // 是否显示快捷选项
}

const props = withDefaults(defineProps<Props>(), {
  startDate: '',
  endDate: '',
  disabled: false,
  clearable: true,
  showStats: true,
  showQuickOptions: true
})

// ===================== Emits =====================
interface Emits {
  (e: 'update:startDate', date: string): void
  (e: 'update:endDate', date: string): void
  (e: 'change', startDate: string, endDate: string): void
}

const emit = defineEmits<Emits>()

// ===================== 状态 =====================
const dateRange = ref<[string, string] | null>(null)

// ===================== 快捷选项定义 =====================
interface QuickOption {
  label: string
  value: string
}

const quickOptions = computed<QuickOption[]>(() => [
  { label: '近1月', value: '1M' },
  { label: '近3月', value: '3M' },
  { label: '近6月', value: '6M' },
  { label: '近1年', value: '1Y' },
  { label: '近3年', value: '3Y' }
])

// ===================== 工具函数 =====================
/**
 * 格式化日期为 YYYY-MM-DD
 */
const formatDate = (date: Date): string => {
  return dayjs(date).format('YYYY-MM-DD')
}

/**
 * 计算两个日期之间的天数
 */
const calculateDaysBetween = (start: string, end: string): number => {
  return dayjs(end).diff(dayjs(start), 'day') + 1
}

/**
 * 计算估算年数(按每年365天计算)
 */
const calculateYears = (days: number): number => {
  return Math.round((days / 365) * 10) / 10
}

// ===================== 计算属性 =====================
/**
 * 总天数
 */
const totalDays = computed(() => {
  if (!dateRange.value || dateRange.value.length !== 2) return 0
  return calculateDaysBetween(dateRange.value[0], dateRange.value[1])
})

/**
 * 估算年数
 */
const estimatedYears = computed(() => {
  return calculateYears(totalDays.value)
})

// ===================== 方法 =====================
/**
 * 日期范围变化处理
 */
const handleDateRangeChange = (value: [string, string] | null) => {
  if (value && value.length === 2) {
    const [start, end] = value
    emit('update:startDate', start)
    emit('update:endDate', end)
    emit('change', start, end)
  } else {
    emit('update:startDate', '')
    emit('update:endDate', '')
    emit('change', '', '')
  }
}

/**
 * 选择快捷选项
 */
const selectQuickOption = (optionValue: string) => {
  const now = dayjs()
  let startDate: dayjs.Dayjs
  let endDate = now

  // 根据选项计算起始日期
  switch (optionValue) {
    case '1M':
      startDate = now.subtract(1, 'month')
      break
    case '3M':
      startDate = now.subtract(3, 'month')
      break
    case '6M':
      startDate = now.subtract(6, 'month')
      break
    case '1Y':
      startDate = now.subtract(1, 'year')
      break
    case '3Y':
      startDate = now.subtract(3, 'year')
      break
    default:
      return
  }

  const start = formatDate(startDate.toDate())
  const end = formatDate(endDate.toDate())

  dateRange.value = [start, end]
  handleDateRangeChange([start, end])
}

// ===================== 监听 Props 变化 =====================
/**
 * 监听外部传入的日期变化
 */
watch(
  () => [props.startDate, props.endDate],
  ([newStart, newEnd]) => {
    if (newStart && newEnd) {
      dateRange.value = [newStart, newEnd]
    } else {
      dateRange.value = null
    }
  },
  { immediate: true }
)
</script>

<style lang="scss" scoped>
.trading-day-range-picker {
  width: 100%;
}

.trading-days-stats {
  margin-top: 12px;
  padding: 8px 12px;
  background-color: var(--el-color-info-light-9);
  border: 1px solid var(--el-color-info-light-7);
  border-radius: 4px;
  font-size: 14px;

  .stats-text {
    display: flex;
    align-items: center;
    gap: 4px;
    color: var(--el-color-info);

    .el-icon {
      font-size: 16px;
    }

    strong {
      color: var(--el-color-primary);
      font-weight: 600;
    }
  }
}

.quick-options {
  margin-top: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
