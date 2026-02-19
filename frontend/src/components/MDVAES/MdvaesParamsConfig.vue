<template>
  <div class="mdvaes-params-config">
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>MDVAES 参数配置</span>
          <el-button 
            type="primary" 
            size="small" 
            @click="handleSave"
            :loading="saving"
          >
            保存配置
          </el-button>
        </div>
      </template>

      <el-form :model="localParams" label-width="140px" size="small">
        <!-- 预测参数 -->
        <div class="form-section">
          <div class="section-title">预测参数</div>
          
          <el-form-item label="EPS预测年数">
            <el-slider
              v-model="localParams.forecast_years"
              :min="1"
              :max="10"
              :marks="{ 1: '1年', 5: '5年', 10: '10年' }"
              show-input
            />
          </el-form-item>
        </div>

        <!-- 估值参数 -->
        <div class="form-section">
          <div class="section-title">估值参数</div>
          
          <el-form-item label="PEG基数">
            <el-slider
              v-model="localParams.peg_base"
              :min="0.5"
              :max="2.0"
              :step="0.1"
              :marks="{ 0.5: '0.5', 1.0: '1.0', 2.0: '2.0' }"
              show-input
            />
            <div class="param-hint">
              较低的PEG基数意味着更保守的估值
            </div>
          </el-form-item>

          <el-form-item label="风险调整幅度">
            <el-slider
              v-model="localParams.risk_adjustment"
              :min="0"
              :max="0.3"
              :step="0.01"
              :marks="{ 0: '0%', 0.1: '10%', 0.3: '30%' }"
              show-input
              :format-tooltip="v => `${(v * 100).toFixed(0)}%`"
            />
            <div class="param-hint">
              根据风险水平调整估值，高风险股票使用更大调整
            </div>
          </el-form-item>
        </div>

        <!-- 安全边际参数 -->
        <div class="form-section">
          <div class="section-title">
            安全边际
            <el-switch v-model="localParams.use_margin" style="margin-left: 10px" />
          </div>
          
          <template v-if="localParams.use_margin">
            <el-form-item label="买入安全边际">
              <el-slider
                v-model="localParams.margin_buy"
                :min="0.5"
                :max="0.95"
                :step="0.05"
                :marks="{ 0.5: '50%', 0.8: '80%', 0.95: '95%' }"
                show-input
                :format-tooltip="v => `${(v * 100).toFixed(0)}%`"
              />
              <div class="param-hint">
                价格低于估值的 {{ (localParams.margin_buy * 100).toFixed(0) }}% 时买入
              </div>
            </el-form-item>

            <el-form-item label="卖出安全边际">
              <el-slider
                v-model="localParams.margin_sell"
                :min="1.05"
                :max="2.0"
                :step="0.05"
                :marks="{ 1.05: '105%', 1.2: '120%', 2.0: '200%' }"
                show-input
                :format-tooltip="v => `${(v * 100).toFixed(0)}%`"
              />
              <div class="param-hint">
                价格高于估值的 {{ ((localParams.margin_sell - 1) * 100).toFixed(0) }}% 时卖出
              </div>
            </el-form-item>
          </template>
          
          <el-alert
            v-else
            type="info"
            :closable="false"
            show-icon
          >
            未启用安全边际，将使用估值区间判断买卖信号
          </el-alert>
        </div>

        <!-- 预设选项 -->
        <div class="form-section">
          <div class="section-title">快速预设</div>
          <div class="preset-buttons">
            <el-button @click="applyPreset('conservative')">保守型</el-button>
            <el-button @click="applyPreset('neutral')">稳健型</el-button>
            <el-button @click="applyPreset('aggressive')">激进型</el-button>
          </div>
        </div>
      </el-form>

      <!-- 保存确认对话框 -->
      <el-dialog
        v-model="showSaveDialog"
        title="确认保存"
        width="400px"
      >
        <p>确定要保存当前参数配置吗？</p>
        <template #footer>
          <el-button @click="showSaveDialog = false">取消</el-button>
          <el-button type="primary" @click="confirmSave">确认</el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useMdvaesStore } from '@/stores/mdvaes'
import type { MDVAESParametersResponse } from '@/api/mdvaes'

const mdvaesStore = useMdvaesStore()

// 本地参数副本
const localParams = reactive<MDVAESParametersResponse>({
  forecast_years: 5,
  peg_base: 1.0,
  risk_adjustment: 0.1,
  use_margin: true,
  margin_buy: 0.8,
  margin_sell: 1.2
})

// 保存状态
const saving = ref(false)
const showSaveDialog = ref(false)

// 初始化参数
watch(() => mdvaesStore.parameters, (params) => {
  if (params) {
    Object.assign(localParams, params)
  }
}, { immediate: true })

// 预设配置
const presets = {
  conservative: {
    forecast_years: 5,
    peg_base: 0.8,
    risk_adjustment: 0.15,
    use_margin: true,
    margin_buy: 0.7,
    margin_sell: 1.15
  },
  neutral: {
    forecast_years: 5,
    peg_base: 1.0,
    risk_adjustment: 0.1,
    use_margin: true,
    margin_buy: 0.8,
    margin_sell: 1.2
  },
  aggressive: {
    forecast_years: 3,
    peg_base: 1.2,
    risk_adjustment: 0.05,
    use_margin: true,
    margin_buy: 0.85,
    margin_sell: 1.3
  }
}

function applyPreset(preset: keyof typeof presets) {
  Object.assign(localParams, presets[preset])
  ElMessage.success(`已应用${preset === 'conservative' ? '保守' : preset === 'neutral' ? '稳健' : '激进'}型预设`)
}

function handleSave() {
  showSaveDialog.value = true
}

async function confirmSave() {
  saving.value = true
  try {
    await mdvaesStore.updateParameters(localParams)
    showSaveDialog.value = false
    ElMessage.success('参数保存成功')
  } catch (error: any) {
    ElMessage.error('参数保存失败: ' + error.message)
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.mdvaes-params-config {
  width: 100%;
}

.config-card {
  border-radius: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.form-section {
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid #eee;
}

.form-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.section-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
}

.param-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.preset-buttons {
  display: flex;
  gap: 12px;
}
</style>
