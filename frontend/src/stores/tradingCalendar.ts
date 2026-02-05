/**
 * 交易日历状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { tradingCalendarApi } from '@/api/tradingCalendar'
import type {
  TradingDayInfo,
  TradingDaysListResponse,
  TradingCalendarInfo
} from '@/api/tradingCalendar'

export const useTradingCalendarStore = defineStore('tradingCalendar', () => {
  // ===================== 状态 =====================
  // 交易日判断缓存: date -> is_trading_day
  const tradingDaysCache = ref<Map<string, boolean>>(new Map())

  // 交易日列表缓存: year/month/range -> trading_days[]
  const tradingDaysListCache = ref<Map<string, string[]>>(new Map())

  // 加载状态
  const loading = ref(false)

  // 错误信息
  const error = ref<string | null>(null)

  // ===================== Getters =====================
  // 缓存统计
  const cacheStats = computed(() => ({
    tradingDays: tradingDaysCache.value.size,
    tradingDaysLists: tradingDaysListCache.value.size
  }))

  // ===================== Actions =====================
  /**
   * 判断指定日期是否为交易日
   */
  async function isTradingDay(date: string): Promise<boolean> {
    // 检查缓存
    if (tradingDaysCache.value.has(date)) {
      return tradingDaysCache.value.get(date)!
    }

    try {
      loading.value = true
      error.value = null

      const response = await tradingCalendarApi.isTradingDay(date)
      const isTrading = response.data.is_trading_day

      // 更新缓存
      tradingDaysCache.value.set(date, isTrading)

      return isTrading
    } catch (err: any) {
      error.value = err.message || '判断交易日失败'
      console.error('判断交易日失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取交易日列表
   */
  async function getTradingDaysInRange(
    startDate: string,
    endDate: string
  ): Promise<string[]> {
    const cacheKey = `${startDate}_${endDate}`

    // 检查缓存
    if (tradingDaysListCache.value.has(cacheKey)) {
      return tradingDaysListCache.value.get(cacheKey)!
    }

    try {
      loading.value = true
      error.value = null

      const response = await tradingCalendarApi.getTradingDays(startDate, endDate)
      const tradingDays = response.data.trading_days

      // 更新缓存
      tradingDaysListCache.value.set(cacheKey, tradingDays)

      return tradingDays
    } catch (err: any) {
      error.value = err.message || '获取交易日列表失败'
      console.error('获取交易日列表失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取前一个交易日
   */
  async function getPreviousTradingDay(date: string): Promise<string> {
    try {
      loading.value = true
      error.value = null

      const response = await tradingCalendarApi.getPreviousTradingDay(date)
      return response.data.previous_trading_day
    } catch (err: any) {
      error.value = err.message || '获取前一个交易日失败'
      console.error('获取前一个交易日失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取后一个交易日
   */
  async function getNextTradingDay(date: string): Promise<string> {
    try {
      loading.value = true
      error.value = null

      const response = await tradingCalendarApi.getNextTradingDay(date)
      return response.data.next_trading_day
    } catch (err: any) {
      error.value = err.message || '获取后一个交易日失败'
      console.error('获取后一个交易日失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取交易日历信息
   */
  async function getTradingCalendarInfo(
    startDate: string,
    endDate: string
  ): Promise<TradingCalendarInfo> {
    try {
      loading.value = true
      error.value = null

      const response = await tradingCalendarApi.getTradingCalendarInfo(
        startDate,
        endDate
      )
      return response.data
    } catch (err: any) {
      error.value = err.message || '获取交易日历信息失败'
      console.error('获取交易日历信息失败:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 清除所有缓存
   */
  function clearCache() {
    tradingDaysCache.value.clear()
    tradingDaysListCache.value.clear()
  }

  /**
   * 清除特定日期的缓存
   */
  function clearDateCache(date: string) {
    tradingDaysCache.value.delete(date)
  }

  /**
   * 清除特定范围的缓存
   */
  function clearRangeCache(startDate: string, endDate: string) {
    const cacheKey = `${startDate}_${endDate}`
    tradingDaysListCache.value.delete(cacheKey)
  }

  // ===================== 返回 =====================
  return {
    // 状态
    tradingDaysCache,
    tradingDaysListCache,
    loading,
    error,

    // Getters
    cacheStats,

    // Actions
    isTradingDay,
    getTradingDaysInRange,
    getPreviousTradingDay,
    getNextTradingDay,
    getTradingCalendarInfo,
    clearCache,
    clearDateCache,
    clearRangeCache
  }
})
