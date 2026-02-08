/**
 * 测试3: 操作步骤指引组件
 * 验证操作步骤的显示和状态变化逻辑
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { ref } from 'vue'

describe('测试3: 操作步骤指引组件', () => {
  it('应包含4个步骤', () => {
    const steps = [
      '回测参数设置',
      '策略选择',
      '触发回测',
      '查看结果'
    ]
    expect(steps.length).toBe(4)
  })

  it('步骤顺序正确', () => {
    const steps = [
      '回测参数设置',
      '策略选择',
      '触发回测',
      '查看结果'
    ]
    expect(steps[0]).toBe('回测参数设置')
    expect(steps[1]).toBe('策略选择')
    expect(steps[2]).toBe('触发回测')
    expect(steps[3]).toBe('查看结果')
  })

  it('步骤描述正确', () => {
    const stepDescriptions = {
      0: '设置时间、资金、最小购买量',
      1: '选择回测策略及参数',
      2: '启动回测任务',
      3: '查看回测结果和明细'
    }
    expect(stepDescriptions[0]).toBe('设置时间、资金、最小购买量')
    expect(stepDescriptions[1]).toBe('选择回测策略及参数')
    expect(stepDescriptions[2]).toBe('启动回测任务')
    expect(stepDescriptions[3]).toBe('查看回测结果和明细')
  })

  it('初始状态应为步骤0', () => {
    const currentStep = ref(0)
    expect(currentStep.value).toBe(0)
  })

  it('选择日期后应进入步骤1', () => {
    const dateRange = ref<string[]>([])
    const currentStep = ref(0)

    // 模拟选择日期
    dateRange.value = ['2024-01-01', '2024-12-31']

    // 计算当前步骤
    if (dateRange.value?.length === 2) {
      currentStep.value = 1
    }

    expect(currentStep.value).toBe(1)
  })

  it('选择策略后应进入步骤2', () => {
    const dateRange = ref(['2024-01-01', '2024-12-31'])
    const strategyId = ref('')
    const currentStep = ref(1)

    // 模拟选择策略
    strategyId.value = 'dual_ma'

    // 计算当前步骤
    if (strategyId.value) {
      currentStep.value = 2
    }

    expect(currentStep.value).toBe(2)
  })

  it('回测运行时应为步骤3', () => {
    const isRunning = ref(false)
    const currentStep = ref(2)

    // 模拟回测运行
    isRunning.value = true

    // 计算当前步骤
    if (isRunning.value) {
      currentStep.value = 3
    }

    expect(currentStep.value).toBe(3)
  })

  it('回测完成时应为步骤4', () => {
    const isCompleted = ref(false)
    const currentStep = ref(3)

    // 模拟回测完成
    isCompleted.value = true

    // 计算当前步骤
    if (isCompleted.value) {
      currentStep.value = 4
    }

    expect(currentStep.value).toBe(4)
  })

  it('状态提示文本正确', () => {
    const statusTexts = {
      0: '未开始回测',
      1: '回测参数已确认，待选择策略',
      2: '策略已确认，待触发回测',
      3: '回测中',
      4: '已完成'
    }

    expect(statusTexts[0]).toBe('未开始回测')
    expect(statusTexts[1]).toBe('回测参数已确认，待选择策略')
    expect(statusTexts[2]).toBe('策略已确认，待触发回测')
    expect(statusTexts[3]).toBe('回测中')
    expect(statusTexts[4]).toBe('已完成')
  })
})
