/**
 * 回测引擎API
 */
import { ApiClient } from './request'

/**
 * 启动回测请求
 */
export interface StartBacktestRequest {
  stock_code: string                      // 股票代码（如 000001.SZ）
  start_date: string                      // 起始日期 YYYY-MM-DD
  end_date: string                        // 结束日期 YYYY-MM-DD
  initial_capital: number                 // 初始资金
  strategy_id?: string                    // 策略ID
  strategy_params?: Record<string, any>   // 策略参数
}

/**
 * 启动回测响应
 */
export interface StartBacktestResponse {
  backtest_id: string                     // 回测任务ID
  status: string                          // 任务状态
}

/**
 * 回测状态信息
 */
export interface BacktestStatus {
  backtest_id: string                     // 回测任务ID
  status: 'created' | 'running' | 'paused' | 'completed' | 'failed' | 'aborted'
  parameters: StartBacktestRequest        // 回测参数
  execution_info: ExecutionInfo           // 执行信息
  error?: ErrorInfo                       // 错误信息
  created_at: string                      // 创建时间
  updated_at: string                      // 更新时间
}

/**
 * 执行信息
 */
export interface ExecutionInfo {
  current_bar_index: number               // 当前K线索引
  total_bars: number                      // 总K线数
  current_date: string | null             // 当前日期
  progress: number                        // 进度百分比（0-100）
  start_time: string                      // 开始时间
  elapsed_time: number                    // 已运行时间（秒）
}

/**
 * 错误信息
 */
export interface ErrorInfo {
  code: string                            // 错误代码
  message: string                         // 错误消息
  details?: any                           // 错误详情
}

/**
 * 持仓信息
 */
export interface PositionInfo {
  cash: number                            // 可用资金
  position: number                        // 持仓股数
  position_cost: number                   // 持仓成本
  current_price: number                   // 当前价格
  market_value: number                    // 市值
  total_value: number                     // 总资产
  profit_loss: number                     // 盈亏金额
  profit_loss_pct: number                 // 盈亏百分比
}

/**
 * WebSocket消息类型
 */
export type WSMessageType =
  | 'connected'                           // 连接成功
  | 'progress'                            // 进度更新
  | 'position'                            // 持仓更新
  | 'trade'                               // 交易信号
  | 'completed'                           // 回测完成
  | 'error'                               // 错误
  | 'pong'                                // 心跳响应

/**
 * WebSocket消息
 */
export interface WSMessage {
  type: WSMessageType                     // 消息类型
  data?: any                              // 消息数据
  timestamp?: string                      // 时间戳
}

/**
 * 回测引擎API
 */
export const backtestEngineApi = {
  /**
   * 启动回测任务
   * @param request 回测参数
   */
  async startBacktest(request: StartBacktestRequest) {
    return ApiClient.post<StartBacktestResponse>(
      '/api/backtest/start',
      request
    )
  },

  /**
   * 暂停回测任务
   * @param backtestId 回测任务ID
   */
  async interruptBacktest(backtestId: string) {
    return ApiClient.post<{ message: string }>(
      `/api/backtest/${backtestId}/interrupt`
    )
  },

  /**
   * 继续回测任务
   * @param backtestId 回测任务ID
   */
  async continueBacktest(backtestId: string) {
    return ApiClient.post<{ message: string }>(
      `/api/backtest/${backtestId}/continue`
    )
  },

  /**
   * 获取回测状态
   * @param backtestId 回测任务ID
   */
  async getBacktestStatus(backtestId: string) {
    return ApiClient.get<BacktestStatus>(
      `/api/backtest/${backtestId}/status`
    )
  },

  /**
   * 放弃回测任务
   * @param backtestId 回测任务ID
   */
  async abortBacktest(backtestId: string) {
    return ApiClient.delete_<{ message: string }>(
      `/api/backtest/${backtestId}`
    )
  },

  /**
   * 获取WebSocket URL
   * @param backtestId 回测任务ID
   */
  getWebSocketUrl(backtestId: string): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    return `${protocol}//${host}/api/backtest/ws/${backtestId}/progress`
  }
}
