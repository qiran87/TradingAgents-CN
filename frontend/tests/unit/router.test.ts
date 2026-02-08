/**
 * 测试1: 导航名称修改
 * 验证路由配置中的导航名称是否正确
 */
import { describe, it, expect } from 'vitest'
import router from '@/router'

describe('测试1: 导航名称修改', () => {
  it('一级导航名称应为"股票回测"', () => {
    const backtestRoute = router.getRoutes().find(route => route.path === '/backtest')
    expect(backtestRoute).toBeDefined()
    expect(backtestRoute?.meta?.title).toBe('股票回测')
  })

  it('二级菜单"执行股票回测"存在', () => {
    const controlRoute = router.getRoutes().find(route => route.name === 'BacktestControl')
    expect(controlRoute).toBeDefined()
    expect(controlRoute?.meta?.title).toBe('执行股票回测')
  })

  it('二级菜单"回测策略列表"存在', () => {
    const strategiesRoute = router.getRoutes().find(route => route.name === 'BacktestStrategies')
    expect(strategiesRoute).toBeDefined()
    expect(strategiesRoute?.meta?.title).toBe('回测策略列表')
  })

  it('二级菜单"历史回测汇总"存在', () => {
    const historyRoute = router.getRoutes().find(route => route.name === 'BacktestHistory')
    expect(historyRoute).toBeDefined()
    expect(historyRoute?.meta?.title).toBe('历史回测汇总')
  })

  it('二级菜单顺序正确', () => {
    const backtestRoute = router.getRoutes().find(route => route.path === '/backtest')
    const children = backtestRoute?.children || []

    if (children.length > 0) {
      expect(children[0].meta?.title).toBe('执行股票回测')
      expect(children[1].meta?.title).toBe('回测策略列表')
      expect(children[2].meta?.title).toBe('历史回测汇总')
    }
  })

  it('导航使用TrendCharts图标', () => {
    const backtestRoute = router.getRoutes().find(route => route.path === '/backtest')
    expect(backtestRoute?.meta?.icon).toBe('TrendCharts')
  })

  it('导航需要认证', () => {
    const backtestRoute = router.getRoutes().find(route => route.path === '/backtest')
    expect(backtestRoute?.meta?.requiresAuth).toBe(true)
  })
})
