/**
 * 策略API单元测试
 *
 * 使用vitest测试策略API的所有方法
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { strategiesApi } from '../strategies'
import axios from 'axios'

// Mock axios
vi.mock('axios')
const mockedAxios = vi.mocked(axios)

describe('strategiesApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const mockStrategies = [
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
    }
  ]

  const mockStrategyDetail = {
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

  const mockCategories = [
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

  describe('getStrategies', () => {
    it('应该成功获取策略列表', async () => {
      const mockResponse = {
        data: {
          strategies: mockStrategies,
          total: 2
        }
      }
      mockedAxios.get.mockResolvedValue(mockResponse)

      const result = await strategiesApi.getStrategies()

      expect(result).toEqual(mockResponse.data)
      expect(mockedAxios.get).toHaveBeenCalledWith('/api/backtest/strategies', {
        params: undefined
      })
    })

    it('应该支持查询参数', async () => {
      const mockResponse = {
        data: {
          strategies: mockStrategies,
          total: 2
        }
      }
      mockedAxios.get.mockResolvedValue(mockResponse)

      const params = {
        category: 'trend',
        search: '双均线',
        sort_by: 'usage_count',
        sort_order: -1,
        skip: 0,
        limit: 20
      }

      await strategiesApi.getStrategies(params)

      expect(mockedAxios.get).toHaveBeenCalledWith('/api/backtest/strategies', {
        params
      })
    })

    it('应该在API调用失败时抛出错误', async () => {
      const error = new Error('网络错误')
      mockedAxios.get.mockRejectedValue(error)

      await expect(strategiesApi.getStrategies()).rejects.toThrow('网络错误')
    })

    it('应该处理空策略列表', async () => {
      const mockResponse = {
        data: {
          strategies: [],
          total: 0
        }
      }
      mockedAxios.get.mockResolvedValue(mockResponse)

      const result = await strategiesApi.getStrategies()

      expect(result.strategies).toEqual([])
      expect(result.total).toBe(0)
    })
  })

  describe('getStrategyDetail', () => {
    it('应该成功获取策略详情', async () => {
      const mockResponse = {
        data: mockStrategyDetail
      }
      mockedAxios.get.mockResolvedValue(mockResponse)

      const result = await strategiesApi.getStrategyDetail('dual_ma')

      expect(result).toEqual(mockStrategyDetail)
      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/api/backtest/strategies/dual_ma'
      )
    })

    it('应该处理不存在的策略', async () => {
      const error = {
        response: {
          status: 404,
          data: { detail: '策略不存在' }
        }
      }
      mockedAxios.get.mockRejectedValue(error)

      await expect(strategiesApi.getStrategyDetail('non_existent')).rejects.toEqual(
        error
      )
    })

    it('应该包含完整的参数信息', async () => {
      const mockResponse = {
        data: mockStrategyDetail
      }
      mockedAxios.get.mockResolvedValue(mockResponse)

      const result = await strategiesApi.getStrategyDetail('dual_ma')

      expect(result.parameters).toHaveLength(2)
      expect(result.parameters[0]).toHaveProperty('name')
      expect(result.parameters[0]).toHaveProperty('type')
      expect(result.parameters[0]).toHaveProperty('default_value')
      expect(result.parameters[0]).toHaveProperty('description')
      expect(result.parameters[0]).toHaveProperty('required')
    })
  })

  describe('getCategories', () => {
    it('应该成功获取分类列表', async () => {
      const mockResponse = {
        data: mockCategories
      }
      mockedAxios.get.mockResolvedValue(mockResponse)

      const result = await strategiesApi.getCategories()

      expect(result).toEqual(mockCategories)
      expect(mockedAxios.get).toHaveBeenCalledWith(
        '/api/backtest/strategies/categories'
      )
    })

    it('应该处理空分类列表', async () => {
      const mockResponse = {
        data: []
      }
      mockedAxios.get.mockResolvedValue(mockResponse)

      const result = await strategiesApi.getCategories()

      expect(result).toEqual([])
    })

    it('应该在API调用失败时抛出错误', async () => {
      const error = new Error('获取分类失败')
      mockedAxios.get.mockRejectedValue(error)

      await expect(strategiesApi.getCategories()).rejects.toThrow('获取分类失败')
    })

    it('应该返回包含strategy_count的分类', async () => {
      const mockResponse = {
        data: mockCategories
      }
      mockedAxios.get.mockResolvedValue(mockResponse)

      const result = await strategiesApi.getCategories()

      expect(result[0]).toHaveProperty('strategy_count')
      expect(typeof result[0].strategy_count).toBe('number')
    })
  })

  describe('validateParams', () => {
    it('应该成功校验有效参数', async () => {
      const mockResponse = {
        data: {
          valid: true,
          errors: null
        }
      }
      mockedAxios.post.mockResolvedValue(mockResponse)

      const params = {
        short_window: 5,
        long_window: 20
      }

      const result = await strategiesApi.validateParams('dual_ma', { params })

      expect(result.valid).toBe(true)
      expect(result.errors).toBeNull()
      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/api/backtest/strategies/dual_ma/validate-params',
        { params }
      )
    })

    it('应该返回校验错误信息', async () => {
      const mockResponse = {
        data: {
          valid: false,
          errors: {
            long_window: '长期窗口必须大于短期窗口',
            short_window: '短期窗口不能小于2'
          }
        }
      }
      mockedAxios.post.mockResolvedValue(mockResponse)

      const params = {
        short_window: 1,
        long_window: 20
      }

      const result = await strategiesApi.validateParams('dual_ma', { params })

      expect(result.valid).toBe(false)
      expect(result.errors).toHaveProperty('long_window')
      expect(result.errors).toHaveProperty('short_window')
    })

    it('应该处理策略不存在的情况', async () => {
      const error = {
        response: {
          status: 404,
          data: { detail: '策略不存在' }
        }
      }
      mockedAxios.post.mockRejectedValue(error)

      await expect(
        strategiesApi.validateParams('non_existent', { params: {} })
      ).rejects.toEqual(error)
    })

    it('应该处理空参数对象', async () => {
      const mockResponse = {
        data: {
          valid: false,
          errors: {
            short_window: '参数 short_window 是必填的',
            long_window: '参数 long_window 是必填的'
          }
        }
      }
      mockedAxios.post.mockResolvedValue(mockResponse)

      const result = await strategiesApi.validateParams('dual_ma', { params: {} })

      expect(result.valid).toBe(false)
      expect(result.errors).not.toBeNull()
    })
  })

  describe('API错误处理', () => {
    it('应该处理500服务器错误', async () => {
      const error = {
        response: {
          status: 500,
          data: { detail: '服务器内部错误' }
        }
      }
      mockedAxios.get.mockRejectedValue(error)

      await expect(strategiesApi.getStrategies()).rejects.toEqual(error)
    })

    it('应该处理网络超时', async () => {
      const error = new Error('timeout of 5000ms exceeded')
      mockedAxios.get.mockRejectedValue(error)

      await expect(strategiesApi.getStrategies()).rejects.toThrow('timeout')
    })

    it('应该处理未经授权的访问', async () => {
      const error = {
        response: {
          status: 401,
          data: { detail: '未授权' }
        }
      }
      mockedAxios.get.mockRejectedValue(error)

      await expect(strategiesApi.getStrategies()).rejects.toEqual(error)
    })
  })

  describe('数据格式验证', () => {
    it('策略摘要应该包含所有必需字段', async () => {
      const mockResponse = {
        data: {
          strategies: mockStrategies,
          total: 2
        }
      }
      mockedAxios.get.mockResolvedValue(mockResponse)

      const result = await strategiesApi.getStrategies()
      const strategy = result.strategies[0]

      expect(strategy).toHaveProperty('strategy_id')
      expect(strategy).toHaveProperty('name')
      expect(strategy).toHaveProperty('description')
      expect(strategy).toHaveProperty('category')
      expect(strategy).toHaveProperty('parameter_count')
      expect(strategy).toHaveProperty('usage_count')
      expect(strategy).toHaveProperty('is_builtin')
    })

    it('策略详情应该包含所有必需字段', async () => {
      const mockResponse = {
        data: mockStrategyDetail
      }
      mockedAxios.get.mockResolvedValue(mockResponse)

      const result = await strategiesApi.getStrategyDetail('dual_ma')

      expect(result).toHaveProperty('strategy_id')
      expect(result).toHaveProperty('name')
      expect(result).toHaveProperty('description')
      expect(result).toHaveProperty('category')
      expect(result).toHaveProperty('parameters')
      expect(result).toHaveProperty('usage_count')
      expect(result).toHaveProperty('is_builtin')
      expect(result).toHaveProperty('parameter_count')
      expect(result).toHaveProperty('created_at')
    })

    it('策略参数应该包含所有必需字段', async () => {
      const mockResponse = {
        data: mockStrategyDetail
      }
      mockedAxios.get.mockResolvedValue(mockResponse)

      const result = await strategiesApi.getStrategyDetail('dual_ma')
      const param = result.parameters[0]

      expect(param).toHaveProperty('name')
      expect(param).toHaveProperty('type')
      expect(param).toHaveProperty('default_value')
      expect(param).toHaveProperty('description')
      expect(param).toHaveProperty('required')
    })

    it('分类应该包含所有必需字段', async () => {
      const mockResponse = {
        data: mockCategories
      }
      mockedAxios.get.mockResolvedValue(mockResponse)

      const result = await strategiesApi.getCategories()
      const category = result[0]

      expect(category).toHaveProperty('category_id')
      expect(category).toHaveProperty('name')
      expect(category).toHaveProperty('strategy_count')
    })
  })

  describe('边界情况', () => {
    it('应该处理非常大的limit参数', async () => {
      const mockResponse = {
        data: {
          strategies: mockStrategies,
          total: 2
        }
      }
      mockedAxios.get.mockResolvedValue(mockResponse)

      const params = { limit: 1000 }

      await strategiesApi.getStrategies(params)

      expect(mockedAxios.get).toHaveBeenCalledWith('/api/backtest/strategies', {
        params
      })
    })

    it('应该处理特殊字符的搜索关键词', async () => {
      const mockResponse = {
        data: {
          strategies: mockStrategies,
          total: 2
        }
      }
      mockedAxios.get.mockResolvedValue(mockResponse)

      const params = { search: '策略@#$%' }

      await strategiesApi.getStrategies(params)

      expect(mockedAxios.get).toHaveBeenCalledWith('/api/backtest/strategies', {
        params
      })
    })

    it('应该处理包含参数的校验请求', async () => {
      const mockResponse = {
        data: {
          valid: true,
          errors: null
        }
      }
      mockedAxios.post.mockResolvedValue(mockResponse)

      const params = {
        short_window: 5,
        long_window: 20,
        // 额外的参数
        extra_param: 'value'
      }

      const result = await strategiesApi.validateParams('dual_ma', { params })

      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/api/backtest/strategies/dual_ma/validate-params',
        { params }
      )
    })
  })
})
