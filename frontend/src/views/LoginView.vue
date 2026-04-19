<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push(auth.homeRoute)
  } catch {
    error.value = '帳號或密碼錯誤'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h1>Grand Hilai</h1>
      <p class="subtitle">旅客報到系統</p>
      <div v-if="error" class="error-msg">{{ error }}</div>
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>帳號</label>
          <input v-model="username" class="form-input" placeholder="請輸入帳號" required />
        </div>
        <div class="form-group">
          <label>密碼</label>
          <input v-model="password" type="password" class="form-input" placeholder="請輸入密碼" required />
        </div>
        <button class="btn btn-primary" style="width: 100%; justify-content: center; margin-top: 8px" :disabled="loading">
          {{ loading ? '登入中...' : '登入' }}
        </button>
      </form>
    </div>
  </div>
</template>
