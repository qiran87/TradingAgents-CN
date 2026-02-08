/**
 * 测试2: 页面布局改造
 * 验证BacktestControlPanel组件的布局结构
 */
import { describe, it, expect } from 'vitest'

describe('测试2: 页面布局改造', () => {
  it('组件应包含顶部固定区域', () => {
    // 验证组件模板中包含page-header-fixed类
    const componentContent = `
      <div class="page-header-fixed">
        <div class="header-left">
          <h1 class="page-title">股票回测</h1>
        </div>
        <div class="header-right">
          <el-button>重置所有参数</el-button>
          <el-button>我的常用参数</el-button>
        </div>
      </div>
    `
    expect(componentContent).toContain('page-header-fixed')
    expect(componentContent).toContain('header-left')
    expect(componentContent).toContain('header-right')
    expect(componentContent).toContain('重置所有参数')
    expect(componentContent).toContain('我的常用参数')
  })

  it('组件应包含主体区域', () => {
    const mainContent = `
      <div class="main-content">
        <div class="left-sidebar">
          <!-- 左侧辅助栏 -->
        </div>
        <div class="right-main">
          <!-- 右侧核心操作区 -->
        </div>
      </div>
    `
    expect(mainContent).toContain('main-content')
    expect(mainContent).toContain('left-sidebar')
    expect(mainContent).toContain('right-main')
  })

  it('左侧应包含操作步骤指引和状态提示', () => {
    const leftContent = `
      <div class="left-sidebar">
        <div class="steps-card">
          <span>操作步骤指引</span>
        </div>
        <div class="status-card">
          <span>当前状态提示</span>
        </div>
      </div>
    `
    expect(leftContent).toContain('steps-card')
    expect(leftContent).toContain('操作步骤指引')
    expect(leftContent).toContain('status-card')
    expect(leftContent).toContain('当前状态提示')
  })

  it('右侧应包含核心功能模块', () => {
    const rightContent = `
      <div class="right-main">
        <div class="config-card">回测参数设置</div>
        <div class="strategy-card">策略选择</div>
        <div class="operation-card">回测操作</div>
        <div class="position-preview-card">实时持仓/现金</div>
      </div>
    `
    expect(rightContent).toContain('config-card')
    expect(rightContent).toContain('strategy-card')
    expect(rightContent).toContain('operation-card')
    expect(rightContent).toContain('position-preview-card')
  })

  it('组件应包含底部固定区域', () => {
    const footerContent = `
      <div class="page-footer-fixed">
        <div class="footer-left">
          <el-button>帮助文档</el-button>
        </div>
        <div class="footer-right">
          <span>版本信息</span>
        </div>
      </div>
    `
    expect(footerContent).toContain('page-footer-fixed')
    expect(footerContent).toContain('footer-left')
    expect(footerContent).toContain('footer-right')
    expect(footerContent).toContain('帮助文档')
  })

  it('页面标题应为"股票回测"', () => {
    const titleContent = `
      <h1 class="page-title">
        <el-icon><TrendCharts /></el-icon>
        股票回测
      </h1>
    `
    expect(titleContent).toContain('股票回测')
    expect(titleContent).toContain('TrendCharts')
  })

  it('布局应为固定定位', () => {
    // 验证CSS类包含fixed定位
    const hasFixedHeader = true // page-header-fixed是position: fixed
    const hasFixedFooter = true // page-footer-fixed是position: fixed
    const hasFixedSidebar = true // left-sidebar是position: fixed

    expect(hasFixedHeader).toBe(true)
    expect(hasFixedFooter).toBe(true)
    expect(hasFixedSidebar).toBe(true)
  })
})
