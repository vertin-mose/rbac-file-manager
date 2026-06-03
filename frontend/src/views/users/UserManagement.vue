<template>
  <div class="users-page">
    <section class="page-hero">
      <div>
        <p class="eyebrow">User Center</p>
        <h1>用户管理</h1>
        <p class="hero-copy">管理系统用户账号，支持创建、禁用/启用、删除与角色分配。</p>
      </div>
      <div class="hero-actions">
        <el-button
          v-if="userStore.hasPermission('user:create')"
          type="primary"
          :icon="Plus"
          @click="openCreateDialog"
        >
          创建用户
        </el-button>
        <el-button :icon="Refresh" :loading="loading" @click="loadData">刷新</el-button>
      </div>
    </section>

    <el-card class="table-card" shadow="never">
      <template #header>
        <div class="table-header">
          <div class="search-bar">
            <el-input
              v-model="searchText"
              placeholder="搜索用户名"
              clearable
              style="width: 200px"
              @input="loadData"
            />
            <el-select
              v-model="searchRole"
              placeholder="按角色筛选"
              clearable
              style="width: 160px"
              @change="loadData"
            >
              <el-option
                v-for="role in allRoles"
                :key="role.id"
                :label="role.name"
                :value="role.name"
              />
            </el-select>
          </div>
          <el-tag type="info" effect="plain">{{ filteredUsers.length }} 个用户</el-tag>
        </div>
      </template>

      <el-table :data="filteredUsers" v-loading="loading" row-key="id" stripe>
        <el-table-column label="ID" prop="id" width="70" />
        <el-table-column label="用户名" prop="username" min-width="130" />
        <el-table-column label="显示名称" min-width="130">
          <template #default="{ row }">
            {{ row.display_name || '--' }}
          </template>
        </el-table-column>
        <el-table-column label="邮箱" min-width="170">
          <template #default="{ row }">
            {{ row.email || '--' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'danger'" size="small" effect="plain">
              {{ row.enabled ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="角色" min-width="200">
          <template #default="{ row }">
            <el-tag
              v-for="r in (row.roles || [])"
              :key="r.id"
              size="small"
              :type="roleTagType(r.name)"
              effect="plain"
              style="margin-right: 4px"
            >
              {{ r.name }}
            </el-tag>
            <span v-if="!row.roles || row.roles.length === 0" style="color:#999">--</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <div class="table-actions">
              <el-button
                v-if="userStore.hasPermission('role:assign')"
                link
                type="primary"
                @click="openAssignDialog(row)"
              >
                分配角色
              </el-button>
              <el-button
                v-if="userStore.hasPermission('user:update')"
                link
                :type="row.enabled ? 'warning' : 'success'"
                @click="handleToggleStatus(row)"
              >
                {{ row.enabled ? '禁用' : '启用' }}
              </el-button>
              <el-button
                v-if="userStore.hasPermission('user:delete')"
                link
                type="danger"
                @click="handleDeleteUser(row)"
              >
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- Create User Dialog -->
    <el-dialog v-model="createDialog.visible" title="创建用户" width="520px">
      <el-form label-position="top">
        <el-form-item label="用户名">
          <el-input v-model="createDialog.form.username" placeholder="登录用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="createDialog.form.password" type="password" placeholder="初始密码" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="createDialog.form.displayName" placeholder="选填" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="createDialog.form.email" placeholder="选填" />
        </el-form-item>
        <el-form-item label="角色">
          <el-checkbox-group v-model="createDialog.form.roleIds">
            <el-checkbox
              v-for="role in allRoles"
              :key="role.id"
              :label="role.id"
            >
              <strong>{{ role.name }}</strong>
              <span style="color:#999; margin-left: 6px; font-size:12px">{{ role.description }}</span>
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="createLoading" @click="submitCreateUser">创建</el-button>
      </template>
    </el-dialog>

    <!-- Assign Role Dialog -->
    <el-dialog v-model="assignDialog.visible" title="分配角色" width="480px">
      <div style="margin-bottom: 12px">
        <strong>用户：</strong>{{ assignDialog.username }}
      </div>
      <el-checkbox-group v-model="assignDialog.selectedRoleIds">
        <div v-for="role in allRoles" :key="role.id" style="margin-bottom: 8px">
          <el-checkbox :label="role.id">
            <strong>{{ role.name }}</strong>
            <span style="color:#999; margin-left: 8px; font-size:12px">{{ role.description }}</span>
          </el-checkbox>
        </div>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="assignDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="assignLoading" @click="submitAssign">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import {
  adminCreateUser, adminDeleteUser, assignUserRoles, getRoles, getUserInfo,
  listUsers, toggleUserStatus, type UserBasic,
} from '@/api/role'
import { useUserStore } from '@/store/user'

interface UserEx extends UserBasic {
  enabled: boolean
  roles?: { id: number; name: string }[]
}

const userStore = useUserStore()
const loading = ref(false)
const assignLoading = ref(false)
const createLoading = ref(false)
const users = ref<UserEx[]>([])
const allRoles = ref<{ id: number; name: string; description: string }[]>([])
const searchText = ref('')
const searchRole = ref('')

const createDialog = reactive({
  visible: false,
  form: {
    username: '',
    password: '',
    displayName: '',
    email: '',
    roleIds: [] as number[],
  },
})

const assignDialog = reactive({
  visible: false,
  userId: 0,
  username: '',
  selectedRoleIds: [] as number[],
})

const filteredUsers = computed(() => {
  let result = users.value
  if (searchText.value.trim()) {
    const q = searchText.value.trim().toLowerCase()
    result = result.filter((u) => u.username.toLowerCase().includes(q))
  }
  if (searchRole.value) {
    result = result.filter((u) =>
      (u.roles || []).some((r) => r.name === searchRole.value)
    )
  }
  return result
})

function roleTagType(name: string): '' | 'danger' | 'warning' | 'primary' | 'info' | 'success' {
  const map: Record<string, '' | 'danger' | 'warning' | 'primary' | 'info' | 'success'> = {
    SUPER_ADMIN: 'danger', ADMIN: 'danger',
    MANAGER: 'warning', EDITOR: 'primary', REVIEWER: 'primary', VIEWER: 'info',
  }
  return map[name] ?? ''
}

async function loadData() {
  loading.value = true
  try {
    const [userList, roleList] = await Promise.all([listUsers(), getRoles()])
    allRoles.value = roleList.map(r => ({ id: r.id, name: r.name, description: r.description }))
    // Enrich users with enabled status and roles
    const enriched = await Promise.all(
      userList.map(async (u: any) => {
        try {
          const info = await getUserInfo(u.id)
          return { ...u, enabled: info.enabled, roles: info.roles }
        } catch {
          return { ...u, enabled: true, roles: [] }
        }
      })
    )
    users.value = enriched
  } catch {
    ElMessage.error('加载用户数据失败')
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  createDialog.form.username = ''
  createDialog.form.password = ''
  createDialog.form.displayName = ''
  createDialog.form.email = ''
  createDialog.form.roleIds = allRoles.value.filter(r => r.name === 'VIEWER').map(r => r.id)
  createDialog.visible = true
}

async function submitCreateUser() {
  if (!createDialog.form.username.trim()) {
    ElMessage.warning('用户名不能为空')
    return
  }
  if (!createDialog.form.password.trim()) {
    ElMessage.warning('密码不能为空')
    return
  }
  createLoading.value = true
  try {
    await adminCreateUser({
      username: createDialog.form.username.trim(),
      password: createDialog.form.password,
      display_name: createDialog.form.displayName.trim() || undefined,
      email: createDialog.form.email.trim() || undefined,
      role_ids: createDialog.form.roleIds,
    })
    ElMessage.success('用户创建成功')
    createDialog.visible = false
    await loadData()
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.response?.data?.message || '创建失败'
    ElMessage.error(msg)
  } finally {
    createLoading.value = false
  }
}

function openAssignDialog(user: any) {
  assignDialog.userId = user.id
  assignDialog.username = user.username
  assignDialog.selectedRoleIds = (user.roles || []).map((r: any) => r.id)
  assignDialog.visible = true
}

async function submitAssign() {
  if (!assignDialog.userId) return
  assignLoading.value = true
  try {
    await assignUserRoles(assignDialog.userId, assignDialog.selectedRoleIds)
    ElMessage.success('角色分配成功')
    assignDialog.visible = false
    await loadData()
  } catch {
    ElMessage.error('角色分配失败')
  } finally {
    assignLoading.value = false
  }
}

async function handleToggleStatus(user: UserEx) {
  const action = user.enabled ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确认${action}用户 "${user.username}" 吗？`, '确认操作', {
      type: 'warning',
    })
    await toggleUserStatus(user.id)
    ElMessage.success(`用户已${action}`)
    await loadData()
  } catch {
    return
  }
}

async function handleDeleteUser(user: UserEx) {
  try {
    await ElMessageBox.confirm(
      `确认永久删除用户 "${user.username}"（ID: ${user.id}）吗？\n此操作不可恢复。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '确认删除', cancelButtonText: '取消' }
    )
    await adminDeleteUser(user.id)
    ElMessage.success('用户已删除')
    await loadData()
  } catch {
    return
  }
}

onMounted(loadData)
</script>

<style scoped>
.users-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-hero {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  padding: 22px 24px;
  border: 1px solid #dce6ee;
  border-radius: 12px;
  background: linear-gradient(135deg, #ffffff 0%, #edf4ff 52%, #eef8f4 100%);
  color: #1f3448;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #1a5fa8;
}

.page-hero h1 { margin: 0; font-size: 34px; }

.hero-copy {
  margin: 10px 0 0;
  line-height: 1.7;
  color: #647789;
}

.hero-actions {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.table-card { border-radius: 12px; }

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.search-bar {
  display: flex;
  gap: 10px;
}

.table-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
