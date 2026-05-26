<template>
  <div class="dashboard-page">
    <section class="hero-card">
      <div>
        <p class="eyebrow">Overview</p>
        <h1>工作台总览</h1>
        <p class="hero-copy">根据当前账户的权限范围，快速了解系统资源与访问级别。</p>
      </div>
      <div class="hero-tags">
        <el-tag effect="dark" type="primary">用户：{{ userStore.username }}</el-tag>
        <el-tag effect="plain">角色：{{ userStore.roleDisplayName || '未分配' }}</el-tag>
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
        <div class="tag-flow">
          <el-tag v-for="permission in userStore.permissions" :key="permission" effect="plain">
            {{ permission }}
          </el-tag>
          <el-empty v-if="userStore.permissions.length === 0" description="暂无权限数据" :image-size="60" />
        </div>
      </el-card>

      <el-card class="info-card" shadow="never">
        <template #header>
          <div class="card-header">
            <div>
              <h2>角色信息</h2>
              <p>当前登录身份与访问层级。</p>
            </div>
          </div>
        </template>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="用户名">
            {{ userStore.username }}
          </el-descriptions-item>
          <el-descriptions-item label="用户 ID">
            {{ userStore.userId || '--' }}
          </el-descriptions-item>
          <el-descriptions-item label="角色列表">
            {{ userStore.roles.join(', ') || '--' }}
          </el-descriptions-item>
          <el-descriptions-item label="最高级别">
            L{{ userStore.highestLevel === 99 ? '--' : userStore.highestLevel }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useUserStore } from '@/store/user'

const userStore = useUserStore()

const cards = computed(() => [
  {
    title: '当前权限数',
    value: userStore.permissions.length,
    hint: '来自角色及继承权限',
  },
  {
    title: '拥有角色数',
    value: userStore.roles.length,
    hint: '可同时包含多个角色',
  },
  {
    title: '访问层级',
    value: userStore.highestLevel === 99 ? '--' : `L${userStore.highestLevel}`,
    hint: '数字越小权限越高',
  },
  {
    title: '文档操作能力',
    value: userStore.hasPermission('doc:create') ? '可编辑' : '只读',
    hint: userStore.hasPermission('doc:approve') ? '含审批能力' : '无审批能力',
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
  padding: 28px 32px;
  border-radius: 24px;
  background:
    radial-gradient(circle at top right, rgba(255, 214, 153, 0.18), transparent 30%),
    linear-gradient(135deg, #23465d 0%, #2d6078 50%, #3b7d96 100%);
  color: #f7fafc;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(255, 224, 174, 0.88);
}

.hero-card h1 {
  margin: 0;
  font-size: 34px;
}

.hero-copy {
  margin: 10px 0 0;
  line-height: 1.7;
  color: rgba(247, 250, 252, 0.82);
}

.hero-tags {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

.metric-card,
.info-card {
  border-radius: 20px;
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

@media (max-width: 960px) {
  .hero-card,
  .info-grid {
    grid-template-columns: 1fr;
    flex-direction: column;
  }

  .hero-tags {
    align-items: flex-start;
  }
}
</style>
