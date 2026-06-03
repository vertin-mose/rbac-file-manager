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
        <el-table-column label="操作" min-width="180">
          <template #default="{ row }">
            <el-tag :type="actionMeta(row.action).type" effect="plain" size="small" :title="row.action">
              {{ actionMeta(row.action).label }}
            </el-tag>
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

type TagType = 'primary' | 'success' | 'warning' | 'danger' | 'info'

const actionOptions: Array<{ value: string; label: string; type: TagType }> = [
  { value: 'LOGIN',             label: '登录成功',    type: 'success' },
  { value: 'LOGIN_FAILED',      label: '登录失败',    type: 'danger'  },
  { value: 'LOGOUT',            label: '退出登录',    type: 'info'    },
  { value: 'REGISTER',          label: '注册账号',    type: 'info'    },
  { value: 'VIEW_FILE',         label: '查看文件',    type: 'primary' },
  { value: 'DOWNLOAD_FILE',     label: '下载文件',    type: 'primary' },
  { value: 'CREATE_DIRECTORY',  label: '创建目录',    type: 'primary' },
  { value: 'UPLOAD_FILE',       label: '上传文件',    type: 'primary' },
  { value: 'RENAME_FILE',       label: '重命名文件',  type: 'warning' },
  { value: 'DELETE_FILE',       label: '删除文件',    type: 'danger'  },
  { value: 'SHARE_FILE',        label: '共享文件',    type: 'success' },
  { value: 'REVIEW_FILE',       label: '审阅文件',    type: 'warning' },
  { value: 'APPROVE_FILE',      label: '审批文件',    type: 'success' },
  { value: 'COMMENT_FILE',      label: '评论文件',    type: 'info'    },
  { value: 'SET_FILE_PERMISSIONS',    label: '设置文件权限', type: 'warning' },
  { value: 'DELETE_FILE_PERMISSION',  label: '删除文件权限', type: 'danger'  },
  { value: 'CREATE_ROLE',       label: '创建角色',    type: 'primary' },
  { value: 'UPDATE_ROLE',       label: '更新角色',    type: 'warning' },
  { value: 'DELETE_ROLE',       label: '删除角色',    type: 'danger'  },
  { value: 'ASSIGN_PERMISSIONS', label: '配置权限',   type: 'warning' },
  { value: 'ASSIGN_USER_ROLES', label: '分配角色',    type: 'primary' },
]

function actionMeta(action: string): { label: string; type: TagType } {
  const found = actionOptions.find(o => o.value === action)
  return found ? { label: found.label, type: found.type } : { label: action, type: 'info' }
}

const actionMap: Record<string, string> = {}
actionOptions.forEach(o => { actionMap[o.value] = o.label })

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
