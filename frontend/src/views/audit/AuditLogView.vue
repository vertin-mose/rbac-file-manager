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
            <el-option v-for="item in actionOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="用户名称">
          <el-input v-model="filters.username" clearable placeholder="输入用户名" style="width: 180px" />
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
    </el-card>

    <el-card class="table-card" shadow="never">
      <div v-if="selectedIds.length > 0" class="batch-actions">
        <span>已选择 {{ selectedIds.length }} 条</span>
        <el-popconfirm title="确定批量删除所选日志？" @confirm="handleBatchDelete">
          <template #reference>
            <el-button type="danger" size="small">批量删除</el-button>
          </template>
        </el-popconfirm>
      </div>
      <el-table :data="rawLogs" v-loading="loading" row-key="id" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column label="序号" width="80">
          <template #default="{ $index }">
            {{ (pagination.page - 1) * pagination.size + $index + 1 }}
          </template>
        </el-table-column>
        <el-table-column prop="username" label="用户" min-width="140" />
        <el-table-column label="操作" min-width="160">
          <template #default="{ row }">
            {{ actionMap[row.action] || row.action }}
          </template>
        </el-table-column>
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
        <el-table-column prop="detail" label="详情" min-width="280">
          <template #default="{ row }">
            <span>{{ row.detail || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-popconfirm title="确定删除该条日志？" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button type="danger" size="small" link>删除</el-button>
              </template>
            </el-popconfirm>
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
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { batchDeleteAuditLogs, deleteAuditLog, exportAuditLogs, getAuditLogs, type AuditLogItem } from '@/api/audit'
import { useUserStore } from '@/store/user'
import { formatDateTime } from '@/utils/format'

const userStore = useUserStore()
const loading = ref(false)
const rawLogs = ref<AuditLogItem[]>([])
const selectedIds = ref<number[]>([])

const filters = reactive({
  action: '',
  username: '',
  dateRange: [] as string[],
})

const pagination = reactive({
  page: 1,
  size: 20,
  total: 0,
})

const actionOptions = [
  { label: '登录', value: 'LOGIN' },
  { label: '登录失败', value: 'LOGIN_FAILED' },
  { label: '登出', value: 'LOGOUT' },
  { label: '注册', value: 'REGISTER' },
  { label: '创建目录', value: 'CREATE_DIRECTORY' },
  { label: '上传文件', value: 'UPLOAD_FILE' },
  { label: '重命名文件', value: 'RENAME_FILE' },
  { label: '删除文件', value: 'DELETE_FILE' },
  { label: '共享文件', value: 'SHARE_FILE' },
  { label: '审阅文件', value: 'REVIEW_FILE' },
  { label: '批准文件', value: 'APPROVE_FILE' },
  { label: '评论文件', value: 'COMMENT_FILE' },
  { label: '创建角色', value: 'CREATE_ROLE' },
  { label: '更新角色', value: 'UPDATE_ROLE' },
  { label: '删除角色', value: 'DELETE_ROLE' },
  { label: '分配权限', value: 'ASSIGN_PERMISSIONS' },
  { label: '分配角色', value: 'ASSIGN_USER_ROLES' },
]

const actionMap: Record<string, string> = {}
actionOptions.forEach((item) => { actionMap[item.value] = item.label })

async function loadLogs() {
  loading.value = true
  try {
    const [start, end] = filters.dateRange
    const result = await getAuditLogs({
      page: pagination.page,
      size: pagination.size,
      action: filters.action || undefined,
      username: filters.username || undefined,
      startDate: start || undefined,
      endDate: end || undefined,
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
  filters.username = ''
  filters.dateRange = []
  pagination.page = 1
  await loadLogs()
}

async function handleSizeChange() {
  pagination.page = 1
  await loadLogs()
}

async function handleDelete(id: number) {
  try {
    await deleteAuditLog(id)
    ElMessage.success('删除成功')
    selectedIds.value = []
    await loadLogs()
  } catch {
    ElMessage.error('删除失败')
  }
}

function handleSelectionChange(rows: AuditLogItem[]) {
  selectedIds.value = rows.map((r) => r.id)
}

async function handleBatchDelete() {
  try {
    await batchDeleteAuditLogs(selectedIds.value)
    ElMessage.success(`成功删除 ${selectedIds.value.length} 条日志`)
    selectedIds.value = []
    await loadLogs()
  } catch {
    ElMessage.error('批量删除失败')
  }
}

async function handleExport() {
  const [start, end] = filters.dateRange
  const blob: Blob = await exportAuditLogs({
    action: filters.action || undefined,
    username: filters.username || undefined,
    startDate: start || undefined,
    endDate: end || undefined,
  })
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

.batch-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  margin-bottom: 12px;
  background: #fef0f0;
  border: 1px solid #fde2e2;
  border-radius: 8px;
  font-size: 14px;
  color: #f56c6c;
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
