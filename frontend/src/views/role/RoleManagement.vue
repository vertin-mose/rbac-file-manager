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
              <p>只读展示 L1-L5 层级继承关系。</p>
            </div>
          </div>
        </template>

        <div class="hierarchy-tree">
          <div class="h-level l1">
            <div class="level-badge">L1</div>
            <div class="level-card super-admin">
              <strong>SUPER_ADMIN</strong>
              <span class="level-desc">超级管理员</span>
            </div>
          </div>
          <div class="h-arrow">▼ 继承</div>
          <div class="h-level l2">
            <div class="level-badge">L2</div>
            <div class="level-card admin">
              <strong>ADMIN</strong>
              <span class="level-desc">系统管理员</span>
            </div>
          </div>
          <div class="h-arrow">▼ 继承</div>
          <div class="h-level l3">
            <div class="level-badge">L3</div>
            <div class="level-card manager">
              <strong>MANAGER</strong>
              <span class="level-desc">部门经理</span>
            </div>
          </div>
          <div class="h-arrow">▼ 继承</div>
          <div class="h-branch">
            <div class="h-level l4">
              <div class="level-badge">L4</div>
              <div class="level-card editor">
                <strong>EDITOR</strong>
                <span class="level-desc">文档编辑员</span>
              </div>
            </div>
            <div class="h-level l4">
              <div class="level-badge">L4</div>
              <div class="level-card reviewer">
                <strong>REVIEWER</strong>
                <span class="level-desc">文档审核员</span>
              </div>
            </div>
          </div>
          <div class="h-arrow l4-arrow">▼ 继承</div>
          <div class="h-level l5">
            <div class="level-badge">L5</div>
            <div class="level-card viewer">
              <strong>VIEWER</strong>
              <span class="level-desc">外部访客</span>
            </div>
          </div>
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
      <div style="margin-bottom: 12px; color: #909399; font-size: 13px">
        直接权限（可勾选）— 继承权限（已勾选，不可修改，来自下级角色的层级继承）
      </div>
      <el-checkbox-group v-model="permissionDialog.permissionIds" class="permission-grid">
        <div v-for="group in permissionGroups" :key="group" class="permission-group">
          <h4>{{ categoryLabel(group) }}</h4>
          <div v-for="permission in permissionsByGroup[group]" :key="permission.id" class="permission-check-item">
            <el-checkbox
              :label="permission.id"
              :disabled="permissionDialog.inheritedPermissionIds.includes(permission.id)"
              :class="{ 'is-inherited': permissionDialog.inheritedPermissionIds.includes(permission.id) }"
            >
              <span class="permission-option">
                <span>{{ permissionDisplayName(permission) }}</span>
                <small>{{ permission.description }}</small>
              </span>
            </el-checkbox>
            <el-tag
              v-if="permissionDialog.inheritedPermissionIds.includes(permission.id)"
              size="small"
              type="info"
              effect="plain"
            >继承</el-tag>
          </div>
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
import { assignPermissions, createRole, deleteRole, getRoles, updateRole, type Permission, type Role } from '@/api/role'
import { PERMISSIONS, PERMISSION_GROUPS, permissionCategoryLabel, permissionDescription, permissionDisplayName, permissionTagType } from '@/constants/permissions'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const loading = ref(false)
const roles = ref<Role[]>([])

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
  inheritedPermissionIds: [] as number[],
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

async function loadData() {
  loading.value = true
  try {
    roles.value = await getRoles()
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
  const directIds = new Set(role.permissions.map((p) => p.id))
  permissionDialog.inheritedPermissionIds = role.inheritedPermissions
    .filter((p) => !directIds.has(p.id))
    .map((p) => p.id)
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

.table-header h2 {
  margin: 0;
}

.table-header p {
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

.permission-check-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.permission-check-item :deep(.is-inherited .el-checkbox__label) {
  color: #a0abb5;
}

/* ── Role Hierarchy Tree ──────────────────────────── */
.hierarchy-tree {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
}
.h-level {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}
.level-badge {
  min-width: 32px; height: 24px;
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; color: #fff; flex-shrink: 0;
}
.l1 .level-badge { background: #e74c3c; }
.l2 .level-badge { background: #e67e22; }
.l3 .level-badge { background: #2980b9; }
.l4 .level-badge { background: #27ae60; }
.l5 .level-badge { background: #95a5a6; }
.level-card {
  flex: 1; padding: 10px 14px; border-radius: 8px;
  border: 1px solid #e1e9f0; display: flex; flex-direction: column; gap: 2px;
}
.level-card strong { font-size: 14px; }
.level-desc { font-size: 12px; color: #7c8b99; }
.super-admin { background: #fdf0ef; border-color: #f5c6cb; }
.admin { background: #fef6ef; border-color: #f8d7a8; }
.manager { background: #eef4fa; border-color: #b8d4f0; }
.editor { background: #eef8f0; border-color: #a8dfb4; }
.reviewer { background: #eef8f0; border-color: #a8dfb4; }
.viewer { background: #f8f9fa; border-color: #d5d8dc; }
.h-arrow { font-size: 11px; color: #95a5a6; text-align: center; line-height: 1.2; }
.h-branch {
  display: flex; flex-direction: column; gap: 6px;
  width: 100%; padding-left: 42px; border-left: 2px solid #d5d8dc;
}
.l4-arrow { padding-left: 42px; }

@media (max-width: 1120px) {
  .page-hero {
    flex-direction: column;
  }

  .content-grid {
    grid-template-columns: 1fr;
  }
}
</style>
