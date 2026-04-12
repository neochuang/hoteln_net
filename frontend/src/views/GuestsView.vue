<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { Guest } from '../types'

const auth = useAuthStore()
const guests = ref<Guest[]>([])
const search = ref('')
const showModal = ref(false)
const editing = ref<Guest | null>(null)

const form = ref({
  first_name: '',
  last_name: '',
  id_type: 'national_id' as const,
  id_number: '',
  phone: '',
  email: '',
  nationality: '台灣',
  notes: '',
})

async function loadGuests() {
  const params = search.value ? { q: search.value } : {}
  const res = await api.get('/guests', { params })
  guests.value = res.data
}

onMounted(loadGuests)

function openCreate() {
  editing.value = null
  form.value = { first_name: '', last_name: '', id_type: 'national_id', id_number: '', phone: '', email: '', nationality: '台灣', notes: '' }
  showModal.value = true
}

function openEdit(guest: Guest) {
  editing.value = guest
  form.value = {
    first_name: guest.first_name,
    last_name: guest.last_name,
    id_type: guest.id_type,
    id_number: guest.id_number,
    phone: guest.phone,
    email: guest.email || '',
    nationality: guest.nationality,
    notes: guest.notes || '',
  }
  showModal.value = true
}

async function save() {
  const data = { ...form.value, email: form.value.email || null, notes: form.value.notes || null }
  if (editing.value) {
    await api.patch(`/guests/${editing.value.id}`, data)
  } else {
    await api.post('/guests', data)
  }
  showModal.value = false
  await loadGuests()
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1>旅客管理</h1>
      <button v-if="auth.canEdit" class="btn btn-primary" @click="openCreate">新增旅客</button>
    </div>

    <div class="search-bar">
      <input v-model="search" class="form-input" placeholder="搜尋姓名、電話或證件號碼..." @input="loadGuests" />
    </div>

    <div class="card">
      <table>
        <thead>
          <tr>
            <th>姓名</th>
            <th>證件類型</th>
            <th>證件號碼</th>
            <th>電話</th>
            <th>國籍</th>
            <th v-if="auth.canEdit">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="g in guests" :key="g.id">
            <td>{{ g.last_name }}{{ g.first_name }}</td>
            <td>{{ g.id_type === 'national_id' ? '身分證' : g.id_type === 'passport' ? '護照' : '其他' }}</td>
            <td>{{ g.id_number }}</td>
            <td>{{ g.phone }}</td>
            <td>{{ g.nationality }}</td>
            <td v-if="auth.canEdit">
              <button class="btn btn-outline btn-sm" @click="openEdit(g)">編輯</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <div class="modal-header">
          <h2>{{ editing ? '編輯旅客' : '新增旅客' }}</h2>
        </div>
        <form @submit.prevent="save">
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px">
            <div class="form-group">
              <label>姓</label>
              <input v-model="form.last_name" class="form-input" required />
            </div>
            <div class="form-group">
              <label>名</label>
              <input v-model="form.first_name" class="form-input" required />
            </div>
          </div>
          <div class="form-group">
            <label>證件類型</label>
            <select v-model="form.id_type" class="form-input">
              <option value="national_id">身分證</option>
              <option value="passport">護照</option>
              <option value="other">其他</option>
            </select>
          </div>
          <div class="form-group">
            <label>證件號碼</label>
            <input v-model="form.id_number" class="form-input" required />
          </div>
          <div class="form-group">
            <label>電話</label>
            <input v-model="form.phone" class="form-input" required />
          </div>
          <div class="form-group">
            <label>Email</label>
            <input v-model="form.email" type="email" class="form-input" />
          </div>
          <div class="form-group">
            <label>國籍</label>
            <input v-model="form.nationality" class="form-input" required />
          </div>
          <div class="form-group">
            <label>備註</label>
            <input v-model="form.notes" class="form-input" />
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
