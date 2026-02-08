/**
 * Vitest 测试环境设置
 */
import { vi } from 'vitest'
import { config } from '@vue/test-utils'

// 全局 mock
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn()
}))

// Element Plus mock
config.global.stubs = {
  'el-icon': true,
  'el-button': true,
  'el-input': true,
  'el-input-number': true,
  'el-select': true,
  'el-option': true,
  'el-date-picker': true,
  'el-form': true,
  'el-form-item': true,
  'el-card': true,
  'el-dialog': true,
  'el-message': true,
  'el-message-box': true,
  'el-steps': true,
  'el-step': true,
  'el-tag': true,
  'el-radio-group': true,
  'el-radio': true,
  'el-row': true,
  'el-col': true,
  'el-divider': true,
  'el-dropdown': true,
  'el-dropdown-menu': true,
  'el-dropdown-item': true,
  'el-alert': true,
  'el-progress': true
}

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn()
  }))
})

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn()
}
global.localStorage = localStorageMock as any
