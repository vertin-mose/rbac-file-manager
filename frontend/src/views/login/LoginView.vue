<template>
  <div class="auth-shell">
    <section class="auth-hero">
      <p class="eyebrow">RBAC Document Manager</p>
      <h1>企业文档管理与协同平台</h1>
      <p class="hero-copy">
        登录后可按角色访问文件、审计和权限管理模块。
      </p>
    </section>

    <el-card class="auth-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div>
            <h2>登录</h2>
            <p>使用已有账号进入系统</p>
          </div>
        </div>
      </template>

      <el-form :model="form" label-position="top" @keyup.enter="handleLogin">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleLogin" :loading="loading" class="submit-button">
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="auth-footer">
        <span>还没有账号？</span>
        <el-button link type="primary" @click="router.push('/register')">立即注册</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/store/user'

const router = useRouter()
const userStore = useUserStore()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

async function handleLogin() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }

  loading.value = true
  try {
    await userStore.login(form)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch {
    ElMessage.error('登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(320px, 1.1fr) minmax(360px, 420px);
  align-items: stretch;
  background:
    radial-gradient(circle at top left, rgba(255, 214, 153, 0.35), transparent 28%),
    radial-gradient(circle at bottom right, rgba(28, 110, 164, 0.18), transparent 30%),
    linear-gradient(135deg, #f3ede2 0%, #e7eef5 45%, #d8e2ec 100%);
}

.auth-hero {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 72px;
  color: #16324f;
}

.eyebrow {
  margin: 0 0 12px;
  font-size: 13px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #9b5e2c;
}

.auth-hero h1 {
  margin: 0;
  font-size: 48px;
  line-height: 1.1;
}

.hero-copy {
  max-width: 460px;
  margin: 20px 0 0;
  font-size: 16px;
  line-height: 1.7;
  color: rgba(22, 50, 79, 0.78);
}

.auth-card {
  align-self: center;
  margin: 32px;
  border: none;
  border-radius: 24px;
}

.card-header h2 {
  margin: 0;
  font-size: 28px;
  color: #16324f;
}

.card-header p {
  margin: 8px 0 0;
  color: #6b7f95;
}

.submit-button {
  width: 100%;
  min-height: 44px;
}

.auth-footer {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 4px;
  color: #6b7f95;
}

@media (max-width: 960px) {
  .auth-shell {
    grid-template-columns: 1fr;
    padding: 24px;
  }

  .auth-hero {
    padding: 32px 8px 12px;
  }

  .auth-hero h1 {
    font-size: 34px;
  }

  .auth-card {
    margin: 0;
  }
}
</style>