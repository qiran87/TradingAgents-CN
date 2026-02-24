<template>
  <div class="stock-selector">
    <!-- 股票搜索输入框 -->
    <el-autocomplete
      v-model="searchKeyword"
      :fetch-suggestions="querySearch"
      :placeholder="placeholder || '输入股票代码或名称'"
      :select-when-unmatched="false"
      :disabled="disabled"
      @select="handleSelect"
      @input="handleInput"
      value-key="stock_code"
      style="width: 100%"
      clearable
    >
      <template #suffix>
        <span v-if="selectedStock" class="market-icon">
          <span :class="getMarketIconClass(selectedStock.market)" />
        </span>
      </template>

      <template #default="{ item }">
        <div class="stock-item">
          <div class="stock-code">{{ item.stock_code }}</div>
          <div class="stock-name">{{ item.stock_name }}</div>
          <el-tag
            v-if="showMarket"
            size="small"
            :type="getMarketType(selectedStock?.market || item.market)"
            class="stock-market-tag"
          >
            {{ item.market }}
          </el-tag>
          <!-- 数据来源标记（调试用，可选显示） -->
          <el-tag
            v-if="item._source"
            size="small"
            :type="item._source === 'stock_basic_info' ? 'success' : 'info'"
            class="stock-source-tag"
          >
            {{ item._source === 'stock_basic_info' ? '基础表' : '信息表' }}
          </el-tag>
        </div>
      </template>
    </el-autocomplete>

    <!-- 选中的股票信息 -->
    <div v-if="selectedStock && showMarket" class="selected-stock-info">
      <span class="stock-name">{{ selectedStock.stock_name }}</span>
      <el-tag size="small" :type="getMarketType(selectedStock.market)">
        {{ selectedStock.market }}
      </el-tag>
      <span v-if="selectedStock.industry" class="stock-industry">
        {{ selectedStock.industry }}
      </span>
    </div>

    <!-- 加载状态 -->
    <div v-if="searchLoading" class="search-loading">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>搜索中...</span>
    </div>

    <!-- 错误提示 -->
    <div v-if="searchError" class="search-error">
      <el-icon><Warning /></el-icon>
      <span>{{ searchError }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElAutocomplete, ElTag, ElIcon, ElMessage } from 'element-plus'
import { Loading, Warning } from '@element-plus/icons-vue'
import { useStockDataStore } from '@/stores/stockData'
import type { StockSearchResult } from '@/api/stockData'

interface Props {
  modelValue: string              // 当前选中的股票代码
  placeholder?: string            // 占位符
  disabled?: boolean              // 是否禁用
  showMarket?: boolean            // 是否显示市场信息
}

interface Emits {
  (e: 'update:modelValue', code: string): void              // 更新股票代码
  (e: 'change', code: string, stock: StockSearchResult): void  // 股票变化
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '输入股票代码或名称',
  disabled: false,
  showMarket: true
})

const emit = defineEmits<Emits>()

const stockDataStore = useStockDataStore()
const searchKeyword = ref(props.modelValue)
const selectedStock = ref<StockSearchResult | null>(null)
const searchLoading = ref(false)
const searchError = ref<string | null>(null)

// 远程搜索（带防抖）
let searchTimer: NodeJS.Timeout | null = null
async function querySearch(queryString: string, cb: any) {
  // 清除之前的定时器
  if (searchTimer) {
    clearTimeout(searchTimer)
  }

  if (!queryString || queryString.length < 1) {
    cb([])
    return
  }

  // 防抖300ms
  searchTimer = setTimeout(async () => {
    searchLoading.value = true
    searchError.value = null

    try {
      const results = await stockDataStore.searchStocks(queryString, 10, true)
      searchLoading.value = false
      cb(results)
    } catch (error: any) {
      searchLoading.value = false
      searchError.value = error?.message || '搜索失败'
      console.error('搜索股票失败:', error)
      ElMessage.error(searchError.value)
      cb([])
    }
  }, 300)
}

// 选择股票
function handleSelect(item: StockSearchResult) {
  selectedStock.value = item
  emit('update:modelValue', item.stock_code)
  emit('change', item.stock_code, item)
  searchError.value = null
}

// 输入事件
function handleInput(value: string) {
  if (!value) {
    selectedStock.value = null
    emit('update:modelValue', '')
  }
}

// 监听modelValue变化
watch(() => props.modelValue, async (newValue) => {
  searchKeyword.value = newValue

  if (newValue) {
    // 如果有值，获取股票信息
    try {
      const info = await stockDataStore.fetchStockInfo(newValue, true)
      if (info) {
        selectedStock.value = {
          stock_code: info.stock_code,
          stock_name: info.stock_name,
          market: info.market,
          industry: info.industry
        }
      }
    } catch (error) {
      console.error('获取股票信息失败:', error)
    }
  } else {
    selectedStock.value = null
  }
}, { immediate: true })

// 获取市场图标类名
function getMarketIconClass(market: string): string {
  if (market === '深圳') return 'market-icon sz'
  if (market === '上海') return 'market-icon sh'
  if (market === '香港') return 'market-icon hk'
  return 'market-icon default'
}

// 获取市场标签类型
function getMarketType(market: string): string {
  if (market === '深圳') return 'primary'
  if (market === '上海') return 'success'
  if (market === '香港') return 'warning'
  return 'info'
}
</script>

<style scoped>
.stock-selector {
  position: relative;
}

.stock-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
}

.stock-code {
  font-weight: bold;
  font-family: 'Courier New', monospace;
  min-width: 100px;
  color: #409eff;
}

.stock-name {
  flex: 1;
  color: #303133;
}

.stock-market-tag {
  font-size: 12px;
}

.stock-source-tag {
  font-size: 11px;
  opacity: 0.8;
}

.selected-stock-info {
  margin-top: 10px;
  padding: 8px 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
}

.selected-stock-info .stock-name {
  font-weight: 500;
  color: #303133;
}

.selected-stock-info .stock-industry {
  color: #909399;
  font-size: 13px;
}

.market-icon {
  display: inline-block;
  width: 20px;
  height: 20px;
  border-radius: 2px;
  position: relative;
}

.market-icon.sz {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.market-icon.sz::after {
  content: '深';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  font-size: 12px;
  font-weight: bold;
}

.market-icon.sh {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.market-icon.sh::after {
  content: '沪';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  font-size: 12px;
  font-weight: bold;
}

.market-icon.hk {
  background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
}

.market-icon.hk::after {
  content: '港';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: white;
  font-size: 12px;
  font-weight: bold;
}

.market-icon.default {
  background: linear-gradient(135deg, #a1c4fd 0%, #c2e9fb 100%);
}

.search-loading {
  position: absolute;
  right: 40px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  gap: 5px;
  color: #909399;
  font-size: 13px;
  z-index: 10;
}

.search-error {
  margin-top: 5px;
  padding: 5px 10px;
  background-color: #fef0f0;
  border-radius: 4px;
  color: #f56c6c;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 5px;
}
</style>
