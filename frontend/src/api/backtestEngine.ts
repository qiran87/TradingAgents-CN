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
 * 收益指标
 */
export interface ReturnMetrics {
  total_return: number                    // 总收益率
  annual_return: number                   // 年化收益率
  cumulative_returns: number[]            // 累计收益率序列
  daily_returns: number[]                 // 日收益率序列
}

/**
 * 风险指标
 */
export interface RiskMetrics {
  max_drawdown: number                    // 最大回撤
  volatility: number                      // 波动率
  downside_volatility: number             // 下行波动率
  var_95: number                          // 95% VaR
}

/**
 * 风险调整收益指标
 */
export interface RiskAdjustedMetrics {
  sharpe_ratio: number                    // 夏普比率
  sortino_ratio: number                   // 索提诺比率
  calmar_ratio: number                    // 卡玛比率
}

/**
 * 交易统计
 */
export interface TradingStats {
  total_trades: number                    // 总交易次数
  winning_trades: number                  // 盈利交易次数
  losing_trades: number                   // 亏损交易次数
  win_rate: number                        // 胜率
  avg_profit: number                      // 平均盈利
  avg_loss: number                        // 平均亏损
  profit_loss_ratio: number               // 盈亏比
}

/**
 * 资金曲线
 */
export interface EquityCurve {
  dates: string[]                         // 日期列表
  total_assets: number[]                  // 总资产
  cash: number[]                          // 现金
  position_value: number[]                // 持仓市值
}

/**
 * 回测结果
 */
export interface BacktestResults {
  backtest_id: string                     // 回测任务ID
  return_metrics: ReturnMetrics           // 收益指标
  risk_metrics: RiskMetrics               // 风险指标
  risk_adjusted_metrics: RiskAdjustedMetrics  // 风险调整收益指标
  trading_stats: TradingStats             // 交易统计
  equity_curve: EquityCurve               // 资金曲线
  created_at: string                      // 创建时间
}

/**
 * 交易记录
 */
export interface TradeRecord {
  backtest_id: string                     // 回测任务ID
  date: string                            // 交易日期
  trade_type: 'buy' | 'sell'              // 交易类型
  price: number                           // 成交价格
  shares: number                          // 成交数量
  amount: number                          // 成交金额
  commission: number                      // 佣金
  stamp_duty: number                      // 印花税
  slippage: number                        // 滑点
  total_cost: number                      // 总费用
  cash_before: number                     // 交易前现金
  cash_after: number                      // 交易后现金
  position_before: number                 // 交易前持仓
  position_after: number                  // 交易后持仓
  cost_basis?: number                     // 成本基(卖出时)
  signal: any                             // 交易信号
  created_at: string                      // 创建时间
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
   * 获取回测结果
   * @param backtestId 回测任务ID
   */
  async getBacktestResults(backtestId: string) {
    return ApiClient.get<BacktestResults>(
      `/api/backtest/${backtestId}/results`
    )
  },

  /**
   * 获取交易明细（支持分页）
   * @param backtestId 回测任务ID
   * @param page 页码（默认1）
   * @param pageSize 每页数量（默认50）
   */
  async getBacktestTrades(backtestId: string, page: number = 1, pageSize: number = 50) {
    return ApiClient.get<{
      trades: TradeRecord[],
      count: number,
      pagination: {
        page: number
        page_size: number
        total: number
        total_pages: number
      }
    }>(
      `/api/backtest/${backtestId}/trades?page=${page}&page_size=${pageSize}`
    )
  },

  /**
   * 获取资金曲线
   * @param backtestId 回测任务ID
   */
  async getEquityCurve(backtestId: string) {
    return ApiClient.get<EquityCurve>(
      `/api/backtest/${backtestId}/equity-curve`
    )
  },

  /**
   * 触发结果计算
   * @param backtestId 回测任务ID
   */
  async calculateResults(backtestId: string) {
    return ApiClient.post<{ message: string }>(
      `/api/backtest/${backtestId}/calculate-results`
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
