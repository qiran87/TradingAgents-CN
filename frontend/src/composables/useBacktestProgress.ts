/**
 * 回测进度统一管理Hook
 * 自动在WebSocket和HTTP轮询之间降级，提供最佳用户体验
 *
 * 功能：
 * - 优先使用WebSocket实时通信
 * - WebSocket失败时自动降级到HTTP轮询
 * - 支持手动重连
 * - 统一的状态管理接口
 */
import { ref, computed, watch, onUnmounted } from 'vue'
import { useHttpPolling } from './useHttpPolling'
import { useBacktestEngineStore } from '@/stores/backtestEngine'

export interface BacktestProgressOptions {
  /** 回测任务ID */
  backtestId: string
  /** WebSocket认证token（可选） */
  token?: string
  /** 状态变化回调 */
  onStateChange?: (state: any, connectionType: 'websocket' | 'http') => void
  /** 连接类型变化回调 */
  onConnectionTypeChange?: (type: 'websocket' | 'http') => void
  /** 错误回调 */
  onError?: (error: Error, connectionType: 'websocket' | 'http') => void
  /** HTTP轮询间隔（毫秒），降级后使用 */
  httpPollingInterval?: number
  /** 是否自动启动，默认true */
  autoStart?: boolean
}

export interface BacktestProgressReturn {
  /** 当前回测状态 */
  currentState: ReturnType<typeof computed<any>>
  /** 连接类型：websocket或http */
  connectionType: ReturnType<typeof ref<'websocket' | 'http'>>
  /** 是否已连接 */
  isConnected: ReturnType<typeof computed<boolean>>
  /** WebSocket是否失败（是否降级到HTTP） */
  isDegraded: ReturnType<typeof computed<boolean>>
  /** 重试次数（HTTP轮询） */
  retryCount: ReturnType<typeof ref<number>>
  /** 手动重连WebSocket */
  reconnectWebSocket: () => void
  /** 停止所有连接 */
  disconnect: () => void
}

/**
 * 回测进度统一管理Hook
 *
 * @param options - 配置选项
 * @returns 进度管理控制对象
 *
 * @example
 * ```ts
 * const {
 *   currentState,
 *   connectionType,
 *   isDegraded,
 *   reconnectWebSocket
 * } = useBacktestProgress({
 *   backtestId: 'bt_123',
 *   token: 'jwt_token',
 *   onStateChange: (state, type) => {
 *     console.log(`状态更新(${type}):`, state)
 *   },
 *   onConnectionTypeChange: (type) => {
 *     console.log(`连接方式切换到: ${type}`)
 *   }
 * })
 * ```
 */
export function useBacktestProgress(
  options: BacktestProgressOptions
): BacktestProgressReturn {
  const {
    backtestId,
    token,
    onStateChange,
    onConnectionTypeChange,
    onError,
    httpPollingInterval = 2000,
    autoStart = true
  } = options

  // 连接类型：默认优先WebSocket
  const connectionType = ref<'websocket' | 'http'>('websocket')
  const wsStore = useBacktestEngineStore()

  // HTTP轮询实例
  let httpPolling: ReturnType<typeof useHttpPolling> | null = null

  /**
   * 当前回测状态（合并WebSocket和HTTP来源）
   */
  const currentState = computed(() => {
    if (connectionType.value === 'websocket') {
      return wsStore.currentState
    } else {
      return httpPolling?.state.value || null
    }
  })

  /**
   * 是否已连接
   */
  const isConnected = computed(() => {
    if (connectionType.value === 'websocket') {
      return wsStore.isConnected
    } else {
      return httpPolling?.isPolling.value || false
    }
  })

  /**
   * 是否降级到HTTP轮询
   */
  const isDegraded = computed(() => {
    return connectionType.value === 'http'
  })

  /**
   * 重试次数
   */
  const retryCount = computed(() => {
    if (connectionType.value === 'http') {
      return httpPolling?.retryCount.value || 0
    }
    return 0
  })

  /**
   * 启动HTTP轮询
   */
  const startHttpPolling = () => {
    if (httpPolling) {
      return // 已经在运行
    }

    console.info('🔄 降级到HTTP轮询模式')

    httpPolling = useHttpPolling(backtestId, {
      interval: httpPollingInterval,
      autoStart: true,
      onStateChange: (state) => {
        onStateChange?.(state, 'http')
      },
      onError: (error) => {
        console.error('HTTP轮询错误:', error)
        onError?.(error, 'http')
      }
    })
  }

  /**
   * 停止HTTP轮询
   */
  const stopHttpPolling = () => {
    if (httpPolling) {
      httpPolling.stop()
      httpPolling = null
    }
  }

  /**
   * 启动WebSocket连接
   */
  const startWebSocket = async () => {
    try {
      // 连接WebSocket
      const wsUrl = token
        ? `ws://localhost:8000/api/backtest/ws/${backtestId}/progress?token=${token}`
        : `ws://localhost:8000/api/backtest/ws/${backtestId}/progress`

      await wsStore.connect(backtestId, wsUrl)

      connectionType.value = 'websocket'
      onConnectionTypeChange?.('websocket')

      console.info('✅ WebSocket连接成功')
    } catch (error) {
      console.error('❌ WebSocket连接失败:', error)
      onError?.(error as Error, 'websocket')
      return false
    }

    return true
  }

  /**
   * 手动重连WebSocket
   */
  const reconnectWebSocket = async () => {
    console.info('🔄 尝试重新连接WebSocket...')

    // 停止HTTP轮询
    stopHttpPolling()

    // 尝试WebSocket连接
    const success = await startWebSocket()

    if (!success) {
      // WebSocket失败，降级到HTTP
      connectionType.value = 'http'
      startHttpPolling()
      onConnectionTypeChange?.('http')
    }
  }

  /**
   * 停止所有连接
   */
  const disconnect = () => {
    // 断开WebSocket
    wsStore.disconnect()

    // 停止HTTP轮询
    stopHttpPolling()
  }

  // 监听WebSocket错误，自动降级
  watch(
    () => wsStore.error,
    (error) => {
      if (error && connectionType.value === 'websocket') {
        console.warn('⚠️ WebSocket错误，自动降级到HTTP轮询:', error)

        // 切换到HTTP轮询
        connectionType.value = 'http'
        onConnectionTypeChange?.('http')

        // 启动HTTP轮询
        startHttpPolling()

        // 断开WebSocket
        wsStore.disconnect()
      }
    }
  )

  // 监听WebSocket连接状态变化
  watch(
    () => wsStore.isConnected,
    (connected) => {
      if (connectionType.value === 'websocket' && connected) {
        console.info('✅ WebSocket已连接')
      }
    }
  )

  // 组件卸载时清理
  onUnmounted(() => {
    disconnect()
  })

  // 自动启动
  if (autoStart) {
    startWebSocket().then((success) => {
      if (!success) {
        // WebSocket初始化失败，立即降级
        connectionType.value = 'http'
        startHttpPolling()
        onConnectionTypeChange?.('http')
      }
    })
  }

  return {
    currentState,
    connectionType,
    isConnected,
    isDegraded,
    retryCount,
    reconnectWebSocket,
    disconnect
  }
}
