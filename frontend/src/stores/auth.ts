import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/client'
import type { User } from '../types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const isLoggedIn = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const canEdit = computed(() => user.value?.role === 'admin' || user.value?.role === 'staff')
  const isCleaner = computed(() => user.value?.role === 'cleaner')
  const canAccessHousekeeping = computed(
    () => user.value?.role === 'admin' || user.value?.role === 'staff' || user.value?.role === 'cleaner'
  )
  const canAccessAdminArea = computed(
    () => user.value?.role === 'admin' || user.value?.role === 'staff'
  )
  const homeRoute = computed(() => (isCleaner.value ? '/cleaner-tasks' : '/'))

  async function login(username: string, password: string) {
    const res = await api.post('/auth/login', { username, password })
    localStorage.setItem('access_token', res.data.access_token)
    localStorage.setItem('refresh_token', res.data.refresh_token)
    await fetchUser()
  }

  async function fetchUser() {
    try {
      const res = await api.get('/auth/me')
      user.value = res.data
    } catch {
      user.value = null
    }
  }

  function logout() {
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  async function init() {
    if (localStorage.getItem('access_token')) {
      await fetchUser()
    }
  }

  return {
    user,
    isLoggedIn,
    isAdmin,
    canEdit,
    isCleaner,
    canAccessHousekeeping,
    canAccessAdminArea,
    homeRoute,
    login,
    fetchUser,
    logout,
    init,
  }
})
