/**
 * 策略管理 Store
 *
 * 管理策略相关的状态和操作
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { strategiesApi, type StrategySummary, type StrategyDetail, type StrategyCategory } from '@/api/strategies'
import { ElMessage } from 'element-plus'

export const useStrategyStore = defineStore('strategy', () => {
  // ===================== 状态 =====================
  const strategies = ref<StrategySummary[]>([])
  const categories = ref<StrategyCategory[]>([])
  const currentStrategy = ref<StrategyDetail | null>(null)
  const loading = ref<boolean>(false)

  // 筛选条件
  const currentCategory = ref<string>('all')
  const searchKeyword = ref<string>('')
  const sortBy = ref<string>('usage_count')

  // ===================== 计算属性 =====================

  /**
   * 过滤后的策略列表
   */
  const filteredStrategies = computed(() => {
    let result = strategies.value

    // 分类过滤
    if (currentCategory.value !== 'all') {
      result = result.filter(s => s.category === currentCategory.value)
    }

    // 关键词搜索
    if (searchKeyword.value) {
      const keyword = searchKeyword.value.toLowerCase()
      result = result.filter(s =>
        s.name.toLowerCase().includes(keyword) ||
        s.description.toLowerCase().includes(keyword)
      )
    }

    // 排序
    result = [...result].sort((a, b) => {
      switch (sortBy.value) {
        case 'usage_count':
          return b.usage_count - a.usage_count
        case 'created_at':
          return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime()
        case 'name_asc':
          return a.name.localeCompare(b.name, 'zh-CN')
        case 'name_desc':
          return b.name.localeCompare(a.name, 'zh-CN')
        default:
          return 0
      }
    })

    return result
  })

  /**
   * 当前分类的策略数量
   */
  const categoryCountMap = computed(() => {
    const map = new Map<string, number>()
    map.set('all', strategies.value.length)
    strategies.value.forEach(s => {
      const count = map.get(s.category) || 0
      map.set(s.category, count + 1)
    })
    return map
  })

  // ===================== Actions =====================

  /**
   * 获取策略列表
   */
  async function fetchStrategies() {
    loading.value = true
    try {
      const response = await strategiesApi.getStrategies()
      strategies.value = response.strategies
    } catch (error: any) {
      console.error('获取策略列表失败:', error)
      ElMessage.error(error.message || '获取策略列表失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取策略分类
   */
  async function fetchCategories() {
    try {
      const data = await strategiesApi.getCategories()
      categories.value = data
    } catch (error: any) {
      console.error('获取策略分类失败:', error)
      ElMessage.error(error.message || '获取策略分类失败')
      throw error
    }
  }

  /**
   * 获取策略详情
   */
  async function fetchStrategyDetail(strategyId: string) {
    try {
      const data = await strategiesApi.getStrategyDetail(strategyId)
      currentStrategy.value = data
      return data
    } catch (error: any) {
      console.error('获取策略详情失败:', error)
      ElMessage.error(error.message || '获取策略详情失败')
      throw error
    }
  }

  /**
   * 校验策略参数
   */
  async function validateParams(strategyId: string, params: Record<string, any>) {
    try {
      const result = await strategiesApi.validateParams(strategyId, { params })
      return result
    } catch (error: any) {
      console.error('校验策略参数失败:', error)
      ElMessage.error(error.message || '校验策略参数失败')
      throw error
    }
  }

  /**
   * 设置当前分类
   */
  function setCategory(category: string) {
    currentCategory.value = category
  }

  /**
   * 设置搜索关键词
   */
  function setSearchKeyword(keyword: string) {
    searchKeyword.value = keyword
  }

  /**
   * 设置排序方式
   */
  function setSortBy(sort: string) {
    sortBy.value = sort
  }

  /**
   * 重置所有筛选条件
   */
  function resetFilters() {
    currentCategory.value = 'all'
    searchKeyword.value = ''
    sortBy.value = 'usage_count'
  }

  /**
   * 初始化数据
   */
  async function initialize() {
    await Promise.all([
      fetchStrategies(),
      fetchCategories()
    ])
  }

  // ===================== 返回 =====================
  return {
    // 状态
    strategies,
    categories,
    currentStrategy,
    loading,
    currentCategory,
    searchKeyword,
    sortBy,

    // 计算属性
    filteredStrategies,
    categoryCountMap,

    // Actions
    fetchStrategies,
    fetchCategories,
    fetchStrategyDetail,
    validateParams,
    setCategory,
    setSearchKeyword,
    setSortBy,
    resetFilters,
    initialize
  }
})
