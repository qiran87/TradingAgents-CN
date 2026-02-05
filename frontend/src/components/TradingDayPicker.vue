<template>
  <div class="trading-day-picker">
    <el-date-picker
      v-model="selectedDate"
      type="date"
      :placeholder="placeholder"
      :disabled="disabled"
      :clearable="clearable"
      :disabled-date="disabledDate"
      :cell-class-name="cellClassName"
      @change="handleDateChange"
      @blur="handleBlur"
    />

    <!-- 交易日提示信息 -->
    <div v-if="selectedDate && showTradingDayInfo" class="trading-day-info">
      <span v-if="isTradingDay" class="success">
        ✓ {{ selectedDate }} 是交易日
      </span>
      <span v-else class="warning">
        ⚠ {{ selectedDate }} 不是交易日
        <el-button
          v-if="nearestTradingDay"
          link
          type="primary"
          size="small"
          @click="selectNearestTradingDay"
        >
          选择最近的交易日({{ nearestTradingDay }})
        </el-button>
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useTradingCalendarStore } from '@/stores/tradingCalendar'

// ===================== Props =====================
interface Props {
  modelValue: string              // 当前选中的日期 YYYY-MM-DD
  label?: string                  // 标签文本
  placeholder?: string            // 占位符
  disabled?: boolean              // 是否禁用
  clearable?: boolean             // 是否可清空
  showTradingDayInfo?: boolean    // 是否显示交易日信息
}

const props = withDefaults(defineProps<Props>(), {
  label: '',
  placeholder: '选择交易日',
  disabled: false,
  clearable: true,
  showTradingDayInfo: true
})

// ===================== Emits =====================
interface Emits {
  (e: 'update:modelValue', date: string): void  // 更新日期
  (e: 'change', date: string): void             // 日期变化
  (e: 'blur'): void                             // 失去焦点
}

const emit = defineEmits<Emits>()

// ===================== Store =====================
const tradingCalendarStore = useTradingCalendarStore()

// ===================== 状态 =====================
const selectedDate = ref<string>(props.modelValue || '')
const isTradingDay = ref<boolean>(false)
const nearestTradingDay = ref<string>('')
const loading = ref<boolean>(false)

// ===================== 方法 =====================
/**
 * 禁用非交易日
 */
const disabledDate = async (date: Date) => {
  if (loading.value) return false

  const dateStr = formatDate(date)
  try {
    const trading = await tradingCalendarStore.isTradingDay(dateStr)
    return !trading
  } catch (error) {
    console.error('判断交易日失败:', error)
    return false // 出错时不禁用
  }
}

/**
 * 单元格样式(交易日/非交易日使用不同样式)
 */
const cellClassName = async (date: Date) => {
  if (loading.value) return ''

  const dateStr = formatDate(date)
  try {
    const trading = await tradingCalendarStore.isTradingDay(dateStr)
    return trading ? 'trading-day' : 'non-trading-day'
  } catch (error) {
    console.error('判断交易日失败:', error)
    return ''
  }
}

/**
 * 日期变化处理
 */
const handleDateChange = async (value: any) => {
  const dateStr = value ? formatDate(value) : ''

  if (dateStr) {
    // 判断是否为交易日
    loading.value = true
    try {
      isTradingDay.value = await tradingCalendarStore.isTradingDay(dateStr)

      // 如果不是交易日,查找最近的交易日
      if (!isTradingDay.value) {
        try {
          // 先尝试前一个交易日
          const prevDay = await tradingCalendarStore.getPreviousTradingDay(dateStr)
          nearestTradingDay.value = prevDay
        } catch {
          // 如果前一个交易日不存在,尝试后一个交易日
          try {
            const nextDay = await tradingCalendarStore.getNextTradingDay(dateStr)
            nearestTradingDay.value = nextDay
          } catch {
            nearestTradingDay.value = ''
          }
        }
      } else {
        nearestTradingDay.value = ''
      }
    } catch (error) {
      console.error('判断交易日失败:', error)
    } finally {
      loading.value = false
    }
  } else {
    isTradingDay.value = false
    nearestTradingDay.value = ''
  }

  // 触发事件
  emit('update:modelValue', dateStr)
  emit('change', dateStr)
}

/**
 * 选择最近的交易日
 */
async function selectNearestTradingDay() {
  if (!selectedDate.value || !nearestTradingDay.value) return

  selectedDate.value = nearestTradingDay.value
  await handleDateChange(nearestTradingDay.value)
}

/**
 * 失去焦点处理
 */
function handleBlur() {
  emit('blur')
}

/**
 * 格式化日期
 */
function formatDate(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

// ===================== 监听 =====================
// 监听外部值变化
watch(() => props.modelValue, (newValue) => {
  selectedDate.value = newValue || ''
  if (newValue) {
    handleDateChange(newValue)
  }
}, { immediate: true })
</script>

<style scoped lang="scss">
.trading-day-picker {
  display: inline-block;
  width: 100%;
}

.trading-day-info {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.5;

  .success {
    color: #67c23a;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .warning {
    color: #e6a23c;
    display: flex;
    align-items: center;
    gap: 4px;
    flex-wrap: wrap;
  }
}

// 日期面板样式
:deep(.trading-day) {
  background-color: #f0f9ff;
  color: #409eff;
  font-weight: 500;
}

:deep(.non-trading-day) {
  background-color: #f5f5f5;
  color: #ccc;
}
</style>
