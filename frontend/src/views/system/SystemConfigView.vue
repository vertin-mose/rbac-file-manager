<template>
  <div class="system-page">
    <section class="page-hero">
      <div>
        <p class="eyebrow">System Center</p>
        <h1>系统配置</h1>
        <p class="hero-copy">集中查看运行状态、存储能力和安全配置入口。</p>
      </div>
      <el-tag type="success" effect="plain" size="large">运行正常</el-tag>
    </section>

    <div class="system-grid">
      <el-card class="system-card" shadow="never">
        <div class="system-card__header">
          <span class="system-card__icon system-card__icon--info">
            <el-icon><Monitor /></el-icon>
          </span>
          <div>
            <h2>系统信息</h2>
            <p>当前服务与存储组件状态</p>
          </div>
        </div>

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

      <el-card class="system-card" shadow="never">
        <div class="system-card__header">
          <span class="system-card__icon system-card__icon--backup">
            <el-icon><DataLine /></el-icon>
          </span>
          <div>
            <h2>系统备份</h2>
            <p>备份与恢复能力规划中</p>
          </div>
        </div>

        <div class="coming-soon">
          <strong>即将推出</strong>
          <span>后续可在此创建备份、查看备份记录并执行恢复。</span>
        </div>
        <div class="button-row">
          <el-button type="primary" disabled>创建备份</el-button>
          <el-button disabled>恢复</el-button>
        </div>
      </el-card>

      <el-card class="system-card" shadow="never">
        <div class="system-card__header">
          <span class="system-card__icon system-card__icon--security">
            <el-icon><Lock /></el-icon>
          </span>
          <div>
            <h2>安全策略</h2>
            <p>密码策略、登录限制与访问控制</p>
          </div>
        </div>

        <div class="policy-list">
          <div>
            <span>密码策略</span>
            <el-tag size="small" type="success" effect="plain">已启用</el-tag>
          </div>
          <div>
            <span>密码复杂度要求</span>
            <span class="policy-detail">最少 8 位，含大小写字母和数字</span>
          </div>
          <div>
            <span>登录限制</span>
            <el-tag size="small" type="success" effect="plain">已启用</el-tag>
          </div>
          <div>
            <span>账户锁定机制</span>
            <span class="policy-detail">连续 5 次失败后锁定 15 分钟</span>
          </div>
          <div>
            <span>安全响应头</span>
            <el-tag size="small" type="success" effect="plain">已启用</el-tag>
          </div>
          <div>
            <span>HTTP 安全头</span>
            <span class="policy-detail">X-Frame-Options / CSP / HSTS 等</span>
          </div>
          <div>
            <span>异常告警</span>
            <el-tag size="small" type="info" effect="plain">待配置</el-tag>
          </div>
        </div>
        <el-button disabled>配置安全策略</el-button>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { DataLine, Lock, Monitor } from '@element-plus/icons-vue'
</script>

<style scoped>
.system-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.page-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 22px 24px;
  border: 1px solid #dce6ee;
  border-radius: 12px;
  background: linear-gradient(135deg, #ffffff 0%, #eef8f4 48%, #f7f3ea 100%);
  color: #1f3448;
}

.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #18746b;
}

.page-hero h1 {
  margin: 0;
  font-size: 34px;
}

.hero-copy {
  margin: 10px 0 0;
  color: #647789;
  line-height: 1.7;
}

.system-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
}

.system-card {
  border-radius: 8px;
}

.system-card__header {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  margin-bottom: 18px;
}

.system-card__header h2 {
  margin: 0;
  color: #1f3448;
  font-size: 18px;
}

.system-card__header p {
  margin: 6px 0 0;
  color: #728293;
}

.system-card__icon {
  display: inline-grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 8px;
  font-size: 18px;
}

.system-card__icon--info {
  color: #1f6fba;
  background: #eaf3ff;
}

.system-card__icon--backup {
  color: #9a5b18;
  background: #fff4e5;
}

.system-card__icon--security {
  color: #18746b;
  background: #e8f6f3;
}

.coming-soon {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 16px;
  padding: 14px;
  border-radius: 8px;
  background: #f7fafc;
  color: #647789;
}

.coming-soon strong {
  color: #1f3448;
}

.button-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.policy-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}

.policy-list div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #f7fafc;
}

.policy-detail {
  color: #8496a6;
  font-size: 12px;
  white-space: nowrap;
}

@media (max-width: 1120px) {
  .system-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .page-hero {
    flex-direction: column;
  }
}
</style>
