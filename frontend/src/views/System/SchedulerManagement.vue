<template>
  <div class="scheduler-management">
    <!-- 页面标题和统计信息 -->
    <el-card class="header-card" shadow="never">
      <div class="header-content">
        <div class="title-section">
          <h2>
            <el-icon><Timer /></el-icon>
            定时任务管理
          </h2>
          <p class="subtitle">管理系统中的所有定时任务，支持暂停、恢复和手动触发</p>
        </div>
        
        <div class="stats-section" v-if="stats">
          <el-statistic title="总任务数" :value="stats.total_jobs">
            <template #prefix>
              <el-icon><List /></el-icon>
            </template>
          </el-statistic>
          <el-statistic title="运行中" :value="stats.running_jobs">
            <template #prefix>
              <el-icon color="#67C23A"><VideoPlay /></el-icon>
            </template>
          </el-statistic>
          <el-statistic title="已暂停" :value="stats.paused_jobs">
            <template #prefix>
              <el-icon color="#E6A23C"><VideoPause /></el-icon>
            </template>
          </el-statistic>
        </div>
      </div>
      
      <div class="actions">
        <el-button @click="loadJobs" :loading="loading" :icon="Refresh">刷新</el-button>
        <el-button @click="showHistoryDialog" :icon="Document">执行历史</el-button>
        <el-button
          v-if="isAdmin"
          type="warning"
          @click="showBatchSyncDialog"
          :icon="Promotion"
        >
          批量同步历史数据
        </el-button>
      </div>
    </el-card>

    <!-- 搜索和筛选 -->
    <el-card class="filter-card" shadow="never">
      <el-form :inline="true" class="filter-form">
        <el-form-item label="任务名称">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索任务名称"
            clearable
            :prefix-icon="Search"
            style="width: 240px"
            @clear="handleSearch"
            @input="handleSearch"
          />
        </el-form-item>

        <el-form-item label="数据源">
          <el-select
            v-model="filterDataSource"
            placeholder="全部数据源"
            clearable
            style="width: 180px"
            @change="handleSearch"
          >
            <el-option label="全部数据源" value="" />
            <el-option label="Tushare" value="Tushare" />
            <el-option label="AKShare" value="AKShare" />
            <el-option label="BaoStock" value="BaoStock" />
            <el-option label="多数据源" value="多数据源" />
            <el-option label="其他" value="其他" />
          </el-select>
        </el-form-item>

        <el-form-item label="状态">
          <el-select
            v-model="filterStatus"
            placeholder="全部状态"
            clearable
            style="width: 150px"
            @change="handleSearch"
          >
            <el-option label="全部状态" value="" />
            <el-option label="运行中" value="running" />
            <el-option label="已暂停" value="paused" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button :icon="Refresh" @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 任务列表 -->
    <el-card class="table-card" shadow="never">
      <el-table
        :data="filteredJobs"
        v-loading="loading"
        stripe
        style="width: 100%"
        :default-sort="{ prop: 'paused', order: 'ascending' }"
      >
        <el-table-column prop="name" label="任务名称" min-width="200" sortable>
          <template #default="{ row }">
            <div class="job-name">
              <el-tag :type="row.paused ? 'warning' : 'success'" size="small">
                {{ row.paused ? '已暂停' : '运行中' }}
              </el-tag>
              <span class="name-text">{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="display_name" label="触发器名称" min-width="150">
          <template #default="{ row }">
            <el-text v-if="row.display_name" size="small">{{ row.display_name }}</el-text>
            <el-text v-else type="info" size="small">-</el-text>
          </template>
        </el-table-column>

        <el-table-column prop="trigger" label="触发器" min-width="180">
          <template #default="{ row }">
            <el-text size="small" type="info">{{ formatTrigger(row.trigger) }}</el-text>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="备注" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <el-text v-if="row.description" size="small">{{ row.description }}</el-text>
            <el-text v-else type="info" size="small">-</el-text>
          </template>
        </el-table-column>

        <el-table-column prop="next_run_time" label="下次执行时间" min-width="180" sortable>
          <template #default="{ row }">
            <div v-if="row.next_run_time">
              <el-text size="small">{{ formatDateTime(row.next_run_time) }}</el-text>
              <br />
              <el-text size="small" type="info">{{ formatRelativeTime(row.next_run_time) }}</el-text>
            </div>
            <el-text v-else type="warning" size="small">已暂停</el-text>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="340" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button
                size="small"
                :icon="Edit"
                @click="showEditDialog(row)"
              >
                编辑
              </el-button>
              <el-button
                v-if="!row.paused"
                size="small"
                type="warning"
                :icon="VideoPause"
                @click="handlePause(row)"
                :loading="actionLoading[row.id]"
              >
                暂停
              </el-button>
              <el-button
                v-else
                size="small"
                type="success"
                :icon="VideoPlay"
                @click="handleResume(row)"
                :loading="actionLoading[row.id]"
              >
                恢复
              </el-button>
              <el-button
                size="small"
                type="primary"
                :icon="Promotion"
                @click="handleTrigger(row)"
                :loading="actionLoading[row.id]"
              >
                立即执行
              </el-button>
              <el-button
                size="small"
                :icon="View"
                @click="showJobDetail(row)"
              >
                详情
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑任务元数据对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑任务信息"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form v-if="editingJob" :model="editForm" label-width="120px">
        <el-form-item label="任务ID">
          <el-text>{{ editingJob.id }}</el-text>
        </el-form-item>
        <el-form-item label="任务名称">
          <el-text>{{ editingJob.name }}</el-text>
        </el-form-item>
        <el-form-item label="触发器名称">
          <el-input
            v-model="editForm.display_name"
            placeholder="请输入触发器名称（可选）"
            clearable
            maxlength="50"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="editForm.description"
            type="textarea"
            :rows="4"
            placeholder="请输入备注信息（可选）"
            clearable
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveMetadata" :loading="saveLoading">保存</el-button>
      </template>
    </el-dialog>

    <!-- 任务详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="任务详情"
      width="700px"
      :close-on-click-modal="false"
    >
      <el-descriptions v-if="currentJob" :column="1" border>
        <el-descriptions-item label="任务ID">{{ currentJob.id }}</el-descriptions-item>
        <el-descriptions-item label="任务名称">{{ currentJob.name }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="currentJob.paused ? 'warning' : 'success'">
            {{ currentJob.paused ? '已暂停' : '运行中' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="触发器">{{ currentJob.trigger }}</el-descriptions-item>
        <el-descriptions-item label="下次执行时间">
          {{ currentJob.next_run_time ? formatDateTime(currentJob.next_run_time) : '已暂停' }}
        </el-descriptions-item>
        <el-descriptions-item label="执行函数" v-if="currentJob.func">
          <el-text size="small" type="info">{{ currentJob.func }}</el-text>
        </el-descriptions-item>
        <el-descriptions-item label="参数" v-if="currentJob.kwargs">
          <pre class="code-block">{{ JSON.stringify(currentJob.kwargs, null, 2) }}</pre>
        </el-descriptions-item>
      </el-descriptions>

      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="showJobHistory(currentJob!)">查看执行历史</el-button>
      </template>
    </el-dialog>

    <!-- 执行历史对话框 -->
    <el-dialog
      v-model="historyDialogVisible"
      title="执行历史"
      width="1200px"
      :close-on-click-modal="false"
    >
      <el-tabs v-model="activeHistoryTab" @tab-change="handleHistoryTabChange">
        <!-- 手动操作历史 -->
        <el-tab-pane label="手动操作历史" name="manual">
          <el-table :data="historyList" v-loading="historyLoading" stripe max-height="500">
            <el-table-column prop="job_name" label="任务名称" min-width="200" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag
                  :type="row.status === 'success' ? 'success' : row.status === 'failed' ? 'danger' : row.status === 'running' ? 'info' : 'warning'"
                  size="small"
                >
                  {{ formatExecutionStatus(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="progress" label="进度" width="150">
              <template #default="{ row }">
                <div v-if="row.status === 'running' && row.progress !== undefined">
                  <el-progress :percentage="row.progress" :stroke-width="6" />
                  <el-text v-if="row.processed_items && row.total_items" size="small" type="info" style="margin-top: 4px">
                    {{ row.processed_items }}/{{ row.total_items }}
                  </el-text>
                </div>
                <el-text v-else-if="row.progress !== undefined" type="info" size="small">{{ row.progress }}%</el-text>
                <el-text v-else type="info" size="small">-</el-text>
              </template>
            </el-table-column>
            <el-table-column prop="progress_message" label="当前操作" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">
                <el-text v-if="row.progress_message" size="small">
                  {{ row.progress_message }}
                </el-text>
                <el-text v-else-if="row.current_item" size="small">
                  {{ row.current_item }}
                </el-text>
                <el-text v-else type="info" size="small">-</el-text>
              </template>
            </el-table-column>
            <el-table-column prop="timestamp" label="执行时长" width="180">
              <template #default="{ row }">
                <span v-if="row.execution_time !== undefined && row.execution_time !== null">
                  {{ row.execution_time.toFixed(2) }}秒
                </span>
                <span v-else-if="row.status === 'running' && row.timestamp">
                  {{ calculateRunningTime(row.updated_at || row.timestamp) }}
                </span>
                <el-text v-else type="info" size="small">-</el-text>
              </template>
            </el-table-column>
            <el-table-column prop="updated_at" label="更新时间" width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.updated_at || row.timestamp) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="row.error_message || row.status === 'running'"
                  link
                  type="primary"
                  size="small"
                  @click="showExecutionDetail(row)"
                >
                  详情
                </el-button>
                <el-button
                  v-if="row.status === 'running'"
                  link
                  type="warning"
                  size="small"
                  @click="handleCancelExecution(row)"
                >
                  终止
                </el-button>
                <el-button
                  v-if="row.status === 'running'"
                  link
                  type="danger"
                  size="small"
                  @click="handleMarkFailed(row)"
                >
                  标记失败
                </el-button>
                <el-button
                  v-if="row.status !== 'running'"
                  link
                  type="danger"
                  size="small"
                  @click="handleDeleteExecution(row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-if="historyTotal > historyPageSize"
            class="pagination"
            :current-page="historyPage"
            :page-size="historyPageSize"
            :total="historyTotal"
            layout="total, prev, pager, next"
            @current-change="handleHistoryPageChange"
          />
        </el-tab-pane>

        <!-- 自动执行监控 -->
        <el-tab-pane label="自动执行监控" name="execution">
          <!-- 筛选条件 -->
          <el-form :inline="true" style="margin-bottom: 16px">
            <el-form-item label="状态">
              <el-select
                v-model="executionStatusFilter"
                placeholder="全部状态"
                clearable
                style="width: 150px"
                @change="loadExecutions"
              >
                <el-option label="全部状态" value="" />
                <el-option label="执行中" value="running" />
                <el-option label="成功" value="success" />
                <el-option label="失败" value="failed" />
                <el-option label="错过" value="missed" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button :icon="Refresh" @click="loadExecutions">刷新</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="executionList" v-loading="executionLoading" stripe max-height="500">
            <el-table-column prop="job_name" label="任务名称" min-width="200" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag
                  :type="row.status === 'success' ? 'success' : row.status === 'failed' ? 'danger' : row.status === 'running' ? 'info' : 'warning'"
                  size="small"
                >
                  {{ formatExecutionStatus(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="progress" label="进度" width="150">
              <template #default="{ row }">
                <div v-if="row.status === 'running' && row.progress !== undefined">
                  <el-progress :percentage="row.progress" :stroke-width="6" />
                  <el-text v-if="row.processed_items && row.total_items" size="small" type="info" style="margin-top: 4px">
                    {{ row.processed_items }}/{{ row.total_items }}
                  </el-text>
                </div>
                <el-text v-else-if="row.progress !== undefined" type="info" size="small">{{ row.progress }}%</el-text>
                <el-text v-else type="info" size="small">-</el-text>
              </template>
            </el-table-column>
            <el-table-column prop="progress_message" label="当前操作" min-width="180" show-overflow-tooltip>
              <template #default="{ row }">
                <el-text v-if="row.progress_message" size="small">
                  {{ row.progress_message }}
                </el-text>
                <el-text v-else-if="row.current_item" size="small">
                  {{ row.current_item }}
                </el-text>
                <el-text v-else type="info" size="small">-</el-text>
              </template>
            </el-table-column>
            <el-table-column prop="execution_time" label="执行时长" width="180">
              <template #default="{ row }">
                <span v-if="row.execution_time !== undefined && row.execution_time !== null">
                  {{ row.execution_time.toFixed(2) }}秒
                </span>
                <span v-else-if="row.status === 'running' && row.timestamp">
                  {{ calculateRunningTime(row.updated_at || row.timestamp) }}
                </span>
                <el-text v-else type="info" size="small">-</el-text>
              </template>
            </el-table-column>
            <el-table-column prop="scheduled_time" label="计划时间" width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.scheduled_time) }}
              </template>
            </el-table-column>
            <el-table-column prop="updated_at" label="更新时间" width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.updated_at || row.timestamp) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="row.error_message || row.status === 'running'"
                  link
                  type="primary"
                  size="small"
                  @click="showExecutionDetail(row)"
                >
                  详情
                </el-button>
                <el-button
                  v-if="row.status === 'running'"
                  link
                  type="warning"
                  size="small"
                  @click="handleCancelExecution(row)"
                >
                  终止
                </el-button>
                <el-button
                  v-if="row.status === 'running'"
                  link
                  type="danger"
                  size="small"
                  @click="handleMarkFailed(row)"
                >
                  标记失败
                </el-button>
                <el-button
                  v-if="row.status !== 'running'"
                  link
                  type="danger"
                  size="small"
                  @click="handleDeleteExecution(row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-if="executionTotal > executionPageSize"
            class="pagination"
            :current-page="executionPage"
            :page-size="executionPageSize"
            :total="executionTotal"
            layout="total, prev, pager, next"
            @current-change="handleExecutionPageChange"
          />
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="historyDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 执行详情对话框 -->
    <el-dialog
      v-model="executionDetailDialogVisible"
      title="执行详情"
      width="900px"
      :close-on-click-modal="false"
    >
      <el-descriptions v-if="currentExecution" :column="1" border>
        <el-descriptions-item label="任务名称">
          {{ currentExecution.job_name }}
        </el-descriptions-item>
        <el-descriptions-item label="任务ID">
          {{ currentExecution.job_id }}
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag
            :type="currentExecution.status === 'success' ? 'success' : currentExecution.status === 'failed' ? 'danger' : currentExecution.status === 'running' ? 'info' : 'warning'"
          >
            {{ formatExecutionStatus(currentExecution.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="进度" v-if="currentExecution.status === 'running' && currentExecution.progress !== undefined">
          <el-progress :percentage="currentExecution.progress" :stroke-width="8" />
          <div v-if="currentExecution.processed_items && currentExecution.total_items" style="margin-top: 8px">
            <el-text size="small">已处理: {{ currentExecution.processed_items }} / {{ currentExecution.total_items }}</el-text>
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="当前操作" v-if="currentExecution.progress_message || currentExecution.current_item">
          <el-text>{{ currentExecution.progress_message || currentExecution.current_item }}</el-text>
        </el-descriptions-item>
        <el-descriptions-item label="计划时间">
          {{ formatDateTime(currentExecution.scheduled_time) }}
        </el-descriptions-item>
        <el-descriptions-item label="更新时间">
          {{ formatDateTime(currentExecution.updated_at || currentExecution.timestamp) }}
        </el-descriptions-item>
        <el-descriptions-item label="执行时长" v-if="currentExecution.execution_time !== undefined">
          {{ currentExecution.execution_time.toFixed(2) }}秒
        </el-descriptions-item>
        <el-descriptions-item label="错误信息" v-if="currentExecution.error_message">
          <el-text type="danger">{{ currentExecution.error_message }}</el-text>
        </el-descriptions-item>
        <el-descriptions-item label="错误堆栈" v-if="currentExecution.traceback">
          <pre style="max-height: 300px; overflow-y: auto; background: #f5f5f5; padding: 12px; border-radius: 4px;">{{ currentExecution.traceback }}</pre>
        </el-descriptions-item>
      </el-descriptions>

      <!-- MDVAES 批量同步详细结果 -->
      <div v-if="currentExecution && currentExecution.return_value && currentExecution.return_value.detailed_description" style="margin-top: 24px;">
        <el-divider content-position="left">
          <strong>📊 同步结果详情</strong>
        </el-divider>
        <div class="mdvaes-sync-detail" style="max-height: 400px; overflow-y: auto; background: #f8f9fa; padding: 16px; border-radius: 8px; margin-top: 12px;">
          <pre style="white-space: pre-wrap; word-wrap: break-word; font-family: inherit; font-size: 14px; line-height: 1.8; margin: 0;">{{ currentExecution.return_value.detailed_description }}</pre>
        </div>
      </div>

      <template #footer>
        <el-button @click="executionDetailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 批量同步历史数据对话框 -->
    <el-dialog
      v-model="batchSyncDialogVisible"
      title="批量同步 MDVAES 历史数据"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-alert
        title="📊 MDVAES 历史数据说明"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 20px"
      >
        <template #default>
          <div style="line-height: 1.8;">
            <p><strong>同步功能：</strong>补充缺失的 MDVAES 模型所需的历史数据，确保估值计算准确性。</p>

            <div style="margin-top: 12px;">
              <el-divider content-position="left">
                <strong>📋 同步数据表详情</strong>
              </el-divider>

              <el-collapse style="margin-top: 12px; border: none;">
                <el-collapse-item title="1️⃣ mdvaes_analyst_forecasts（分析师盈利预测）" name="1">
                  <ul style="margin: 8px 0 0 20px; padding-left: 20px; line-height: 1.6;">
                    <li><strong>数据来源：</strong>Tushare pro.fina_indicator（财务指标接口）</li>
                    <li><strong>同步字段：</strong>
                      <ul style="margin: 4px 0 0 8px; padding-left: 20px;">
                        <li>ts_code - 股票代码（如 000001.SZ）</li>
                        <li>report_date - 研报发布日期（YYYYMMDD格式）</li>
                        <li>quarter - 预测季度（如 2024Q1、2024Q2）</li>
                        <li>eps - EPS预测值（每股收益）</li>
                      </ul>
                    </li>
                    <li><strong>用途：</strong>优先用于EPS预测（比历史外推更准确）</li>
                    <li><strong>更新频率：</strong>季度/年度更新</li>
                  </ul>
                </el-collapse-item>

                <el-collapse-item title="2️⃣ mdvaes_pe_history（PE历史数据）" name="2">
                  <ul style="margin: 8px 0 0 20px; padding-left: 20px; line-height: 1.6;">
                    <li><strong>数据来源：</strong>Tushare pro.daily_basic（日线行情接口）</li>
                    <li><strong>同步字段：</strong>
                      <ul style="margin: 4px 0 0 8px; padding-left: 20px;">
                        <li>ts_code - 股票代码</li>
                        <li>trade_date - 交易日期（YYYYMMDD格式）</li>
                        <li>pe_ttm - 滚动市盈率（股价 / 最近12个月EPS）</li>
                        <li>turnover_rate - 换手率</li>
                        <li>volume_ratio - 量比</li>
                      </ul>
                    </li>
                    <li><strong>用途：</strong>用于估值时的当前PE参数</li>
                    <li><strong>更新频率：</strong>每个交易日更新</li>
                  </ul>
                </el-collapse-item>

                <el-collapse-item title="3️⃣ mdvaes_bond_rate（国债收益率）" name="3">
                  <ul style="margin: 8px 0 0 20px; padding-left: 20px; line-height: 1.6;">
                    <li><strong>数据来源：</strong>Tushare pro.yc_cb（国债期货收益率曲线）</li>
                    <li><strong>同步字段：</strong>
                      <ul style="margin: 4px 0 0 8px; padding-left: 20px;">
                        <li>trade_date - 交易日期</li>
                        <li>curve_term - 期限（固定10.0）</li>
                        <li>yield - 收益率（百分比，如2.75表示2.75%）</li>
                      </ul>
                    </li>
                    <li><strong>用途：</strong>用于估值时的无风险利率参数</li>
                    <li><strong>更新频率：</strong>每个交易日更新</li>
                  </ul>
                </el-collapse-item>

                <el-collapse-item title="4️⃣ mdvaes_financial_ratios（财务比率数据）" name="4">
                  <ul style="margin: 8px 0 0 20px; padding-left: 20px; line-height: 1.6;">
                    <li><strong>数据来源：</strong>Tushare pro.fina_indicator（财务指标接口）</li>
                    <li><strong>同步字段：</strong>
                      <ul style="margin: 4px 0 0 8px; padding-left: 20px;">
                        <li>ts_code - 股票代码</li>
                        <li>ann_date - 公告日期（YYYYMMDD格式）</li>
                        <li>end_date - 报告期（YYYYMMDD格式，如20231231）</li>
                        <li>debt_to_assets - 资产负债率（百分比）</li>
                        <li>current_ratio - 流动比率</li>
                        <li>quick_ratio - 速动比率</li>
                        <li>roe - 净资产收益率（ROE）</li>
                        <li>roa - 总资产收益率（ROA）</li>
                      </ul>
                    </li>
                    <li><strong>用途：</strong>用于风险评估（资产负债率、流动性等）</li>
                    <li><strong>更新频率：</strong>季度/年度更新</li>
                  </ul>
                </el-collapse-item>

                <el-collapse-item title="5️⃣ mdvaes_eps_history（EPS历史数据）" name="5">
                  <ul style="margin: 8px 0 0 20px; padding-left: 20px; line-height: 1.6;">
                    <li><strong>数据来源：</strong>Tushare pro.fina_indicator（财务指标接口）</li>
                    <li><strong>同步字段：</strong>
                      <ul style="margin: 4px 0 0 8px; padding-left: 20px;">
                        <li>ts_code - 股票代码</li>
                        <li>ann_date - 公告日期（YYYYMMDD格式）</li>
                        <li>end_date - 报告期（YYYYMMDD格式，如20231231）</li>
                        <li>eps - 基本每股收益</li>
                        <li>dt_eps - 稀释每股收益</li>
                      </ul>
                    </li>
                    <li><strong>用途：</strong>用于历史EPS外推（当无分析师预测时使用）</li>
                    <li><strong>更新频率：</strong>季度/年度更新</li>
                  </ul>
                </el-collapse-item>
              </el-collapse>
            </div>

            <div style="margin-top: 12px;">
              <el-divider content-position="left">
                <strong>⚡ 同步策略</strong>
              </el-divider>
              <ul style="margin: 8px 0 0 0; padding-left: 20px; line-height: 1.6;">
                <li><strong>按年份批量同步：</strong>支持多年度数据同步（如2020-2023）</li>
                <li><strong>智能去重：</strong>使用 upsert 策略，已存在数据自动跳过</li>
                <li><strong>批次处理：</strong>每批100只股票，避免API超时</li>
                <li><strong>过滤无效值：</strong>自动过滤 NaN 值，只存储有效数据</li>
              </ul>
            </div>

            <div style="margin-top: 12px; padding: 8px; background: #fff3cd; border-radius: 4px; border-left: 3px solid #ffc107;">
              <p style="margin: 0; color: #664d03;"><strong>⚠️ 建议：</strong>在非交易时间进行大范围同步，避免影响交易时段的系统性能。</p>
            </div>
          </div>
        </template>
      </el-alert>

      <el-form :model="batchSyncForm" label-width="100px" label-position="top">
        <!-- 快捷选择 -->
        <el-form-item label="快捷选择">
          <div class="quick-ranges">
            <el-button
              v-for="range in quickDateRanges"
              :key="range.label"
              size="small"
              @click="selectQuickDateRange(range)"
            >
              {{ range.label }}
            </el-button>
          </div>
        </el-form-item>

        <!-- 日期范围选择 -->
        <el-form-item label="自定义范围" required>
          <el-date-picker
            v-model="batchSyncForm.dateRange"
            type="daterange"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            :disabled-date="disabledDate"
            :clearable="false"
            style="width: 100%"
          />
        </el-form-item>

        <!-- 表选择 -->
        <el-form-item label="选择要同步的表">
          <el-checkbox-group v-model="batchSyncForm.selectedTables">
            <el-checkbox-button
              v-for="table in mdvaesTableOptions"
              :key="table.value"
              :label="table.value"
              style="margin-right: 8px; margin-bottom: 8px"
            >
              {{ table.label }}
            </el-checkbox-button>
          </el-checkbox-group>
          <div style="margin-top: 8px;">
            <el-button size="small" @click="selectAllTables">全选</el-button>
            <el-button size="small" @click="clearAllTables">清空</el-button>
            <el-button size="small" type="primary" @click="selectCommonTables">常用选择</el-button>
          </div>
        </el-form-item>

        <!-- 预估信息 -->
        <el-form-item label="预估信息">
          <div v-if="batchSyncForm.dateRange && batchSyncForm.dateRange.length === 2" class="estimate-info">
            <el-text size="small">
              <el-icon><Calendar /></el-icon>
              同步天数：<strong>{{ estimatedDays }}</strong> 天
            </el-text>
            <br />
            <el-text size="small" type="info">
              预计耗时：约 <strong>{{ estimatedTime }}</strong> （实际视网络情况而定）
            </el-text>
            <br />
            <el-text size="small" type="info">
              已选择：<strong>{{ batchSyncForm.selectedTables.length }}</strong> 张表
            </el-text>
          </div>
          <el-text v-else type="info">请选择日期范围</el-text>
        </el-form-item>

        <!-- 注意事项 -->
        <el-form-item label="注意事项">
          <div class="tips">
            <p>• 单次同步时间范围不超过 3 年</p>
            <p>• 可重复执行不同时间段，已存在数据会自动跳过</p>
            <p>• 确保网络连接稳定，Tushare API 有调用限制</p>
            <p>• 至少选择一张表进行同步</p>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="batchSyncDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          @click="startBatchSync"
          :loading="batchSyncSubmitting"
          :disabled="!batchSyncForm.dateRange || batchSyncForm.dateRange.length !== 2 || batchSyncForm.selectedTables.length === 0"
        >
          开始同步
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Timer,
  List,
  VideoPlay,
  VideoPause,
  Refresh,
  Document,
  Promotion,
  View,
  Edit,
  Search,
  Calendar
} from '@element-plus/icons-vue'
import {
  getJobs,
  getJobDetail,
  pauseJob,
  resumeJob,
  triggerJob,
  updateJobMetadata,
  getSchedulerStats,
  getJobExecutions,
  getSingleJobExecutions,
  cancelExecution,
  markExecutionFailed,
  deleteExecution,
  type Job,
  type JobHistory,
  type JobExecution,
  type SchedulerStats
} from '@/api/scheduler'
import { formatDateTime, formatRelativeTime } from '@/utils/datetime'
import { useAuthStore } from '@/stores/auth'
import dayjs from 'dayjs'

// 数据
const loading = ref(false)
const jobs = ref<Job[]>([])
const stats = ref<SchedulerStats | null>(null)
const actionLoading = reactive<Record<string, boolean>>({})

// 用户信息
const authStore = useAuthStore()
const isAdmin = computed(() => authStore.user?.is_admin === true)

// 搜索和筛选
const searchKeyword = ref('')
const filterDataSource = ref('')
const filterStatus = ref('')

// 编辑任务元数据
const editDialogVisible = ref(false)
const editingJob = ref<Job | null>(null)
const editForm = reactive({
  display_name: '',
  description: ''
})
const saveLoading = ref(false)

// 任务详情
const detailDialogVisible = ref(false)
const currentJob = ref<Job | null>(null)

// 执行历史
const historyDialogVisible = ref(false)
const historyLoading = ref(false)
const historyList = ref<JobHistory[]>([])
const historyTotal = ref(0)
const historyPage = ref(1)
const historyPageSize = ref(20)
const currentHistoryJobId = ref<string | null>(null)
const activeHistoryTab = ref('manual')

// 任务执行监控
const executionLoading = ref(false)
const executionList = ref<JobExecution[]>([])
const executionTotal = ref(0)
const executionPage = ref(1)
const executionPageSize = ref(20)
const executionStatusFilter = ref('')
const executionDetailDialogVisible = ref(false)
const currentExecution = ref<JobExecution | null>(null)

// 批量同步历史数据
const batchSyncDialogVisible = ref(false)
const batchSyncSubmitting = ref(false)
const batchSyncForm = reactive({
  dateRange: [null, null] as [string | null, string | null],
  selectedTables: ['analyst_forecasts', 'pe_history', 'bond_rate', 'financial_ratios', 'eps_history'] as string[]
})

// MDVAES 表选项
const mdvaesTableOptions = [
  { label: '分析师盈利预测', value: 'analyst_forecasts' },
  { label: 'PE历史数据', value: 'pe_history' },
  { label: '国债收益率', value: 'bond_rate' },
  { label: '财务比率数据', value: 'financial_ratios' },
  { label: 'EPS历史数据', value: 'eps_history' }
]

// 全选表
const selectAllTables = () => {
  batchSyncForm.selectedTables = mdvaesTableOptions.map(t => t.value)
}

// 清空选择
const clearAllTables = () => {
  batchSyncForm.selectedTables = []
}

// 常用选择（排除 EPS 历史数据，因为它通常数据量最大）
const selectCommonTables = () => {
  batchSyncForm.selectedTables = ['analyst_forecasts', 'pe_history', 'bond_rate', 'financial_ratios']
}

// 快捷日期范围选项
const quickDateRanges = [
  {
    label: '最近 1 个月',
    value: () => [dayjs().subtract(1, 'month').format('YYYY-MM-DD'), dayjs().format('YYYY-MM-DD')]
  },
  {
    label: '最近 3 个月',
    value: () => [dayjs().subtract(3, 'month').format('YYYY-MM-DD'), dayjs().format('YYYY-MM-DD')]
  },
  {
    label: '最近半年',
    value: () => [dayjs().subtract(6, 'month').format('YYYY-MM-DD'), dayjs().format('YYYY-MM-DD')]
  },
  {
    label: '最近 1 年',
    value: () => [dayjs().subtract(1, 'year').format('YYYY-MM-DD'), dayjs().format('YYYY-MM-DD')]
  },
  {
    label: '今年',
    value: () => [dayjs().startOf('year').format('YYYY-MM-DD'), dayjs().format('YYYY-MM-DD')]
  },
  {
    label: '去年',
    value: () => [
      dayjs().subtract(1, 'year').startOf('year').format('YYYY-MM-DD'),
      dayjs().subtract(1, 'year').endOf('year').format('YYYY-MM-DD')
    ]
  }
]

// 计算属性
const filteredJobs = computed(() => {
  let result = [...jobs.value]

  // 按任务名称搜索
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(job =>
      job.name.toLowerCase().includes(keyword) ||
      job.id.toLowerCase().includes(keyword) ||
      (job.display_name && job.display_name.toLowerCase().includes(keyword)) ||
      (job.description && job.description.toLowerCase().includes(keyword))
    )
  }

  // 按数据源筛选
  if (filterDataSource.value) {
    if (filterDataSource.value === '其他') {
      // 其他：不包含 Tushare、AKShare、BaoStock、多数据源
      result = result.filter(job =>
        !job.name.includes('Tushare') &&
        !job.name.includes('AKShare') &&
        !job.name.includes('BaoStock') &&
        !job.name.includes('多数据源')
      )
    } else {
      result = result.filter(job => job.name.includes(filterDataSource.value))
    }
  }

  // 按状态筛选
  if (filterStatus.value) {
    if (filterStatus.value === 'running') {
      result = result.filter(job => !job.paused)
    } else if (filterStatus.value === 'paused') {
      result = result.filter(job => job.paused)
    }
  }

  // 默认排序：运行中的任务优先（paused=false 排在前面）
  result.sort((a, b) => {
    // 先按状态排序（运行中优先）
    if (a.paused !== b.paused) {
      return a.paused ? 1 : -1
    }
    // 状态相同时按名称排序
    return a.name.localeCompare(b.name, 'zh-CN')
  })

  return result
})

// 批量同步计算属性
const estimatedDays = computed(() => {
  if (!batchSyncForm.dateRange || batchSyncForm.dateRange.length !== 2) {
    return 0
  }
  const [start, end] = batchSyncForm.dateRange
  return dayjs(end).diff(dayjs(start), 'day') + 1
})

const estimatedTime = computed(() => {
  const days = estimatedDays.value
  if (days <= 0) return '-'
  if (days <= 30) return '1-3 分钟'
  if (days <= 90) return '3-10 分钟'
  if (days <= 365) return '10-30 分钟'
  if (days <= 1095) return '30-60 分钟'
  return '超过 1 小时'
})

// 方法
const loadJobs = async () => {
  loading.value = true
  try {
    const [jobsRes, statsRes] = await Promise.all([getJobs(), getSchedulerStats()])
    // ApiClient.get 返回 ApiResponse<T>，其中 data 字段就是我们需要的数据
    jobs.value = Array.isArray(jobsRes.data) ? jobsRes.data : []
    stats.value = statsRes.data || null
  } catch (error: any) {
    ElMessage.error(error.message || '加载任务列表失败')
    jobs.value = []
    stats.value = null
  } finally {
    loading.value = false
  }
}

const showEditDialog = (job: Job) => {
  editingJob.value = job
  editForm.display_name = job.display_name || ''
  editForm.description = job.description || ''
  editDialogVisible.value = true
}

const handleSaveMetadata = async () => {
  if (!editingJob.value) return

  try {
    saveLoading.value = true
    await updateJobMetadata(editingJob.value.id, {
      display_name: editForm.display_name || undefined,
      description: editForm.description || undefined
    })
    ElMessage.success('任务信息已更新')
    editDialogVisible.value = false
    await loadJobs()
  } catch (error: any) {
    ElMessage.error(error.message || '更新任务信息失败')
  } finally {
    saveLoading.value = false
  }
}

const showJobDetail = async (job: Job) => {
  try {
    const res = await getJobDetail(job.id)
    // request.get 已经返回了 response.data
    currentJob.value = res.data || null
    detailDialogVisible.value = true
  } catch (error: any) {
    ElMessage.error(error.message || '获取任务详情失败')
  }
}

const handlePause = async (job: Job) => {
  try {
    await ElMessageBox.confirm(`确定要暂停任务"${job.name}"吗？`, '确认暂停', {
      type: 'warning'
    })

    actionLoading[job.id] = true
    await pauseJob(job.id)
    ElMessage.success('任务已暂停')
    await loadJobs()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '暂停任务失败')
    }
  } finally {
    actionLoading[job.id] = false
  }
}

const handleResume = async (job: Job) => {
  try {
    actionLoading[job.id] = true
    await resumeJob(job.id)
    ElMessage.success('任务已恢复')
    await loadJobs()
  } catch (error: any) {
    ElMessage.error(error.message || '恢复任务失败')
  } finally {
    actionLoading[job.id] = false
  }
}

const handleTrigger = async (job: Job) => {
  try {
    await ElMessageBox.confirm(
      `确定要立即执行任务"${job.name}"吗？任务将在后台执行。`,
      '确认执行',
      {
        type: 'warning'
      }
    )

    actionLoading[job.id] = true
    await triggerJob(job.id)
    ElMessage.success('任务已触发执行')
    await loadJobs()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '触发任务失败')
    }
  } finally {
    actionLoading[job.id] = false
  }
}

const showJobHistory = async (job: Job) => {
  currentHistoryJobId.value = job.id
  historyPage.value = 1
  detailDialogVisible.value = false
  historyDialogVisible.value = true
  await loadHistory()
}

const showHistoryDialog = async () => {
  currentHistoryJobId.value = null
  historyPage.value = 1
  historyDialogVisible.value = true
  await loadHistory()
}

const loadHistory = async () => {
  historyLoading.value = true
  try {
    const params: any = {
      limit: historyPageSize.value,
      offset: (historyPage.value - 1) * historyPageSize.value,
      is_manual: true  // 只显示手动触发的执行记录
    }

    if (currentHistoryJobId.value) {
      params.job_id = currentHistoryJobId.value
    }

    const res = currentHistoryJobId.value
      ? await getSingleJobExecutions(currentHistoryJobId.value, params)
      : await getJobExecutions(params)

    // 直接使用执行记录，不需要转换格式
    const executions = Array.isArray(res.data?.items) ? res.data.items : []
    historyList.value = executions
    historyTotal.value = res.data?.total || 0
  } catch (error: any) {
    ElMessage.error(error.message || '加载执行历史失败')
    historyList.value = []
    historyTotal.value = 0
  } finally {
    historyLoading.value = false
  }
}

const handleHistoryPageChange = (page: number) => {
  historyPage.value = page
  loadHistory()
}

const handleHistoryTabChange = (tabName: string) => {
  if (tabName === 'execution') {
    executionPage.value = 1
    loadExecutions()
  } else {
    historyPage.value = 1
    loadHistory()
  }
  // 两个标签页都启动自动刷新
  startAutoRefresh()
}

// 自动刷新定时器
let autoRefreshTimer: number | null = null

const startAutoRefresh = () => {
  // 清除旧的定时器
  stopAutoRefresh()

  // 每5秒刷新一次
  autoRefreshTimer = window.setInterval(() => {
    // 根据当前标签页刷新对应的数据
    if (historyDialogVisible.value) {
      if (activeHistoryTab.value === 'execution') {
        loadExecutions()
      } else {
        loadHistory()
      }
    }
  }, 5000)
}

const stopAutoRefresh = () => {
  if (autoRefreshTimer) {
    window.clearInterval(autoRefreshTimer)
    autoRefreshTimer = null
  }
}

// 监听对话框关闭，停止自动刷新
watch(historyDialogVisible, (newVal) => {
  if (!newVal) {
    stopAutoRefresh()
  }
})

// ========== 批量同步历史数据相关方法 ==========

// 显示批量同步对话框
const showBatchSyncDialog = () => {
  // 重置表单
  batchSyncForm.dateRange = [null, null]
  // 重置表选择为默认全选
  batchSyncForm.selectedTables = ['analyst_forecasts', 'pe_history', 'bond_rate', 'financial_ratios', 'eps_history']
  batchSyncDialogVisible.value = true
}

// 禁用未来日期
const disabledDate = (time: Date) => {
  return time.getTime() > Date.now()
}

// 选择快捷日期范围
const selectQuickDateRange = (range: { label: string; value: () => [string, string] }) => {
  batchSyncForm.dateRange = range.value()
}

// 开始批量同步
const startBatchSync = async () => {
  // 验证日期范围
  if (!batchSyncForm.dateRange || batchSyncForm.dateRange.length !== 2) {
    ElMessage.warning('请选择日期范围')
    return
  }

  // 验证至少选择一张表
  if (batchSyncForm.selectedTables.length === 0) {
    ElMessage.warning('请至少选择一张表进行同步')
    return
  }

  const [start, end] = batchSyncForm.dateRange

  // 验证日期范围不超过3年
  const daysDiff = dayjs(end).diff(dayjs(start), 'day')
  if (daysDiff > 1095) {
    ElMessage.warning('单次同步时间范围不能超过 3 年')
    return
  }

  // 确保结束日期不早于开始日期
  if (dayjs(end).isBefore(dayjs(start))) {
    ElMessage.warning('结束日期不能早于开始日期')
    return
  }

  batchSyncSubmitting.value = true

  try {
    // 调用批量同步 API
    const response = await fetch('/api/mdvaes/batch-sync', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify({
        start_date: start,
        end_date: end,
        tables: batchSyncForm.selectedTables
      })
    })

    const result = await response.json()

    if (result.success || result.task_id) {
      ElMessage.success(`批量同步任务已启动，任务ID: ${result.task_id}`)

      // 关闭批量同步对话框
      batchSyncDialogVisible.value = false

      // 等待一小段时间后，打开执行历史对话框并切换到手动操作历史标签
      setTimeout(() => {
        activeHistoryTab.value = 'manual'
        historyDialogVisible.value = true
        // 刷新历史列表以显示新任务
        loadHistory()
      }, 500)
    } else {
      throw new Error(result.message || '启动批量同步任务失败')
    }
  } catch (error: any) {
    ElMessage.error(error.message || '启动批量同步任务失败')
  } finally {
    batchSyncSubmitting.value = false
  }
}

const loadExecutions = async () => {
  executionLoading.value = true
  try {
    const params: any = {
      limit: executionPageSize.value,
      offset: (executionPage.value - 1) * executionPageSize.value,
      is_manual: false  // 只显示自动触发的执行记录
    }

    if (currentHistoryJobId.value) {
      params.job_id = currentHistoryJobId.value
    }

    if (executionStatusFilter.value) {
      params.status = executionStatusFilter.value
    }

    const res = currentHistoryJobId.value
      ? await getSingleJobExecutions(currentHistoryJobId.value, params)
      : await getJobExecutions(params)

    executionList.value = Array.isArray(res.data?.items) ? res.data.items : []
    executionTotal.value = res.data?.total || 0
  } catch (error: any) {
    ElMessage.error(error.message || '加载执行历史失败')
    executionList.value = []
    executionTotal.value = 0
  } finally {
    executionLoading.value = false
  }
}

const handleExecutionPageChange = (page: number) => {
  executionPage.value = page
  loadExecutions()
}

const showExecutionDetail = (execution: JobExecution) => {
  currentExecution.value = execution
  executionDetailDialogVisible.value = true
}

const formatExecutionStatus = (status: string) => {
  const statusMap: Record<string, string> = {
    running: '执行中',
    success: '成功',
    failed: '失败',
    missed: '错过'
  }
  return statusMap[status] || status
}

const calculateRunningTime = (startTime: string) => {
  try {
    const start = new Date(startTime)
    const now = new Date()
    const seconds = Math.floor((now.getTime() - start.getTime()) / 1000)

    if (seconds < 60) {
      return `${seconds}秒`
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60)
      const remainingSeconds = seconds % 60
      return `${minutes}分${remainingSeconds}秒`
    } else {
      const hours = Math.floor(seconds / 3600)
      const minutes = Math.floor((seconds % 3600) / 60)
      return `${hours}小时${minutes}分`
    }
  } catch (error) {
    return '-'
  }
}

const formatTrigger = (trigger: string) => {
  // 简化触发器显示
  if (trigger.includes('cron')) {
    return trigger.replace(/cron\[|\]/g, '')
  }
  if (trigger.includes('interval')) {
    return trigger.replace(/interval\[|\]/g, '')
  }
  return trigger
}

const formatAction = (action: string) => {
  const actionMap: Record<string, string> = {
    pause: '暂停',
    resume: '恢复',
    trigger: '手动触发',
    execute: '执行'
  }
  return actionMap[action] || action
}

const handleSearch = () => {
  // 搜索和筛选会自动通过 computed 属性生效
}

const handleReset = () => {
  searchKeyword.value = ''
  filterDataSource.value = ''
  filterStatus.value = ''
}

// 取消/终止任务执行
const handleCancelExecution = async (execution: any) => {
  try {
    await ElMessageBox.confirm(
      '确定要终止这个任务吗？任务将在下次检查时停止执行。',
      '确认终止',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await cancelExecution(execution._id)
    ElMessage.success('已设置取消标记，任务将在下次检查时停止')

    // 刷新列表
    if (activeHistoryTab.value === 'execution') {
      await loadExecutions()
    } else {
      await loadHistory()
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '终止任务失败')
    }
  }
}

// 标记执行记录为失败
const handleMarkFailed = async (execution: any) => {
  try {
    const { value: reason } = await ElMessageBox.prompt(
      '请输入失败原因（可选）',
      '标记为失败',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        inputPlaceholder: '例如：进程已手动终止',
        inputValue: '进程已手动终止'
      }
    )

    await markExecutionFailed(execution._id, reason || '用户手动标记为失败')
    ElMessage.success('已标记为失败状态')

    // 刷新列表
    if (activeHistoryTab.value === 'execution') {
      await loadExecutions()
    } else {
      await loadHistory()
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '标记失败')
    }
  }
}

// 删除执行记录
const handleDeleteExecution = async (execution: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除这条执行记录吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await deleteExecution(execution._id)
    ElMessage.success('执行记录已删除')

    // 刷新列表
    if (activeHistoryTab.value === 'execution') {
      await loadExecutions()
    } else {
      await loadHistory()
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

// 生命周期
onMounted(() => {
  loadJobs()
})
</script>

<style scoped lang="scss">
.scheduler-management {
  padding: 20px;

  .header-card {
    margin-bottom: 16px;

    .header-content {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 20px;

      .title-section {
        h2 {
          display: flex;
          align-items: center;
          gap: 8px;
          margin: 0 0 8px 0;
          font-size: 24px;
          font-weight: 600;
        }

        .subtitle {
          margin: 0;
          color: var(--el-text-color-secondary);
          font-size: 14px;
        }
      }

      .stats-section {
        display: flex;
        gap: 40px;
      }
    }

    .actions {
      display: flex;
      gap: 10px;
    }
  }

  .filter-card {
    margin-bottom: 16px;

    .filter-form {
      margin-bottom: 0;

      :deep(.el-form-item) {
        margin-bottom: 0;
      }
    }
  }

  .table-card {
    .job-name {
      display: flex;
      align-items: center;
      gap: 8px;

      .name-text {
        font-weight: 500;
      }
    }
  }

  .code-block {
    background: var(--el-fill-color-light);
    padding: 8px;
    border-radius: 4px;
    font-size: 12px;
    font-family: 'Courier New', monospace;
    overflow-x: auto;
  }

  .pagination {
    margin-top: 20px;
    display: flex;
    justify-content: center;
  }

  // 批量同步对话框样式
  .quick-ranges {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 16px;
  }

  .estimate-info {
    padding: 12px 16px;
    background: var(--el-fill-color-light);
    border-radius: 4px;
    margin-bottom: 16px;

    .info-label {
      color: var(--el-text-color-secondary);
      font-size: 13px;
      margin-right: 8px;
    }

    .info-value {
      font-weight: 500;
      font-size: 14px;

      &.highlight {
        color: var(--el-color-warning);
        font-weight: 600;
      }
    }
  }

  .tips {
    font-size: 13px;
    color: var(--el-text-color-secondary);
    line-height: 1.6;

    p {
      margin: 4px 0;

      &:first-child {
        margin-top: 0;
      }

      &:last-child {
        margin-bottom: 0;
      }
    }

    .tip-icon {
      margin-right: 4px;
      color: var(--el-color-warning);
    }
  }
}
</style>

