<template>
  <el-dialog
    :model-value="visible"
    :title="`权限管理 — ${fileName}`"
    width="720px"
    @close="$emit('close')"
  >
    <!-- Read-only hint -->
    <el-alert
      v-if="readonlyHint"
      :title="readonlyHint"
      type="warning"
      show-icon
      :closable="false"
      class="hint-alert"
    />

    <div class="perm-section">
      <h4>当前权限配置</h4>
      <el-table :data="permissions" v-loading="loading" size="small" stripe>
        <el-table-column label="授权对象" min-width="160">
          <template #default="{ row }">
            <span v-if="row.roleName">
              <el-tag size="small" type="info">{{ roleDisplayName(row.roleName) }}</el-tag>
              — 全部用户
            </span>
            <span v-else>{{ row.username || '--' }}</span>
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
            <el-button
              link
              type="danger"
              size="small"
              @click="handleDelete(row)"
              :disabled="isReadonly"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && permissions.length === 0" description="暂无权限配置" :image-size="60" />
    </div>

    <el-divider />

    <div class="perm-section" v-if="!isReadonly">
      <h4>新增权限</h4>

      <el-form label-position="top" @submit.prevent>
        <el-form-item label="选择角色（可多选）">
          <el-select v-model="form.roleIds" multiple placeholder="请选择角色，可多选" style="width: 100%" @change="handleRoleChange">
            <el-option v-for="role in roles" :key="role.id" :label="roleDisplayName(role.name) || role.name" :value="role.id" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="form.roleIds.length > 0" label="选择用户">
          <div class="user-checkbox-group">
            <el-checkbox v-model="form.allUsers" @change="handleAllUsersChange">
              <strong>全部用户</strong>
              <span class="hint-text">（所选角色下的所有用户）</span>
            </el-checkbox>
            <el-divider style="margin: 4px 0" />
            <el-checkbox
              v-for="user in usersByRole"
              :key="user.id"
              v-model="form.selectedUserIds"
              :label="user.id"
              :disabled="form.allUsers"
            >
              {{ user.username }}
              <span v-if="user.display_name" class="hint-text">（{{ user.display_name }}）</span>
            </el-checkbox>
            <el-empty v-if="usersByRole.length === 0" description="所选角色下暂无用户" :image-size="40" />
          </div>
        </el-form-item>

        <el-form-item label="权限类型">
          <el-checkbox-group v-model="form.types">
            <el-checkbox label="read">查看</el-checkbox>
            <el-checkbox label="write">编辑</el-checkbox>
            <el-checkbox label="delete">删除</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleAdd" :disabled="!canAdd">
            添加权限
          </el-button>
        </el-form-item>
      </el-form>
    </div>
    <div v-else-if="readonlyHint" class="perm-section">
      <el-empty description="您没有权限修改此文件的权限配置" :image-size="50" />
    </div>

    <template #footer>
      <el-button @click="$emit('close')">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getFilePermissions,
  setFilePermissions,
  deleteFilePermission,
  type FilePermissionItem,
} from '@/api/file'
import { getRoles, listUsers, type UserBasic } from '@/api/role'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()

const props = defineProps<{
  visible: boolean
  fileId: number
  fileName: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'updated'): void
}>()

const loading = ref(false)
const permissions = ref<FilePermissionItem[]>([])
const roles = ref<{ id: number; name: string }[]>([])
const users = ref<UserBasic[]>([])

const form = reactive({
  roleIds: [] as number[],
  allUsers: false,
  selectedUserIds: [] as number[],
  types: [] as string[],
})

/** Whether current user can only view (not modify) permissions */
const isReadonly = computed(() => {
  if (userStore.hasPermission('file:permission:manage')) {
    return false
  }
  // Non-admin user in dialog: only allow if no permissions exist yet (initial setup)
  return permissions.value.length > 0
})

const readonlyHint = computed(() => {
  if (userStore.hasPermission('file:permission:manage')) {
    return ''
  }
  if (permissions.value.length === 0) {
    return '首次设置权限：您可以在此配置文件的初始权限。保存后仅管理员可修改。'
  }
  return '权限已配置，仅管理员可以修改。'
})

const canAdd = computed(() => {
  if (isReadonly.value) return false
  if (form.roleIds.length === 0) return false
  if (!form.allUsers && form.selectedUserIds.length === 0) return false
  if (form.types.length === 0) return false
  return true
})

const usersByRole = computed(() => {
  if (form.roleIds.length === 0) return []
  return users.value.filter((u) =>
    u.roles?.some((r) => form.roleIds.includes(r.id)),
  )
})

function roleDisplayName(roleName: string): string {
  const names: Record<string, string> = {
    SUPER_ADMIN: '超级管理员',
    ADMIN: '系统管理员',
    MANAGER: '部门经理',
    EDITOR: '文档编辑员',
    REVIEWER: '文档审核员',
    VIEWER: '访客',
  }
  return names[roleName] || roleName
}

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

function resetForm() {
  form.roleIds = []
  form.allUsers = false
  form.selectedUserIds = []
  form.types = []
}

function handleRoleChange() {
  form.allUsers = false
  form.selectedUserIds = []
}

function handleAllUsersChange(val: boolean) {
  if (val) {
    form.selectedUserIds = []
  }
}

async function loadPermissions() {
  loading.value = true
  try {
    permissions.value = await getFilePermissions(props.fileId)
  } finally {
    loading.value = false
  }
}

async function loadRoles() {
  try {
    const data = await getRoles()
    roles.value = data.map((r) => ({ id: r.id, name: r.name }))
  } catch {
    // ignore
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
  if (!canAdd.value) return

  const newPerms: Array<{ role_id?: number; user_id?: number; permission_type: string }> = []

  if (form.allUsers) {
    for (const t of form.types) {
      for (const rid of form.roleIds) {
        newPerms.push({ role_id: rid, permission_type: t })
      }
    }
  } else {
    for (const uid of form.selectedUserIds) {
      for (const t of form.types) {
        newPerms.push({ user_id: uid, permission_type: t })
      }
    }
  }

  // Merge with existing: keep old permissions that don't conflict
  const existingPerms = permissions.value
    .filter((p) => {
      if (form.allUsers) {
        return !(p.roleId && form.roleIds.includes(p.roleId))
      }
      return !(p.userId && form.selectedUserIds.includes(p.userId))
    })
    .map((p) => ({
      role_id: p.roleId ?? undefined,
      user_id: p.userId ?? undefined,
      permission_type: p.permissionType,
    }))

  const allPerms = [...existingPerms, ...newPerms]

  try {
    await setFilePermissions(props.fileId, allPerms)
    ElMessage.success('权限已添加')
    emit('updated')
    resetForm()
    await loadPermissions()
  } catch {
    ElMessage.error('权限添加失败')
  }
}

async function handleDelete(row: FilePermissionItem) {
  if (isReadonly.value) return
  const target = row.roleName
    ? `${roleDisplayName(row.roleName)} 角色（全部用户）`
    : row.username || '未知'
  try {
    await ElMessageBox.confirm(
      `确认删除 ${target} 的 ${permLabel(row.permissionType)} 权限吗？`,
      '删除确认',
      { type: 'warning' },
    )
    await deleteFilePermission(props.fileId, row.id)
    ElMessage.success('已删除')
    emit('updated')
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
      loadRoles()
      loadUsers()
      resetForm()
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

.hint-alert {
  margin-bottom: 16px;
}

.hint-text {
  color: #999;
  margin-left: 4px;
}

.user-checkbox-group {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 16px;
  border-radius: 12px;
  background: #f6f9fb;
}
</style>
