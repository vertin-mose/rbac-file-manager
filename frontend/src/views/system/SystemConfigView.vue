<template>
  <div>
    <h1>系统配置</h1>
    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <span>系统信息</span>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="系统版本">1.0.0</el-descriptions-item>
            <el-descriptions-item label="运行环境">Python FastAPI</el-descriptions-item>
            <el-descriptions-item label="数据库状态">
              <el-tag size="small" type="success">正常</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="文件存储">
              <el-tag size="small" type="success">MinIO 已就绪</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <span>系统备份</span>
          </template>
          <p style="color: #909399; margin-bottom: 16px;">系统备份与恢复功能</p>
          <el-button type="primary" disabled>创建备份</el-button>
          <el-button disabled>恢复</el-button>
          <p style="margin-top: 12px; font-size: 12px; color: #c0c4cc;">功能即将推出</p>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <span>安全策略</span>
          </template>
          <p style="color: #909399; margin-bottom: 16px;">密码策略、登录限制等安全配置</p>
          <el-button disabled>配置安全策略</el-button>
          <p style="margin-top: 12px; font-size: 12px; color: #c0c4cc;">功能即将推出</p>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
