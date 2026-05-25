<template>
  <div class="audit-page">
    <section class="page-hero">
      <div>
        <p class="eyebrow">Audit Center</p>
        <h1>审计日志</h1>
        <p class="hero-copy">查看登录、权限和文件操作记录，并导出 CSV。</p>
      </div>
      <div class="hero-actions">
        <el-button @click="loadLogs" :loading="loading">刷新</el-button>
        <el-button
          v-if="userStore.hasPermission('audit:export')"
          type="primary"
          @click="handleExport"
        >
          导出 CSV
        </el-button>
      </div>
    </section>

    <el-card class="filter-card" shadow="never">
      <el-form :inline="true" class="filter-form">
        <el-form-item label="操作类型">
          <el-select v-model="filters.action" clearable filterable placeholder="全部类型" style="width: 180px">
            <el-option v-for="action in actionOptions" :key="action" :label="action" :value="action" />
          </el-select>
        </el-form-item>
        <el-form-item label="用户 ID">
          <el-input-number v-model="filters.userId" :min="1" controls-position="right" />
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="applyFilters">筛选</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
      <p class="filter-note">日期范围为前端本地过滤，当前后端接口仅支持按操作类型和用户 ID 查询。</p>
    </el-card>

    <el-card class="table-card" shadow="never">
      <el-table :data="displayLogs" v-loading="loading" row-key="id">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户" min-width="140" />
        <el-table-column prop="action" label="操作" min-width="160" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.success ? 'success' : 'danger'">
              {{ row.success ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="ipAddress" label="IP" min-width="140" />
        <el-table-column label="时间" min-width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.createdAt) }}
          </template>
        </el-table-column>
        <el-table-column label="详情" min-width="320">
          <template #default="{ row }">
            <el-popover placement="top-start" width="320" trigger="click">
              <template #reference>
                <el-button link type="primary">查看详情</el-button>
              </template>
              <div class="detail-text">{{ row.detail || '无详情' }}</div>
            </el-popover>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          layout="total, prev, pager, next, sizes"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          @current-change="loadLogs"
          @size-change="handleSizeChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { exportAuditLogs, getAuditLogs, type AuditLogItem } from '@/api/audit'
import { useUserStore } from '@/store/user'
import { formatDateTime } from '@/utils/format'

const userStore = useUserStore()
const loading = ref(false)
const rawLogs = ref<AuditLogItem[]>([])

const filters = reactive({
  action: '',
  userId: undefined as number | undefined,
  dateRange: [] as string[],
})

const pagination = reactive({
  page: 1,
  size: 20,
  total: 0,
})

const actionOptions = [
  'LOGIN',
  'LOGIN_FAILED',
  'LOGOUT',
  'CREATE_DIRECTORY',
  'UPLOAD_FILE',
  'RENAME_FILE',
  'DELETE_FILE',
  'SHARE_FILE',
  'REVIEW_FILE',
  'APPROVE_FILE',
  'COMMENT_FILE',
  'DELETE_ROLE',
  'ASSIGN_PERMISSIONS',
  'ASSIGN_USER_ROLES',
]

const displayLogs = computed(() => {
  if (filters.dateRange.length !== 2) {
    return rawLogs.value
  }
  const [start, end] = filters.dateRange
  const startDate = new Date(`${start}T00:00:00`)
  const endDate = new Date(`${end}T23:59:59`)
  return rawLogs.value.filter((item) => {
    if (!item.createdAt) return false
    const current = new Date(item.createdAt)
    return current >= startDate && current <= endDate
  })
})

async function loadLogs() {
  loading.value = true
  try {
    const result = await getAuditLogs({
      page: pagination.page,
      size: pagination.size,
      action: filters.action || undefined,
      userId: filters.userId,
    })
    rawLogs.value = result.items
    pagination.total = result.total
  } finally {
    loading.value = false
  }
}

async function applyFilters() {
  pagination.page = 1
  await loadLogs()
}

async function resetFilters() {
  filters.action = ''
  filters.userId = undefined
  filters.dateRange = []
  pagination.page = 1
  await loadLogs()
}

async function handleSizeChange() {
  pagination.page = 1
  await loadLogs()
}

async function handleExport() {
  const blob: Blob = await exportAuditLogs()
  const url = window.URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'audit_logs.csv'
  anchor.click()
  window.URL.revokeObjectURL(url)
  ElMessage.success('导出成功')
}

onMounted(loadLogs)
</script>

<style scoped>
.audit-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  padding: 28px 32px;
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(251, 209, 124, 0.16), transparent 28%),
    linear-gradient(135deg, #3b2d26 0%, #5a4638 52%, #73624a 100%);
  color: #fbf8f2;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(255, 225, 176, 0.86);
}

.page-hero h1 {
  margin: 0;
  font-size: 34px;
}

.hero-copy {
  margin: 10px 0 0;
  line-height: 1.7;
  color: rgba(251, 248, 242, 0.78);
}

.hero-actions {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.filter-card,
.table-card {
  border-radius: 20px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
}

.filter-note {
  margin: 8px 0 0;
  color: #7c8b99;
  font-size: 13px;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.detail-text {
  white-space: pre-wrap;
  line-height: 1.6;
}

@media (max-width: 960px) {
  .page-hero {
    flex-direction: column;
  }
}
</style>
