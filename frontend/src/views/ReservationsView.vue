<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { Reservation, Guest, RoomType } from '../types'

const auth = useAuthStore()
const reservations = ref<Reservation[]>([])
const guests = ref<Guest[]>([])
const roomTypes = ref<RoomType[]>([])
const statusFilter = ref('')
const showModal = ref(false)

const form = ref({
  guest_id: '',
  room_type_id: '',
  check_in_date: '',
  check_out_date: '',
  num_guests: 1,
  includes_breakfast: false,
  breakfast_guests: 0,
  total_price: 0,
  notes: '',
})

async function loadData() {
  const params: any = {}
  if (statusFilter.value) params.status = statusFilter.value
  const [resRes, guestsRes, typesRes] = await Promise.all([
    api.get('/reservations', { params }),
    api.get('/guests'),
    api.get('/rooms/types'),
  ])
  reservations.value = resRes.data
  guests.value = guestsRes.data
  roomTypes.value = typesRes.data
}

onMounted(loadData)

function guestName(id: string) {
  const g = guests.value.find(g => g.id === id)
  return g ? `${g.last_name}${g.first_name}` : '-'
}

function typeName(id: string) {
  return roomTypes.value.find(t => t.id === id)?.name || '-'
}

function openCreate() {
  form.value = {
    guest_id: guests.value[0]?.id || '',
    room_type_id: roomTypes.value[0]?.id || '',
    check_in_date: '',
    check_out_date: '',
    num_guests: 1,
    includes_breakfast: false,
    breakfast_guests: 0,
    total_price: 0,
    notes: '',
  }
  showModal.value = true
}

async function save() {
  await api.post('/reservations', { ...form.value, notes: form.value.notes || null })
  showModal.value = false
  await loadData()
}

async function cancel(id: string) {
  if (!confirm('確定要取消此訂房嗎？')) return
  await api.post(`/reservations/${id}/cancel`)
  await loadData()
}

const statusLabel: Record<string, string> = {
  confirmed: '已確認',
  checked_in: '已入住',
  checked_out: '已退房',
  cancelled: '已取消',
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1>訂房管理</h1>
      <button v-if="auth.canEdit" class="btn btn-primary" @click="openCreate">新增訂房</button>
    </div>

    <div class="search-bar">
      <select v-model="statusFilter" class="form-input" style="width: 200px" @change="loadData">
        <option value="">全部狀態</option>
        <option value="confirmed">已確認</option>
        <option value="checked_in">已入住</option>
        <option value="checked_out">已退房</option>
        <option value="cancelled">已取消</option>
      </select>
    </div>

    <div class="card">
      <table>
        <thead>
          <tr>
            <th>旅客</th>
            <th>房型</th>
            <th>入住日期</th>
            <th>退房日期</th>
            <th>人數</th>
            <th>早餐</th>
            <th>金額</th>
            <th>狀態</th>
            <th v-if="auth.canEdit">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in reservations" :key="r.id">
            <td>{{ guestName(r.guest_id) }}</td>
            <td>{{ typeName(r.room_type_id) }}</td>
            <td>{{ r.check_in_date }}</td>
            <td>{{ r.check_out_date }}</td>
            <td>{{ r.num_guests }}</td>
            <td>{{ r.includes_breakfast ? `${r.breakfast_guests}人` : '無' }}</td>
            <td>NT$ {{ r.total_price }}</td>
            <td><span :class="'badge badge-' + r.status">{{ statusLabel[r.status] }}</span></td>
            <td v-if="auth.canEdit">
              <button v-if="r.status === 'confirmed'" class="btn btn-danger btn-sm" @click="cancel(r.id)">取消</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="showModal" class="modal-overlay" @click.self="showModal = false">
      <div class="modal">
        <div class="modal-header"><h2>新增訂房</h2></div>
        <form @submit.prevent="save">
          <div class="form-group">
            <label>旅客</label>
            <select v-model="form.guest_id" class="form-input" required>
              <option v-for="g in guests" :key="g.id" :value="g.id">{{ g.last_name }}{{ g.first_name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>房型</label>
            <select v-model="form.room_type_id" class="form-input" required>
              <option v-for="t in roomTypes" :key="t.id" :value="t.id">{{ t.name }} (NT$ {{ t.base_price }})</option>
            </select>
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px">
            <div class="form-group">
              <label>入住日期</label>
              <input v-model="form.check_in_date" type="date" class="form-input" required />
            </div>
            <div class="form-group">
              <label>退房日期</label>
              <input v-model="form.check_out_date" type="date" class="form-input" required />
            </div>
          </div>
          <div class="form-group">
            <label>入住人數</label>
            <input v-model.number="form.num_guests" type="number" min="1" class="form-input" required />
          </div>
          <div class="form-group">
            <label>
              <input v-model="form.includes_breakfast" type="checkbox" /> 含早餐
            </label>
          </div>
          <div v-if="form.includes_breakfast" class="form-group">
            <label>早餐人數</label>
            <input v-model.number="form.breakfast_guests" type="number" min="0" class="form-input" />
          </div>
          <div class="form-group">
            <label>總金額</label>
            <input v-model.number="form.total_price" type="number" min="0" class="form-input" required />
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
