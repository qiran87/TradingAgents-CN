<template>
  <el-menu
    :default-active="activeMenu"
    :collapse="appStore.sidebarCollapsed"
    :unique-opened="true"
    router
    class="sidebar-menu"
  >
    <!-- 动态渲染菜单项 -->
    <template v-for="item in visibleMenuItems" :key="item.path">
      <!-- 有子菜单 -->
      <el-sub-menu v-if="item.children && item.children.length > 0" :index="item.path">
        <template #title>
          <el-icon v-if="item.icon">
            <component :is="getIconComponent(item.icon)" />
          </el-icon>
          <span>{{ item.title }}</span>
        </template>
        <!-- 递归渲染子菜单 -->
        <template v-for="child in item.children" :key="child.path">
          <el-sub-menu v-if="child.children && child.children.length > 0" :index="child.path">
            <template #title>{{ child.title }}</template>
            <el-menu-item
              v-for="grandchild in child.children"
              :key="grandchild.path"
              :index="grandchild.path"
            >
              {{ grandchild.title }}
            </el-menu-item>
          </el-sub-menu>
          <el-menu-item v-else :index="child.path">
            {{ child.title }}
          </el-menu-item>
        </template>
      </el-sub-menu>

      <!-- 无子菜单 -->
      <el-menu-item v-else :index="item.path">
        <el-icon v-if="item.icon">
          <component :is="getIconComponent(item.icon)" />
        </el-icon>
        <template #title>{{ item.title }}</template>
      </el-menu-item>
    </template>
  </el-menu>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import { menuConfig, getIconComponent, type MenuItem } from '@/config/menuConfig'

const route = useRoute()
const appStore = useAppStore()
const authStore = useAuthStore()

const activeMenu = computed(() => route.path)

/**
 * 检查用户是否有菜单访问权限
 * 开源版：所有登录用户都有admin权限，可以访问所有菜单
 * 预留扩展：为将来的多权限系统做准备
 */
const hasMenuPermission = (requiredRoles?: string[]): boolean => {
  // 未登录用户不能访问任何菜单
  if (!authStore.isAuthenticated) {
    return false
  }

  // 开源版：所有登录用户都是admin，可以访问所有菜单
  if (authStore.isAdmin) {
    return true
  }

  // 如果没有指定角色要求，默认允许访问
  if (!requiredRoles || requiredRoles.length === 0) {
    return true
  }

  // 检查用户是否具有所需角色之一
  return requiredRoles.some(role => authStore.hasRole(role))
}

/**
 * 递归过滤菜单项，只保留用户有权限的菜单
 */
const filterMenuByPermission = (items: MenuItem[]): MenuItem[] => {
  return items.filter(item => {
    // 检查是否隐藏
    if (item.hidden) return false

    // 检查权限
    if (!hasMenuPermission(item.roles)) return false

    // 如果有子菜单，递归过滤
    if (item.children && item.children.length > 0) {
      const filteredChildren = filterMenuByPermission(item.children)
      // 如果所有子菜单都被过滤掉，则不显示父菜单
      if (filteredChildren.length === 0) return false
      // 更新子菜单列表
      item.children = filteredChildren
    }

    return true
  })
}

/**
 * 根据权限过滤后的可见菜单项
 */
const visibleMenuItems = computed(() => filterMenuByPermission(menuConfig))
</script>

<style lang="scss" scoped>
.sidebar-menu {
  border: none;
  height: 100%;

  :deep(.el-menu-item),
  :deep(.el-sub-menu__title) {
    height: 48px;
    line-height: 48px;
  }

  :deep(.el-menu-item.is-active) {
    background-color: var(--el-color-primary-light-9);
    color: var(--el-color-primary);
  }
}
</style>
