/**
 * 回测历史记录管理API（增强版）
 */
import { ApiClient } from './request'

/**
 * 保存到历史记录请求
 */
export interface SaveToHistoryRequest {
  name: string                           // 记录名称
  description?: string                   // 记录描述
  tags?: string[]                        // 标签列表
}

/**
 * 保存到历史记录响应
 */
export interface SaveToHistoryResponse {
  record_id: string                      // 记录ID
  name: string                           // 记录名称
  message: string                        // 消息
}

/**
 * 关键指标快照
 */
export interface MetricsSnapshot {
  total_return: number                   // 总收益率
  max_drawdown: number                   // 最大回撤
  sharpe_ratio: number                   // 夏普比率
  win_rate: number                       // 胜率
  total_trades: number                   // 总交易次数
}

/**
 * 历史记录
 */
export interface HistoryRecord {
  record_id: string                      // 记录ID
  user_id: string                        // 用户ID
  name: string                           // 记录名称
  description: string                    // 记录描述
  tags: string[]                         // 标签
  parameters: {                          // 回测参数
    stock_code: string
    start_date: string
    end_date: string
    initial_capital: number
    strategy_id: string
    strategy_params: Record<string, any>
  }
  results_id: string                     // 回测结果ID
  backtest_id: string                    // 回测任务ID
  metrics_snapshot: MetricsSnapshot      // 关键指标快照
  is_deleted: boolean                    // 是否已删除（软删除）
  created_at: string                     // 创建时间
  updated_at: string                     // 更新时间
}

/**
 * 历史记录列表响应
 */
export interface HistoryListResponse {
  records: HistoryRecord[]               // 历史记录列表
  total: number                          // 总数
}

/**
 * 历史记录详情响应
 */
export interface HistoryDetailResponse {
  history: HistoryRecord                 // 历史记录
  results: any                           // 完整回测结果
}

/**
 * 对比历史记录请求
 */
export interface CompareHistoryRequest {
  record_ids: string[]                   // 记录ID列表（2-3个）
}

/**
 * 对比历史记录响应
 */
export interface CompareHistoryResponse {
  records: Array<{
    record_id: string
    name: string
    metrics_snapshot: MetricsSnapshot
    parameters: HistoryRecord['parameters']
    results: any
  }>
}

/**
 * 批量删除请求
 */
export interface BatchDeleteRequest {
  record_ids: string[]                   // 记录ID列表
  permanent?: boolean                    // 是否永久删除（默认false）
}

/**
 * 批量删除响应
 */
export interface BatchDeleteResponse {
  message: string                        // 消息
  deleted_count: number                  // 删除数量
}

/**
 * 导出历史记录响应
 */
export interface ExportHistoryResponse {
  format: 'json' | 'excel' | 'pdf'      // 导出格式
  data: any                              // 导出数据
  filename: string                       // 文件名
}

/**
 * 回测历史记录API（增强版）
 */
export const backtestHistoryApi = {
  /**
   * 保存回测结果到历史记录
   * @param backtestId 回测任务ID
   * @param request 保存请求
   */
  async saveToHistory(backtestId: string, request: SaveToHistoryRequest) {
    return ApiClient.post<SaveToHistoryResponse>(
      `/api/backtest/${backtestId}/save`,
      request
    )
  },

  /**
   * 获取历史记录列表
   * @param params 查询参数
   */
  async getHistoryList(params: {
    skip?: number                        // 跳过记录数
    limit?: number                       // 返回记录数
    strategy_id?: string                 // 策略ID筛选
    stock_code?: string                  // 股票代码筛选
    search?: string                      // 关键词搜索
    include_deleted?: boolean             // 是否包含已删除记录（回收站）
  }) {
    const queryParams = new URLSearchParams()
    if (params.skip !== undefined) queryParams.append('skip', params.skip.toString())
    if (params.limit !== undefined) queryParams.append('limit', params.limit.toString())
    if (params.strategy_id) queryParams.append('strategy_id', params.strategy_id)
    if (params.stock_code) queryParams.append('stock_code', params.stock_code)
    if (params.search) queryParams.append('search', params.search)
    if (params.include_deleted !== undefined) queryParams.append('include_deleted', params.include_deleted.toString())

    const queryStr = queryParams.toString()
    return ApiClient.get<HistoryListResponse>(
      `/api/backtest/history${queryStr ? `?${queryStr}` : ''}`
    )
  },

  /**
   * 获取历史记录详情
   * @param recordId 历史记录ID
   */
  async getHistoryDetail(recordId: string) {
    return ApiClient.get<HistoryDetailResponse>(
      `/api/backtest/history/${recordId}`
    )
  },

  /**
   * 对比历史记录
   * @param request 对比请求
   */
  async compareHistory(request: CompareHistoryRequest) {
    return ApiClient.post<CompareHistoryResponse>(
      '/api/backtest/history/compare',
      request
    )
  },

  /**
   * 删除历史记录（支持软删除和永久删除）
   * @param recordId 历史记录ID
   * @param permanent 是否永久删除（默认false，软删除）
   */
  async deleteHistory(recordId: string, permanent: boolean = false) {
    return ApiClient.delete_<{ message: string }>(
      `/api/backtest/history/${recordId}${permanent ? '?permanent=true' : ''}`
    )
  },

  /**
   * 批量删除历史记录
   * @param request 批量删除请求
   */
  async batchDelete(request: BatchDeleteRequest) {
    return ApiClient.post<BatchDeleteResponse>(
      '/api/backtest/history/batch-delete',
      request
    )
  },

  /**
   * 恢复历史记录（从回收站）
   * @param recordId 历史记录ID
   */
  async restoreHistory(recordId: string) {
    return ApiClient.post<{ message: string }>(
      `/api/backtest/history/${recordId}/restore`
    )
  },

  /**
   * 导出历史记录
   * @param recordId 历史记录ID
   * @param format 导出格式（json/excel/pdf）
   */
  async exportHistory(recordId: string, format: 'json' | 'excel' | 'pdf' = 'json') {
    return ApiClient.get<ExportHistoryResponse>(
      `/api/backtest/history/${recordId}/export?format=${format}`
    )
  }
}
