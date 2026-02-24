<template>
  <div class="backtest-control-panel">
    <!-- 页面头部 -->
    <div class="page-header">
      <h1 class="page-title">
        <el-icon><TrendCharts /></el-icon>
        股票回测
      </h1>
      <p class="page-description">
        设置回测参数、选择策略并执行回测任务
      </p>
    </div>

    <!-- 主体区域（左20%右80%布局） -->
    <div class="main-content">
      <!-- 左侧辅助信息栏（20%） -->
      <div class="left-sidebar">
        <!-- 操作步骤指引 -->
        <el-card class="steps-card" shadow="never">
          <template #header>
            <span class="card-title">
              <el-icon><List /></el-icon>
              操作步骤指引
            </span>
          </template>
          <el-steps :active="currentStep" :space="80" direction="vertical" process-status="process">
            <el-step title="回测参数设置" description="设置时间、资金、最小购买量" />
            <el-step title="策略选择" description="选择回测策略及参数" />
            <el-step title="触发回测" description="启动回测任务" />
            <el-step title="查看结果" description="查看回测结果和明细" />
          </el-steps>
        </el-card>

        <!-- 当前状态提示 -->
        <el-card class="status-card" shadow="never">
          <template #header>
            <span class="card-title">
              <el-icon><InfoFilled /></el-icon>
              当前状态提示
            </span>
          </template>
          <div class="status-content">
            <el-tag :type="currentStatusTag" size="large" class="status-tag">
              {{ currentStatusText }}
            </el-tag>
            <div v-if="currentStatusDetail" class="status-detail">
              {{ currentStatusDetail }}
            </div>

            <!-- 已选策略信息 -->
            <el-divider v-if="selectedStrategy && strategyConfirmed" style="margin: 12px 0;"></el-divider>
            <div v-if="selectedStrategy && strategyConfirmed" class="selected-strategy-info">
              <div class="strategy-label">已选策略：</div>
              <div class="strategy-value">
                <el-tag type="success" size="default">{{ selectedStrategy.name }}</el-tag>
              </div>
            </div>

            <!-- 已确认参数信息 -->
            <el-divider v-if="paramsConfirmed" style="margin: 12px 0;"></el-divider>
            <div v-if="paramsConfirmed" class="confirmed-params-info">
              <div class="params-label">已确认参数：</div>
              <div class="params-list">
                <div class="param-item">
                  <span class="param-key">股票：</span>
                  <span class="param-value">{{ form.stock_code }}</span>
                </div>
                <div class="param-item">
                  <span class="param-key">日期：</span>
                  <span class="param-value">{{ form.start_date }} 至 {{ form.end_date }}</span>
                </div>
                <div class="param-item">
                  <span class="param-key">资金：</span>
                  <span class="param-value">{{ form.initial_capital?.toLocaleString() }} 元</span>
                </div>
                <div class="param-item">
                  <span class="param-key">最小购买：</span>
                  <span class="param-value">{{ form.min_purchase }} 股</span>
                </div>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 快捷操作 -->
        <el-card class="actions-card" shadow="never">
          <template #header>
            <span class="card-title">
              <el-icon><Setting /></el-icon>
              快捷操作
            </span>
          </template>
          <div class="actions-content">
            <el-button @click="handleResetParams" :icon="RefreshLeft" style="width: 100%; margin-bottom: 8px;">
              重置所有参数
            </el-button>
            <el-dropdown @command="handleLoadSavedParams" trigger="click" style="width: 100%;">
              <el-button :icon="Star" style="width: 100%;">
                我的常用参数
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item v-if="savedParamsList.length === 0" disabled>
                    暂无保存的参数
                  </el-dropdown-item>
                  <el-dropdown-item
                    v-for="item in savedParamsList"
                    :key="item.id"
                    :command="item.id"
                  >
                    {{ item.name }}
                  </el-dropdown-item>
                  <el-dropdown-item divided :command="'save'" v-if="canSaveParams">
                    <el-icon><Plus /></el-icon>
                    保存当前参数
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </el-card>
      </div>

      <!-- 右侧核心操作栏（80%） -->
      <div class="right-main">
        <!-- 回测参数设置区 -->
        <el-card class="config-card" shadow="never">
          <template #header>
            <div class="card-header-row">
              <span class="card-title">
                <el-icon><Setting /></el-icon>
                回测参数设置
              </span>
              <el-button type="primary" size="small" @click="handleConfirmParams">
                参数确认
              </el-button>
            </div>
          </template>

          <el-form :model="form" :rules="formRules" ref="formRef" label-width="140px" label-position="left">
            <!-- 日期范围 - 使用日期范围选择器 -->
            <el-form-item label="回测日期范围" required>
              <TradingDayRangePicker
                v-model:start-date="form.start_date"
                v-model:end-date="form.end_date"
                :show-stats="true"
                :show-quick-options="true"
              />
            </el-form-item>

            <!-- 初始资金 -->
            <el-form-item label="初始资金（元）" prop="initial_capital" required>
              <el-input-number
                v-model="form.initial_capital"
                :min="1000"
                :max="10000000"
                :step="10000"
                :precision="2"
                controls-position="right"
                style="width: 100%"
              />
              <div class="form-tip">范围：1,000 - 10,000,000 元，保留2位小数</div>
            </el-form-item>

            <!-- 股票最小购买量 -->
            <el-form-item label="股票最小购买量" prop="min_purchase" required>
              <el-input-number
                v-model="form.min_purchase"
                :min="100"
                :max="10000"
                :step="100"
                :precision="0"
                controls-position="right"
                style="width: 100%"
              />
              <div class="form-tip warning-tip">
                ⚠️ 必须为100的倍数，范围100-10000股
              </div>
            </el-form-item>

            <!-- 股票代码 - 使用股票选择器 -->
            <el-form-item label="股票代码" prop="stock_code" required>
              <StockSelector
                v-model="form.stock_code"
                :show-market="true"
                placeholder="请输入股票代码或名称（如 000001.SZ 或 平安银行）"
              />
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 策略选择区 -->
        <el-card class="strategy-card" shadow="never">
          <template #header>
            <div class="card-header-row">
              <span class="card-title">
                <el-icon><Grid /></el-icon>
                策略选择
              </span>
              <el-button type="primary" size="small" @click="handleConfirmStrategy" :disabled="!form.strategy_id">
                策略确认
              </el-button>
            </div>
          </template>

          <el-row :gutter="20">
            <el-col :span="12">
              <!-- 策略筛选 -->
              <el-form label-width="80px">
                <el-form-item label="分类">
                  <el-select v-model="strategyFilter.category" placeholder="全部分类" clearable>
                    <el-option label="趋势策略" value="trend" />
                    <el-option label="震荡策略" value="oscillator" />
                    <el-option label="估值策略" value="valuation" />
                  </el-select>
                </el-form-item>
                <el-form-item label="搜索">
                  <el-input
                    v-model="strategyFilter.search"
                    placeholder="搜索策略名称"
                    clearable
                  >
                    <template #prefix>
                      <el-icon><Search /></el-icon>
                    </template>
                  </el-input>
                </el-form-item>
              </el-form>

              <!-- 策略选择下拉框 -->
              <el-form-item label="选择策略">
                <el-select
                  v-model="form.strategy_id"
                  placeholder="请选择策略"
                  filterable
                  clearable
                  style="width: 100%"
                >
                  <el-option
                    v-for="strategy in filteredStrategies"
                    :key="strategy.id"
                    :label="strategy.name"
                    :value="strategy.id"
                  >
                    <div class="strategy-option">
                      <div class="strategy-option-name">
                        {{ strategy.name }}
                        <el-tag v-if="strategy.is_builtin" type="info" size="small">内置</el-tag>
                        <el-tag v-else type="warning" size="small">自定义</el-tag>
                      </div>
                      <div class="strategy-option-desc">{{ strategy.description }}</div>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>
            </el-col>

            <el-col :span="12">
              <!-- 策略详细说明 -->
              <div v-if="selectedStrategy" class="strategy-detail">
                <h3>{{ selectedStrategy.name }}</h3>
                <p class="strategy-full-desc">{{ selectedStrategy.description }}</p>

                <el-divider />

                <!-- 多锚点权重配置（仅 MDVAES 策略显示） -->
                <div v-if="selectedStrategy?.hasAnchorWeight" class="anchor-weight-config">
                  <h4>多锚点权重配置</h4>
                  <div class="weight-tip">
                    <el-icon><InfoFilled /></el-icon>
                    四个估值方法的权重总和必须等于 1.0（100%）
                  </div>
                  <el-form label-width="100px" class="weight-form">
                    <el-row :gutter="12">
                      <el-col :span="12">
                        <el-form-item label="PEG权重">
                          <el-input-number
                            v-model="form.anchor_weight.peg"
                            :min="0"
                            :max="1"
                            :step="0.05"
                            :precision="3"
                            controls-position="right"
                            style="width: 100%"
                            @change="validateAnchorWeight"
                          />
                        </el-form-item>
                      </el-col>
                      <el-col :span="12">
                        <el-form-item label="PE权重">
                          <el-input-number
                            v-model="form.anchor_weight.pe_historical"
                            :min="0"
                            :max="1"
                            :step="0.05"
                            :precision="3"
                            controls-position="right"
                            style="width: 100%"
                            @change="validateAnchorWeight"
                          />
                        </el-form-item>
                      </el-col>
                    </el-row>
                    <el-row :gutter="12">
                      <el-col :span="12">
                        <el-form-item label="PB权重">
                          <el-input-number
                            v-model="form.anchor_weight.pb"
                            :min="0"
                            :max="1"
                            :step="0.05"
                            :precision="3"
                            controls-position="right"
                            style="width: 100%"
                            @change="validateAnchorWeight"
                          />
                        </el-form-item>
                      </el-col>
                      <el-col :span="12">
                        <el-form-item label="DCF权重">
                          <el-input-number
                            v-model="form.anchor_weight.dcf"
                            :min="0"
                            :max="1"
                            :step="0.05"
                            :precision="3"
                            controls-position="right"
                            style="width: 100%"
                            @change="validateAnchorWeight"
                          />
                        </el-form-item>
                      </el-col>
                    </el-row>
                    <el-row>
                      <el-col :span="24">
                        <div class="weight-total" :class="{ 'weight-invalid': !isAnchorWeightValid }">
                          权重总和: {{ anchorWeightTotal.toFixed(3) }}
                          <el-tag v-if="isAnchorWeightValid" type="success" size="small" style="margin-left: 8px">
                            有效
                          </el-tag>
                          <el-tag v-else type="danger" size="small" style="margin-left: 8px">
                            总和必须为 1.0
                          </el-tag>
                        </div>
                      </el-col>
                    </el-row>
                  </el-form>
                  <el-button
                    size="small"
                    text
                    @click="resetAnchorWeight"
                    style="margin-top: 8px;"
                  >
                    <el-icon><RefreshLeft /></el-icon>
                    重置为默认权重
                  </el-button>
                </div>

                <!-- 策略参数设置 -->
                <div v-if="selectedStrategy.parameters && selectedStrategy.parameters.length > 0">
                  <h4 v-if="!selectedStrategy?.hasAnchorWeight">策略参数设置</h4>
                  <h4 v-else>其他策略参数</h4>
                  <el-form label-width="120px">
                    <el-form-item
                      v-for="param in selectedStrategy.parameters"
                      :key="param.name"
                      :label="param.label"
                    >
                      <el-input-number
                        v-if="param.type === 'number'"
                        v-model="form.strategy_params[param.name]"
                        :min="param.min"
                        :max="param.max"
                        :step="param.step"
                        :precision="param.precision || 0"
                      />
                      <el-select
                        v-else-if="param.type === 'select'"
                        v-model="form.strategy_params[param.name]"
                      >
                        <el-option
                          v-for="option in param.options"
                          :key="option.value"
                          :label="option.label"
                          :value="option.value"
                        />
                      </el-select>
                      <el-button
                        v-if="form.strategy_params[param.name] !== undefined"
                        size="small"
                        text
                        @click="resetStrategyParam(param.name)"
                      >
                        重置
                      </el-button>
                    </el-form-item>
                  </el-form>
                </div>
                <div v-else-if="!selectedStrategy?.hasAnchorWeight" class="no-params">
                  该策略无可配置参数
                </div>
              </div>
              <div v-else class="no-strategy-selected">
                <el-empty description="请选择策略" :image-size="100" />
              </div>
            </el-col>
          </el-row>
        </el-card>

        <!-- 回测操作区 + 模拟持仓预览区 -->
        <el-row :gutter="20">
          <!-- 回测操作区 -->
          <el-col :span="14">
            <el-card class="operation-card" shadow="never">
              <template #header>
                <span class="card-title">
                  <el-icon><VideoPlay /></el-icon>
                  回测操作
                </span>
              </template>

              <div class="operation-buttons">
                <el-button
                  type="primary"
                  size="large"
                  :loading="backtestStore.startingBacktest"
                  :disabled="!canStartBacktest"
                  @click="handleStartBacktest"
                >
                  <el-icon><VideoPlay /></el-icon>
                  开始回测
                </el-button>
                <el-button
                  v-if="backtestStore.isRunning"
                  type="warning"
                  size="large"
                  @click="handleInterruptBacktest"
                >
                  <el-icon><VideoPause /></el-icon>
                  中断回测
                </el-button>
                <el-button
                  v-if="backtestStore.isPaused"
                  type="success"
                  size="large"
                  @click="handleContinueBacktest"
                >
                  <el-icon><VideoPlay /></el-icon>
                  继续回测
                </el-button>
                <el-button
                  v-if="backtestStore.isCompleted || backtestStore.isFailed"
                  type="info"
                  size="large"
                  @click="handleRestartBacktest"
                >
                  <el-icon><RefreshRight /></el-icon>
                  重新回测
                </el-button>
              </div>

              <!-- 进度条 -->
              <div v-if="backtestStore.currentBacktestId" class="progress-section">
                <div class="progress-info">
                  <span>进度：{{ backtestStore.progress.toFixed(2) }}%</span>
                  <span>{{ backtestStore.currentBarIndex }} / {{ backtestStore.totalBars }} 个交易日</span>
                </div>
                <el-progress
                  :percentage="backtestStore.progress"
                  :status="progressStatus"
                  :stroke-width="24"
                />
                <div v-if="backtestStore.currentDate" class="current-date">
                  <el-icon><Calendar /></el-icon>
                  当前日期：{{ backtestStore.currentDate }}
                </div>
              </div>
            </el-card>
          </el-col>

          <!-- 模拟持仓/现金预览区 -->
          <el-col :span="10">
            <el-card class="position-preview-card" shadow="never">
              <template #header>
                <span class="card-title">
                  <el-icon><Wallet /></el-icon>
                  实时持仓/现金
                </span>
              </template>

              <div class="position-content">
                <!-- 回测前 -->
                <div v-if="!backtestStore.currentBacktestId" class="before-backtest">
                  <div class="position-item">
                    <div class="label">初始资金</div>
                    <div class="value">{{ formatCurrency(form.initial_capital) }}</div>
                  </div>
                  <div class="position-item">
                    <div class="label">初始持仓</div>
                    <div class="value no-position">无持仓</div>
                  </div>
                </div>

                <!-- 回测中/后 -->
                <div v-else class="during-backtest">
                  <div class="position-item">
                    <div class="label">可用现金</div>
                    <div class="value highlight">{{ formatCurrency(backtestStore.cash) }}</div>
                  </div>
                  <div class="position-item">
                    <div class="label">持仓市值</div>
                    <div class="value">{{ formatCurrency(backtestStore.marketValue) }}</div>
                  </div>
                  <div class="position-item">
                    <div class="label">总资产</div>
                    <div class="value highlight">{{ formatCurrency(backtestStore.totalValue) }}</div>
                  </div>
                  <div class="position-item">
                    <div class="label">盈亏</div>
                    <div
                      class="value"
                      :class="backtestStore.profitLoss >= 0 ? 'profit' : 'loss'"
                    >
                      {{ formatCurrency(backtestStore.profitLoss) }}
                      ({{ backtestStore.profitLossPct.toFixed(2) }}%)
                    </div>
                  </div>
                  <el-divider />
                  <div class="position-detail">
                    <div class="detail-title">持仓明细</div>
                    <div v-if="backtestStore.hasPosition" class="detail-list">
                      <div
                        v-for="(pos, code) in backtestStore.positions"
                        :key="code"
                        class="detail-item"
                      >
                        {{ code }}: {{ pos.shares }}股 (成本: {{ formatCurrency(pos.cost) }})
                      </div>
                    </div>
                    <div v-else class="no-position">无持仓</div>
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 回测结果展示区 -->
        <el-card v-if="backtestStore.isCompleted" class="results-card" shadow="never">
          <template #header>
            <span class="card-title">
              <el-icon><DataLine /></el-icon>
              回测结果展示
            </span>
          </template>

          <BacktestResults :backtest-id="backtestStore.currentBacktestId" />
        </el-card>

        <!-- 错误提示 -->
        <el-alert
          v-if="backtestStore.startError || backtestStore.statusError"
          type="error"
          :title="backtestStore.startError || backtestStore.statusError || '未知错误'"
          :closable="false"
          show-icon
          class="error-alert"
        />
      </div>
    </div>

    <!-- 底部区域（固定） -->
    <div class="page-footer-fixed">
      <div class="footer-left">
        <el-button text @click="showHelpDialog = true">
          <el-icon><QuestionFilled /></el-icon>
          帮助文档
        </el-button>
      </div>
      <div class="footer-right">
        <span class="version-info">TradingAgents v1.0.0 | {{ currentDate }}</span>
      </div>
    </div>

    <!-- 参数确认弹窗 -->
    <el-dialog
      v-model="showParamsConfirmDialog"
      title="确认回测参数"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-descriptions :column="1" border>
        <el-descriptions-item label="回测时间区间">
          {{ form.start_date }} 至 {{ form.end_date }}
        </el-descriptions-item>
        <el-descriptions-item label="初始资金">
          {{ formatCurrency(form.initial_capital) }}
        </el-descriptions-item>
        <el-descriptions-item label="股票最小购买量">
          {{ form.min_purchase }}股
        </el-descriptions-item>
        <el-descriptions-item label="股票代码">
          {{ form.stock_code }}
        </el-descriptions-item>
        <el-descriptions-item label="策略名称">
          {{ selectedStrategy?.name || '未选择' }}
        </el-descriptions-item>
        <el-descriptions-item label="策略参数" v-if="Object.keys(form.strategy_params).length > 0">
          {{ formatStrategyParams() }}
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="showParamsConfirmDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmStartBacktest">确认回测</el-button>
      </template>
    </el-dialog>

    <!-- 新手指引弹窗 -->
    <el-dialog
      v-model="showNewUserGuide"
      title="欢迎使用股票回测功能"
      width="700px"
      :close-on-click-modal="false"
    >
      <el-steps :active="guideStep" finish-status="success" simple>
        <el-step title="步骤1" />
        <el-step title="步骤2" />
        <el-step title="步骤3" />
      </el-steps>

      <div class="guide-content">
        <div v-if="guideStep === 0" class="guide-step">
          <h3>1. 设置回测参数</h3>
          <p>在"回测参数设置区"配置：</p>
          <ul>
            <li>回测时间区间（选择起止日期）</li>
            <li>初始资金（1,000 - 10,000,000元）</li>
            <li>股票最小购买量（必须为100的倍数）</li>
            <li>股票代码（如 000001.SZ）</li>
          </ul>
          <p>完成后点击"参数确认"按钮。</p>
        </div>
        <div v-if="guideStep === 1" class="guide-step">
          <h3>2. 选择回测策略</h3>
          <p>在"策略选择区"：</p>
          <ul>
            <li>浏览策略列表（包含内置和自定义策略）</li>
            <li>选择一个策略</li>
            <li>配置策略参数（如果有）</li>
          </ul>
          <p>完成后点击"策略确认"按钮。</p>
        </div>
        <div v-if="guideStep === 2" class="guide-step">
          <h3>3. 触发回测</h3>
          <p>在"回测操作区"：</p>
          <ul>
            <li>点击"开始回测"按钮</li>
            <li>实时查看回测进度和持仓变化</li>
            <li>回测完成后查看详细结果</li>
          </ul>
          <p>您可以随时中断回测，之后选择继续或放弃。</p>
        </div>
      </div>

      <template #footer>
        <el-button v-if="guideStep > 0" @click="guideStep--">上一步</el-button>
        <el-button v-if="guideStep < 2" type="primary" @click="guideStep++">下一步</el-button>
        <el-button v-else type="primary" @click="handleGuideFinished">我知道了</el-button>
      </template>
    </el-dialog>

    <!-- 帮助文档弹窗 -->
    <el-dialog
      v-model="showHelpDialog"
      title="帮助文档"
      width="650px"
      custom-class="help-dialog-right"
    >
      <div class="help-content">
        <h3>📖 股票回测功能使用指南</h3>

        <h4>1. 回测参数设置</h4>
        <ul>
          <li><strong>日期范围</strong>：支持日历选择，自动跳过非交易日</li>
          <li><strong>初始资金</strong>：范围1,000-10,000,000元，自动保留2位小数</li>
          <li><strong>最小购买量</strong>：必须为100的倍数，范围100-10,000股</li>
          <li><strong>股票代码</strong>：支持A股（如000001.SZ）和港股</li>
        </ul>

        <h4>2. 策略选择</h4>
        <ul>
          <li><strong>内置策略</strong>：双均线、MACD等基础策略</li>
          <li><strong>自定义策略</strong>：管理员通过后台注册的策略</li>
          <li><strong>策略参数</strong>：部分策略支持参数自定义</li>
        </ul>

        <h4>3. 回测操作</h4>
        <ul>
          <li><strong>开始回测</strong>：启动回测任务</li>
          <li><strong>中断回测</strong>：暂停当前回测，进度保留7天</li>
          <li><strong>继续回测</strong>：从中断点继续执行</li>
          <li><strong>重新回测</strong>：使用相同参数重新执行</li>
        </ul>

        <h4>4. 结果查看</h4>
        <ul>
          <li><strong>核心指标</strong>：收益率、回撤、夏普比率等</li>
          <li><strong>交易明细</strong>：每笔交易的完整记录</li>
          <li><strong>资金曲线</strong>：可视化展示资产变化</li>
          <li><strong>导出功能</strong>：支持导出为Excel文件</li>
        </ul>

        <h4>5. 常用功能</h4>
        <ul>
          <li><strong>重置参数</strong>：一键恢复默认参数</li>
          <li><strong>常用参数</strong>：保存最多10组参数配置</li>
          <li><strong>历史记录</strong>：查看、对比、导出历史回测</li>
        </ul>

        <el-alert type="info" :closable="false">
          💡 提示：使用快捷键 Ctrl+S 保存参数，Ctrl+R 开始回测
        </el-alert>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useBacktestEngineStore } from '@/stores/backtestEngine'
import BacktestResults from '@/components/BacktestResults.vue'
import TradingDayRangePicker from '@/components/TradingDayRangePicker.vue'
import StockSelector from '@/components/StockSelector.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  TrendCharts,
  Setting,
  VideoPlay,
  VideoPause,
  RefreshRight,
  RefreshLeft,
  CircleClose,
  DataLine,
  Calendar,
  Wallet,
  List,
  InfoFilled,
  Grid,
  Search,
  Star,
  ArrowDown,
  Plus,
  QuestionFilled
} from '@element-plus/icons-vue'
import { savedParamsApi, type SavedBacktestParams } from '@/api/savedParams'

// Store
const backtestStore = useBacktestEngineStore()

// 表单引用
const formRef = ref()

// 表单数据
const form = ref({
  stock_code: '000001.SZ',
  start_date: '',
  end_date: '',
  initial_capital: 100000,
  min_purchase: 100,
  strategy_id: '',
  strategy_params: {},
  // 多锚点权重配置（用于 MDVAES 策略）
  anchor_weight: {
    peg: 0.4,
    pe_historical: 0.3,
    pb: 0.15,
    dcf: 0.15
  }
})

// 表单验证规则
const formRules = {
  initial_capital: [
    { required: true, message: '请输入初始资金', trigger: 'blur' },
    { type: 'number', min: 1000, max: 10000000, message: '资金范围：1,000 - 10,000,000元', trigger: 'blur' }
  ],
  min_purchase: [
    { required: true, message: '请输入最小购买量', trigger: 'blur' },
    {
      type: 'number',
      validator: (_rule: any, value: number, callback: any) => {
        if (value < 100 || value > 10000) {
          callback(new Error('范围：100 - 10,000股'))
        } else if (value % 100 !== 0) {
          callback(new Error('必须为100的倍数'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  stock_code: [{ required: true, message: '请输入股票代码', trigger: 'blur' }]
}

// 策略数据
const strategies = ref([
  {
    id: 'dual_ma',
    name: '双均线策略',
    description: '均线金叉买入、死叉卖出，默认使用5日均线与20日均线',
    is_builtin: true,
    category: 'trend',
    parameters: [
      { name: 'short_period', label: '短期均线', type: 'number', min: 5, max: 20, step: 1, default: 5, precision: 0 },
      { name: 'long_period', label: '长期均线', type: 'number', min: 20, max: 60, step: 1, default: 20, precision: 0 }
    ]
  },
  {
    id: 'buy_and_hold',
    name: '买入持有策略',
    description: '在回测开始日买入，持有至结束日',
    is_builtin: true,
    category: 'trend',
    parameters: []
  },
  {
    id: 'mdvaes',
    name: 'MDVAES估值策略',
    description: '基于多锚点估值系统(MDVAES)进行价值投资决策，通过分析师盈利预测和多锚点估值计算内在价值',
    is_builtin: true,
    category: 'valuation',
    hasAnchorWeight: true,  // 标识该策略需要配置多锚点权重
    parameters: [
      { name: 'symbol', label: '股票代码', type: 'string', default: '000001.SZ' },
      { name: 'forecast_years', label: 'EPS预测年数', type: 'number', min: 1, max: 10, step: 1, default: 5, precision: 0 },
      { name: 'peg_base', label: 'PEG基数', type: 'number', min: 0.5, max: 2.0, step: 0.1, default: 1.0, precision: 2 },
      { name: 'risk_adjustment', label: '风险调整幅度', type: 'number', min: 0, max: 0.3, step: 0.01, default: 0.1, precision: 3 },
      { name: 'rebalance_frequency', label: '重新估值频率(天)', type: 'number', min: 1, max: 365, step: 1, default: 30, precision: 0 },
      { name: 'use_margin', label: '使用安全边际', type: 'boolean', default: true },
      { name: 'margin_buy', label: '买入安全边际', type: 'number', min: 0.5, max: 1.03, step: 0.05, default: 0.8, precision: 3 },
      { name: 'margin_sell', label: '卖出安全边际', type: 'number', min: 1.05, max: 2.0, step: 0.05, default: 1.2, precision: 3 }
    ],
    // 多锚点权重默认配置
    anchorWeightDefaults: {
      peg: 0.4,
      pe_historical: 0.3,
      pb: 0.15,
      dcf: 0.15
    }
  }
])

const strategyFilter = ref({
  category: '',
  search: ''
})

// 常用参数
const savedParamsList = ref<any[]>([])

// 弹窗状态
const showParamsConfirmDialog = ref(false)
const showNewUserGuide = ref(false)
const showHelpDialog = ref(false)
const guideStep = ref(0)

// 策略确认状态
const strategyConfirmed = ref(false)
// 参数确认状态
const paramsConfirmed = ref(false)

// 计算属性
const canStartBacktest = computed(() => {
  const basicValid = form.value.stock_code &&
         form.value.start_date &&
         form.value.end_date &&
         form.value.initial_capital >= 1000 &&
         form.value.min_purchase >= 100 &&
         form.value.min_purchase % 100 === 0 &&
         form.value.strategy_id

  // 如果是 MDVAES 策略，需要额外验证权重总和
  if (basicValid && form.value.strategy_id === 'mdvaes') {
    return isAnchorWeightValid.value
  }

  return basicValid
})

const canSaveParams = computed(() => {
  return canStartBacktest.value && savedParamsList.value.length < 10
})

const selectedStrategy = computed(() => {
  return strategies.value.find(s => s.id === form.value.strategy_id)
})

const filteredStrategies = computed(() => {
  return strategies.value.filter(s => {
    const matchCategory = !strategyFilter.value.category || s.category === strategyFilter.value.category
    const matchSearch = !strategyFilter.value.search ||
                        s.name.toLowerCase().includes(strategyFilter.value.search.toLowerCase())
    return matchCategory && matchSearch
  })
})

const currentStep = computed(() => {
  if (backtestStore.isCompleted) return 4
  if (backtestStore.isRunning || backtestStore.isPaused) return 3
  if (form.value.strategy_id) return 2
  if (form.value.start_date && form.value.end_date) return 1
  return 0
})

const currentStatusTag = computed(() => {
  if (backtestStore.isRunning) return 'warning'
  if (backtestStore.isPaused) return 'info'
  if (backtestStore.isCompleted) return 'success'
  if (backtestStore.isFailed) return 'danger'
  return 'info'
})

const currentStatusText = computed(() => {
  if (backtestStore.isRunning) return '回测中'
  if (backtestStore.isPaused) return '已暂停'
  if (backtestStore.isCompleted) return '已完成'
  if (backtestStore.isFailed) return '失败'
  if (form.value.strategy_id && form.value.start_date && form.value.end_date) return '策略已确认，待触发回测'
  if (form.value.start_date && form.value.end_date) return '回测参数已确认，待选择策略'
  return '未开始回测'
})

const currentStatusDetail = computed(() => {
  if (backtestStore.isRunning) {
    return `进度：${backtestStore.progress.toFixed(2)}% (${backtestStore.currentBarIndex}/${backtestStore.totalBars})`
  }
  if (backtestStore.isFailed) {
    return backtestStore.statusError || '回测执行失败'
  }
  return ''
})

const progressStatus = computed(() => {
  if (backtestStore.isCompleted) return 'success'
  if (backtestStore.isFailed) return 'exception'
  return undefined
})

const currentDate = computed(() => {
  return new Date().toLocaleDateString('zh-CN')
})

// 多锚点权重相关计算属性
const anchorWeightTotal = computed(() => {
  const w = form.value.anchor_weight
  return (w.peg || 0) + (w.pe_historical || 0) + (w.pb || 0) + (w.dcf || 0)
})

const isAnchorWeightValid = computed(() => {
  return Math.abs(anchorWeightTotal.value - 1.0) < 0.001
})

// 方法
/**
 * 处理交易日数量变化
 */
function handleConfirmParams() {
  formRef.value?.validateField('initial_capital')
  formRef.value?.validateField('min_purchase')
  paramsConfirmed.value = true
  ElMessage.success('参数已确认')
}

function handleConfirmStrategy() {
  if (!form.value.strategy_id) {
    ElMessage.warning('请先选择策略')
    return
  }
  strategyConfirmed.value = true
  ElMessage.success('策略已确认')
}

async function handleStartBacktest() {
  // 检查是否首次使用
  const hasShownGuide = localStorage.getItem('backtest_guide_shown')
  if (!hasShownGuide) {
    showNewUserGuide.value = true
    return
  }

  if (!canStartBacktest.value) {
    ElMessage.warning('请完善回测参数')
    return
  }

  // 显示参数确认弹窗
  showParamsConfirmDialog.value = true
}

async function confirmStartBacktest() {
  showParamsConfirmDialog.value = false

  // 如果是 MDVAES 策略，将 anchor_weight 添加到 strategy_params 中
  const requestParams = { ...form.value }
  if (requestParams.strategy_id === 'mdvaes') {
    // 验证权重总和
    if (!isAnchorWeightValid.value) {
      ElMessage.error(`权重总和必须为 1.0，当前为 ${anchorWeightTotal.value.toFixed(3)}`)
      showParamsConfirmDialog.value = true
      return
    }
    // 将权重配置添加到策略参数中，同时将 symbol 更新为实际的 stock_code
    requestParams.strategy_params = {
      ...requestParams.strategy_params,
      symbol: requestParams.stock_code,  // 使用用户选择的股票代码
      anchor_weight: { ...requestParams.anchor_weight }
    }
  }

  try {
    await backtestStore.startBacktest(requestParams)
    ElMessage.success('回测任务已启动')
    localStorage.setItem('backtest_guide_shown', 'true')
  } catch (error: any) {
    ElMessage.error(error?.message || '启动失败')
  }
}

// 新手引导弹窗关闭后，继续启动回测
async function handleGuideFinished() {
  showNewUserGuide.value = false
  localStorage.setItem('backtest_guide_shown', 'true')

  // 继续执行回测启动流程
  if (!canStartBacktest.value) {
    ElMessage.warning('请完善回测参数')
    return
  }

  // 显示参数确认弹窗
  showParamsConfirmDialog.value = true
}

async function handleInterruptBacktest() {
  try {
    await ElMessageBox.confirm('确认暂停回测任务？', '提示', {
      type: 'warning'
    })
    await backtestStore.interruptBacktest()
    ElMessage.success('回测已暂停')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error?.message || '暂停失败')
    }
  }
}

async function handleContinueBacktest() {
  try {
    await backtestStore.continueBacktest()
    ElMessage.success('回测已继续')
  } catch (error: any) {
    ElMessage.error(error?.message || '继续失败')
  }
}

async function handleRestartBacktest() {
  try {
    await backtestStore.restartBacktest()
    ElMessage.success('重新回测已启动')
  } catch (error: any) {
    ElMessage.error(error?.message || '重启失败')
  }
}

function handleResetParams() {
  form.value = {
    stock_code: '000001.SZ',
    start_date: '',
    end_date: '',
    initial_capital: 100000,
    min_purchase: 100,
    strategy_id: '',
    strategy_params: {},
    // 重置权重为默认值
    anchor_weight: {
      peg: 0.4,
      pe_historical: 0.3,
      pb: 0.15,
      dcf: 0.15
    }
  }
  strategyConfirmed.value = false  // 重置策略确认状态
  paramsConfirmed.value = false  // 重置参数确认状态
  ElMessage.success('参数已重置')
}

/**
 * 验证多锚点权重总和是否为 1.0
 */
function validateAnchorWeight() {
  const total = anchorWeightTotal.value
  if (Math.abs(total - 1.0) >= 0.001) {
    ElMessage.warning(`权重总和为 ${total.toFixed(3)}，必须等于 1.0`)
  }
}

/**
 * 重置多锚点权重为默认值
 */
function resetAnchorWeight() {
  const strategy = strategies.value.find(s => s.id === form.value.strategy_id)
  if (strategy?.anchorWeightDefaults) {
    form.value.anchor_weight = { ...strategy.anchorWeightDefaults }
    ElMessage.success('权重已重置为默认值')
  }
}

async function handleLoadSavedParams(command: string | number) {
  if (command === 'save') {
    // 保存当前参数
    try {
      const { value } = await ElMessageBox.prompt('请输入参数名称', '保存常用参数', {
        confirmButtonText: '保存',
        cancelButtonText: '取消',
        inputPattern: /^.{1,50}$/,
        inputErrorMessage: '名称长度为1-50个字符'
      })

      if (!value) return

      const params = {
        start_date: form.value.start_date || '',
        end_date: form.value.end_date || '',
        initial_capital: form.value.initial_capital,
        min_purchase: form.value.min_purchase,
        stock_code: form.value.stock_code,
        strategy_id: form.value.strategy_id,
        strategy_params: form.value.strategy_params
      }

      await savedParamsApi.createParams({
        name: value,
        params
      })

      ElMessage.success('参数已保存')
      await loadSavedParamsList()
    } catch (error: any) {
      if (error !== 'cancel') {
        ElMessage.error(error?.response?.data?.detail || '保存失败')
      }
    }
  } else {
    // 加载保存的参数
    try {
      const params = await savedParamsApi.getParams(command as string)
      form.value.start_date = params.start_date
      form.value.end_date = params.end_date
      form.value.initial_capital = params.initial_capital
      form.value.min_purchase = params.min_purchase
      form.value.stock_code = params.stock_code
      form.value.strategy_id = params.strategy_id
      form.value.strategy_params = params.strategy_params

      // 增加使用次数
      await savedParamsApi.useParams(params.id!)

      ElMessage.success(`已加载参数: ${params.name}`)
    } catch (error: any) {
      ElMessage.error('加载参数失败')
    }
  }
}

// 加载保存的参数列表
async function loadSavedParamsList() {
  try {
    savedParamsList.value = await savedParamsApi.getParamsList()
  } catch (error: any) {
    console.error('加载常用参数列表失败:', error)
  }
}

function resetStrategyParam(paramName: string) {
  const param = selectedStrategy.value?.parameters.find(p => p.name === paramName)
  if (param && param.default !== undefined) {
    form.value.strategy_params[paramName] = param.default
  }
}

function formatCurrency(value: number): string {
  return `¥${value.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',')}`
}

function formatStrategyParams(): string {
  const params = Object.entries(form.value.strategy_params)
    .map(([key, value]) => `${key}: ${value}`)
    .join(', ')
  return params || '无'
}

// 快捷键支持
function handleKeydown(event: KeyboardEvent) {
  // Ctrl+S: 保存参数
  if (event.ctrlKey && event.key === 's') {
    event.preventDefault()
    if (canSaveParams.value) {
      handleLoadSavedParams('save')
    }
  }
  // Ctrl+R: 开始回测
  if (event.ctrlKey && event.key === 'r') {
    event.preventDefault()
    handleStartBacktest()
  }
  // Esc: 关闭弹窗
  if (event.key === 'Escape') {
    showParamsConfirmDialog.value = false
    showNewUserGuide.value = false
    showHelpDialog.value = false
  }
}

// 监听策略选择变化，自动填充默认参数值
watch(() => form.value.strategy_id, (newStrategyId, oldStrategyId) => {
  if (newStrategyId && newStrategyId !== oldStrategyId) {
    const strategy = strategies.value.find(s => s.id === newStrategyId)

    // 初始化多锚点权重（如果是 MDVAES 策略）
    if (strategy?.hasAnchorWeight && strategy?.anchorWeightDefaults) {
      form.value.anchor_weight = { ...strategy.anchorWeightDefaults }
    } else {
      // 非权重策略，重置为默认值
      form.value.anchor_weight = {
        peg: 0.4,
        pe_historical: 0.3,
        pb: 0.15,
        dcf: 0.15
      }
    }

    if (strategy && strategy.parameters && strategy.parameters.length > 0) {
      // 重置策略参数
      form.value.strategy_params = {}

      // 填充每个参数的默认值
      strategy.parameters.forEach(param => {
        if (param.default !== undefined) {
          form.value.strategy_params[param.name] = param.default
        }
      })
    } else {
      // 如果策略没有参数，清空参数对象
      form.value.strategy_params = {}
    }

    // 重置策略确认状态
    strategyConfirmed.value = false
  }
})

// 生命周期
onMounted(() => {
  // 检查是否首次使用
  const hasShownGuide = localStorage.getItem('backtest_guide_shown')
  if (!hasShownGuide) {
    setTimeout(() => {
      showNewUserGuide.value = true
    }, 500)
  }

  // 加载保存的参数列表
  loadSavedParamsList()

  // 注册快捷键
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  backtestStore.cleanup()
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped lang="scss">
.backtest-control-panel {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;

  // 页面头部
  .page-header {
    padding: 24px 20px 20px;

    .page-title {
      font-size: 24px;
      font-weight: 600;
      color: #303133;
      margin: 0 0 8px 0;
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .page-description {
      font-size: 14px;
      color: #909399;
      margin: 0;
    }
  }

  // 主体区域
  .main-content {
    display: flex;
    padding: 0 20px 20px;
    min-height: calc(100vh - 120px);
  }

  // 左侧辅助栏（20%）
  .left-sidebar {
    width: 20%;
    padding: 20px;
    background: white;
    border-right: 1px solid #e4e7ed;

    .steps-card,
    .status-card,
    .actions-card {
      margin-bottom: 20px;

      .card-title {
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 8px;
      }
    }

    // 快捷操作卡片样式
    .actions-card {
      :deep(.el-card__header) {
        padding: 12px 15px;
      }

      :deep(.el-card__body) {
        padding: 15px;
      }

      .actions-content {
        display: flex;
        flex-direction: column;
      }
    }

    .status-content {
      .status-tag {
        width: 100%;
        justify-content: center;
        margin-bottom: 10px;
      }

      .status-detail {
        font-size: 14px;
        color: #606266;
        text-align: center;
      }

      // 已选策略信息样式
      .selected-strategy-info {
        margin-top: 8px;

        .strategy-label {
          font-size: 13px;
          color: #909399;
          margin-bottom: 8px;
          text-align: center;
        }

        .strategy-value {
          display: flex;
          justify-content: center;
        }
      }

      // 已确认参数信息样式
      .confirmed-params-info {
        margin-top: 8px;

        .params-label {
          font-size: 13px;
          color: #909399;
          margin-bottom: 8px;
          text-align: center;
        }

        .params-list {
          .param-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 6px 0;
            font-size: 13px;

            .param-key {
              color: #606266;
              font-weight: 500;
            }

            .param-value {
              color: #303133;
              font-weight: 600;
            }
          }
        }
      }
    }
  }

  // 右侧核心操作栏（80%）
  .right-main {
    width: 80%;
    padding: 20px;

    .config-card,
    .strategy-card,
    .operation-card,
    .position-preview-card,
    .results-card {
      margin-bottom: 20px;

      .card-title {
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .card-header-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        width: 100%;
      }
    }

    .form-tip {
      font-size: 12px;
      color: #909399;
      margin-top: 4px;

      &.warning-tip {
        color: #e6a23c;
      }
    }

    .strategy-detail {
      h3 {
        margin: 0 0 10px 0;
      }

      .strategy-full-desc {
        color: #606266;
        line-height: 1.6;
      }

      h4 {
        margin: 20px 0 10px 0;
      }

      .no-params {
        color: #909399;
        text-align: center;
        padding: 20px;
      }
    }

    .no-strategy-selected {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 300px;
    }

    // 多锚点权重配置样式
    .anchor-weight-config {
      h4 {
        margin: 0 0 10px 0;
        font-size: 15px;
        font-weight: 600;
        color: #303133;
      }

      .weight-tip {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 8px 12px;
        margin-bottom: 15px;
        background: #f0f9ff;
        border: 1px solid #b3d8ff;
        border-radius: 4px;
        font-size: 13px;
        color: #409eff;

        .el-icon {
          font-size: 16px;
        }
      }

      .weight-form {
        .el-form-item {
          margin-bottom: 12px;
        }
      }

      .weight-total {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 10px;
        margin-top: 8px;
        background: #f5f7fa;
        border-radius: 4px;
        font-weight: 600;
        font-size: 15px;
        color: #67c23a;

        &.weight-invalid {
          color: #f56c6c;
          background: #fef0f0;
        }
      }
    }

    .operation-buttons {
      display: flex;
      gap: 12px;
      margin-bottom: 20px;
      justify-content: center;
    }

    .progress-section {
      .progress-info {
        display: flex;
        justify-content: space-between;
        margin-bottom: 10px;
        font-weight: 500;
      }

      .current-date {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 15px;
        font-size: 16px;
        font-weight: 500;
      }
    }

    .position-content {
      .position-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 0;
        border-bottom: 1px solid #f0f0f0;

        &:last-child {
          border-bottom: none;
        }

        .label {
          color: #909399;
          font-size: 14px;
        }

        .value {
          font-size: 18px;
          font-weight: 600;
          color: #303133;

          &.highlight {
            color: #409eff;
            font-size: 20px;
          }

          &.profit {
            color: #f56c6c;
          }

          &.loss {
            color: #67c23a;
          }
        }

        &.no-position {
          color: #909399;
          font-style: italic;
        }
      }

      .position-detail {
        .detail-title {
          font-weight: 600;
          margin-bottom: 10px;
          color: #606266;
        }

        .detail-list {
          max-height: 200px;
          overflow-y: auto;

          .detail-item {
            padding: 6px 0;
            font-size: 13px;
            color: #606266;
            border-bottom: 1px dashed #e4e7ed;
          }
        }

        .no-position {
          color: #909399;
          text-align: center;
          padding: 20px 0;
        }
      }

      .before-backtest,
      .during-backtest {
        .position-item:first-child {
          padding-top: 0;
        }
      }
    }

    .error-alert {
      margin-bottom: 20px;
    }
  }

  // 底部区域（流式布局，不覆盖侧边栏）
  .page-footer-fixed {
    height: 50px;
    background: white;
    border-top: 1px solid #e4e7ed;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
    margin-top: 20px;

    .version-info {
      font-size: 12px;
      color: #909399;
    }
  }
}

// 新手指引样式
.guide-content {
  padding: 20px 0;

  .guide-step {
    h3 {
      color: #409eff;
      margin-bottom: 15px;
    }

    p {
      color: #606266;
      line-height: 1.8;
    }

    ul {
      padding-left: 20px;

      li {
        color: #606266;
        line-height: 1.8;
        margin: 8px 0;
      }
    }
  }
}

// 帮助文档样式
.help-content {
  h3 {
    color: #409eff;
    margin-bottom: 20px;
  }

  h4 {
    color: #303133;
    margin: 20px 0 10px 0;
    font-size: 16px;
  }

  ul {
    padding-left: 20px;

    li {
      color: #606266;
      line-height: 1.8;
      margin: 8px 0;

      strong {
        color: #303133;
      }
    }
  }

  .el-alert {
    margin-top: 20px;
  }
}
</style>

<style lang="scss">
// 帮助文档对话框定位样式（非scoped，全局生效）
.help-dialog-right {
  position: fixed !important;
  left: 30% !important;  // 调整为30%，对应新的布局
  top: 50% !important;
  transform: translateY(-50%) !important;

  .el-dialog__header {
    background-color: #f5f7fa;
    border-bottom: 1px solid #e4e7ed;
  }
}

// 策略选择下拉框选项样式
.el-select-dropdown__item {
  height: auto !important;
  padding: 12px 15px !important;

  .strategy-option {
    .strategy-option-name {
      font-weight: 600;
      margin-bottom: 6px;
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
    }

    .strategy-option-desc {
      font-size: 12px;
      color: #909399;
      line-height: 1.5;
    }
  }
}
</style>
