<template>
  <div>
    <h1>总体数据</h1>
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="6">
        <el-card shadow="hover">
          <h3>文件总数</h3>
          <p style="font-size: 24px; color: #409EFF">--</p>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <h3>用户数</h3>
          <p style="font-size: 24px; color: #67C23A">--</p>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <h3>角色数</h3>
          <p style="font-size: 24px; color: #E6A23C">--</p>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <h3>已用存储</h3>
          <p style="font-size: 24px; color: #F56C6C">--</p>
        </el-card>
      </el-col>
    </el-row>
    <!--
      TODO: Add charts, recent activity, storage usage breakdown
      - File operation statistics (upload/download/delete counts)
      - Recent audit log entries
      - Storage usage by user/role
    -->
  </div>
</template>

<script setup lang="ts">
// TODO: Add data fetching and display logic
</script>
