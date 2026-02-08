/**
 * 交易日历API
 */
import { request } from './request'

/**
 * 交易日信息
 */
export interface TradingDayInfo {
  date: string                    // 日期 YYYY-MM-DD
  is_trading_day: boolean         // 是否为交易日
  is_holiday: boolean             // 是否为节假日
  is_weekend: boolean             // 是否为周末
  weekday: number                 // 星期几（1-7，1为周一）
  holiday_name?: string           // 节假日名称
}

/**
 * 交易日列表响应
 */
export interface TradingDaysListResponse {
  trading_days: string[]          // 交易日列表
  total: number                   // 总数
}

/**
 * 交易日历统计信息
 */
export interface TradingCalendarInfo {
  date_range: {
    start_date: string
    end_date: string
  }
  trading_days_count: number
  holidays_count: number
  weekends_count: number
  first_trading_day: {
    date: string
    weekday: string
  }
  last_trading_day: {
    date: string
    weekday: string
  }
  trading_day_percentage: number
}

/**
 * 前一个交易日响应
 */
export interface PreviousTradingDayResponse {
  previous_trading_day: string
  previous_date: string
}

/**
 * 后一个交易日响应
 */
export interface NextTradingDayResponse {
  next_trading_day: string
  next_date: string
}

/**
 * 交易日历API
 */
export const tradingCalendarApi = {
  /**
   * 获取交易日列表
   * @param startDate 起始日期 YYYY-MM-DD
   * @param endDate 结束日期 YYYY-MM-DD
   */
  async getTradingDays(startDate: string, endDate: string) {
    return request.get<TradingDaysListResponse>(
      '/api/backtest/trading-days',
      { start_date: startDate, end_date: endDate }
    )
  },

  /**
   * 获取交易日历信息
   * @param startDate 起始日期 YYYY-MM-DD
   * @param endDate 结束日期 YYYY-MM-DD
   */
  async getTradingCalendarInfo(startDate: string, endDate: string) {
    return request.get<TradingCalendarInfo>(
      '/api/backtest/trading-days/info',
      { start_date: startDate, end_date: endDate }
    )
  },

  /**
   * 判断是否为交易日
   * @param date 日期 YYYY-MM-DD
   */
  async isTradingDay(date: string) {
    return request.get<TradingDayInfo>(`/api/backtest/trading-days/${date}`)
  },

  /**
   * 获取前一个交易日
   * @param date 日期 YYYY-MM-DD
   */
  async getPreviousTradingDay(date: string) {
    return request.get<PreviousTradingDayResponse>(
      `/api/backtest/trading-days/${date}/previous`
    )
  },

  /**
   * 获取后一个交易日
   * @param date 日期 YYYY-MM-DD
   */
  async getNextTradingDay(date: string) {
    return request.get<NextTradingDayResponse>(
      `/api/backtest/trading-days/${date}/next`
    )
  }
}
