<template>
  <el-dialog
    :model-value="visible"
    :title="`权限管理 — ${fileName}`"
    width="680px"
    @close="$emit('close')"
  >
    <div class="perm-section">
      <h4>当前权限配置</h4>
      <el-table :data="permissions" v-loading="loading" size="small" stripe>
        <el-table-column label="用户" min-width="140">
          <template #default="{ row }">
            {{ row.username || '--' }}
          </template>
        </el-table-column>
        <el-table-column label="权限类型" min-width="100">
          <template #default="{ row }">
            <el-tag :type="permTagType(row.permissionType)" size="small">
              {{ permLabel(row.permissionType) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="授予时间" min-width="160">
          <template #default="{ row }">
            {{ row.grantedAt || '--' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="danger" size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && permissions.length === 0" description="暂无权限配置" :image-size="60" />
    </div>

    <el-divider />

    <div class="perm-section">
      <h4>新增权限</h4>
      <el-form :inline="true" @submit.prevent>
        <el-form-item label="用户">
          <el-select v-model="newPerm.userId" placeholder="选择用户" style="width: 160px" filterable>
            <el-option
              v-for="u in users"
              :key="u.id"
              :label="u.username"
              :value="u.id"
            >
              <span>{{ u.username }}</span>
              <span v-if="u.display_name" style="color: #999; margin-left: 8px">{{ u.display_name }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="权限">
          <el-checkbox-group v-model="newPerm.types">
            <el-checkbox label="read">查看</el-checkbox>
            <el-checkbox label="write">编辑</el-checkbox>
            <el-checkbox label="delete">删除</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="small" @click="handleAdd"
            :disabled="!newPerm.userId || newPerm.types.length === 0">
            添加
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <template #footer>
      <el-button @click="$emit('close')">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getFilePermissions,
  setFilePermissions,
  deleteFilePermission,
  type FilePermissionItem,
} from '@/api/file'
import { listUsers, type UserBasic } from '@/api/role'

const props = defineProps<{
  visible: boolean
  fileId: number
  fileName: string
}>()

defineEmits<{
  (e: 'close'): void
  (e: 'updated'): void
}>()

const loading = ref(false)
const permissions = ref<FilePermissionItem[]>([])
const users = ref<UserBasic[]>([])

const newPerm = reactive({
  userId: null as number | null,
  types: [] as string[],
})

function permLabel(type: string): string {
  const map: Record<string, string> = { read: '查看', write: '编辑', delete: '删除' }
  return map[type] || type
}

function permTagType(type: string): '' | 'success' | 'warning' | 'danger' {
  const map: Record<string, '' | 'success' | 'warning' | 'danger'> = {
    read: '',
    write: 'warning',
    delete: 'danger',
  }
  return map[type] || ''
}

async function loadPermissions() {
  loading.value = true
  try {
    permissions.value = await getFilePermissions(props.fileId)
  } finally {
    loading.value = false
  }
}

async function loadUsers() {
  try {
    users.value = await listUsers()
  } catch {
    // ignore
  }
}

async function handleAdd() {
  if (!newPerm.userId || newPerm.types.length === 0) return

  const existing = permissions.value.filter((p) => p.userId === newPerm.userId)
  const merged = [...new Set([...existing.map((p) => p.permissionType), ...newPerm.types])]

  const allPerms = permissions.value
    .filter((p) => p.userId !== newPerm.userId && p.userId != null)
    .map((p) => ({ user_id: p.userId!, permission_type: p.permissionType }))

  for (const t of merged) {
    allPerms.push({ user_id: newPerm.userId!, permission_type: t })
  }

  await setFilePermissions(props.fileId, allPerms)
  ElMessage.success('权限已添加')
  newPerm.userId = null
  newPerm.types = []
  await loadPermissions()
}

async function handleDelete(row: FilePermissionItem) {
  const target = row.username || '未知'
  try {
    await ElMessageBox.confirm(
      `确认删除 ${target} 的 ${permLabel(row.permissionType)} 权限吗？`,
      '删除确认',
      { type: 'warning' },
    )
    await deleteFilePermission(props.fileId, row.id)
    ElMessage.success('已删除')
    await loadPermissions()
  } catch {
    // cancelled
  }
}

watch(
  () => props.visible,
  (val) => {
    if (val) {
      loadPermissions()
      loadUsers()
    }
  },
)
</script>

<style scoped>
.perm-section h4 {
  margin: 0 0 12px;
  font-size: 14px;
  color: #303133;
}
.perm-tabs {
  margin-top: 4px;
}
</style>
