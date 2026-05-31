<template>
  <div class="role-page">
    <section class="page-hero">
      <div>
        <p class="eyebrow">RBAC Admin</p>
        <h1>角色管理</h1>
        <p class="hero-copy">维护角色定义、权限矩阵和角色继承关系。</p>
      </div>
      <div class="hero-actions">
        <el-button v-if="userStore.hasPermission('role:create')" type="primary" @click="openCreateDialog">
          新建角色
        </el-button>
        <el-button @click="loadData" :loading="loading">刷新</el-button>
      </div>
    </section>

    <div class="content-grid">
      <el-card class="table-card" shadow="never">
        <template #header>
          <div class="table-header">
            <div>
              <h2>角色列表</h2>
              <p>展示角色本身权限和继承权限。</p>
            </div>
          </div>
        </template>

        <el-table :data="roles" v-loading="loading" row-key="id">
          <el-table-column prop="name" label="角色名" min-width="140" />
          <el-table-column prop="description" label="描述" min-width="220" />
          <el-table-column label="自身权限" min-width="260">
            <template #default="{ row }">
              <div class="tag-flow">
                <el-tag v-for="perm in row.permissions" :key="perm.id" effect="plain">
                  {{ perm.name }}
                </el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="继承权限" min-width="260">
            <template #default="{ row }">
              <div class="tag-flow">
                <el-tag
                  v-for="perm in row.inheritedPermissions"
                  :key="`inherited-${perm.id}`"
                  type="info"
                  effect="plain"
                >
                  {{ perm.name }}
                </el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <div class="table-actions">
                <el-button
                  v-if="userStore.hasPermission('role:update')"
                  link
                  @click="openEditDialog(row)"
                >
                  编辑
                </el-button>
                <el-button
                  v-if="userStore.hasPermission('role:update')"
                  link
                  @click="openPermissionDialog(row)"
                >
                  权限配置
                </el-button>
                <el-button
                  v-if="userStore.hasPermission('role:delete')"
                  link
                  type="danger"
                  @click="confirmDelete(row.id, row.name)"
                >
                  删除
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <el-card class="sidebar-card" shadow="never">
        <template #header>
          <div class="table-header">
            <div>
              <h2>角色层级</h2>
              <p>只读展示后端配置的继承关系。</p>
            </div>
          </div>
        </template>

        <el-timeline>
          <el-timeline-item
            v-for="item in hierarchy"
            :key="`${item.roleId}-${item.inheritedRoleId}`"
            type="primary"
          >
            <strong>{{ item.roleName }}</strong>
            继承
            <strong>{{ item.inheritedRoleName }}</strong>
          </el-timeline-item>
        </el-timeline>

        <el-divider />

        <div class="assign-box">
          <div class="assign-header">
            <h3>用户角色分配</h3>
            <p>输入用户 ID 查询用户信息后，选择角色并确认分配。</p>
          </div>
          <el-form label-position="top">
            <el-form-item label="用户 ID">
              <el-input-number v-model="assignForm.userId" :min="1" controls-position="right" @change="handleUserIdChange" />
            </el-form-item>

            <!-- Show matched user info -->
            <el-alert
              v-if="userInfo"
              :title="userInfo.username"
              :description="`显示名: ${userInfo.display_name || '--'} | 邮箱: ${userInfo.email || '--'} | 当前角色: ${userInfo.roles.map((r: any) => r.name).join(', ') || '无'}`"
              type="success"
              show-icon
              :closable="false"
              class="user-info-alert"
            />
            <el-alert
              v-if="userInfoError"
              :title="userInfoError"
              type="error"
              show-icon
              :closable="false"
              class="user-info-alert"
            />
            <div v-if="userInfoLoading" class="user-info-loading">查询中...</div>

            <el-form-item label="角色">
              <el-select v-model="assignForm.roleIds" multiple filterable style="width: 100%">
                <el-option v-for="role in roles" :key="role.id" :label="role.name" :value="role.id" />
              </el-select>
            </el-form-item>
            <el-button
              v-if="userStore.hasPermission('role:assign')"
              type="primary"
              @click="confirmAssignRoles"
              :disabled="!userInfo"
            >
              保存分配
            </el-button>
          </el-form>
        </div>
      </el-card>
    </div>

    <el-dialog v-model="roleDialog.visible" :title="roleDialog.editingId ? '编辑角色' : '新建角色'" width="640px">
      <el-form label-position="top">
        <el-form-item label="角色名">
          <el-input v-model="roleDialog.form.name" :disabled="Boolean(roleDialog.editingId)" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="roleDialog.form.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="权限">
          <el-checkbox-group v-model="roleDialog.form.permissionIds" class="permission-grid">
            <div v-for="group in permissionGroups" :key="group" class="permission-group">
              <h4>{{ categoryLabel(group) }}</h4>
              <el-checkbox
                v-for="permission in permissionsByGroup[group]"
                :key="permission.id"
                :label="permission.id"
              >
                {{ permission.name }}
              </el-checkbox>
            </div>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="roleDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitRoleDialog">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="permissionDialog.visible" title="权限配置" width="640px">
      <el-checkbox-group v-model="permissionDialog.permissionIds" class="permission-grid">
        <div v-for="group in permissionGroups" :key="group" class="permission-group">
          <h4>{{ categoryLabel(group) }}</h4>
          <el-checkbox
            v-for="permission in permissionsByGroup[group]"
            :key="permission.id"
            :label="permission.id"
          >
            {{ permission.name }}
          </el-checkbox>
        </div>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="permissionDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitPermissionDialog">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { assignPermissions, assignUserRoles, createRole, deleteRole, getRoleHierarchy, getRoles, getUserInfo, updateRole, type Role, type RoleHierarchyItem } from '@/api/role'
import { PERMISSIONS, PERMISSION_GROUPS } from '@/constants/permissions'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const loading = ref(false)
const roles = ref<Role[]>([])
const hierarchy = ref<RoleHierarchyItem[]>([])

const userInfo = ref<any>(null)
const userInfoLoading = ref(false)
const userInfoError = ref('')

const assignForm = reactive({
  userId: 0,
  roleIds: [] as number[],
})

const roleDialog = reactive({
  visible: false,
  editingId: 0,
  form: {
    name: '',
    description: '',
    permissionIds: [] as number[],
  },
})

const permissionDialog = reactive({
  visible: false,
  roleId: 0,
  permissionIds: [] as number[],
})

const permissionGroups = [...PERMISSION_GROUPS]

const permissionsByGroup = computed(() =>
  permissionGroups.reduce((acc, group) => {
    acc[group] = PERMISSIONS.filter((permission) => permission.category === group)
    return acc
  }, {} as Record<string, typeof PERMISSIONS>),
)

function categoryLabel(category: string) {
  const labels: Record<string, string> = {
    document: '文档权限',
    user: '用户权限',
    role: '角色权限',
    audit: '审计权限',
    system: '系统权限',
  }
  return labels[category] || category
}

async function loadData() {
  loading.value = true
  try {
    const [roleList, hierarchyList] = await Promise.all([
      getRoles(),
      getRoleHierarchy(),
    ])
    roles.value = roleList
    hierarchy.value = hierarchyList
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  roleDialog.visible = true
  roleDialog.editingId = 0
  roleDialog.form.name = ''
  roleDialog.form.description = ''
  roleDialog.form.permissionIds = []
}

function openEditDialog(role: Role) {
  roleDialog.visible = true
  roleDialog.editingId = role.id
  roleDialog.form.name = role.name
  roleDialog.form.description = role.description
  roleDialog.form.permissionIds = role.permissions.map((permission) => permission.id)
}

async function submitRoleDialog() {
  if (!roleDialog.form.name.trim()) {
    ElMessage.warning('角色名不能为空')
    return
  }
  if (roleDialog.editingId) {
    await updateRole(roleDialog.editingId, {
      name: roleDialog.form.name.trim(),
      description: roleDialog.form.description.trim(),
    })
  } else {
    await createRole({
      name: roleDialog.form.name.trim(),
      description: roleDialog.form.description.trim(),
      permissionIds: roleDialog.form.permissionIds,
    })
  }
  roleDialog.visible = false
  ElMessage.success('角色已保存')
  await loadData()
}

function openPermissionDialog(role: Role) {
  permissionDialog.visible = true
  permissionDialog.roleId = role.id
  permissionDialog.permissionIds = role.permissions.map((permission) => permission.id)
}

async function submitPermissionDialog() {
  await assignPermissions(permissionDialog.roleId, permissionDialog.permissionIds)
  permissionDialog.visible = false
  ElMessage.success('权限已更新')
  await loadData()
}

async function confirmDelete(roleId: number, roleName: string) {
  await ElMessageBox.confirm(`确认删除角色 ${roleName} 吗？`, '删除确认', {
    type: 'warning',
  })
  await deleteRole(roleId)
  ElMessage.success('角色已删除')
  await loadData()
}

async function handleUserIdChange() {
  if (!assignForm.userId || assignForm.userId < 1) {
    userInfo.value = null
    userInfoError.value = ''
    return
  }
  userInfoLoading.value = true
  userInfo.value = null
  userInfoError.value = ''
  try {
    userInfo.value = await getUserInfo(assignForm.userId)
  } catch {
    userInfoError.value = '未找到该用户'
  } finally {
    userInfoLoading.value = false
  }
}

async function confirmAssignRoles() {
  if (!assignForm.userId || assignForm.roleIds.length === 0) {
    ElMessage.warning('请填写用户 ID 并选择角色')
    return
  }
  if (!userInfo.value) {
    ElMessage.warning('请先查询确认用户信息')
    return
  }
  const currentRoles = userInfo.value.roles.map((r: any) => r.name).join(', ') || '无'
  const newRoles = assignForm.roleIds.map((id: number) => roles.value.find(r => r.id === id)?.name || id).join(', ')
  await ElMessageBox.confirm(
    `将用户 "${userInfo.value.username}"（ID: ${assignForm.userId}）的角色从 [${currentRoles}] 变更为 [${newRoles}]，确认？`,
    '角色分配确认',
    { type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消' }
  )
  await assignUserRoles(assignForm.userId, assignForm.roleIds)
  ElMessage.success('用户角色已更新')
}

onMounted(loadData)
</script>

<style scoped>
.role-page {
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
    radial-gradient(circle at top right, rgba(219, 175, 73, 0.18), transparent 28%),
    linear-gradient(135deg, #273746 0%, #39566a 52%, #4c6d82 100%);
  color: #f8fafc;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(248, 220, 174, 0.9);
}

.page-hero h1 {
  margin: 0;
  font-size: 34px;
}

.hero-copy {
  margin: 10px 0 0;
  line-height: 1.7;
  color: rgba(248, 250, 252, 0.78);
}

.hero-actions {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(320px, 420px);
  gap: 20px;
}

.table-card,
.sidebar-card {
  border-radius: 20px;
}

.table-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.table-header h2,
.assign-header h3 {
  margin: 0;
}

.table-header p,
.assign-header p {
  margin: 6px 0 0;
  color: #7c8b99;
}

.tag-flow,
.table-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.assign-box {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.user-info-alert {
  margin-bottom: 8px;
}

.user-info-loading {
  color: #909399;
  font-size: 13px;
  margin-bottom: 8px;
}

.permission-grid {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.permission-group {
  padding: 16px;
  border-radius: 16px;
  background: #f6f9fb;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.permission-group h4 {
  margin: 0;
  color: #213547;
}

@media (max-width: 1120px) {
  .page-hero,
  .content-grid {
    grid-template-columns: 1fr;
  }
}
</style>
