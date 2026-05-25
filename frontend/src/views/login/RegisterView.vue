<template>
  <div class="auth-shell">
    <section class="auth-hero">
      <p class="eyebrow">New Account</p>
      <h1>创建新账号</h1>
      <p class="hero-copy">
        注册成功后即可返回登录页，使用新账号进入系统。
      </p>
    </section>

    <el-card class="auth-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div>
            <h2>注册</h2>
            <p>填写基础信息创建用户</p>
          </div>
        </div>
      </template>

      <el-form :model="form" label-position="top" @keyup.enter="handleRegister">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="显示名称">
          <el-input v-model="form.displayName" placeholder="请输入显示名称" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="form.email" placeholder="选填，用于联系" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="form.confirmPassword" type="password" show-password placeholder="请再次输入密码" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" class="submit-button" @click="handleRegister">
            注册
          </el-button>
        </el-form-item>
      </el-form>

      <div class="auth-footer">
        <span>已经有账号？</span>
        <el-button link type="primary" @click="router.push('/login')">返回登录</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { register } from '@/api/auth'

const router = useRouter()
const loading = ref(false)

const form = reactive({
  username: '',
  displayName: '',
  email: '',
  password: '',
  confirmPassword: '',
})

async function handleRegister() {
  if (!form.username || !form.password) {
    ElMessage.warning('用户名和密码不能为空')
    return
  }
  if (form.password !== form.confirmPassword) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }

  loading.value = true
  try {
    await register({
      username: form.username,
      password: form.password,
      displayName: form.displayName || undefined,
      email: form.email || undefined,
    })
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch {
    ElMessage.error('注册失败，请检查输入信息')
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
    radial-gradient(circle at top left, rgba(207, 233, 168, 0.35), transparent 28%),
    radial-gradient(circle at bottom right, rgba(24, 92, 140, 0.18), transparent 30%),
    linear-gradient(135deg, #eef5df 0%, #e2ecf3 46%, #d1dde8 100%);
}

.auth-hero {
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 72px;
  color: #17354d;
}

.eyebrow {
  margin: 0 0 12px;
  font-size: 13px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: #547b2c;
}

.auth-hero h1 {
  margin: 0;
  font-size: 48px;
  line-height: 1.1;
}

.hero-copy {
  max-width: 440px;
  margin: 20px 0 0;
  font-size: 16px;
  line-height: 1.7;
  color: rgba(23, 53, 77, 0.76);
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
  color: #17354d;
}

.card-header p {
  margin: 8px 0 0;
  color: #68829a;
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
  color: #68829a;
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
