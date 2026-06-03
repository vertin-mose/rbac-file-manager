<template>
  <div class="users-page">
    <section class="page-hero">
      <div>
        <p class="eyebrow">User Center</p>
        <h1>用户管理</h1>
        <p class="hero-copy">查看系统用户列表，为用户分配角色。</p>
      </div>
      <div class="hero-actions">
        <el-button :loading="loading" @click="loadData">刷新</el-button>
      </div>
    </section>

    <el-card class="table-card" shadow="never">
      <el-table :data="users" v-loading="loading" row-key="id" stripe>
        <el-table-column label="ID" prop="id" width="80" />
        <el-table-column label="用户名" prop="username" min-width="140" />
        <el-table-column label="显示名称" min-width="140">
          <template #default="{ row }">
            {{ row.display_name || '--' }}
          </template>
        </el-table-column>
        <el-table-column label="邮箱" min-width="180">
          <template #default="{ row }">
            {{ row.email || '--' }}
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
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              @click="openAssignDialog(row)"
            >
              分配角色
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

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
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { listUsers, getRoles, assignUserRoles, getUserInfo, type UserBasic } from '@/api/role'

const loading = ref(false)
const assignLoading = ref(false)
const users = ref<(UserBasic & { roles?: { id: number; name: string }[] })[]>([])
const allRoles = ref<{ id: number; name: string; description: string }[]>([])

const assignDialog = reactive({
  visible: false,
  userId: 0,
  username: '',
  selectedRoleIds: [] as number[],
})

async function loadData() {
  loading.value = true
  try {
    const [userList, roleList] = await Promise.all([listUsers(), getRoles()])
    allRoles.value = roleList.map(r => ({ id: r.id, name: r.name, description: r.description }))
    // Fetch role info for each user
    const enriched = await Promise.all(
      userList.map(async (u) => {
        try {
          const info = await getUserInfo(u.id)
          return { ...u, roles: info.roles }
        } catch {
          return { ...u, roles: [] }
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

function roleTagType(name: string): '' | 'danger' | 'warning' | 'primary' | 'info' | 'success' {
  const map: Record<string, '' | 'danger' | 'warning' | 'primary' | 'info' | 'success'> = {
    SUPER_ADMIN: 'danger', ADMIN: 'danger',
    MANAGER: 'warning', EDITOR: 'primary', REVIEWER: 'primary', VIEWER: 'info',
  }
  return map[name] ?? ''
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
</style>
