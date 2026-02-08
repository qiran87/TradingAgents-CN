/**
 * 单元测试：TradingDayRangePicker 组件
 * 测试交易日历范围选择器的主要功能
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import TradingDayRangePicker from '@/components/TradingDayRangePicker.vue'

// Mock tradingCalendarStore
vi.mock('@/stores/tradingCalendar', () => ({
  useTradingCalendarStore: () => ({
    isTradingDay: vi.fn((date: string) => {
      // Mock: 周末不是交易日，周一到周五是交易日
      const date = new Date(date)
      const day = date.getDay()
      return day > 0 && day < 6 // 1-5 是周一到周五
    }),
    getTradingDaysInRange: vi.fn((start: string, end: string) => {
      // Mock: 简单返回范围内的所有日期（排除周末）
      const dates: string[] = []
      const current = new Date(start)
      const endDate = new Date(end)

      while (current <= endDate) {
        const day = current.getDay()
        if (day > 0 && day < 6) { // 排除周末
          dates.push(current.toISOString().split('T')[0])
        }
        current.setDate(current.getDate() + 1)
      }
      return Promise.resolve(dates)
    })
  })
}))

describe('TradingDayRangePicker 组件测试', () => {
  it('组件应该正确渲染', () => {
    const wrapper = mount(TradingDayRangePicker, {
      props: {
        startDate: '',
        endDate: '',
        showStats: true,
        showQuickOptions: true
      }
    })

    expect(wrapper.find('.trading-day-range-picker').exists()).toBe(true)
    expect(wrapper.find('input[type="text"]').exists()).toBe(true) // el-date-picker
  })

  it('应该显示交易日统计信息', async () => {
    const wrapper = mount(TradingDayRangePicker, {
      props: {
        startDate: '2024-01-02',
        endDate: '2024-01-05',
        showStats: true
      }
    })

    // 等待异步操作完成
    await new Promise(resolve => setTimeout(resolve, 100))
    await wrapper.vm.$nextTick()

    // 检查是否显示交易日统计
    const statsElement = wrapper.find('.trading-days-stats')
    expect(statsElement.exists()).toBe(true)
  })

  it('应该显示快捷选项', () => {
    const wrapper = mount(TradingDayRangePicker, {
      props: {
        startDate: '',
        endDate: '',
        showQuickOptions: true
      }
    })

    const quickOptions = wrapper.find('.quick-options')
    expect(quickOptions.exists()).toBe(true)

    // 检查快捷选项按钮
    const buttons = quickOptions.findAll('button')
    expect(buttons.length).toBeGreaterThan(0)
  })

  it('应该正确触发交易日变化事件', async () => {
    const wrapper = mount(TradingDayRangePicker, {
      props: {
        startDate: '',
        endDate: ''
      }
    })

    // Mock emit
    const emitSpy = vi.spyOn(wrapper.vm, '$emit')

    // 模拟选择日期范围
    await wrapper.vm.handleDateRangeChange(['2024-01-02', '2024-01-05'])

    // 等待异步操作
    await new Promise(resolve => setTimeout(resolve, 100))
    await wrapper.vm.$nextTick()

    // 验证事件是否触发
    expect(emitSpy).toHaveBeenCalled()
  })

  it('应该正确计算交易日数量', async () => {
    const wrapper = mount(TradingDayRangePicker, {
      props: {
        startDate: '2024-01-02',  // 周二
        endDate: '2024-01-05'     // 周五
      }
    })

    // 等待异步操作
    await new Promise(resolve => setTimeout(resolve, 100))
    await wrapper.vm.$nextTick()

    // 2024-01-02 到 2024-01-05 应该有 4 个交易日（周二到周五）
    expect(wrapper.vm.tradingDaysList.length).toBe(4)
    expect(wrapper.vm.tradingDaysCount).toBe(4)
  })

  it('应该支持快捷选项选择', async () => {
    const wrapper = mount(TradingDayRangePicker, {
      props: {
        startDate: '',
        endDate: '',
        showQuickOptions: true
      }
    })

    // 测试选择"近1月"快捷选项
    await wrapper.vm.selectQuickOption('1M')

    // 等待异步操作
    await new Promise(resolve => setTimeout(resolve, 100))
    await wrapper.vm.$nextTick()

    // 验证日期范围已设置
    expect(wrapper.vm.dateRange).not.toBeNull()
    expect(wrapper.vm.dateRange).toHaveLength(2)
  })

  it('应该正确禁用非交易日', async () => {
    const wrapper = mount(TradingDayRangePicker, {
      props: {
        startDate: '',
        endDate: ''
      }
    })

    // 测试周六（2024-01-06是周六）
    const saturday = new Date('2024-01-06')
    const isDisabled = await wrapper.vm.disabledDate(saturday)

    expect(isDisabled).toBe(true)
  })

  it('应该正确标记交易日样式', async () => {
    const wrapper = mount(TradingDayRangePicker, {
      props: {
        startDate: '',
        endDate: ''
      }
    })

    // 测试交易日
    const tradingDay = new Date('2024-01-02') // 周二
    const className = await wrapper.vm.cellClassName(tradingDay)

    expect(className).toBe('trading-day')
  })

  it('应该正确处理空日期范围', async () => {
    const wrapper = mount(TradingDayRangePicker, {
      props: {
        startDate: '',
        endDate: ''
      }
    })

    await wrapper.vm.handleDateRangeChange(null)

    // 验证状态已重置
    expect(wrapper.vm.tradingDaysList).toEqual([])
    expect(wrapper.vm.tradingDaysCount).toBe(0)
  })

  it('应该显示非交易日警告', async () => {
    const wrapper = mount(TradingDayRangePicker, {
      props: {
        startDate: '2024-01-06', // 周六
        endDate: '2024-01-07'   // 周日
      }
    })

    // 等待异步操作
    await new Promise(resolve => setTimeout(resolve, 100))
    await wrapper.vm.$nextTick()

    // 检查警告是否显示
    const warning = wrapper.find('.non-trading-warning')
    expect(warning.exists()).toBe(true)
  })
})
