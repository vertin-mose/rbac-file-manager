<template>
  <el-dialog :model-value="visible" :title="dialogTitle" width="600px" @close="handleClose" destroy-on-close>
    <div v-loading="loading" class="activity-dialog">
      <!-- History Section -->
      <div v-if="historyActivities.length > 0" class="activity-section">
        <h3 class="section-title collapsed" @click="showHistory = !showHistory">
          <el-icon><ArrowDown v-if="showHistory" /><ArrowRight v-else /></el-icon>
          历史{{ modeLabel }} ({{ historyActivities.length }})
        </h3>
        <div v-show="showHistory" class="activity-list">
          <div v-for="act in historyActivities" :key="act.id" class="activity-item history">
            <div class="activity-meta">
              <el-tag size="small" type="info" effect="plain">历史</el-tag>
              <strong>{{ act.username }}</strong>
              <span class="activity-time">{{ formatTime(act.createdAt) }}</span>
            </div>
            <div v-if="act.activityType === 'approve'" class="activity-result">
              <el-tag :type="act.approved ? 'success' : 'danger'" size="small" effect="dark">
                {{ act.approved ? '通过' : '驳回' }}
              </el-tag>
            </div>
            <p v-if="act.content" class="activity-content">{{ act.content }}</p>
          </div>
        </div>
      </div>

      <!-- Current Activities Section -->
      <div class="activity-section">
        <h3 class="section-title">
          当前{{ modeLabel }}
          <span v-if="currentActivities.length === 0" class="section-empty">暂无</span>
        </h3>
        <div class="activity-list">
          <div v-for="act in currentActivities" :key="act.id" class="activity-item current">
            <div class="activity-meta">
              <strong>{{ act.username }}</strong>
              <span class="activity-time">{{ formatTime(act.createdAt) }}</span>
            </div>
            <div v-if="act.activityType === 'approve'" class="activity-result">
              <el-tag :type="act.approved ? 'success' : 'danger'" size="small" effect="dark">
                {{ act.approved ? '通过' : '驳回' }}
              </el-tag>
            </div>
            <p v-if="act.content" class="activity-content">{{ act.content }}</p>
          </div>
          <el-empty v-if="currentActivities.length === 0" description="暂无内容" :image-size="60" />
        </div>
      </div>

      <!-- Submit Form -->
      <el-divider />
      <div class="submit-section">
        <h3 class="section-title">提交{{ modeLabel }}</h3>
        <template v-if="approveDisabled">
          <el-alert
            type="info"
            show-icon
            :closable="false"
            title="该文件已完成审批，更新文件后可再次提交审批"
          />
        </template>
        <template v-else>
          <div v-if="mode === 'approve'" class="approve-radio">
            <el-radio-group v-model="submitForm.approved">
              <el-radio :label="true" border>通过</el-radio>
              <el-radio :label="false" border>驳回</el-radio>
            </el-radio-group>
          </div>
          <el-input
            v-model="submitForm.content"
            type="textarea"
            :rows="3"
            :placeholder="submitPlaceholder"
            maxlength="500"
            show-word-limit
          />
          <div class="submit-actions">
            <el-button @click="handleClose">取消</el-button>
            <el-button type="primary" :loading="submitting" @click="submitActivity">
              提交{{ modeLabel }}
            </el-button>
          </div>
        </template>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ArrowDown, ArrowRight } from '@element-plus/icons-vue'
import { approveFile, commentFile, getFileActivities, reviewFile, type FileActivityItem } from '@/api/file'

const props = defineProps<{
  visible: boolean
  fileId: number
  fileName: string
  mode: 'review' | 'approve' | 'comment'
}>()

const emit = defineEmits<{
  close: []
  updated: []
}>()

const loading = ref(false)
const submitting = ref(false)
const showHistory = ref(false)
const activities = ref<FileActivityItem[]>([])
const submitForm = reactive({
  content: '',
  approved: true,
})

const modeLabel = computed(() => {
  switch (props.mode) {
    case 'review': return '审阅'
    case 'approve': return '审批'
    case 'comment': return '评论'
  }
})

const dialogTitle = computed(() => {
  return `${modeLabel.value} — ${props.fileName}`
})

const submitPlaceholder = computed(() => {
  if (props.mode === 'comment') return '请输入评论内容'
  return `请输入${modeLabel.value}说明`
})

const historyActivities = computed(() =>
  activities.value.filter((a) => a.isHistory && a.activityType === props.mode)
)

const currentActivities = computed(() =>
  activities.value.filter((a) => !a.isHistory && a.activityType === props.mode)
)

const approveDisabled = computed(() =>
  props.mode === 'approve' && currentActivities.value.length > 0
)

function formatTime(t: string | null): string {
  if (!t) return ''
  return t.replace('T', ' ').slice(0, 16)
}

async function loadActivities() {
  if (!props.fileId) return
  loading.value = true
  try {
    activities.value = await getFileActivities(props.fileId)
  } catch {
    // ignore
  } finally {
    loading.value = false
  }
}

async function submitActivity() {
  if (!submitForm.content.trim() && props.mode !== 'approve') {
    ElMessage.warning('请输入内容')
    return
  }
  submitting.value = true
  try {
    if (props.mode === 'review') {
      await reviewFile(props.fileId, submitForm.content)
    } else if (props.mode === 'approve') {
      await approveFile(props.fileId, submitForm.content, submitForm.approved)
    } else {
      await commentFile(props.fileId, submitForm.content)
    }
    ElMessage.success(`${modeLabel.value}已提交`)
    submitForm.content = ''
    emit('updated')
    await loadActivities()
  } catch {
    ElMessage.error('提交失败')
  } finally {
    submitting.value = false
  }
}

function handleClose() {
  submitForm.content = ''
  submitForm.approved = true
  emit('close')
}

watch(() => props.visible, (val) => {
  if (val) {
    showHistory.value = false
    loadActivities()
  }
})
</script>

<style scoped>
.activity-dialog {
  min-height: 200px;
}

.activity-section {
  margin-bottom: 16px;
}

.section-title {
  margin: 0 0 10px;
  font-size: 15px;
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  user-select: none;
}

.section-title.collapsed:hover {
  color: #409eff;
}

.section-empty {
  color: #909399;
  font-size: 12px;
  font-weight: 400;
}

.activity-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.activity-item {
  padding: 10px 12px;
  border-radius: 8px;
  border: 1px solid #eee;
}

.activity-item.history {
  background: #f8f9fa;
  opacity: 0.85;
}

.activity-item.current {
  background: #fff;
}

.activity-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  font-size: 13px;
}

.activity-time {
  color: #909399;
  font-size: 12px;
}

.activity-result {
  margin-bottom: 4px;
}

.activity-content {
  margin: 4px 0 0;
  color: #444;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-word;
}

.approve-radio {
  margin-bottom: 10px;
}

.submit-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.submit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
