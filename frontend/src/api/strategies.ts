/**
 * 策略管理API
 *
 * 提供策略相关的API调用接口
 */
import { ApiClient } from './request'

// ===================== 类型定义 =====================

export interface StrategyParameterRange {
  min?: number
  max?: number
}

export interface StrategyParameter {
  name: string
  type: 'int' | 'float' | 'bool' | 'string' | 'list'
  default_value: any
  range?: StrategyParameterRange
  options?: string[]
  description: string
  required: boolean
}

export interface StrategySummary {
  strategy_id: string
  name: string
  description: string
  category: string
  parameter_count: number
  usage_count: number
  is_builtin: boolean
}

export interface StrategyDetail extends StrategySummary {
  long_description?: string
  parameters: StrategyParameter[]
  created_at: string
}

export interface StrategyCategory {
  category_id: string
  name: string
  description?: string
  strategy_count: number
}

export interface ValidateParamsRequest {
  params: Record<string, any>
}

export interface ValidateParamsResponse {
  valid: boolean
  errors?: Record<string, string>
}

export interface StrategyListResponse {
  strategies: StrategySummary[]
  total: number
}

export interface GetStrategiesParams {
  category?: string
  search?: string
  sort_by?: string
  sort_order?: number
  skip?: number
  limit?: number
}

// ===================== API接口 =====================

export const strategiesApi = {
  /**
   * 获取策略列表
   * @param params 查询参数
   */
  async getStrategies(params?: GetStrategiesParams) {
    return ApiClient.get<StrategyListResponse>('/api/backtest/strategies', params)
  },

  /**
   * 获取策略详情
   * @param strategyId 策略ID
   */
  async getStrategyDetail(strategyId: string) {
    return ApiClient.get<StrategyDetail>(`/api/backtest/strategies/${strategyId}`)
  },

  /**
   * 获取策略分类列表
   */
  async getCategories() {
    return ApiClient.get<StrategyCategory[]>('/api/backtest/strategies/categories')
  },

  /**
   * 校验策略参数
   * @param strategyId 策略ID
   * @param params 参数
   */
  async validateParams(strategyId: string, params: ValidateParamsRequest) {
    return ApiClient.post<ValidateParamsResponse>(
      `/api/backtest/strategies/${strategyId}/validate-params`,
      params
    )
  }
}
