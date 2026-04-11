<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'
import type { User } from '../types'

const users = ref<User[]>([])
const showModal = ref(false)

const form = ref({
  username: '',
  password: '',
  full_name: '',
  role: 'staff' as 'admin' | 'staff' | 'readonly',
})

async function loadUsers() {
  const res = await api.get('/users')
  users.value = res.data
}

onMounted(loadUsers)

async function save() {
  await api.post('/users', form.value)
  showModal.value = false
  await loadUsers()
}

async function toggleActive(user: User) {
  await api.patch(`/users/${user.id}`, { is_active: !user.is_active })
  await loadUsers()
}

const roleLabel: Record<string, string> = {
  admin: '管理員',
  staff: '前台人員',
  readonly: '唯讀',
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1>使用者管理</h1>
      <button class="btn btn-primary" @click="form = { username: '', password: '', full_name: '', role: 'staff' }; showModal = true">
        新增使用者
      </button>
    </div>

    <div class="card">
      <table>
        <thead>
          <tr>
            <th>帳號</th>
            <th>姓名</th>
            <th>角色</th>
            <th>狀態</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.username }}</td>
            <td>{{ u.full_name }}</td>
            <td>{{ roleLabel[u.role] }}</td>
            <td>
              <span :class="u.is_active ? 'badge badge-available' : 'badge badge-cancelled'">
                {{ u.is_active ? '啟用' : '停用' }}
              </span>
            </td>
            <td>
              <button class="btn btn-sm" :class="u.is_active ? 'btn-danger' : 'btn-success'" @click="toggleActive(u)">
                {{ u.is_active ? '停用' : '啟用' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <div class="modal-header"><h2>新增使用者</h2></div>
        <form @submit.prevent="save">
          <div class="form-group">
            <label>帳號</label>
            <input v-model="form.username" class="form-input" required />
          </div>
          <div class="form-group">
            <label>密碼</label>
            <input v-model="form.password" type="password" class="form-input" required />
          </div>
          <div class="form-group">
            <label>姓名</label>
            <input v-model="form.full_name" class="form-input" required />
          </div>
          <div class="form-group">
            <label>角色</label>
            <select v-model="form.role" class="form-input">
              <option value="admin">管理員</option>
              <option value="staff">前台人員</option>
              <option value="readonly">唯讀</option>
            </select>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-outline" @click="showModal = false">取消</button>
            <button type="submit" class="btn btn-primary">儲存</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
