<template>
  <div class="strategy-list">
    <div class="page-header">
      <h1 class="page-title">
        <el-icon><TrendCharts /></el-icon>
        策略管理
      </h1>
      <p class="page-description">
        查看和管理回测策略
      </p>
    </div>

    <!-- 筛选和操作栏 -->
    <el-card class="filter-card" shadow="never">
      <el-row :gutter="16" align="middle">
        <!-- 分类选择 -->
        <el-col :span="6">
          <div class="category-tabs">
            <el-radio-group v-model="strategyStore.currentCategory" @change="handleCategoryChange">
              <el-radio-button label="all">全部 ({{ strategyStore.categoryCountMap.get('all') || 0 }})</el-radio-button>
              <el-radio-button
                v-for="category in strategyStore.categories"
                :key="category.category_id"
                :label="category.category_id"
              >
                {{ category.name }} ({{ strategyStore.categoryCountMap.get(category.category_id) || 0 }})
              </el-radio-button>
            </el-radio-group>
          </div>
        </el-col>

        <!-- 搜索框 -->
        <el-col :span="6">
          <el-input
            v-model="searchInput"
            placeholder="搜索策略名称或描述"
            clearable
            @input="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>

        <!-- 排序选择 -->
        <el-col :span="6">
          <el-select v-model="strategyStore.sortBy" placeholder="排序方式" @change="handleSortChange">
            <el-option label="使用最多" value="usage_count" />
            <el-option label="名称 A-Z" value="name_asc" />
            <el-option label="名称 Z-A" value="name_desc" />
          </el-select>
        </el-col>

        <!-- 操作按钮 -->
        <el-col :span="6" class="action-buttons">
          <el-button @click="handleRefresh" :loading="strategyStore.loading">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
          <el-button v-if="hasFilters" @click="handleResetFilters" type="warning" plain>
            <el-icon><Delete /></el-icon>
            清除筛选
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 策略列表 -->
    <div v-loading="strategyStore.loading" class="strategy-grid-container">
      <!-- 空状态 -->
      <el-empty
        v-if="!strategyStore.loading && strategyStore.filteredStrategies.length === 0"
        description="暂无策略"
        :image-size="200"
      >
        <template #extra>
          <el-button v-if="hasFilters" type="primary" @click="handleResetFilters">
            清除筛选条件
          </el-button>
        </template>
      </el-empty>

      <!-- 策略卡片网格 -->
      <div v-else class="strategy-grid">
        <el-card
          v-for="strategy in strategyStore.filteredStrategies"
          :key="strategy.strategy_id"
          class="strategy-card"
          shadow="hover"
          @click="handleViewDetail(strategy)"
        >
          <!-- 策略头部 -->
          <template #header>
            <div class="strategy-card-header">
              <div class="strategy-name">{{ strategy.name }}</div>
              <el-tag v-if="strategy.is_builtin" type="success" size="small">内置</el-tag>
            </div>
          </template>

          <!-- 策略内容 -->
          <div class="strategy-card-body">
            <p class="strategy-description">{{ strategy.description }}</p>

            <div class="strategy-meta">
              <div class="meta-item">
                <el-icon><DataLine /></el-icon>
                <span>使用次数: {{ strategy.usage_count }}</span>
              </div>
              <div class="meta-item">
                <el-icon><Operation /></el-icon>
                <span>参数数量: {{ strategy.parameter_count }}</span>
              </div>
              <div class="meta-item">
                <el-tag :type="getCategoryTagType(strategy.category)" size="small">
                  {{ getCategoryName(strategy.category) }}
                </el-tag>
              </div>
            </div>
          </div>

          <!-- 操作按钮 -->
          <template #footer>
            <el-button type="primary" link @click.stop="handleViewDetail(strategy)">
              查看详情
            </el-button>
          </template>
        </el-card>
      </div>
    </div>

    <!-- 策略详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      :title="currentStrategyDetail?.name"
      width="700px"
      @closed="handleDialogClosed"
    >
      <div v-if="currentStrategyDetail" class="strategy-detail">
        <!-- 描述 -->
        <div class="detail-section">
          <h3>策略说明</h3>
          <p class="description">{{ currentStrategyDetail.long_description || currentStrategyDetail.description }}</p>
        </div>

        <!-- 分类 -->
        <div class="detail-section">
          <h3>策略分类</h3>
          <el-tag :type="getCategoryTagType(currentStrategyDetail.category)" size="large">
            {{ getCategoryName(currentStrategyDetail.category) }}
          </el-tag>
        </div>

        <!-- 统计信息 -->
        <div class="detail-section">
          <h3>统计信息</h3>
          <el-row :gutter="16">
            <el-col :span="8">
              <div class="stat-item">
                <div class="stat-label">使用次数</div>
                <div class="stat-value">{{ currentStrategyDetail.usage_count }}</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-item">
                <div class="stat-label">参数数量</div>
                <div class="stat-value">{{ currentStrategyDetail.parameter_count }}</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-item">
                <div class="stat-label">策略类型</div>
                <div class="stat-value">{{ currentStrategyDetail.is_builtin ? '内置策略' : '自定义策略' }}</div>
              </div>
            </el-col>
          </el-row>
        </div>

        <!-- 参数列表 -->
        <div class="detail-section">
          <h3>策略参数</h3>
          <el-table :data="currentStrategyDetail.parameters" border>
            <el-table-column prop="name" label="参数名称" width="120" />
            <el-table-column prop="type" label="类型" width="80">
              <template #default="{ row }">
                <el-tag size="small">{{ row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="default_value" label="默认值" width="100" />
            <el-table-column prop="description" label="说明" />
            <el-table-column label="取值范围" width="150">
              <template #default="{ row }">
                <span v-if="row.range">
                  {{ row.range.min }} ~ {{ row.range.max }}
                </span>
                <span v-else-if="row.options">
                  {{ row.options.join(', ') }}
                </span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="必填" width="80">
              <template #default="{ row }">
                <el-tag :type="row.required ? 'danger' : 'info'" size="small">
                  {{ row.required ? '是' : '否' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="detailDialogVisible = false">关闭</el-button>
          <el-button type="primary" @click="handleUseStrategy">
            使用此策略
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useStrategyStore } from '@/stores/strategy'
import { type StrategySummary, type StrategyDetail } from '@/api/strategies'
import { ElMessage } from 'element-plus'
import {
  TrendCharts,
  Search,
  Refresh,
  Delete,
  DataLine,
  Operation
} from '@element-plus/icons-vue'

// ===================== Store =====================
const strategyStore = useStrategyStore()

// ===================== 响应式数据 =====================
const searchInput = ref('')
const detailDialogVisible = ref(false)
const currentStrategyDetail = ref<StrategyDetail | null>(null)

// ===================== 计算属性 =====================
const hasFilters = computed(() => {
  return strategyStore.currentCategory !== 'all' ||
         strategyStore.searchKeyword !== '' ||
         strategyStore.sortBy !== 'usage_count'
})

// ===================== 方法 =====================

/**
 * 初始化
 */
async function initialize() {
  try {
    await strategyStore.initialize()
  } catch (error) {
    console.error('初始化失败:', error)
  }
}

/**
 * 刷新数据
 */
async function handleRefresh() {
  await initialize()
  ElMessage.success('刷新成功')
}

/**
 * 分类变化
 */
function handleCategoryChange() {
  // 分类变化时自动更新
}

/**
 * 搜索输入（带防抖）
let searchTimer: number | null = null
function handleSearch() {
  if (searchTimer) {
    clearTimeout(searchTimer)
  }
  searchTimer = setTimeout(() => {
    strategyStore.setSearchKeyword(searchInput.value)
  }, 300)
}

/**
 * 排序变化
 */
function handleSortChange() {
  // 排序变化时自动更新
}

/**
 * 重置筛选
 */
function handleResetFilters() {
  searchInput.value = ''
  strategyStore.resetFilters()
  ElMessage.info('已重置筛选条件')
}

/**
 * 查看策略详情
 */
async function handleViewDetail(strategy: StrategySummary) {
  try {
    const detail = await strategyStore.fetchStrategyDetail(strategy.strategy_id)
    currentStrategyDetail.value = detail
    detailDialogVisible.value = true
  } catch (error) {
    console.error('获取策略详情失败:', error)
  }
}

/**
 * 对话框关闭
 */
function handleDialogClosed() {
  currentStrategyDetail.value = null
}

/**
 * 使用策略
 */
function handleUseStrategy() {
  if (!currentStrategyDetail.value) return

  ElMessage.info(`已选择策略：${currentStrategyDetail.value.name}`)
  // TODO: 跳转到回测页面并预选该策略
  detailDialogVisible.value = false
}

/**
 * 获取分类名称
 */
function getCategoryName(categoryId: string) {
  const category = strategyStore.categories.find(c => c.category_id === categoryId)
  return category?.name || categoryId
}

/**
 * 获取分类标签类型
 */
function getCategoryTagType(categoryId: string) {
  const typeMap: Record<string, string> = {
    'trend': 'success',
    'oscillation': 'warning',
    'momentum': 'danger'
  }
  return typeMap[categoryId] || 'info'
}

// ===================== 生命周期 =====================
onMounted(() => {
  initialize()
})
</script>

<style scoped lang="scss">
.strategy-list {
  padding: 20px;

  .page-header {
    margin-bottom: 20px;

    .page-title {
      font-size: 24px;
      font-weight: 600;
      margin: 0 0 8px 0;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .page-description {
      font-size: 14px;
      color: var(--el-text-color-secondary);
      margin: 0;
    }
  }

  .filter-card {
    margin-bottom: 20px;

    .category-tabs {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .action-buttons {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
    }
  }

  .strategy-grid-container {
    min-height: 400px;
  }

  .strategy-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 20px;

    .strategy-card {
      cursor: pointer;
      transition: all 0.3s;

      &:hover {
        transform: translateY(-4px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      }

      .strategy-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;

        .strategy-name {
          font-size: 18px;
          font-weight: 600;
          color: var(--el-text-color-primary);
        }
      }

      .strategy-card-body {
        .strategy-description {
          font-size: 14px;
          color: var(--el-text-color-secondary);
          margin: 12px 0;
          min-height: 40px;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }

        .strategy-meta {
          display: flex;
          gap: 16px;
          margin-top: 12px;

          .meta-item {
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 12px;
            color: var(--el-text-color-secondary);
          }
        }
      }
    }
  }

  .strategy-detail {
    .detail-section {
      margin-bottom: 24px;

      &:last-child {
        margin-bottom: 0;
      }

      h3 {
        font-size: 16px;
        font-weight: 600;
        margin: 0 0 12px 0;
        color: var(--el-text-color-primary);
      }

      .description {
        font-size: 14px;
        line-height: 1.6;
        color: var(--el-text-color-regular);
        margin: 0;
      }

      .stat-item {
        text-align: center;
        padding: 12px;
        background: var(--el-fill-color-light);
        border-radius: 4px;

        .stat-label {
          font-size: 12px;
          color: var(--el-text-color-secondary);
          margin-bottom: 4px;
        }

        .stat-value {
          font-size: 18px;
          font-weight: 600;
          color: var(--el-color-primary);
        }
      }
    }
  }
}
</style>
