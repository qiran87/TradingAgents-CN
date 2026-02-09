/**
 * 回测引擎Store - 管理回测任务状态和WebSocket连接
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { backtestEngineApi } from '@/api/backtestEngine'
import type {
  StartBacktestRequest,
  BacktestStatus,
  PositionInfo,
  ExecutionInfo,
  WSMessage
} from '@/api/backtestEngine'

export const useBacktestEngineStore = defineStore('backtestEngine', () => {
  // ===================== 状态 =====================

  // 当前回测任务ID
  const currentBacktestId = ref<string | null>(null)

  // 回测状态
  const backtestStatus = ref<BacktestStatus | null>(null)
  const statusLoading = ref(false)
  const statusError = ref<string | null>(null)

  // 实时持仓
  const currentPosition = ref<PositionInfo | null>(null)

  // WebSocket连接
  const ws = ref<WebSocket | null>(null)
  const wsConnected = ref(false)
  const wsError = ref<string | null>(null)

  // 启动回测loading
  const startingBacktest = ref(false)
  const startError = ref<string | null>(null)

  // 进度更新历史（用于图表）
  const progressHistory = ref<Array<{ date: string; value: number }>>([])

  // 交易信号历史
  const tradeHistory = ref<Array<any>>([])

  // 心跳定时器
  let heartbeatTimer: number | null = null

  // 状态轮询定时器
  let statusPollingTimer: number | null = null

  // ===================== 计算属性 =====================

  const isRunning = computed(() => backtestStatus.value?.status === 'running')
  const isPaused = computed(() => backtestStatus.value?.status === 'paused')
  const isCompleted = computed(() => backtestStatus.value?.status === 'completed')
  const isFailed = computed(() => backtestStatus.value?.status === 'failed')

  const progress = computed(() => backtestStatus.value?.execution_info?.progress ?? 0)
  const currentBarIndex = computed(() => backtestStatus.value?.execution_info?.current_bar_index ?? 0)
  const totalBars = computed(() => backtestStatus.value?.execution_info?.total_bars ?? 0)
  const currentDate = computed(() => backtestStatus.value?.execution_info?.current_date ?? null)

  const hasPosition = computed(() => currentPosition.value !== null)
  const profitLoss = computed(() => currentPosition.value?.profit_loss ?? 0)
  const profitLossPct = computed(() => currentPosition.value?.profit_loss_pct ?? 0)

  const totalValue = computed(() => currentPosition.value?.total_value ?? 0)
  const cash = computed(() => currentPosition.value?.cash ?? 0)
  const marketValue = computed(() => currentPosition.value?.market_value ?? 0)

  // ===================== Actions =====================

  /**
   * 启动回测任务
   */
  async function startBacktest(request: StartBacktestRequest) {
    startingBacktest.value = true
    startError.value = null

    try {
      const response = await backtestEngineApi.startBacktest(request)
      currentBacktestId.value = response.data.backtest_id

      // 立即初始化回测状态为running
      backtestStatus.value = {
        backtest_id: response.data.backtest_id,
        status: 'running',
        execution_info: {
          current_bar_index: 0,
          total_bars: 0,
          current_date: null,
          progress: 0,
          start_time: new Date().toISOString(),
          elapsed_time: 0
        }
      } as BacktestStatus

      // 连接WebSocket
      connectWebSocket(response.data.backtest_id)

      // 启动状态轮询(作为WebSocket的备用机制)
      startStatusPolling(response.data.backtest_id)

      return response.data
    } catch (error: any) {
      startError.value = error?.message || '启动回测失败'
      throw error
    } finally {
      startingBacktest.value = false
    }
  }

  /**
   * 暂停回测任务
   */
  async function interruptBacktest(backtestId?: string) {
    const id = backtestId || currentBacktestId.value
    if (!id) throw new Error('没有回测任务ID')

    await backtestEngineApi.interruptBacktest(id)
  }

  /**
   * 继续回测任务
   */
  async function continueBacktest(backtestId?: string) {
    const id = backtestId || currentBacktestId.value
    if (!id) throw new Error('没有回测任务ID')

    await backtestEngineApi.continueBacktest(id)
  }

  /**
   * 获取回测状态
   */
  async function fetchBacktestStatus(backtestId?: string) {
    const id = backtestId || currentBacktestId.value
    if (!id) throw new Error('没有回测任务ID')

    statusLoading.value = true
    statusError.value = null

    try {
      const response = await backtestEngineApi.getBacktestStatus(id)
      backtestStatus.value = response.data
      return response.data
    } catch (error: any) {
      statusError.value = error?.message || '获取状态失败'
      throw error
    } finally {
      statusLoading.value = false
    }
  }

  /**
   * 放弃回测任务
   */
  async function abortBacktest(backtestId?: string) {
    const id = backtestId || currentBacktestId.value
    if (!id) throw new Error('没有回测任务ID')

    await backtestEngineApi.abortBacktest(id)

    // 断开WebSocket
    disconnectWebSocket()

    // 清空状态
    resetState()
  }

  /**
   * 连接WebSocket
   */
  function connectWebSocket(backtestId: string) {
    // 先断开现有连接
    disconnectWebSocket()

    const url = backtestEngineApi.getWebSocketUrl(backtestId)
    ws.value = new WebSocket(url)

    ws.value.onopen = () => {
      console.log('[BacktestEngine] WebSocket连接成功')
      wsConnected.value = true
      wsError.value = null

      // 启动心跳
      startHeartbeat()
    }

    ws.value.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data)
        handleWSMessage(message)
      } catch (error) {
        console.error('[BacktestEngine] WebSocket消息解析失败:', error)
      }
    }

    ws.value.onerror = (event) => {
      console.error('[BacktestEngine] WebSocket错误:', event)
      wsError.value = 'WebSocket连接错误'
    }

    ws.value.onclose = () => {
      console.log('[BacktestEngine] WebSocket连接关闭')
      wsConnected.value = false
      stopHeartbeat()
    }
  }

  /**
   * 断开WebSocket
   */
  function disconnectWebSocket() {
    if (ws.value) {
      ws.value.close()
      ws.value = null
    }
    wsConnected.value = false
    stopHeartbeat()
  }

  /**
   * 处理WebSocket消息
   */
  function handleWSMessage(message: WSMessage) {
    switch (message.type) {
      case 'connected':
        console.log('[BacktestEngine] 已连接到回测任务:', message.data?.backtest_id)
        break

      case 'progress':
        if (message.data?.execution_info) {
          // 更新回测状态
          backtestStatus.value = {
            ...backtestStatus.value,
            execution_info: message.data.execution_info
          } as BacktestStatus

          // 记录进度历史
          if (message.data.execution_info.current_date) {
            progressHistory.value.push({
              date: message.data.execution_info.current_date,
              value: message.data.execution_info.progress
            })
          }
        }
        break

      case 'position':
        if (message.data) {
          currentPosition.value = message.data as PositionInfo
        }
        break

      case 'trade':
        if (message.data) {
          tradeHistory.value.push(message.data)
        }
        break

      case 'completed':
        console.log('[BacktestEngine] 回测完成:', message.data)
        // 更新最终状态
        if (message.data?.status) {
          backtestStatus.value = message.data as BacktestStatus
        }
        break

      case 'error':
        console.error('[BacktestEngine] 回测错误:', message.data)
        statusError.value = message.data?.error?.message || message.data?.message || '回测执行出错'

        // 更新回测状态为失败
        if (backtestStatus.value) {
          backtestStatus.value = {
            ...backtestStatus.value,
            status: 'failed'
          } as BacktestStatus
        }
        break

      case 'pong':
        // 心跳响应，无需处理
        break

      default:
        console.warn('[BacktestEngine] 未知消息类型:', message.type)
    }
  }

  /**
   * 启动心跳
   */
  function startHeartbeat() {
    stopHeartbeat()

    heartbeatTimer = window.setInterval(() => {
      if (ws.value && wsConnected.value) {
        ws.value.send('ping')
      }
    }, 30000) // 30秒一次心跳
  }

  /**
   * 停止心跳
   */
  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  /**
   * 启动状态轮询
   */
  function startStatusPolling(backtestId: string) {
    stopStatusPolling()

    console.log('[BacktestEngine] 启动状态轮询:', backtestId)

    // 立即查询一次状态
    fetchBacktestStatus(backtestId).catch(err => {
      console.warn('[BacktestEngine] 首次状态查询失败:', err)
    })

    // 每2秒轮询一次状态
    statusPollingTimer = window.setInterval(async () => {
      try {
        const status = await fetchBacktestStatus(backtestId)

        // 如果回测已完成,自动保存到历史记录并停止轮询
        if (status?.status === 'completed') {
          console.log('[BacktestEngine] 回测完成,自动保存到历史记录')
          stopStatusPolling()
          disconnectWebSocket()

          // 自动保存到历史记录
          await autoSaveToHistory(backtestId, status)
        }
        // 如果回测失败,停止轮询
        else if (status?.status === 'failed') {
          console.log('[BacktestEngine] 回测失败,停止轮询:', status.status)
          stopStatusPolling()
          disconnectWebSocket()
        }
      } catch (error) {
        console.error('[BacktestEngine] 状态轮询失败:', error)
      }
    }, 2000)
  }

  /**
   * 自动保存到历史记录
   */
  async function autoSaveToHistory(backtestId: string, status: BacktestStatus) {
    try {
      // 导入历史记录 store
      const { useBacktestHistoryStore } = await import('@/stores/backtestHistory')
      const historyStore = useBacktestHistoryStore()

      // 生成默认名称
      const parameters = status.parameters || {}
      const stockCode = parameters.stock_code || '未知股票'
      const strategyId = parameters.strategy_id || '未知策略'
      const startDate = parameters.start_date || ''
      const endDate = parameters.end_date || ''

      const defaultName = `${stockCode} ${strategyId} ${startDate}至${endDate}`

      // 自动保存
      await historyStore.saveToHistory(backtestId, {
        name: defaultName,
        description: '自动保存的回测结果',
        tags: ['自动保存']
      })

      console.log('[BacktestEngine] 已自动保存到历史记录:', defaultName)

      // 显示提示
      if (typeof ElMessage !== 'undefined') {
        ElMessage.success({
          message: `回测完成!已自动保存到历史记录: ${defaultName}`,
          duration: 5000
        })
      }
    } catch (error) {
      console.error('[BacktestEngine] 自动保存到历史记录失败:', error)
      // 自动保存失败不影响用户体验,只记录错误
    }
  }

  /**
   * 停止状态轮询
   */
  function stopStatusPolling() {
    if (statusPollingTimer) {
      clearInterval(statusPollingTimer)
      statusPollingTimer = null
      console.log('[BacktestEngine] 状态轮询已停止')
    }
  }

  /**
   * 重置状态
   */
  function resetState() {
    currentBacktestId.value = null
    backtestStatus.value = null
    currentPosition.value = null
    progressHistory.value = []
    tradeHistory.value = []
    statusError.value = null
    startError.value = null
  }

  /**
   * 清理资源
   */
  function cleanup() {
    stopStatusPolling()
    disconnectWebSocket()
    resetState()
  }

  // ===================== 返回 =====================

  return {
    // 状态
    currentBacktestId,
    backtestStatus,
    statusLoading,
    statusError,
    currentPosition,
    wsConnected,
    wsError,
    startingBacktest,
    startError,
    progressHistory,
    tradeHistory,

    // 计算属性
    isRunning,
    isPaused,
    isCompleted,
    isFailed,
    progress,
    currentBarIndex,
    totalBars,
    currentDate,
    hasPosition,
    profitLoss,
    profitLossPct,
    totalValue,
    cash,
    marketValue,

    // Actions
    startBacktest,
    interruptBacktest,
    continueBacktest,
    abortBacktest,
    fetchBacktestStatus,
    connectWebSocket,
    disconnectWebSocket,
    startStatusPolling,
    stopStatusPolling,
    cleanup,
    resetState
  }
})
