<template>
  <div>
    <h1>文件管理</h1>

    <!-- 工具栏 — 根据角色显示不同按钮 -->
    <div style="margin: 16px 0; display: flex; gap: 8px;">
      <el-button
          v-if="userStore.hasPermission('doc:create')"
          type="primary"
          @click="handleCreate"
      >
        新建目录
      </el-button>
      <el-button
          v-if="userStore.hasPermission('doc:create')"
          type="success"
          @click="handleUpload"
      >
        上传文件
      </el-button>
    </div>

    <!-- 文件列表（占位） -->
    <el-empty v-if="!userStore.hasPermission('doc:read')" description="您没有查看文件的权限" />
    <el-empty v-else description="文件管理 - 即将推出" />

    <!-- 提示当前角色拥有的文件操作权限 -->
    <el-card style="margin-top: 20px">
      <template #header>
        <span>当前角色权限</span>
      </template>
      <div v-if="userStore.roles.length > 0">
        <el-tag
            v-if="userStore.hasPermission('doc:create')"
            size="small"
            style="margin: 2px"
            effect="plain"
        >创建文档</el-tag>
        <el-tag
            v-if="userStore.hasPermission('doc:update')"
            size="small"
            style="margin: 2px"
            effect="plain"
        >编辑文档</el-tag>
        <el-tag
            v-if="userStore.hasPermission('doc:delete')"
            size="small"
            style="margin: 2px"
            effect="plain"
        >删除文档</el-tag>
        <el-tag
            v-if="userStore.hasPermission('doc:review')"
            size="small"
            style="margin: 2px"
            effect="plain"
        >审核文档</el-tag>
        <el-tag
            v-if="userStore.hasPermission('doc:approve')"
            size="small"
            style="margin: 2px"
            effect="plain"
        >审批文档</el-tag>
        <el-tag
            v-if="userStore.hasPermission('doc:share')"
            size="small"
            style="margin: 2px"
            effect="plain"
        >共享文档</el-tag>
        <el-tag
            v-if="userStore.hasPermission('doc:comment')"
            size="small"
            style="margin: 2px"
            effect="plain"
        >评论文档</el-tag>
        <el-tag
            v-if="userStore.hasPermission('doc:export')"
            size="small"
            style="margin: 2px"
            effect="plain"
        >导出文档</el-tag>
        <el-tag
            v-if="userStore.hasPermission('doc:read') && !userStore.hasPermission('doc:create')"
            size="small"
            style="margin: 2px"
            type="info"
            effect="plain"
        >仅查看</el-tag>
      </div>
      <el-empty v-else description="暂无角色" :image-size="60" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { useUserStore } from '@/store/user'

const userStore = useUserStore()

function handleCreate() {
  // TODO: 创建目录对话框
}

function handleUpload() {
  // TODO: 上传文件对话框
}
</script>
