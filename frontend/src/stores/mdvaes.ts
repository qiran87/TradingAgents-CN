/**
 * MDVAES 估值 Store
 *
 * 管理估值状态和参数
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { mdvaesApi, type MDVAESCalculateRequest, type MDVAESCalculateResponse, type MDVAESParametersResponse } from '@/api/mdvaes'

export const useMdvaesStore = defineStore('mdvaes', () => {
  // ===================== 状态 =====================
  
  // 计算状态
  const loading = ref(false)
  const calculating = ref(false)
  const error = ref<string | null>(null)
  
  // 估值结果
  const currentResult = ref<MDVAESCalculateResponse | null>(null)
  
  // 参数配置
  const parameters = ref<MDVAESParametersResponse>({
    forecast_years: 5,
    peg_base: 1.0,
    risk_adjustment: 0.1,
    use_margin: true,
    margin_buy: 0.8,
    margin_sell: 1.2
  })
  
  // 缓存状态
  const cacheStatus = ref<{
    total_entries: number
    symbols_cached: string[]
    oldest_entry?: string
    newest_entry?: string
    cache_hit_rate?: number
  } | null>(null)

  // ===================== 计算属性 =====================
  
  const hasResult = computed(() => currentResult.value?.success ?? false)
  
  const hasError = computed(() => !!error.value)
  
  const valuation = computed(() => currentResult.value?.valuation)
  
  const growthMetrics = computed(() => currentResult.value?.growth_metrics)
  
  const epsForecasts = computed(() => currentResult.value?.eps_forecasts ?? [])
  
  const signalType = computed(() => {
    const signal = valuation.value?.signal
    if (signal === 'buy') return 'success'
    if (signal === 'sell') return 'danger'
    return 'info'
  })

  // ===================== 操作 =====================
  
  /**
   * 计算 MDVAES 估值
   */
  async function calculateValuation(params: MDVAESCalculateRequest) {
    calculating.value = true
    error.value = null
    
    try {
      const response = await mdvaesApi.calculateValuation(params)
      currentResult.value = response
      
      if (!response.success) {
        error.value = response.error ?? '计算失败'
      }
      
      return response
    } catch (e: any) {
      error.value = e.message ?? '计算失败'
      throw e
    } finally {
      calculating.value = false
    }
  }
  
  /**
   * 获取默认参数
   */
  async function fetchParameters() {
    loading.value = true
    error.value = null
    
    try {
      const response = await mdvaesApi.getParameters()
      parameters.value = response
      return response
    } catch (e: any) {
      error.value = e.message ?? '获取参数失败'
      throw e
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 更新参数
   */
  async function updateParameters(updates: Partial<MDVAESParametersResponse>) {
    loading.value = true
    error.value = null
    
    try {
      const response = await mdvaesApi.updateParameters(updates)
      parameters.value = response
      return response
    } catch (e: any) {
      error.value = e.message ?? '更新参数失败'
      throw e
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 获取缓存状态
   */
  async function fetchCacheStatus() {
    loading.value = true
    error.value = null
    
    try {
      const response = await mdvaesApi.getCacheStatus()
      cacheStatus.value = response
      return response
    } catch (e: any) {
      error.value = e.message ?? '获取缓存状态失败'
      throw e
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 清除错误
   */
  function clearError() {
    error.value = null
  }
  
  /**
   * 重置状态
   */
  function reset() {
    currentResult.value = null
    error.value = null
  }

  // ===================== 返回 =====================
  
  return {
    // 状态
    loading,
    calculating,
    error,
    currentResult,
    parameters,
    cacheStatus,
    
    // 计算属性
    hasResult,
    hasError,
    valuation,
    growthMetrics,
    epsForecasts,
    signalType,
    
    // 操作
    calculateValuation,
    fetchParameters,
    updateParameters,
    fetchCacheStatus,
    clearError,
    reset
  }
})
