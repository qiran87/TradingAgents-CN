/**
 * 菜单配置
 *
 * 统一管理侧边栏菜单结构，支持权限控制和图标映射
 * 优势：
 * 1. 单一数据源，避免路由和菜单不同步
 * 2. 支持权限控制
 * 3. 便于维护和扩展
 */
import type { Component } from 'vue'
import * as Icons from '@element-plus/icons-vue'

/**
 * 菜单项接口
 */
export interface MenuItem {
  /** 菜单唯一标识（对应路由path） */
  path: string
  /** 菜单显示名称 */
  title: string
  /** 图标名称（来自 @element-plus/icons-vue） */
  icon?: string
  /** 子菜单项 */
  children?: MenuItem[]
  /** 需要的角色权限（空数组表示所有登录用户可访问） */
  roles?: string[]
  /** 是否隐藏（用于特殊情况） */
  hidden?: boolean
}

/**
 * 侧边栏菜单配置
 *
 * 注意：
 * - path 必须与路由配置匹配
 * - icon 名称需在 @element-plus/icons-vue 中存在
 * - roles 用于权限控制，开源版所有用户都是 admin
 */
export const menuConfig: MenuItem[] = [
  {
    path: '/dashboard',
    title: '仪表板',
    icon: 'Odometer',
    roles: ['admin', 'user']
  },
  {
    path: '/learning',
    title: '学习中心',
    icon: 'Reading',
    roles: ['admin', 'user']
  },
  {
    path: '/analysis',
    title: '股票分析',
    icon: 'TrendCharts',
    roles: ['admin', 'user'],
    children: [
      {
        path: '/analysis/single',
        title: '单股分析',
        roles: ['admin', 'user']
      },
      {
        path: '/analysis/batch',
        title: '批量分析',
        roles: ['admin', 'user']
      },
      {
        path: '/reports',
        title: '分析报告',
        roles: ['admin', 'user']
      }
    ]
  },
  {
    path: '/tasks',
    title: '任务中心',
    icon: 'List',
    roles: ['admin', 'user']
  },
  {
    path: '/screening',
    title: '股票筛选',
    icon: 'Search',
    roles: ['admin', 'user']
  },
  {
    path: '/favorites',
    title: '我的自选股',
    icon: 'Star',
    roles: ['admin', 'user']
  },
  {
    path: '/paper',
    title: '模拟交易',
    icon: 'CreditCard',
    roles: ['admin', 'user']
  },
  {
    path: '/backtest',
    title: '回测管理',
    icon: 'TrendCharts',
    roles: ['admin', 'user'],
    children: [
      {
        path: '/backtest/strategies',
        title: '策略管理',
        roles: ['admin', 'user']
      }
    ]
  },
  {
    path: '/settings',
    title: '设置',
    icon: 'Setting',
    roles: ['admin'],
    children: [
      {
        path: '/settings-personal',
        title: '个人设置',
        roles: ['admin'],
        children: [
          { path: '/settings', title: '通用设置', roles: ['admin'] },
          { path: '/settings?tab=appearance', title: '外观设置', roles: ['admin'] },
          { path: '/settings?tab=analysis', title: '分析偏好', roles: ['admin'] },
          { path: '/settings?tab=notifications', title: '通知设置', roles: ['admin'] },
          { path: '/settings?tab=security', title: '安全设置', roles: ['admin'] }
        ]
      },
      {
        path: '/settings-config',
        title: '系统配置',
        roles: ['admin'],
        children: [
          { path: '/settings/config', title: '配置管理', roles: ['admin'] },
          { path: '/settings/cache', title: '缓存管理', roles: ['admin'] }
        ]
      },
      {
        path: '/settings-admin',
        title: '系统管理',
        roles: ['admin'],
        children: [
          { path: '/settings/database', title: '数据库管理', roles: ['admin'] },
          { path: '/settings/logs', title: '操作日志', roles: ['admin'] },
          { path: '/settings/system-logs', title: '系统日志', roles: ['admin'] },
          { path: '/settings/sync', title: '多数据源同步', roles: ['admin'] },
          { path: '/settings/scheduler', title: '定时任务', roles: ['admin'] },
          { path: '/settings/usage', title: '使用统计', roles: ['admin'] }
        ]
      }
    ]
  },
  {
    path: '/about',
    title: '关于',
    icon: 'InfoFilled',
    roles: ['admin', 'user']
  }
]

/**
 * 图标名称到组件的映射
 */
export const iconMap: Record<string, Component> = {
  Odometer: Icons.Odometer,
  Reading: Icons.Reading,
  TrendCharts: Icons.TrendCharts,
  Search: Icons.Search,
  Star: Icons.Star,
  List: Icons.List,
  Setting: Icons.Setting,
  InfoFilled: Icons.InfoFilled,
  CreditCard: Icons.CreditCard
}

/**
 * 获取图标组件
 */
export function getIconComponent(iconName?: string): Component | undefined {
  if (!iconName) return undefined
  return iconMap[iconName]
}
