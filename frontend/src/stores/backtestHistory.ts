/**
 * 回测历史记录Store（增强版）- 管理历史记录数据
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { backtestHistoryApi } from '@/api/backtestHistory'
import type {
  HistoryRecord,
  HistoryDetailResponse,
  CompareHistoryResponse,
  ExportHistoryResponse
} from '@/api/backtestHistory'
import { ElMessage } from 'element-plus'

export const useBacktestHistoryStore = defineStore('backtestHistory', () => {
  // ===================== 状态 =====================

  // 历史记录列表
  const records = ref<HistoryRecord[]>([])
  const total = ref(0)
  const listLoading = ref(false)
  const listError = ref<string | null>(null)

  // 当前选中的历史记录
  const selectedRecordId = ref<string | null>(null)
  const recordDetail = ref<HistoryDetailResponse | null>(null)
  const detailLoading = ref(false)
  const detailError = ref<string | null>(null)

  // 对比记录
  const compareRecordIds = ref<string[]>([])
  const compareResults = ref<CompareHistoryResponse | null>(null)
  const compareLoading = ref(false)
  const compareError = ref<string | null>(null)

  // 删除状态
  const deleteLoading = ref(false)
  const deleteError = ref<string | null>(null)

  // 回收站视图
  const showRecycleBin = ref(false)

  // 批量选择
  const selectedRecords = ref<string[]>([])

  // 导出状态
  const exportLoading = ref(false)

  // 筛选条件
  const filters = ref({
    strategy_id: '',
    stock_code: '',
    search: ''
  })

  // 分页
  const pagination = ref({
    skip: 0,
    limit: 20
  })

  // ===================== 计算属性 =====================

  const hasRecords = computed(() => records.value.length > 0)
  const hasSelected = computed(() => selectedRecordId.value !== null)
  const canCompare = computed(
    () => compareRecordIds.value.length >= 2 && compareRecordIds.value.length <= 3
  )
  const hasBatchSelection = computed(() => selectedRecords.value.length > 0)
  const isRecycleBinView = computed(() => showRecycleBin.value)

  // ===================== Actions =====================

  /**
   * 获取历史记录列表
   */
  async function fetchHistoryList(reset = true) {
    listLoading.value = true
    listError.value = null

    if (reset) {
      pagination.value.skip = 0
      selectedRecords.value = []
    }

    try {
      const response = await backtestHistoryApi.getHistoryList({
        skip: pagination.value.skip,
        limit: pagination.value.limit,
        strategy_id: filters.value.strategy_id || undefined,
        stock_code: filters.value.stock_code || undefined,
        search: filters.value.search || undefined,
        include_deleted: showRecycleBin.value
      })

      if (reset) {
        records.value = response.data.records
      } else {
        records.value.push(...response.data.records)
      }
      total.value = response.data.total
    } catch (error: any) {
      listError.value = error.message || '获取历史记录列表失败'
      ElMessage.error(listError.value)
      throw error
    } finally {
      listLoading.value = false
    }
  }

  /**
   * 加载更多
   */
  async function loadMore() {
    pagination.value.skip += pagination.value.limit
    await fetchHistoryList(false)
  }

  /**
   * 切换到回收站视图
   */
  async function toggleRecycleBin(show: boolean) {
    showRecycleBin.value = show
    selectedRecords.value = []
    await fetchHistoryList(true)
  }

  /**
   * 获取历史记录详情
   */
  async function fetchHistoryDetail(recordId: string) {
    detailLoading.value = true
    detailError.value = null
    selectedRecordId.value = recordId

    try {
      const response = await backtestHistoryApi.getHistoryDetail(recordId)
      recordDetail.value = response.data
    } catch (error: any) {
      detailError.value = error.message || '获取历史记录详情失败'
      ElMessage.error(detailError.value)
      throw error
    } finally {
      detailLoading.value = false
    }
  }

  /**
   * 保存回测结果到历史记录
   */
  async function saveToHistory(backtestId: string, request: {
    name: string
    description?: string
    tags?: string[]
  }) {
    listLoading.value = true
    listError.value = null

    try {
      const response = await backtestHistoryApi.saveToHistory(backtestId, request)
      // 重新获取列表
      await fetchHistoryList()
      ElMessage.success('已保存到历史记录')
      return response.data
    } catch (error: any) {
      listError.value = error.message || '保存到历史记录失败'
      ElMessage.error(listError.value)
      throw error
    } finally {
      listLoading.value = false
    }
  }

  /**
   * 对比历史记录
   */
  async function compareHistory() {
    if (!canCompare.value) {
      compareError.value = '请选择2-3条记录进行对比'
      ElMessage.warning(compareError.value)
      return
    }

    compareLoading.value = true
    compareError.value = null

    try {
      const response = await backtestHistoryApi.compareHistory({
        record_ids: compareRecordIds.value
      })
      compareResults.value = response.data
    } catch (error: any) {
      compareError.value = error.message || '对比历史记录失败'
      ElMessage.error(compareError.value)
      throw error
    } finally {
      compareLoading.value = false
    }
  }

  /**
   * 添加对比记录
   */
  function addToCompare(recordId: string) {
    if (compareRecordIds.value.length >= 3) {
      compareError.value = '最多只能对比3条记录'
      ElMessage.warning(compareError.value)
      return
    }
    if (!compareRecordIds.value.includes(recordId)) {
      compareRecordIds.value.push(recordId)
      ElMessage.success('已添加到对比列表')
    }
  }

  /**
   * 移除对比记录
   */
  function removeFromCompare(recordId: string) {
    const index = compareRecordIds.value.indexOf(recordId)
    if (index > -1) {
      compareRecordIds.value.splice(index, 1)
    }
  }

  /**
   * 清空对比列表
   */
  function clearCompare() {
    compareRecordIds.value = []
    compareResults.value = null
    compareError.value = null
  }

  /**
   * 删除历史记录
   */
  async function deleteHistory(recordId: string, permanent: boolean = false) {
    deleteLoading.value = true
    deleteError.value = null

    try {
      await backtestHistoryApi.deleteHistory(recordId, permanent)

      // 从列表中移除
      const index = records.value.findIndex(r => r.record_id === recordId)
      if (index > -1) {
        records.value.splice(index, 1)
        total.value -= 1
      }

      // 如果删除的是当前选中的记录，清空详情
      if (selectedRecordId.value === recordId) {
        selectedRecordId.value = null
        recordDetail.value = null
      }

      // 从对比列表中移除
      removeFromCompare(recordId)

      ElMessage.success(permanent ? '记录已永久删除' : '记录已移至回收站')
    } catch (error: any) {
      deleteError.value = error.message || '删除历史记录失败'
      ElMessage.error(deleteError.value)
      throw error
    } finally {
      deleteLoading.value = false
    }
  }

  /**
   * 批量删除历史记录
   */
  async function batchDelete(recordIds: string[], permanent: boolean = false) {
    deleteLoading.value = true
    deleteError.value = null

    try {
      const response = await backtestHistoryApi.batchDelete({
        record_ids: recordIds,
        permanent: permanent
      })

      // 重新获取列表
      await fetchHistoryList(true)
      selectedRecords.value = []

      ElMessage.success(response.data.message)
    } catch (error: any) {
      deleteError.value = error.message || '批量删除失败'
      ElMessage.error(deleteError.value)
      throw error
    } finally {
      deleteLoading.value = false
    }
  }

  /**
   * 恢复历史记录
   */
  async function restoreHistory(recordId: string) {
    deleteLoading.value = true
    deleteError.value = null

    try {
      await backtestHistoryApi.restoreHistory(recordId)

      // 重新获取列表
      await fetchHistoryList(true)

      ElMessage.success('记录已恢复')
    } catch (error: any) {
      deleteError.value = error.message || '恢复记录失败'
      ElMessage.error(deleteError.value)
      throw error
    } finally {
      deleteLoading.value = false
    }
  }

  /**
   * 导出历史记录
   */
  async function exportHistory(recordId: string, format: 'json' | 'excel' | 'pdf' = 'json') {
    exportLoading.value = true

    try {
      const response = await backtestHistoryApi.exportHistory(recordId, format)

      // 创建下载链接
      const dataStr = JSON.stringify(response.data.data, null, 2)
      const blob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(blob)

      const link = document.createElement('a')
      link.href = url
      link.download = response.data.filename
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)

      ElMessage.success('导出成功')
    } catch (error: any) {
      ElMessage.error('导出失败')
      throw error
    } finally {
      exportLoading.value = false
    }
  }

  /**
   * 更新筛选条件
   */
  function updateFilters(newFilters: Partial<typeof filters.value>) {
    Object.assign(filters.value, newFilters)
  }

  /**
   * 重置筛选条件
   */
  function resetFilters() {
    filters.value = {
      strategy_id: '',
      stock_code: '',
      search: ''
    }
  }

  /**
   * 批量选择/取消选择
   */
  function toggleRecordSelection(recordId: string) {
    const index = selectedRecords.value.indexOf(recordId)
    if (index > -1) {
      selectedRecords.value.splice(index, 1)
    } else {
      selectedRecords.value.push(recordId)
    }
  }

  /**
   * 全选/取消全选
   */
  function toggleSelectAll() {
    if (selectedRecords.value.length === records.value.length) {
      selectedRecords.value = []
    } else {
      selectedRecords.value = records.value.map(r => r.record_id)
    }
  }

  return {
    // 状态
    records,
    total,
    listLoading,
    listError,
    selectedRecordId,
    recordDetail,
    detailLoading,
    detailError,
    compareRecordIds,
    compareResults,
    compareLoading,
    compareError,
    deleteLoading,
    deleteError,
    showRecycleBin,
    selectedRecords,
    exportLoading,
    filters,
    pagination,

    // 计算属性
    hasRecords,
    hasSelected,
    canCompare,
    hasBatchSelection,
    isRecycleBinView,

    // Actions
    fetchHistoryList,
    loadMore,
    toggleRecycleBin,
    fetchHistoryDetail,
    saveToHistory,
    compareHistory,
    addToCompare,
    removeFromCompare,
    clearCompare,
    deleteHistory,
    batchDelete,
    restoreHistory,
    exportHistory,
    updateFilters,
    resetFilters,
    toggleRecordSelection,
    toggleSelectAll
  }
})
