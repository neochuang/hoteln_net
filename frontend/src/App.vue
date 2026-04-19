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
      <div class="sidebar-title">Grand Hilai</div>
      <nav>
        <router-link to="/" v-if="auth.canAccessAdminArea">Dashboard</router-link>
        <router-link to="/guests" v-if="auth.canAccessAdminArea">旅客管理</router-link>
        <router-link to="/rooms" v-if="auth.canAccessAdminArea">房間管理</router-link>
        <router-link to="/reservations" v-if="auth.canAccessAdminArea">訂房管理</router-link>
        <router-link to="/checkin" v-if="auth.canEdit">報到 / 退房</router-link>
        <router-link to="/breakfast" v-if="auth.canEdit">早餐管理</router-link>
        <router-link to="/housekeeping" v-if="auth.canAccessHousekeeping">房務清潔</router-link>
        <router-link to="/users" v-if="auth.isAdmin">使用者管理</router-link>
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
