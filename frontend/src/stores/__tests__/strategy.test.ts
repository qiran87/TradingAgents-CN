/**
 * 策略Store单元测试
 *
 * 使用vitest测试Pinia store的所有功能
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useStrategyStore } from '../strategy'
import { strategiesApi } from '@/api/strategies'
import type { StrategySummary, StrategyDetail, StrategyCategory } from '@/api/strategies'

// Mock API
vi.mock('@/api/strategies', () => ({
  strategiesApi: {
    getStrategies: vi.fn(),
    getStrategyDetail: vi.fn(),
    getCategories: vi.fn(),
    validateParams: vi.fn()
  }
}))

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    error: vi.fn(),
    success: vi.fn(),
    info: vi.fn()
  }
}))

describe('StrategyStore', () => {
  beforeEach(() => {
    // 创建新的pinia实例
    setActivePinia(createPinia())
    // 清除所有mock
    vi.clearAllMocks()
  })

  const mockStrategies: StrategySummary[] = [
    {
      strategy_id: 'dual_ma',
      name: '双均线策略',
      description: '基于快慢均线的交叉信号进行交易',
      category: 'trend',
      parameter_count: 2,
      usage_count: 100,
      is_builtin: true
    },
    {
      strategy_id: 'bollinger_bands',
      name: '布林带策略',
      description: '基于布林带的突破和回归进行交易',
      category: 'oscillation',
      parameter_count: 2,
      usage_count: 50,
      is_builtin: true
    },
    {
      strategy_id: 'macd',
      name: 'MACD策略',
      description: '基于MACD指标的金叉死叉进行交易',
      category: 'trend',
      parameter_count: 3,
      usage_count: 75,
      is_builtin: true
    }
  ]

  const mockCategories: StrategyCategory[] = [
    {
      category_id: 'trend',
      name: '趋势跟踪策略',
      description: '基于价格趋势的策略',
      strategy_count: 2
    },
    {
      category_id: 'oscillation',
      name: '震荡策略',
      description: '基于价格波动的策略',
      strategy_count: 1
    }
  ]

  const mockStrategyDetail: StrategyDetail = {
    strategy_id: 'dual_ma',
    name: '双均线策略',
    description: '基于快慢均线的交叉信号进行交易',
    long_description: '双均线策略是一种经典的趋势跟踪策略',
    category: 'trend',
    parameters: [
      {
        name: 'short_window',
        type: 'int',
        default_value: 5,
        range: { min: 2, max: 60 },
        description: '短期均线窗口',
        required: true
      },
      {
        name: 'long_window',
        type: 'int',
        default_value: 20,
        range: { min: 5, max: 250 },
        description: '长期均线窗口',
        required: true
      }
    ],
    usage_count: 100,
    is_builtin: true,
    parameter_count: 2,
    created_at: '2024-01-01T00:00:00Z'
  }

  describe('状态初始化', () => {
    it('应该有正确的初始状态', () => {
      const store = useStrategyStore()

      expect(store.strategies).toEqual([])
      expect(store.categories).toEqual([])
      expect(store.currentStrategy).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.currentCategory).toBe('all')
      expect(store.searchKeyword).toBe('')
      expect(store.sortBy).toBe('usage_count')
    })
  })

  describe('fetchStrategies', () => {
    it('应该成功获取策略列表', async () => {
      const store = useStrategyStore()
      vi.mocked(strategiesApi.getStrategies).mockResolvedValue({
        strategies: mockStrategies
      })

      await store.fetchStrategies()

      expect(store.strategies).toEqual(mockStrategies)
      expect(store.loading).toBe(false)
      expect(strategiesApi.getStrategies).toHaveBeenCalledOnce()
    })

    it('应该在失败时显示错误消息', async () => {
      const store = useStrategyStore()
      const error = new Error('获取失败')
      vi.mocked(strategiesApi.getStrategies).mockRejectedValue(error)

      await expect(store.fetchStrategies()).rejects.toThrow('获取失败')
      expect(store.loading).toBe(false)
    })

    it('应该在请求时设置loading状态', async () => {
      const store = useStrategyStore()
      let resolvePromise: (value: any) => void

      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve
      })

      vi.mocked(strategiesApi.getStrategies).mockReturnValue(pendingPromise as any)

      const fetchPromise = store.fetchStrategies()

      expect(store.loading).toBe(true)

      resolvePromise!({ strategies: mockStrategies })
      await fetchPromise

      expect(store.loading).toBe(false)
    })
  })

  describe('fetchCategories', () => {
    it('应该成功获取分类列表', async () => {
      const store = useStrategyStore()
      vi.mocked(strategiesApi.getCategories).mockResolvedValue(mockCategories)

      await store.fetchCategories()

      expect(store.categories).toEqual(mockCategories)
      expect(strategiesApi.getCategories).toHaveBeenCalledOnce()
    })

    it('应该在失败时显示错误消息', async () => {
      const store = useStrategyStore()
      const error = new Error('获取分类失败')
      vi.mocked(strategiesApi.getCategories).mockRejectedValue(error)

      await expect(store.fetchCategories()).rejects.toThrow('获取分类失败')
    })
  })

  describe('fetchStrategyDetail', () => {
    it('应该成功获取策略详情', async () => {
      const store = useStrategyStore()
      vi.mocked(strategiesApi.getStrategyDetail).mockResolvedValue(mockStrategyDetail)

      const result = await store.fetchStrategyDetail('dual_ma')

      expect(result).toEqual(mockStrategyDetail)
      expect(store.currentStrategy).toEqual(mockStrategyDetail)
      expect(strategiesApi.getStrategyDetail).toHaveBeenCalledWith('dual_ma')
    })

    it('应该在失败时显示错误消息', async () => {
      const store = useStrategyStore()
      const error = new Error('获取详情失败')
      vi.mocked(strategiesApi.getStrategyDetail).mockRejectedValue(error)

      await expect(store.fetchStrategyDetail('dual_ma')).rejects.toThrow('获取详情失败')
    })
  })

  describe('validateParams', () => {
    it('应该成功校验有效参数', async () => {
      const store = useStrategyStore()
      const mockResult = { valid: true, errors: null }
      vi.mocked(strategiesApi.validateParams).mockResolvedValue(mockResult)

      const result = await store.validateParams('dual_ma', {
        short_window: 5,
        long_window: 20
      })

      expect(result).toEqual(mockResult)
      expect(strategiesApi.validateParams).toHaveBeenCalledWith('dual_ma', {
        params: { short_window: 5, long_window: 20 }
      })
    })

    it('应该成功校验无效参数', async () => {
      const store = useStrategyStore()
      const mockResult = {
        valid: false,
        errors: { long_window: '长期窗口必须大于短期窗口' }
      }
      vi.mocked(strategiesApi.validateParams).mockResolvedValue(mockResult)

      const result = await store.validateParams('dual_ma', {
        short_window: 30,
        long_window: 20
      })

      expect(result).toEqual(mockResult)
    })
  })

  describe('filteredStrategies', () => {
    beforeEach(() => {
      const store = useStrategyStore()
      store.strategies = mockStrategies
      store.categories = mockCategories
    })

    it('应该返回所有策略当没有筛选条件时', () => {
      const store = useStrategyStore()
      const filtered = store.filteredStrategies

      expect(filtered).toHaveLength(3)
    })

    it('应该按分类筛选策略', () => {
      const store = useStrategyStore()
      store.setCategory('trend')

      const filtered = store.filteredStrategies

      expect(filtered).toHaveLength(2)
      expect(filtered.every(s => s.category === 'trend')).toBe(true)
    })

    it('应该按关键词搜索策略', () => {
      const store = useStrategyStore()
      store.setSearchKeyword('双均线')

      const filtered = store.filteredStrategies

      expect(filtered).toHaveLength(1)
      expect(filtered[0].strategy_id).toBe('dual_ma')
    })

    it('应该在名称和描述中搜索', () => {
      const store = useStrategyStore()
      store.setSearchKeyword('策略')

      const filtered = store.filteredStrategies

      expect(filtered.length).toBeGreaterThan(0)
    })

    it('应该按使用次数排序', () => {
      const store = useStrategyStore()
      store.setSortBy('usage_count')

      const filtered = store.filteredStrategies

      expect(filtered[0].usage_count).toBeGreaterThanOrEqual(filtered[1].usage_count)
      expect(filtered[1].usage_count).toBeGreaterThanOrEqual(filtered[2].usage_count)
    })

    it('应该按名称升序排序', () => {
      const store = useStrategyStore()
      store.setSortBy('name_asc')

      const filtered = store.filteredStrategies

      expect(filtered[0].name).localeCompare(filtered[1].name, 'zh-CN')).toBeLessThanOrEqual(0)
    })

    it('应该按名称降序排序', () => {
      const store = useStrategyStore()
      store.setSortBy('name_desc')

      const filtered = store.filteredStrategies

      expect(filtered[0].name).localeCompare(filtered[1].name, 'zh-CN')).toBeGreaterThanOrEqual(0)
    })

    it('应该支持组合筛选', () => {
      const store = useStrategyStore()
      store.setCategory('trend')
      store.setSearchKeyword('策略')
      store.setSortBy('usage_count')

      const filtered = store.filteredStrategies

      expect(filtered.every(s => s.category === 'trend')).toBe(true)
      expect(filtered.every(s => s.name.includes('策略') || s.description.includes('策略'))).toBe(true)
    })
  })

  describe('categoryCountMap', () => {
    beforeEach(() => {
      const store = useStrategyStore()
      store.strategies = mockStrategies
      store.categories = mockCategories
    })

    it('应该正确统计所有分类的策略数量', () => {
      const store = useStrategyStore()
      const countMap = store.categoryCountMap

      expect(countMap.get('all')).toBe(3)
      expect(countMap.get('trend')).toBe(2)
      expect(countMap.get('oscillation')).toBe(1)
    })
  })

  describe('setCategory', () => {
    it('应该设置当前分类', () => {
      const store = useStrategyStore()
      store.setCategory('trend')

      expect(store.currentCategory).toBe('trend')
    })

    it('应该设置为all显示所有策略', () => {
      const store = useStrategyStore()
      store.setCategory('all')

      expect(store.currentCategory).toBe('all')
    })
  })

  describe('setSearchKeyword', () => {
    it('应该设置搜索关键词', () => {
      const store = useStrategyStore()
      store.setSearchKeyword('双均线')

      expect(store.searchKeyword).toBe('双均线')
    })

    it('应该清空搜索关键词', () => {
      const store = useStrategyStore()
      store.setSearchKeyword('')

      expect(store.searchKeyword).toBe('')
    })
  })

  describe('setSortBy', () => {
    it('应该设置排序方式', () => {
      const store = useStrategyStore()
      store.setSortBy('name_asc')

      expect(store.sortBy).toBe('name_asc')
    })
  })

  describe('resetFilters', () => {
    it('应该重置所有筛选条件', () => {
      const store = useStrategyStore()
      store.strategies = mockStrategies

      // 设置一些筛选条件
      store.setCategory('trend')
      store.setSearchKeyword('双均线')
      store.setSortBy('name_asc')

      // 重置
      store.resetFilters()

      expect(store.currentCategory).toBe('all')
      expect(store.searchKeyword).toBe('')
      expect(store.sortBy).toBe('usage_count')
    })
  })

  describe('initialize', () => {
    it('应该同时获取策略和分类', async () => {
      const store = useStrategyStore()
      vi.mocked(strategiesApi.getStrategies).mockResolvedValue({
        strategies: mockStrategies
      })
      vi.mocked(strategiesApi.getCategories).mockResolvedValue(mockCategories)

      await store.initialize()

      expect(store.strategies).toEqual(mockStrategies)
      expect(store.categories).toEqual(mockCategories)
      expect(strategiesApi.getStrategies).toHaveBeenCalledOnce()
      expect(strategiesApi.getCategories).toHaveBeenCalledOnce()
    })

    it('应该在初始化失败时抛出错误', async () => {
      const store = useStrategyStore()
      vi.mocked(strategiesApi.getStrategies).mockRejectedValue(new Error('网络错误'))

      await expect(store.initialize()).rejects.toThrow('网络错误')
    })
  })

  describe('边界情况', () => {
    it('应该处理空的策略列表', () => {
      const store = useStrategyStore()
      store.strategies = []

      const filtered = store.filteredStrategies

      expect(filtered).toHaveLength(0)
    })

    it('应该处理搜索关键词为空字符串', () => {
      const store = useStrategyStore()
      store.strategies = mockStrategies
      store.setSearchKeyword('')

      const filtered = store.filteredStrategies

      expect(filtered).toHaveLength(3)
    })

    it('应该处理搜索关键词没有匹配结果', () => {
      const store = useStrategyStore()
      store.strategies = mockStrategies
      store.setSearchKeyword('不存在的内容xyz')

      const filtered = store.filteredStrategies

      expect(filtered).toHaveLength(0)
    })

    it('应该处理分类没有匹配结果', () => {
      const store = useStrategyStore()
      store.strategies = mockStrategies
      store.setCategory('non_existent')

      const filtered = store.filteredStrategies

      expect(filtered).toHaveLength(0)
    })
  })
})
