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
          <el-table-column label="操作" width="220" fixed="right" v-if="userStore.highestLevel <= 2">
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
              <p>动态展示层级继承关系，新建角色时可在此选择位置。</p>
            </div>
          </div>
        </template>

        <div class="hierarchy-tree">
          <template v-for="(group, gidx) in hierarchyByLevel" :key="gidx">
            <!-- Arrow between levels -->
            <div v-if="gidx > 0" class="h-arrow">▼ 继承</div>
            <!-- Roles at this level -->
            <div v-for="role in group.roles" :key="role.id" class="h-level-branch">
              <div class="h-level" :class="'l' + group.level">
                <div class="level-badge">L{{ group.level }}</div>
                <div class="level-card" :class="levelCardClass(role.name)">
                  <strong>{{ role.name }}</strong>
                  <span class="level-desc">{{ role.display_name }}</span>
                </div>
              </div>
            </div>
          </template>
          <div v-if="hierarchyByLevel.length === 0" style="color: #999; padding: 20px; text-align: center;">
            暂无层级数据
          </div>
        </div>
      </el-card>
    </div>

    <el-dialog v-model="roleDialog.visible" :title="roleDialog.editingId ? '编辑角色' : '新建角色'" width="720px">
      <!-- ── Edit Mode ── -->
      <div v-if="roleDialog.editingId" class="step-content">
        <el-form label-position="top">
          <el-form-item label="角色名">
            <el-input v-model="roleDialog.form.name" :disabled="Boolean(roleDialog.editingId)" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="roleDialog.form.description" type="textarea" :rows="3" />
          </el-form-item>
        </el-form>
      </div>

      <!-- ── Create Mode (Wizard) ── -->
      <div v-else class="dialog-wizard">
        <el-steps :active="roleDialog.currentStep" finish-status="success" align-center style="margin-bottom: 24px">
          <el-step title="基本信息" />
          <el-step title="层级位置" />
          <el-step title="权限配置" />
        </el-steps>

        <!-- Step 0: Basic Info -->
        <div v-show="roleDialog.currentStep === 0" class="step-content">
          <div class="step-inner">
            <el-form label-position="top">
              <el-form-item label="角色名">
                <el-input v-model="roleDialog.form.name" placeholder="输入新角色名称" />
              </el-form-item>
              <el-form-item label="描述">
                <el-input v-model="roleDialog.form.description" type="textarea" :rows="4" placeholder="角色描述（可选）" />
              </el-form-item>
            </el-form>
          </div>
        </div>

        <!-- Step 1: Hierarchy Position -->
        <div v-show="roleDialog.currentStep === 1" class="step-content">
          <div class="hint-text">选择此角色继承自哪个层级，可在同层级内勾选多个角色以合并继承权限。</div>
          <div class="wizard-hierarchy">
            <div v-for="(group, gidx) in hierarchyByLevel" :key="gidx" class="wizard-level-row">
              <div class="wizard-level-header">
                <el-radio v-model="roleDialog.selectedLevel" :value="group.level">
                  <span :class="'level-tag l' + group.level">L{{ group.level }}</span>
                  <span class="level-role-names">{{ group.roles.map(r => r.name).join('、') }}</span>
                </el-radio>
              </div>
              <div v-if="roleDialog.selectedLevel === group.level && group.roles.length > 1" class="wizard-level-roles">
                <el-checkbox-group v-model="roleDialog.selectedInheritedRoleIds">
                  <el-checkbox v-for="role in group.roles" :key="role.id" :label="role.id">
                    <span class="wizard-checkbox-label">
                      <span>{{ role.name }}</span>
                      <span class="role-desc">{{ role.display_name }}</span>
                    </span>
                  </el-checkbox>
                </el-checkbox-group>
              </div>
              <div v-else-if="roleDialog.selectedLevel === group.level && group.roles.length === 1" class="wizard-level-roles">
                <span class="single-role-hint">继承自：<strong>{{ group.roles[0].name }}</strong></span>
              </div>
            </div>
          </div>

          <!-- Placement option: parallel vs insert -->
          <div v-if="roleDialog.selectedInheritedRoleIds.length > 0" class="placement-section">
            <div class="hint-text">放置方式</div>
            <el-radio-group v-model="roleDialog.placement" class="placement-radio-group">
              <el-radio value="parallel" border>
                <div class="placement-option">
                  <strong>与父角色同级并列</strong>
                  <span class="placement-desc">新角色与所继承的角色位于同一层级</span>
                </div>
              </el-radio>
              <el-radio value="insert" border>
                <div class="placement-option">
                  <strong>插入层级之间</strong>
                  <span class="placement-desc">
                    新角色插入到父角色与
                    <template v-if="hasSelectedChildren">【{{ getChildNames() }}】</template>
                    <template v-else>其直接继承者</template>
                    之间，以下角色依次顺延
                  </span>
                </div>
              </el-radio>
            </el-radio-group>
          </div>
        </div>

        <!-- Step 2: Permission Selection -->
        <div v-show="roleDialog.currentStep === 2" class="step-content">
          <div class="perm-hint">继承权限（自动勾选，不可取消）— 可额外勾选其他权限</div>
          <el-checkbox-group v-model="roleDialog.form.permissionIds" class="permission-grid">
            <div v-for="group in permissionGroups" :key="group" class="permission-group">
              <h4>{{ categoryLabel(group) }}</h4>
              <div v-for="permission in permissionsByGroup[group]" :key="permission.id" class="permission-check-item">
                <el-checkbox
                  :label="permission.id"
                  :disabled="isPermissionInherited(permission.id)"
                  :class="{ 'is-inherited': isPermissionInherited(permission.id) }"
                >
                  <span class="permission-option">
                    <span>{{ permissionDisplayName(permission) }}</span>
                    <small>{{ permission.description }}</small>
                  </span>
                </el-checkbox>
                <el-tag v-if="isPermissionInherited(permission.id)" size="small" type="info" effect="plain">继承</el-tag>
              </div>
            </div>
          </el-checkbox-group>
        </div>
      </div>

      <template #footer>
        <el-button @click="roleDialog.visible = false">取消</el-button>
        <el-button v-if="roleDialog.editingId" type="primary" @click="submitRoleDialog">保存</el-button>
        <el-button v-if="!roleDialog.editingId && roleDialog.currentStep > 0" @click="roleDialog.currentStep--">上一步</el-button>
        <el-button v-if="!roleDialog.editingId && roleDialog.currentStep < 2" type="primary" @click="nextStep">下一步</el-button>
        <el-button v-if="!roleDialog.editingId && roleDialog.currentStep === 2" type="primary" @click="submitRoleDialog">保存</el-button>
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
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import {
  assignPermissions, createRole, deleteRole, getRoles, getRoleHierarchyStructure, updateRole,
  type HierarchyRole, type Permission, type Role,
} from '@/api/role'
import { PERMISSIONS, PERMISSION_GROUPS, permissionCategoryLabel, permissionDescription, permissionDisplayName, permissionTagType } from '@/constants/permissions'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()
const loading = ref(false)
const roles = ref<Role[]>([])
const hierarchyRoles = ref<HierarchyRole[]>([])

/** Group roles by level for hierarchy tree display */
const hierarchyByLevel = computed(() => {
  const map = new Map<number, { level: number; roles: HierarchyRole[] }>()
  for (const role of hierarchyRoles.value) {
    if (!map.has(role.level)) map.set(role.level, { level: role.level, roles: [] })
    map.get(role.level)!.roles.push(role)
  }
  return Array.from(map.values()).sort((a, b) => a.level - b.level)
})

/** Permission IDs that would be inherited from the selected role */
const inheritedPermissionIds = ref<Set<number>>(new Set())

function isPermissionInherited(permId: number): boolean {
  return inheritedPermissionIds.value.has(permId)
}

function levelCardClass(name: string): string {
  const map: Record<string, string> = {
    SUPER_ADMIN: 'super-admin', ADMIN: 'admin', MANAGER: 'manager',
    EDITOR: 'editor', REVIEWER: 'reviewer', VIEWER: 'viewer',
  }
  return map[name] || ''
}

/** Check if any existing role directly inherits from the selected inherited role(s) */
const hasSelectedChildren = computed(() => {
  if (roleDialog.selectedInheritedRoleIds.length === 0) return false
  return hierarchyRoles.value.some(hr =>
    hr.inherited_from.some(parent =>
      roleDialog.selectedInheritedRoleIds.includes(parent.id)
    )
  )
})

/** Get display names of roles that would be rewired (children of selected parent) */
function getChildNames(): string {
  const names = new Set<string>()
  for (const hr of hierarchyRoles.value) {
    for (const parent of hr.inherited_from) {
      if (roleDialog.selectedInheritedRoleIds.includes(parent.id)) {
        names.add(hr.display_name || hr.name)
      }
    }
  }
  return Array.from(names).join('、')
}

const roleDialog = reactive({
  visible: false,
  editingId: 0,
  currentStep: 0,
  selectedLevel: 0,
  selectedInheritedRoleIds: [] as number[],
  placement: 'parallel' as 'parallel' | 'insert',
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
    const [roleList, hierarchyList] = await Promise.all([getRoles(), getRoleHierarchyStructure()])
    roles.value = roleList
    hierarchyRoles.value = hierarchyList
  } finally {
    loading.value = false
  }
}

// When user selects inherited roles, compute merged inherited permission IDs
watch(() => roleDialog.selectedInheritedRoleIds, (newVal) => {
  if (!newVal || newVal.length === 0) {
    inheritedPermissionIds.value = new Set()
    roleDialog.form.permissionIds = []
    return
  }
  const permNames = new Set<string>()
  for (const roleId of newVal) {
    const selected = hierarchyRoles.value.find(r => r.id === roleId)
    if (selected) {
      selected.effective_permissions.forEach(p => permNames.add(p))
    }
  }
  const ids = PERMISSIONS.filter(p => permNames.has(p.name)).map(p => p.id)
  inheritedPermissionIds.value = new Set(ids)
  // Remove inherited perms from manual selection
  roleDialog.form.permissionIds = roleDialog.form.permissionIds.filter(
    id => !inheritedPermissionIds.value.has(id)
  )
})

// When level changes, reset inherited role selection
watch(() => roleDialog.selectedLevel, (level) => {
  if (!level) { roleDialog.selectedInheritedRoleIds = []; return }
  roleDialog.selectedInheritedRoleIds = []
  const group = hierarchyByLevel.value.find(g => g.level === level)
  if (group && group.roles.length === 1) {
    roleDialog.selectedInheritedRoleIds = [group.roles[0].id]
  }
})

function nextStep() {
  if (roleDialog.currentStep === 0) {
    if (!roleDialog.form.name.trim()) {
      ElMessage.warning('角色名不能为空')
      return
    }
  }
  if (roleDialog.currentStep === 1) {
    if (roleDialog.selectedInheritedRoleIds.length === 0) {
      ElMessage.warning('请至少选择一个要继承的角色')
      return
    }
  }
  roleDialog.currentStep++
}

function openCreateDialog() {
  roleDialog.visible = true
  roleDialog.editingId = 0
  roleDialog.currentStep = 0
  roleDialog.selectedLevel = 0
  roleDialog.selectedInheritedRoleIds = []
  roleDialog.placement = 'parallel'
  roleDialog.form.name = ''
  roleDialog.form.description = ''
  roleDialog.form.permissionIds = []
  inheritedPermissionIds.value = new Set()
}

function openEditDialog(role: Role) {
  roleDialog.visible = true
  roleDialog.editingId = role.id
  roleDialog.form.name = role.name
  roleDialog.form.description = role.description
  roleDialog.form.permissionIds = role.permissions.map((permission) => permission.id)
}

async function submitRoleDialog() {
  if (roleDialog.editingId) {
    if (!roleDialog.form.name.trim()) {
      ElMessage.warning('角色名不能为空')
      return
    }
    await updateRole(roleDialog.editingId, {
      name: roleDialog.form.name.trim(),
      description: roleDialog.form.description.trim(),
    })
  } else {
    if (!roleDialog.form.name.trim()) {
      ElMessage.warning('角色名不能为空')
      return
    }
    await createRole({
      name: roleDialog.form.name.trim(),
      description: roleDialog.form.description.trim(),
      permissionIds: roleDialog.form.permissionIds,
      inheritedRoleIds: roleDialog.selectedInheritedRoleIds,
      rewireChildren: roleDialog.placement === 'insert',
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
.h-level-branch {
  width: 100%;
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

/* ── Step Wizard ──────────────────────────────── */
.step-content {
  min-height: 280px;
}
.step-inner {
  padding: 8px 4px;
}

/* ── Wizard Hierarchy Selector ───────────────── */
.wizard-hierarchy {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.wizard-level-row {
  border: 1px solid #e1e9f0;
  border-radius: 8px;
  overflow: hidden;
}
.wizard-level-header {
  padding: 10px 14px;
  background: #f7fafc;
}
.wizard-level-header .el-radio {
  display: flex;
  align-items: center;
  width: 100%;
  height: auto;
  margin-right: 0;
}
.level-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 28px; height: 20px;
  padding: 0 8px;
  border-radius: 10px;
  font-size: 11px; font-weight: 700; color: #fff;
  margin-right: 10px;
}
.level-tag.l1 { background: #e74c3c; }
.level-tag.l2 { background: #e67e22; }
.level-tag.l3 { background: #2980b9; }
.level-tag.l4 { background: #27ae60; }
.level-tag.l5 { background: #95a5a6; }
.level-role-names {
  color: #213547;
  font-weight: 600;
  font-size: 14px;
}
.wizard-level-roles {
  padding: 8px 14px 12px 52px;
  border-top: 1px solid #eef2f6;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.wizard-level-roles .el-checkbox {
  display: flex;
  align-items: center;
  margin-right: 0;
  height: 32px;
}
.wizard-checkbox-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.role-desc {
  color: #909399;
  font-size: 12px;
}
.single-role-hint {
  color: #606266;
  font-size: 13px;
}

/* ── Placement selector ───────────────────────── */
.placement-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #e1e9f0;
}
.placement-radio-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}
.placement-radio-group .el-radio {
  width: 100%;
  height: auto;
  margin-right: 0;
  padding: 12px 16px;
}
.placement-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
  line-height: 1.4;
}
.placement-option strong {
  font-size: 14px;
  color: #213547;
}
.placement-desc {
  font-size: 12px;
  color: #909399;
}

/* ── Inherited permission styling ────────────────── */
.perm-hint {
  color: #909399;
  font-size: 13px;
  margin-bottom: 12px;
}
.hint-text {
  color: #909399;
  font-size: 13px;
  margin-bottom: 16px;
  line-height: 1.5;
}
.permission-check-item :deep(.is-inherited .el-checkbox__label) {
  color: #a0abb5;
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
