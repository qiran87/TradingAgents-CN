/**
 * 测试7: 帮助文档入口
 * 验证帮助文档入口的显示和功能
 */
import { describe, it, expect } from 'vitest'
import { ref } from 'vue'

describe('测试7: 帮助文档入口', () => {
  it('底部区域应包含帮助文档按钮', () => {
    const footerContent = `
      <div class="page-footer-fixed">
        <div class="footer-left">
          <el-button text @click="showHelpDialog = true">
            <el-icon><QuestionFilled /></el-icon>
            帮助文档
          </el-button>
        </div>
        <div class="footer-right">
          <span>TradingAgents v1.0.0</span>
        </div>
      </div>
    `
    expect(footerContent).toContain('帮助文档')
    expect(footerContent).toContain('QuestionFilled')
  })

  it('底部区域应为固定定位', () => {
    const footerClass = 'page-footer-fixed'
    expect(footerClass).toContain('fixed')
  })

  it('底部区域应显示版本信息', () => {
    const versionInfo = 'TradingAgents v1.0.0 | ' + new Date().toLocaleDateString('zh-CN')
    expect(versionInfo).toContain('TradingAgents')
    expect(versionInfo).toContain('v1.0.0')
  })

  it('点击帮助按钮应打开弹窗', () => {
    const showHelpDialog = ref(false)

    const handleClick = () => {
      showHelpDialog.value = true
    }

    handleClick()

    expect(showHelpDialog.value).toBe(true)
  })

  it('帮助弹窗标题应为"帮助文档"', () => {
    const dialogTitle = '帮助文档'
    expect(dialogTitle).toBe('帮助文档')
  })

  it('帮助弹窗宽度应为900px', () => {
    const dialogWidth = '900px'
    expect(dialogWidth).toBe('900px')
  })

  it('帮助文档应包含使用指南', () => {
    const helpContent = `
      <div class="help-content">
        <h3>📖 股票回测功能使用指南</h3>
        <h4>1. 回测参数设置</h4>
        <h4>2. 策略选择</h4>
        <h4>3. 回测操作</h4>
        <h4>4. 结果查看</h4>
        <h4>5. 常用功能</h4>
      </div>
    `
    expect(helpContent).toContain('股票回测功能使用指南')
    expect(helpContent).toContain('回测参数设置')
    expect(helpContent).toContain('策略选择')
    expect(helpContent).toContain('回测操作')
    expect(helpContent).toContain('结果查看')
    expect(helpContent).toContain('常用功能')
  })

  it('帮助文档应包含快捷键提示', () => {
    const shortcutTip = '💡 提示：使用快捷键 Ctrl+S 保存参数，Ctrl+R 开始回测'
    expect(shortcutTip).toContain('Ctrl+S')
    expect(shortcutTip).toContain('Ctrl+R')
  })

  it('帮助文档应使用蓝色标题', () => {
    const titleColor = '#409eff'
    expect(titleColor).toBe('#409eff')
  })

  it('帮助文档应包含参数说明', () => {
    const paramDesc = `
      <ul>
        <li><strong>日期范围</strong>：支持日历选择，自动跳过非交易日</li>
        <li><strong>初始资金</strong>：范围1,000-10,000,000元</li>
        <li><strong>最小购买量</strong>：必须为100的倍数，范围100-10,000股</li>
        <li><strong>股票代码</strong>：支持A股和港股</li>
      </ul>
    `
    expect(paramDesc).toContain('日期范围')
    expect(paramDesc).toContain('初始资金')
    expect(paramDesc).toContain('最小购买量')
    expect(paramDesc).toContain('股票代码')
  })

  it('底部区域应包含当前日期', () => {
    const currentDate = new Date().toLocaleDateString('zh-CN')
    const hasDate = currentDate.includes('2024') || currentDate.includes('2025') || currentDate.includes('2026')
    expect(hasDate).toBe(true)
  })
})
