<template>
  <el-container class="layout-shell">
    <el-aside width="248px" class="layout-aside">
      <div class="brand-block">
        <p class="brand-mark">RBAC</p>
        <h2>文档管理系统</h2>
      </div>

      <el-menu
        :default-active="route.path"
        router
        class="layout-menu"
        background-color="transparent"
        text-color="#dbe6ef"
        active-text-color="#f8d694"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Monitor /></el-icon>
          <span>总体数据</span>
        </el-menu-item>

        <el-menu-item index="/files">
          <el-icon><Folder /></el-icon>
          <span>文件管理</span>
        </el-menu-item>

        <el-menu-item v-if="userStore.highestLevel <= 2" index="/roles">
          <el-icon><Setting /></el-icon>
          <span>角色管理</span>
        </el-menu-item>

        <el-menu-item v-if="userStore.highestLevel <= 3" index="/audit">
          <el-icon><Document /></el-icon>
          <span>审计日志</span>
        </el-menu-item>

        <el-menu-item v-if="userStore.hasRole('SUPER_ADMIN')" index="/system-config">
          <el-icon><Tools /></el-icon>
          <span>系统配置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="layout-header">
        <div class="header-intro">
          <h1>{{ currentTitle }}</h1>
          <p>基于角色权限控制的文档协作平台</p>
        </div>

        <div class="header-actions">
          <el-tag :type="roleTagType" size="large" effect="dark" round>
            {{ userStore.roleDisplayName || '未分配角色' }}
          </el-tag>
          <el-dropdown trigger="click">
            <span class="user-dropdown">
              {{ userStore.displayName || userStore.username }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item disabled>
                  当前角色：{{ userStore.roles.join(', ') || '无' }}
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="layout-main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { logout as apiLogout } from '@/api/auth'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const roleTagType = computed(() => {
  if (userStore.highestLevel <= 2) return 'danger'
  if (userStore.highestLevel <= 3) return 'warning'
  if (userStore.highestLevel <= 4) return 'primary'
  return 'info'
})

const currentTitle = computed(() => {
  const map: Record<string, string> = {
    '/dashboard': '总体数据',
    '/files': '文件管理',
    '/roles': '角色管理',
    '/audit': '审计日志',
    '/system-config': '系统配置',
  }
  return map[route.path] || '文档管理系统'
})

async function handleLogout() {
  await apiLogout()
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.layout-shell {
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(180deg, #eff4f7 0%, #e6edf3 100%);
}

.el-container:last-child {
  height: 100vh;
  overflow: hidden;
}

.layout-aside {
  padding: 20px 16px;
  background:
    radial-gradient(circle at top left, rgba(244, 204, 116, 0.18), transparent 24%),
    linear-gradient(180deg, #14324a 0%, #1d4860 48%, #28586d 100%);
  color: #fff;
  height: 100vh;
  overflow-y: auto;
  position: sticky;
  top: 0;
}

.brand-block {
  padding: 16px 18px 22px;
}

.brand-mark {
  margin: 0 0 6px;
  font-size: 12px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: rgba(248, 214, 148, 0.82);
}

.brand-block h2 {
  margin: 0;
  font-size: 24px;
  line-height: 1.2;
}

.layout-menu {
  border: none;
}

.layout-menu :deep(.el-menu-item) {
  margin: 6px 0;
  border-radius: 14px;
}

.layout-menu :deep(.el-menu-item.is-active) {
  background: rgba(255, 255, 255, 0.08);
}

.layout-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  min-height: 84px;
  padding: 16px 28px;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(18px);
  border-bottom: 1px solid rgba(20, 50, 74, 0.08);
}

.header-intro h1 {
  margin: 0;
  font-size: 26px;
  color: #1e3447;
}

.header-intro p {
  margin: 6px 0 0;
  color: #718293;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-dropdown {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 14px;
  border-radius: 999px;
  background: #fff;
  cursor: pointer;
  color: #1e3447;
}

.layout-main {
  padding: 24px 28px;
  overflow-y: auto;
  height: calc(100vh - 84px);
}

@media (max-width: 960px) {
  .layout-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
