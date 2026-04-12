<script setup lang="ts">
import { useAuthStore } from './stores/auth'
import { useRouter, useRoute } from 'vue-router'
import { computed } from 'vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const isSelfCheckIn = computed(() => route.path === '/self-checkin')

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div v-if="isSelfCheckIn">
    <router-view />
  </div>
  <div v-else-if="!auth.isLoggedIn">
    <router-view />
  </div>
  <div v-else class="app-layout">
    <aside class="sidebar">
      <div class="sidebar-title">Neo Hotel</div>
      <nav>
        <router-link to="/">Dashboard</router-link>
        <router-link to="/guests">旅客管理</router-link>
        <router-link to="/rooms">房間管理</router-link>
        <router-link to="/reservations">訂房管理</router-link>
        <router-link to="/checkin">報到 / 退房</router-link>
        <router-link to="/breakfast">早餐管理</router-link>
        <router-link to="/cleaning">清潔紀錄</router-link>
        <router-link v-if="auth.isAdmin" to="/users">使用者管理</router-link>
        <router-link to="/api-keys" v-if="auth.isAdmin">API Key</router-link>
      </nav>
    </aside>
    <div class="main-content">
      <header class="topbar">
        <span class="user-info">{{ auth.user?.full_name }} ({{ auth.user?.role }})</span>
        <button class="btn btn-outline btn-sm" @click="logout">登出</button>
      </header>
      <main class="page-content">
        <router-view />
      </main>
    </div>
  </div>
</template>
