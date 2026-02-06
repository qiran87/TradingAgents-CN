/**
 * HTTP轮询备用方案
 * 当WebSocket不可用时，使用HTTP轮询获取回测进度
 *
 * 功能：
 * - 自动轮询回测状态
 * - 指数退避重试机制
 * - 429状态码智能限流处理
 */
import { ref, onUnmounted } from 'vue'
import axios, { AxiosError } from 'axios'

export interface HttpPollingOptions {
  /** 轮询间隔（毫秒），默认2秒 */
  interval?: number
  /** 自动启动，默认true */
  autoStart?: boolean
  /** 轮询状态变化回调 */
  onStateChange?: (state: any) => void
  /** 错误回调 */
  onError?: (error: Error) => void
  /** 重试次数，默认3次 */
  retryAttempts?: number
  /** 重试基础延迟（毫秒），默认1000ms */
  retryDelay?: number
  /** 是否启用重试，默认true */
  enableRetry?: boolean
}

export interface HttpPollingReturn {
  /** 当前状态数据 */
  state: any
  /** 是否正在轮询 */
  isPolling: boolean
  /** 重试次数 */
  retryCount: ReturnType<typeof ref<number>>
  /** 开始轮询 */
  start: () => void
  /** 停止轮询 */
  stop: () => void
  /** 手动刷新一次 */
  refresh: () => Promise<void>
}

/**
 * HTTP轮询Composable
 *
 * @param backtestId - 回测任务ID
 * @param options - 配置选项
 * @returns 轮询控制对象
 *
 * @example
 * ```ts
 * const { state, isPolling, start, stop } = useHttpPolling('bt_123', {
 *   interval: 2000,
 *   retryAttempts: 3,
 *   onStateChange: (newState) => {
 *     console.log('状态更新:', newState)
 *   }
 * })
 *
 * // 开始轮询
 * start()
 *
 * // 停止轮询
 * stop()
 * ```
 */
export function useHttpPolling(
  backtestId: string,
  options: HttpPollingOptions = {}
): HttpPollingReturn {
  const {
    interval = 2000,
    autoStart = true,
    onStateChange,
    onError,
    retryAttempts = 3,
    retryDelay = 1000,
    enableRetry = true
  } = options

  const state = ref<any>(null)
  const isPolling = ref(false)
  const retryCount = ref(0)
  let timer: ReturnType<typeof setInterval> | null = null

  /**
   * 延迟函数
   */
  const delay = (ms: number): Promise<void> => {
    return new Promise(resolve => setTimeout(resolve, ms))
  }

  /**
   * 获取当前状态
   */
  const fetchState = async (): Promise<any> => {
    try {
      const response = await axios.get(
        `/api/backtest/${backtestId}/current-state`,
        {
          timeout: 5000 // 5秒超时
        }
      )

      if (response.data.code === 200) {
        return response.data.data
      } else {
        throw new Error(response.data.message || '获取状态失败')
      }
    } catch (error: any) {
      // 处理429限流错误
      if (error.response?.status === 429) {
        const retryAfter = error.response.headers['retry-after']
        const waitTime = retryAfter ? parseInt(retryAfter) * 1000 : 1000
        console.warn(`限流触发，等待 ${waitTime}ms 后重试`)
        await delay(waitTime)
        return fetchState() // 递归重试
      }

      // 处理网络错误
      if (error.code === 'ECONNABORTED') {
        throw new Error('请求超时，请检查网络连接')
      }

      if (error.response?.status >= 500) {
        throw new Error(`服务器错误: ${error.response.status}`)
      }

      throw error
    }
  }

  /**
   * 刷新状态（带重试机制）
   */
  const refresh = async (): Promise<void> => {
    let lastError: Error | null = null

    for (let attempt = 0; attempt <= retryAttempts; attempt++) {
      try {
        const newState = await fetchState()
        state.value = newState
        retryCount.value = 0 // 成功后重置重试计数
        onStateChange?.(newState)
        return
      } catch (error: any) {
        lastError = error

        // 如果不启用重试或达到最大重试次数，停止
        if (!enableRetry || attempt >= retryAttempts) {
          break
        }

        // 计算退避延迟（指数退避）
        const backoffDelay = retryDelay * Math.pow(2, attempt)
        console.warn(
          `轮询失败（第${attempt + 1}次尝试）: ${error.message}，` +
          `${backoffDelay}ms后重试...`
        )

        retryCount.value = attempt + 1
        await delay(backoffDelay)
      }
    }

    // 所有重试都失败
    onError?.(lastError!)
  }

  /**
   * 开始轮询
   */
  const start = (): void => {
    if (isPolling.value) {
      return
    }

    isPolling.value = true

    // 立即执行一次
    refresh()

    // 设置定时器
    timer = setInterval(() => {
      refresh()
    }, interval)
  }

  /**
   * 停止轮询
   */
  const stop = (): void => {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
    isPolling.value = false
    retryCount.value = 0
  }

  // 组件卸载时自动停止轮询
  onUnmounted(() => {
    stop()
  })

  // 自动启动
  if (autoStart && backtestId) {
    start()
  }

  return {
    state,
    isPolling,
    retryCount,
    start,
    stop,
    refresh
  }
}
