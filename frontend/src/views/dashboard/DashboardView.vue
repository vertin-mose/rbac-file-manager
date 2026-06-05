<template>
  <div class="dashboard-page">
    <section class="hero-card">
      <div>
        <p class="eyebrow">Overview</p>
        <h1>工作台总览</h1>
        <p class="hero-copy">根据当前账户的权限范围，快速了解系统资源与访问级别。</p>
      </div>
      <div class="hero-meter">
        <span>权限覆盖</span>
        <strong>{{ permissionCoverageTotal }}%</strong>
        <el-progress :percentage="permissionCoverageTotal" :show-text="false" :stroke-width="8" />
      </div>
    </section>

    <el-row :gutter="20">
      <el-col v-for="card in cards" :key="card.title" :xs="24" :sm="12" :xl="6">
        <el-card class="metric-card" shadow="hover">
          <p class="metric-title">{{ card.title }}</p>
          <strong class="metric-value">{{ card.value }}</strong>
          <span class="metric-hint">{{ card.hint }}</span>
        </el-card>
      </el-col>
    </el-row>

    <div class="info-grid">
      <el-card class="info-card" shadow="never">
        <template #header>
          <div class="card-header">
            <div>
              <h2>权限概览</h2>
              <p>当前账号实际可执行的关键操作。</p>
            </div>
          </div>
        </template>
        <div class="permission-overview" v-if="effectivePermissions.length > 0">
          <div class="coverage-list">
            <div v-for="group in permissionCoverage" :key="group.category" class="coverage-row">
              <span>{{ group.shortLabel }}</span>
              <el-progress :percentage="group.percent" :show-text="false" :stroke-width="8" />
              <strong>{{ group.count }}/{{ group.total }}</strong>
            </div>
          </div>

          <div class="permission-list">
            <section v-for="group in visiblePermissionGroups" :key="group.category" class="permission-group">
              <div class="permission-group__header">
                <span>{{ group.label }}</span>
                <el-tag size="small" :type="group.tagType" effect="plain">{{ group.items.length }} 项</el-tag>
              </div>
              <div class="tag-flow">
                <el-tag
                  v-for="permission in group.items"
                  :key="permission.name"
                  :type="permission.tagType"
                  effect="plain"
                  :title="permission.description"
                >
                  {{ permission.displayName }}
                </el-tag>
              </div>
            </section>
          </div>
        </div>
        <el-empty v-else description="暂无权限数据" :image-size="60" />
      </el-card>

      <el-card class="info-card" shadow="never">
        <template #header>
          <div class="card-header">
            <div>
              <h2>用户信息</h2>
              <p>当前登录账户详情，可修改个人资料与密码。</p>
            </div>
            <el-button type="primary" size="small" @click="openProfileDialog">编辑资料</el-button>
          </div>
        </template>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="用户名">
            {{ userStore.username }}
          </el-descriptions-item>
          <el-descriptions-item label="显示名称">
            {{ userStore.displayName || '--' }}
          </el-descriptions-item>
          <el-descriptions-item label="用户 ID">
            {{ userStore.userId || '--' }}
          </el-descriptions-item>
          <el-descriptions-item label="角色列表">
            {{ roleDisplayNames || '--' }}
          </el-descriptions-item>
          <el-descriptions-item label="最高级别">
            L{{ userStore.highestLevel === 99 ? '--' : userStore.highestLevel }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>
    </div>

    <!-- Profile Edit Dialog -->
    <el-dialog v-model="profileDialog.visible" title="编辑个人资料" width="480px">
      <el-form label-position="top">
        <el-form-item label="显示名称">
          <el-input v-model="profileDialog.form.displayName" placeholder="选填" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="profileDialog.form.email" placeholder="选填" />
        </el-form-item>
        <el-divider>修改密码（可选）</el-divider>
        <el-form-item label="旧密码">
          <el-input v-model="profileDialog.form.oldPassword" type="password" placeholder="输入旧密码" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="profileDialog.form.newPassword" type="password" placeholder="输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="profileDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="profileSaving" @click="submitProfile">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/user'
import { PERMISSIONS, PERMISSION_CATEGORY_META, PERMISSION_GROUPS, resolvePermission } from '@/constants/permissions'
import { getRoles } from '@/api/role'
import { getFiles } from '@/api/file'
import { getAuditLogs } from '@/api/audit'
import { updateProfile } from '@/api/auth'

const userStore = useUserStore()

// Real-time stats from backend
const totalRoles = ref(0)
const totalFiles = ref(0)
const totalAuditLogs = ref(0)
const statsLoading = ref(false)

async function loadStats() {
  statsLoading.value = true
  try {
    if (userStore.hasPermission('role:read')) {
      const roles = await getRoles()
      totalRoles.value = roles.length
    }
    if (userStore.hasPermission('doc:read')) {
      const files = await getFiles(0)
      totalFiles.value = files.length
    }
    if (userStore.hasPermission('audit:read')) {
      const logs = await getAuditLogs({ page: 1, size: 1 })
      totalAuditLogs.value = logs.total
    }
  } catch {
    // Silently ignore — stats are supplementary
  } finally {
    statsLoading.value = false
  }
}

const profileSaving = ref(false)
const profileDialog = reactive({
  visible: false,
  form: {
    displayName: '',
    email: '',
    oldPassword: '',
    newPassword: '',
  },
})

function openProfileDialog() {
  profileDialog.form.displayName = userStore.displayName || ''
  profileDialog.form.email = ''
  profileDialog.form.oldPassword = ''
  profileDialog.form.newPassword = ''
  profileDialog.visible = true
}

async function submitProfile() {
  const payload: any = {}
  if (profileDialog.form.displayName !== userStore.displayName) {
    payload.display_name = profileDialog.form.displayName.trim() || undefined
  }
  if (profileDialog.form.email) {
    payload.email = profileDialog.form.email.trim()
  }
  if (profileDialog.form.oldPassword && profileDialog.form.newPassword) {
    payload.old_password = profileDialog.form.oldPassword
    payload.new_password = profileDialog.form.newPassword
  } else if (profileDialog.form.oldPassword || profileDialog.form.newPassword) {
    ElMessage.warning('请同时填写旧密码和新密码')
    return
  }
  if (Object.keys(payload).length === 0) {
    ElMessage.warning('没有需要修改的内容')
    return
  }
  profileSaving.value = true
  try {
    await updateProfile(payload)
    ElMessage.success('个人资料已更新，重新登录后生效')
    profileDialog.visible = false
    // Refresh displayName in store
    if (payload.display_name) {
      localStorage.setItem('displayName', payload.display_name)
      userStore.displayName = payload.display_name
    }
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.response?.data?.message || '更新失败'
    ElMessage.error(msg)
  } finally {
    profileSaving.value = false
  }
}

onMounted(loadStats)

const effectivePermissions = computed(() =>
  Array.from(new Set(userStore.permissions)).map((permission) => resolvePermission(permission)),
)

const permissionGroups = computed(() =>
  PERMISSION_GROUPS.map((category) => {
    const meta = PERMISSION_CATEGORY_META[category]
    const total = PERMISSIONS.filter((permission) => permission.category === category).length
    const items = effectivePermissions.value.filter((permission) => permission.category === category)
    return {
      category,
      label: meta.label,
      shortLabel: meta.shortLabel,
      tagType: meta.tagType,
      total,
      items,
    }
  }),
)

const visiblePermissionGroups = computed(() => permissionGroups.value.filter((group) => group.items.length > 0))

const roleDisplayNames = computed(() => {
  if (userStore.roleInfo.length > 0) {
    return userStore.roleInfo.map((role) => role.display_name || role.name).join('、')
  }
  return userStore.roles.join('、')
})

const permissionCoverage = computed(() =>
  permissionGroups.value.map((group) => ({
    category: group.category,
    shortLabel: group.shortLabel,
    count: group.items.length,
    total: group.total,
    percent: group.total ? Math.round((group.items.length / group.total) * 100) : 0,
  })),
)

const permissionCoverageTotal = computed(() => {
  const knownPermissions = new Set(PERMISSIONS.map((permission) => permission.name))
  const matchedCount = effectivePermissions.value.filter((permission) => knownPermissions.has(permission.name)).length
  return Math.round((matchedCount / PERMISSIONS.length) * 100)
})

const cards = computed(() => [
  {
    title: '当前权限数',
    value: effectivePermissions.value.length,
    hint: '来自角色及继承权限',
  },
  {
    title: '系统角色数',
    value: totalRoles.value || userStore.roles.length,
    hint: userStore.hasPermission('role:read') ? '实时数据' : '可见角色',
  },
  {
    title: '访问层级',
    value: userStore.highestLevel === 99 ? '--' : `L${userStore.highestLevel}`,
    hint: '数字越小权限越高',
  },
  {
    title: userStore.hasPermission('audit:read') ? '审计日志总数' : '文档操作能力',
    value: userStore.hasPermission('audit:read')
      ? totalAuditLogs.value
      : (userStore.hasPermission('doc:create') ? '可编辑' : '只读'),
    hint: userStore.hasPermission('audit:read')
      ? '系统全部操作记录'
      : (userStore.hasPermission('doc:approve') ? '含审批能力' : '无审批能力'),
  },
])
</script>

<style scoped>
.dashboard-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hero-card {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  padding: 22px 24px;
  border: 1px solid #dce6ee;
  border-radius: 12px;
  background: linear-gradient(135deg, #ffffff 0%, #eef6ff 54%, #f8f4e8 100%);
  color: #1f3448;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #2f7d73;
}

.hero-card h1 {
  margin: 0;
  font-size: 34px;
}

.hero-copy {
  margin: 10px 0 0;
  line-height: 1.7;
  color: #647789;
}

.hero-meter {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 8px;
  min-width: 180px;
  padding: 14px 16px;
  border: 1px solid rgba(47, 125, 115, 0.18);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.74);
}

.hero-meter span {
  color: #66788a;
  font-size: 13px;
}

.hero-meter strong {
  color: #1f3448;
  font-size: 28px;
}

.metric-card,
.info-card {
  border-radius: 8px;
}

.metric-card {
  min-height: 156px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.metric-title {
  margin: 0;
  color: #6f8190;
}

.metric-value {
  font-size: 34px;
  color: #20384b;
}

.metric-hint {
  color: #8a99a7;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.card-header h2 {
  margin: 0;
}

.card-header p {
  margin: 6px 0 0;
  color: #7c8b99;
}

.tag-flow {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.permission-overview {
  display: grid;
  grid-template-columns: minmax(220px, 0.72fr) minmax(0, 1fr);
  gap: 18px;
}

.coverage-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
  border-radius: 8px;
  background: #f6f9fc;
}

.coverage-row {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) 48px;
  align-items: center;
  gap: 10px;
  color: #506171;
  font-size: 13px;
}

.coverage-row strong {
  text-align: right;
  color: #20384b;
  font-weight: 700;
}

.permission-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.permission-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.permission-group__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: #20384b;
  font-weight: 700;
}

@media (max-width: 960px) {
  .hero-card,
  .info-grid {
    grid-template-columns: 1fr;
    flex-direction: column;
  }

  .hero-meter {
    min-width: 100%;
  }

  .permission-overview {
    grid-template-columns: 1fr;
  }
}
</style>
