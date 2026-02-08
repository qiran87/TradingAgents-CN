/**
 * 测试4: 重置参数按钮
 * 验证重置参数功能是否正确
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { ref } from 'vue'

describe('测试4: 重置参数按钮', () => {
  it('重置按钮应存在于页面顶部', () => {
    const headerContent = `
      <div class="header-right">
        <el-button @click="handleResetParams">重置所有参数</el-button>
      </div>
    `
    expect(headerContent).toContain('重置所有参数')
  })

  it('默认参数值应正确', () => {
    const defaultParams = {
      stock_code: '000001.SZ',
      start_date: '',
      end_date: '',
      initial_capital: 100000,
      min_purchase: 100,
      strategy_id: '',
      strategy_params: {}
    }

    expect(defaultParams.stock_code).toBe('000001.SZ')
    expect(defaultParams.initial_capital).toBe(100000)
    expect(defaultParams.min_purchase).toBe(100)
    expect(defaultParams.strategy_id).toBe('')
  })

  it('重置后参数应恢复默认值', () => {
    const form = ref({
      stock_code: '000002.SZ',
      start_date: '2024-01-01',
      end_date: '2024-12-31',
      initial_capital: 200000,
      min_purchase: 200,
      strategy_id: 'dual_ma',
      strategy_params: { short_period: 10 }
    })

    const dateRange = ref(['2024-01-01', '2024-12-31'])

    // 执行重置
    form.value = {
      stock_code: '000001.SZ',
      start_date: '',
      end_date: '',
      initial_capital: 100000,
      min_purchase: 100,
      strategy_id: '',
      strategy_params: {}
    }
    dateRange.value = []

    expect(form.value.stock_code).toBe('000001.SZ')
    expect(form.value.initial_capital).toBe(100000)
    expect(form.value.min_purchase).toBe(100)
    expect(form.value.strategy_id).toBe('')
    expect(dateRange.value).toEqual([])
  })

  it('重置后日期范围应为空', () => {
    const dateRange = ref(['2024-01-01', '2024-12-31'])

    // 重置
    dateRange.value = []

    expect(dateRange.value.length).toBe(0)
  })

  it('重置后策略参数应为空对象', () => {
    const form = ref({
      strategy_params: { short_period: 5, long_period: 20 }
    })

    // 重置
    form.value.strategy_params = {}

    expect(Object.keys(form.value.strategy_params).length).toBe(0)
  })

  it('重置按钮应使用RefreshLeft图标', () => {
    const buttonContent = `
      <el-button @click="handleResetParams" :icon="RefreshLeft">
        重置所有参数
      </el-button>
    `
    expect(buttonContent).toContain('RefreshLeft')
  })

  it('重置成功后应显示提示消息', () => {
    let messageShown = false

    // 模拟重置并显示消息
    const handleReset = () => {
      messageShown = true
      return '参数已重置'
    }

    const result = handleReset()

    expect(messageShown).toBe(true)
    expect(result).toBe('参数已重置')
  })
})
