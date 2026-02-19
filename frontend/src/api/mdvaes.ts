/**
 * MDVAES 估值 API
 *
 * 提供多锚点估值系统相关的API调用接口
 */
import { ApiClient } from './request'

// ===================== 类型定义 =====================

export interface EPSForecastResponse {
  year: number
  eps_forecast: number
  forecast_date: string
  analyst_count: number
  source: string
}

export interface GrowthMetricsResponse {
  cagr: number
  growth_rate: number
  r_squared: number
  growth_quality_score: number
  trend_stability: string
}

export interface ValuationMethodBreakdown {
  peg: number
  pe_historical: number
  pb: number
  dcf: number
}

export interface ValuationResultResponse {
  intrinsic_value: number
  lower_bound: number
  upper_bound: number
  confidence: number
  valuation_method: ValuationMethodBreakdown
  signal: 'buy' | 'sell' | 'hold'
}

export interface MDVAESCalculateRequest {
  symbol: string
  calculation_date: string
  forecast_years?: number
  peg_base?: number
  risk_adjustment?: number
  use_margin?: boolean
  margin_buy?: number
  margin_sell?: number
}

export interface MDVAESCalculateResponse {
  success: boolean
  symbol: string
  calculation_date: string
  valuation?: ValuationResultResponse
  growth_metrics?: GrowthMetricsResponse
  eps_forecasts?: EPSForecastResponse[]
  current_pe?: number
  bond_rate?: number
  error?: string
}

export interface MDVAESParametersResponse {
  forecast_years: number
  peg_base: number
  risk_adjustment: number
  use_margin: boolean
  margin_buy: number
  margin_sell: number
}

export interface MDVAESParamsUpdateRequest {
  forecast_years?: number
  peg_base?: number
  risk_adjustment?: number
  use_margin?: boolean
  margin_buy?: number
  margin_sell?: number
}

export interface CacheStatusResponse {
  total_entries: number
  symbols_cached: string[]
  oldest_entry?: string
  newest_entry?: string
  cache_hit_rate?: number
}

// ===================== API接口 =====================

export const mdvaesApi = {
  /**
   * 计算 MDVAES 估值
   */
  async calculateValuation(params: MDVAESCalculateRequest) {
    return ApiClient.post<MDVAESCalculateResponse>('/api/mdvaes/calculate', params)
  },

  /**
   * 获取 MDVAES 参数
   */
  async getParameters() {
    return ApiClient.get<MDVAESParametersResponse>('/api/mdvaes/parameters')
  },

  /**
   * 更新 MDVAES 参数
   */
  async updateParameters(params: MDVAESParamsUpdateRequest) {
    return ApiClient.put<MDVAESParametersResponse>('/api/mdvaes/parameters', params)
  },

  /**
   * 获取 EPS 预测
   */
  async getForecasts(symbol: string, calculationDate: string, forecastYears = 5) {
    return ApiClient.get<EPSForecastResponse[]>('/api/mdvaes/forecasts/' + symbol, {
      calculation_date: calculationDate,
      forecast_years: forecastYears
    })
  },

  /**
   * 获取缓存状态
   */
  async getCacheStatus() {
    return ApiClient.get<CacheStatusResponse>('/api/mdvaes/cache/status')
  }
}
