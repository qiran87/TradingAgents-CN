/**
 * 股票数据Store - 回测功能专用
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { stockDataApi } from '@/api/stockData'
import type {
  StockInfo,
  QuoteData,
  DataAvailabilityInfo,
  StockSearchResult
} from '@/api/stockData'

export const useStockDataStore = defineStore('stockData', () => {
  // ===================== 状态 =====================

  // 股票基础信息
  const stockInfo = ref<StockInfo | null>(null)
  const stockInfoLoading = ref(false)
  const stockInfoError = ref<string | null>(null)

  // 行情数据
  const quotes = ref<QuoteData[]>([])
  const quotesLoading = ref(false)
  const quotesError = ref<string | null>(null)

  // 数据可用性
  const dataAvailability = ref<DataAvailabilityInfo | null>(null)
  const dataAvailabilityLoading = ref(false)
  const dataAvailabilityError = ref<string | null>(null)

  // 股票搜索结果
  const searchResults = ref<StockSearchResult[]>([])
  const searchLoading = ref(false)
  const searchError = ref<string | null>(null)

  // 缓存
  const stockInfoCache = ref<Map<string, StockInfo>>(new Map())
  const searchCache = ref<Map<string, StockSearchResult[]>>(new Map())

  // ===================== 计算属性 =====================

  const hasStockInfo = computed(() => stockInfo.value !== null)
  const hasQuotes = computed(() => quotes.value.length > 0)
  const hasSearchResults = computed(() => searchResults.value.length > 0)
  const isDataAvailable = computed(() => dataAvailability.value?.is_available ?? false)
  const dataCoverage = computed(() => {
    const coverage = dataAvailability.value?.coverage ?? 0
    return Math.round(coverage * 100)
  })

  // ===================== Actions =====================

  /**
   * 获取股票基础信息
   */
  async function fetchStockInfo(stockCode: string, useCache = true) {
    // 检查缓存
    if (useCache && stockInfoCache.value.has(stockCode)) {
      stockInfo.value = stockInfoCache.value.get(stockCode)!
      stockInfoError.value = null
      return stockInfo.value
    }

    stockInfoLoading.value = true
    stockInfoError.value = null

    try {
      const response = await stockDataApi.getStockInfo(stockCode)
      stockInfo.value = response.data

      // 更新缓存
      if (stockInfo.value) {
        stockInfoCache.value.set(stockCode, stockInfo.value)
      }

      return stockInfo.value
    } catch (error: any) {
      stockInfoError.value = error?.message || '获取股票信息失败'
      throw error
    } finally {
      stockInfoLoading.value = false
    }
  }

  /**
   * 获取行情数据
   */
  async function fetchQuotes(stockCode: string, startDate: string, endDate: string) {
    quotesLoading.value = true
    quotesError.value = null

    try {
      const response = await stockDataApi.getQuotes(stockCode, startDate, endDate)
      quotes.value = response.data.quotes

      return quotes.value
    } catch (error: any) {
      quotesError.value = error?.message || '获取行情数据失败'
      throw error
    } finally {
      quotesLoading.value = false
    }
  }

  /**
   * 检查数据可用性
   */
  async function checkDataAvailability(stockCode: string, startDate: string, endDate: string) {
    dataAvailabilityLoading.value = true
    dataAvailabilityError.value = null

    try {
      const response = await stockDataApi.checkDataAvailability(stockCode, startDate, endDate)
      dataAvailability.value = response.data

      return dataAvailability.value
    } catch (error: any) {
      dataAvailabilityError.value = error?.message || '检查数据可用性失败'
      throw error
    } finally {
      dataAvailabilityLoading.value = false
    }
  }

  /**
   * 搜索股票
   */
  async function searchStocks(keyword: string, limit = 10, useCache = true) {
    // 检查缓存
    const cacheKey = `${keyword}_${limit}`
    if (useCache && searchCache.value.has(cacheKey)) {
      searchResults.value = searchCache.value.get(cacheKey)!
      searchError.value = null
      return searchResults.value
    }

    searchLoading.value = true
    searchError.value = null

    try {
      const response = await stockDataApi.searchStocks(keyword, limit)
      searchResults.value = response.data.stocks

      // 更新缓存
      searchCache.value.set(cacheKey, searchResults.value)

      return searchResults.value
    } catch (error: any) {
      searchError.value = error?.message || '搜索股票失败'
      throw error
    } finally {
      searchLoading.value = false
    }
  }

  /**
   * 清除股票信息
   */
  function clearStockInfo() {
    stockInfo.value = null
    stockInfoError.value = null
  }

  /**
   * 清除行情数据
   */
  function clearQuotes() {
    quotes.value = []
    quotesError.value = null
  }

  /**
   * 清除数据可用性
   */
  function clearDataAvailability() {
    dataAvailability.value = null
    dataAvailabilityError.value = null
  }

  /**
   * 清除搜索结果
   */
  function clearSearchResults() {
    searchResults.value = []
    searchError.value = null
  }

  /**
   * 清除所有缓存
   */
  function clearCache() {
    stockInfoCache.value.clear()
    searchCache.value.clear()
  }

  /**
   * 重置所有状态
   */
  function reset() {
    clearStockInfo()
    clearQuotes()
    clearDataAvailability()
    clearSearchResults()
    clearCache()
  }

  // ===================== 返回 =====================

  return {
    // 状态
    stockInfo,
    stockInfoLoading,
    stockInfoError,
    quotes,
    quotesLoading,
    quotesError,
    dataAvailability,
    dataAvailabilityLoading,
    dataAvailabilityError,
    searchResults,
    searchLoading,
    searchError,

    // 计算属性
    hasStockInfo,
    hasQuotes,
    hasSearchResults,
    isDataAvailable,
    dataCoverage,

    // Actions
    fetchStockInfo,
    fetchQuotes,
    checkDataAvailability,
    searchStocks,
    clearStockInfo,
    clearQuotes,
    clearDataAvailability,
    clearSearchResults,
    clearCache,
    reset
  }
})
