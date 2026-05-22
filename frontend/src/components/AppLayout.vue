<template>
  <el-container style="height: 100vh">
    <!-- 侧边栏 -->
    <el-aside width="220px" style="background-color: #304156">
      <div class="logo-container">
        <h2 class="logo-text">文档管理系统</h2>
      </div>
      <el-menu
          :default-active="route.path"
          router
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409EFF"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Monitor /></el-icon>
          <span>总体数据</span>
        </el-menu-item>

        <el-menu-item index="/files">
          <el-icon><Folder /></el-icon>
          <span>文件管理</span>
        </el-menu-item>

        <el-menu-item
            v-if="userStore.highestLevel <= 2"
            index="/roles"
        >
          <el-icon><Setting /></el-icon>
          <span>角色管理</span>
        </el-menu-item>

        <el-menu-item
            v-if="userStore.highestLevel <= 3"
            index="/audit"
        >
          <el-icon><Document /></el-icon>
          <span>审计日志</span>
        </el-menu-item>

        <el-menu-item
            v-if="userStore.hasRole('SUPER_ADMIN')"
            index="/system-config"
        >
          <el-icon><Tools /></el-icon>
          <span>系统配置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container>
      <!-- 顶部栏 -->
      <el-header style="border-bottom: 1px solid #e6e6e6; display: flex; align-items: center; justify-content: flex-end; gap: 16px;">
        <el-tag :type="roleTagType" size="small" effect="dark" class="role-tag">
          {{ userStore.roleDisplayName }}
        </el-tag>
        <el-dropdown trigger="click">
          <span class="user-dropdown">
            {{ userStore.displayName || userStore.username }}
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item disabled style="font-size: 12px; color: #999;">
                角色：{{ userStore.roles.join(', ') }}
              </el-dropdown-item>
              <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>

      <!-- 页面内容 -->
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const roleTagType = computed(() => {
  if (userStore.highestLevel <= 2) return 'danger'
  if (userStore.highestLevel <= 3) return 'warning'
  if (userStore.highestLevel <= 4) return 'primary'
  return 'info'
})

function handleLogout() {
  userStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.logo-container {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo-text {
  color: #fff;
  font-size: 16px;
  white-space: nowrap;
}

.user-dropdown {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}

.role-tag {
  margin-right: auto;
}
</style>
