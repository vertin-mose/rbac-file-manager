<template>
  <div class="role-page">
    <section class="page-hero">
      <div>
        <p class="eyebrow">RBAC Admin</p>
        <h1>角色管理</h1>
        <p class="hero-copy">维护角色定义、权限矩阵和角色继承关系。</p>
      </div>
      <div class="hero-actions">
        <el-button v-if="userStore.hasPermission('role:create')" type="primary" :icon="Plus" @click="openCreateDialog">
          新建角色
        </el-button>
        <el-button :icon="Refresh" @click="loadData" :loading="loading">刷新</el-button>
      </div>
    </section>

    <div class="content-grid">
      <el-card class="table-card" shadow="never">
        <template #header>
          <div class="table-header">
            <div>
              <h2>角色列表</h2>
              <p>合并展示直接权限与继承权限。</p>
            </div>
          </div>
        </template>

        <el-table :data="roles" v-loading="loading" row-key="id">
          <el-table-column prop="name" label="角色名" min-width="140" />
          <el-table-column prop="description" label="描述" min-width="220" />
          <el-table-column label="权限覆盖" min-width="360">
            <template #default="{ row }">
              <div class="permission-cell" v-if="hasAnyPermissions(row)">
                <div class="permission-line" v-if="directPermissions(row).length">
                  <span class="permission-line__label">直接</span>
                  <el-tag
                    v-for="perm in directPermissions(row)"
                    :key="perm.name"
                    :type="permissionTagType(perm)"
                    effect="plain"
                    :title="permissionDescription(perm)"
                  >
                    {{ permissionDisplayName(perm) }}
                  </el-tag>
                </div>
                <div class="permission-line" v-if="inheritedPermissions(row).length">
                  <span class="permission-line__label">继承</span>
                  <el-tag
                    v-for="perm in inheritedPermissions(row)"
                    :key="`inherited-${perm.name}`"
                    type="info"
                    effect="plain"
                    :title="permissionDescription(perm)"
                  >
                    {{ permissionDisplayName(perm) }}
                  </el-tag>
                </div>
              </div>
              <el-tag v-else type="info" effect="plain">暂无权限</el-tag>
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
              :description="formatUserInfoDescription(userInfo)"
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
        <el-form-item v-if="!roleDialog.editingId" label="初始权限">
          <el-checkbox-group v-model="roleDialog.form.permissionIds" class="permission-grid">
            <div v-for="group in permissionGroups" :key="group" class="permission-group">
              <h4>{{ categoryLabel(group) }}</h4>
              <el-checkbox
                v-for="permission in permissionsByGroup[group]"
                :key="permission.id"
                :label="permission.id"
              >
                <span class="permission-option">
                  <span>{{ permissionDisplayName(permission) }}</span>
                  <small>{{ permission.description }}</small>
                </span>
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
            <span class="permission-option">
              <span>{{ permissionDisplayName(permission) }}</span>
              <small>{{ permission.description }}</small>
            </span>
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
import { Plus, Refresh } from '@element-plus/icons-vue'
import { assignPermissions, assignUserRoles, createRole, deleteRole, getRoleHierarchy, getRoles, getUserInfo, updateRole, type Permission, type Role, type RoleHierarchyItem } from '@/api/role'
import { PERMISSIONS, PERMISSION_GROUPS, permissionCategoryLabel, permissionDescription, permissionDisplayName, permissionTagType } from '@/constants/permissions'
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
  return permissionCategoryLabel(category)
}

function dedupePermissions(permissions: Permission[]) {
  const seen = new Set<string>()
  return permissions.filter((permission) => {
    if (seen.has(permission.name)) return false
    seen.add(permission.name)
    return true
  })
}

function directPermissions(role: Role) {
  return dedupePermissions(role.permissions)
}

function inheritedPermissions(role: Role) {
  const directNames = new Set(role.permissions.map((permission) => permission.name))
  return dedupePermissions(role.inheritedPermissions).filter((permission) => !directNames.has(permission.name))
}

function hasAnyPermissions(role: Role) {
  return directPermissions(role).length > 0 || inheritedPermissions(role).length > 0
}

function formatUserInfoDescription(info: {
  display_name?: string | null
  email?: string | null
  roles?: Array<{ name: string }>
}) {
  const roleNames = info.roles?.map((role) => role.name).join(', ') || '无'
  return `显示名: ${info.display_name || '--'} | 邮箱: ${info.email || '--'} | 当前角色: ${roleNames}`
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
  padding: 22px 24px;
  border: 1px solid #dce6ee;
  border-radius: 12px;
  background: linear-gradient(135deg, #ffffff 0%, #f1f7fb 52%, #f8f1e8 100%);
  color: #1f3448;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #8a5d16;
}

.page-hero h1 {
  margin: 0;
  font-size: 34px;
}

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

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(320px, 420px);
  gap: 20px;
}

.table-card,
.sidebar-card {
  border-radius: 8px;
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

.permission-cell {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.permission-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

.permission-line__label {
  min-width: 34px;
  color: #66788a;
  font-size: 12px;
  font-weight: 700;
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
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 16px;
}

.permission-group {
  padding: 16px;
  border: 1px solid #e1e9f0;
  border-radius: 8px;
  background: #f7fafc;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.permission-group h4 {
  margin: 0;
  color: #213547;
}

.permission-option {
  display: inline-flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.35;
  white-space: normal;
}

.permission-option small {
  color: #81909f;
  font-size: 12px;
}

@media (max-width: 1120px) {
  .page-hero {
    flex-direction: column;
  }

  .content-grid {
    grid-template-columns: 1fr;
  }
}
</style>
