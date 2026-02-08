/**
 * 回测常用参数 API
 */
import axios from 'axios'

const API_BASE = '/api/backtest/saved-params'

export interface SavedBacktestParams {
  id?: string
  user_id: string
  name: string
  description?: string
  start_date: string
  end_date: string
  initial_capital: number
  min_purchase: number
  stock_code: string
  strategy_id: string
  strategy_params: Record<string, any>
  created_at: string
  updated_at: string
  usage_count: number
  is_default: boolean
}

export interface CreateSavedParamsRequest {
  name: string
  description?: string
  params: {
    start_date: string
    end_date: string
    initial_capital: number
    min_purchase: number
    stock_code: string
    strategy_id: string
    strategy_params: Record<string, any>
  }
}

export interface UpdateSavedParamsRequest {
  name?: string
  description?: string
  params?: {
    start_date?: string
    end_date?: string
    initial_capital?: number
    min_purchase?: number
    stock_code?: string
    strategy_id?: string
    strategy_params?: Record<string, any>
  }
}

export const savedParamsApi = {
  /**
   * 创建保存的参数
   */
  async createParams(request: CreateSavedParamsRequest): Promise<SavedBacktestParams> {
    const response = await axios.post<SavedBacktestParams>(API_BASE, request)
    return response.data
  },

  /**
   * 获取用户的所有保存参数
   */
  async getParamsList(): Promise<SavedBacktestParams[]> {
    const response = await axios.get<SavedBacktestParams[]>(API_BASE)
    return response.data
  },

  /**
   * 获取指定的保存参数
   */
  async getParams(paramsId: string): Promise<SavedBacktestParams> {
    const response = await axios.get<SavedBacktestParams>(`${API_BASE}/${paramsId}`)
    return response.data
  },

  /**
   * 更新保存的参数
   */
  async updateParams(
    paramsId: string,
    request: UpdateSavedParamsRequest
  ): Promise<SavedBacktestParams> {
    const response = await axios.put<SavedBacktestParams>(
      `${API_BASE}/${paramsId}`,
      request
    )
    return response.data
  },

  /**
   * 删除保存的参数
   */
  async deleteParams(paramsId: string): Promise<{ success: boolean; message: string }> {
    const response = await axios.delete<{ success: boolean; message: string }>(
      `${API_BASE}/${paramsId}`
    )
    return response.data
  },

  /**
   * 使用保存的参数（增加使用次数）
   */
  async useParams(paramsId: string): Promise<{ success: boolean; message: string }> {
    const response = await axios.post<{ success: boolean; message: string }>(
      `${API_BASE}/${paramsId}/use`
    )
    return response.data
  }
}
