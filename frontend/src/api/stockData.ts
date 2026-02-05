/**
 * 股票数据API - 回测功能专用
 */
import { ApiClient } from './request'

/**
 * 股票基础信息
 */
export interface StockInfo {
  stock_code: string                 // 股票代码（如 000001.SZ）
  stock_name: string                 // 股票名称
  market: string                     // 市场（上海/深圳）
  industry?: string                  // 行业
  list_date?: string                 // 上市日期 YYYY-MM-DD
  data_range: DataRange              // 数据范围
  data_completeness: number          // 数据完整性百分比
  total_trading_days: number         // 总交易日数
  last_updated?: string              // 最后更新时间
}

/**
 * 数据范围
 */
export interface DataRange {
  first_date: string | null          // 第一个数据日期
  last_date: string | null           // 最后一个数据日期
}

/**
 * 行情数据
 */
export interface QuoteData {
  date: string                       // 日期 YYYY-MM-DD
  open: number                       // 开盘价
  high: number                       // 最高价
  low: number                        // 最低价
  close: number                      // 收盘价
  volume: number                     // 成交量
  amount: number                     // 成交额
}

/**
 * 行情列表响应
 */
export interface QuotesListResponse {
  stock_code: string                 // 股票代码
  quotes: QuoteData[]                // 行情数据列表
  total: number                      // 总记录数
}

/**
 * 数据可用性信息
 */
export interface DataAvailabilityInfo {
  stock_code: string                 // 股票代码
  date_range: DataRange              // 日期范围
  is_available: boolean              // 是否可用
  coverage: number                   // 数据覆盖率（0-1）
  missing_dates: string[]            // 缺失日期列表
  first_available_date?: string      // 第一个可用日期
  last_available_date?: string       // 最后一个可用日期
}

/**
 * 股票搜索结果
 */
export interface StockSearchResult {
  stock_code: string                 // 股票代码
  stock_name: string                 // 股票名称
  market: string                     // 市场
  industry?: string                  // 行业
}

/**
 * 股票搜索响应
 */
export interface StockSearchResponse {
  stocks: StockSearchResult[]        // 股票列表
  total: number                      // 总数
}

/**
 * 股票数据API
 */
export const stockDataApi = {
  /**
   * 获取股票基础信息
   * @param stockCode 股票代码（如 000001.SZ 或 000001）
   */
  async getStockInfo(stockCode: string) {
    return ApiClient.get<StockInfo>(
      '/api/backtest/stock/info',
      { stock_code: stockCode }
    )
  },

  /**
   * 获取历史行情数据
   * @param stockCode 股票代码
   * @param startDate 起始日期 YYYY-MM-DD
   * @param endDate 结束日期 YYYY-MM-DD
   */
  async getQuotes(stockCode: string, startDate: string, endDate: string) {
    return ApiClient.get<QuotesListResponse>(
      '/api/backtest/stock/quotes',
      {
        stock_code: stockCode,
        start_date: startDate,
        end_date: endDate
      }
    )
  },

  /**
   * 检查数据可用性
   * @param stockCode 股票代码
   * @param startDate 起始日期 YYYY-MM-DD
   * @param endDate 结束日期 YYYY-MM-DD
   */
  async checkDataAvailability(stockCode: string, startDate: string, endDate: string) {
    return ApiClient.get<DataAvailabilityInfo>(
      '/api/backtest/stock/quotes/check-availability',
      {
        stock_code: stockCode,
        start_date: startDate,
        end_date: endDate
      }
    )
  },

  /**
   * 搜索股票
   * @param keyword 搜索关键词（股票代码或名称）
   * @param limit 返回数量限制
   */
  async searchStocks(keyword: string, limit = 10) {
    return ApiClient.get<StockSearchResponse>(
      '/api/backtest/stock/search',
      { keyword, limit }
    )
  }
}
