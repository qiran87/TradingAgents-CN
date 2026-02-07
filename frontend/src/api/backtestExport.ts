/**
 * 回测结果导出 API
 */
import ApiClient from './client'

export interface ExportStatusResponse {
  success: boolean
  can_export: boolean
  message: string
  backtest_id: string
  has_equity_curve?: boolean
  trades_count?: number
}

/**
 * 回测导出 API
 */
export const backtestExportApi = {
  /**
   * 导出回测结果为 Excel 文件
   * @param backtestId 回测ID
   * @returns Promise<Blob> Excel文件的Blob对象
   */
  async exportToExcel(backtestId: string): Promise<Blob> {
    const response = await ApiClient.get<Blob>(
      `/api/backtest/${backtestId}/export/excel`,
      {
        responseType: 'blob'
      }
    )
    return response.data
  },

  /**
   * 检查回测结果是否可导出
   * @param backtestId 回测ID
   * @returns 导出状态信息
   */
  async getExportStatus(backtestId: string): Promise<ExportStatusResponse> {
    const response = await ApiClient.get<ExportStatusResponse>(
      `/api/backtest/${backtestId}/export/status`
    )
    return response.data
  },

  /**
   * 下载Excel文件的辅助方法
   * @param backtestId 回测ID
   * @param customFilename 自定义文件名（可选）
   */
  async downloadExcel(
    backtestId: string,
    customFilename?: string
  ): Promise<void> {
    try {
      // 获取Excel文件
      const blob = await this.exportToExcel(backtestId)

      // 生成文件名
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5)
      const filename = customFilename || `backtest_${backtestId}_${timestamp}.xlsx`

      // 创建下载链接
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.style.display = 'none'

      document.body.appendChild(link)
      link.click()

      // 清理
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('下载Excel文件失败:', error)
      throw error
    }
  }
}

/**
 * 图表导出工具
 */
export const chartExportUtils = {
  /**
   * 导出 ECharts 图表为 PNG 图片
   * @param chartId 图表容器DOM ID
   * @param filename 文件名（不含扩展名）
   * @param pixelRatio 像素比率，默认2（高清）
   */
  exportEChartsToPNG(
    chartId: string,
    filename: string,
    pixelRatio: number = 2
  ): void {
    // 获取 ECharts 实例
    const echarts = (window as any).echarts
    if (!echarts) {
      console.error('ECharts 未加载')
      return
    }

    const chartDom = document.getElementById(chartId)
    if (!chartDom) {
      console.error(`图表容器不存在: ${chartId}`)
      return
    }

    const chart = echarts.getInstanceByDom(chartDom)
    if (!chart) {
      console.error(`图表实例不存在: ${chartId}`)
      return
    }

    try {
      // 导出为 DataURL (PNG)
      const url = chart.getDataURL({
        type: 'png',
        pixelRatio: pixelRatio,
        backgroundColor: '#fff'
      })

      // 创建下载链接
      const link = document.createElement('a')
      link.href = url
      link.download = `${filename}.png`
      link.style.display = 'none'

      document.body.appendChild(link)
      link.click()

      // 清理
      document.body.removeChild(link)
    } catch (error) {
      console.error('导出图表失败:', error)
      throw error
    }
  },

  /**
   * 导出多个图表为 PNG 图片
   * @param chartConfigs 图表配置数组 {chartId, filename}
   */
  exportMultipleCharts(chartConfigs: Array<{ chartId: string; filename: string }>): void {
    chartConfigs.forEach((config, index) => {
      // 延迟执行，避免同时导出导致的问题
      setTimeout(() => {
        this.exportEChartsToPNG(config.chartId, config.filename)
      }, index * 500)
    })
  }
}
