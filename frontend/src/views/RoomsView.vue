<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { Room, RoomType } from '../types'

const auth = useAuthStore()
const rooms = ref<Room[]>([])
const roomTypes = ref<RoomType[]>([])
const statusFilter = ref('')
const showRoomModal = ref(false)
const showTypeModal = ref(false)

const roomForm = ref({ room_number: '', floor: 1, room_type_id: '', notes: '' })
const typeForm = ref({ name: '', capacity: 1, base_price: 0, description: '' })

async function loadData() {
  const params: any = {}
  if (statusFilter.value) params.status = statusFilter.value
  const [roomsRes, typesRes] = await Promise.all([
    api.get('/rooms', { params }),
    api.get('/rooms/types'),
  ])
  rooms.value = roomsRes.data
  roomTypes.value = typesRes.data
}

onMounted(loadData)

async function updateStatus(room: Room, status: string) {
  await api.patch(`/rooms/${room.id}`, { status })
  await loadData()
}

async function saveRoom() {
  await api.post('/rooms', { ...roomForm.value, notes: roomForm.value.notes || null })
  showRoomModal.value = false
  await loadData()
}

async function saveType() {
  await api.post('/rooms/types', { ...typeForm.value, description: typeForm.value.description || null })
  showTypeModal.value = false
  await loadData()
}

async function markCleaning(room: Room) {
  if (!confirm(`確定要將房間 ${room.room_number} 標註為可清潔？`)) return
  await api.post(`/housekeeping/rooms/${room.room_number}/mark-cleaning`)
  await loadData()
}

async function cleanComplete(room: Room) {
  if (!confirm(`確定房間 ${room.room_number} 已清潔完成？`)) return
  await api.post(`/housekeeping/rooms/${room.room_number}/clean-complete`, {})
  await loadData()
}

function typeName(id: string) {
  return roomTypes.value.find(t => t.id === id)?.name || '-'
}

const statusLabel: Record<string, string> = {
  available: '空房',
  occupied: '已入住',
  cleaning: '清潔中',
  maintenance: '維修中',
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1>房間管理</h1>
      <div v-if="auth.canEdit" style="display: flex; gap: 8px">
        <button class="btn btn-outline" @click="showTypeModal = true">新增房型</button>
        <button class="btn btn-primary" @click="roomForm = { room_number: '', floor: 1, room_type_id: roomTypes[0]?.id || '', notes: '' }; showRoomModal = true">新增房間</button>
      </div>
    </div>

    <div class="search-bar">
      <select v-model="statusFilter" class="form-input" style="width: 200px" @change="loadData">
        <option value="">全部狀態</option>
        <option value="available">空房</option>
        <option value="occupied">已入住</option>
        <option value="cleaning">清潔中</option>
        <option value="maintenance">維修中</option>
      </select>
    </div>

    <!-- Room Types -->
    <div class="card" style="margin-bottom: 16px">
      <h2 style="font-size: 16px; margin-bottom: 12px">房型列表</h2>
      <table>
        <thead>
          <tr><th>房型</th><th>容量</th><th>基本價格</th><th>說明</th></tr>
        </thead>
        <tbody>
          <tr v-for="t in roomTypes" :key="t.id">
            <td>{{ t.name }}</td>
            <td>{{ t.capacity }} 人</td>
            <td>NT$ {{ t.base_price }}</td>
            <td>{{ t.description || '-' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Rooms -->
    <div class="card">
      <h2 style="font-size: 16px; margin-bottom: 12px">房間列表</h2>
      <table>
        <thead>
          <tr><th>房號</th><th>樓層</th><th>房型</th><th>狀態</th><th v-if="auth.canEdit">操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="r in rooms" :key="r.id">
            <td>{{ r.room_number }}</td>
            <td>{{ r.floor }}F</td>
            <td>{{ typeName(r.room_type_id) }}</td>
            <td><span :class="'badge badge-' + r.status">{{ statusLabel[r.status] }}</span></td>
            <td v-if="auth.canEdit">
              <select class="form-input" style="width: 120px; padding: 4px 8px; font-size: 12px" :value="r.status" @change="updateStatus(r, ($event.target as HTMLSelectElement).value)">
                <option value="available">空房</option>
                <option value="occupied">已入住</option>
                <option value="cleaning">清潔中</option>
                <option value="maintenance">維修中</option>
              </select>
              <button
                v-if="r.status === 'occupied' && auth.canEdit"
                class="btn btn-sm"
                style="background: #f59e0b; color: white; margin-left: 4px"
                @click="markCleaning(r)"
              >
                標註可清潔
              </button>
              <button
                v-if="r.status === 'cleaning' && auth.canEdit"
                class="btn btn-sm btn-success"
                style="margin-left: 4px"
                @click="cleanComplete(r)"
              >
                清潔完成
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- New Room Modal -->
    <div v-if="showRoomModal" class="modal-overlay" @click.self="showRoomModal = false">
      <div class="modal">
        <div class="modal-header"><h2>新增房間</h2></div>
        <form @submit.prevent="saveRoom">
          <div class="form-group">
            <label>房號</label>
            <input v-model="roomForm.room_number" class="form-input" required />
          </div>
          <div class="form-group">
            <label>樓層</label>
            <input v-model.number="roomForm.floor" type="number" class="form-input" required />
          </div>
          <div class="form-group">
            <label>房型</label>
            <select v-model="roomForm.room_type_id" class="form-input" required>
              <option v-for="t in roomTypes" :key="t.id" :value="t.id">{{ t.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>備註</label>
            <input v-model="roomForm.notes" class="form-input" />
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-outline" @click="showRoomModal = false">取消</button>
            <button type="submit" class="btn btn-primary">儲存</button>
          </div>
        </form>
      </div>
    </div>

    <!-- New RoomType Modal -->
    <div v-if="showTypeModal" class="modal-overlay" @click.self="showTypeModal = false">
      <div class="modal">
        <div class="modal-header"><h2>新增房型</h2></div>
        <form @submit.prevent="saveType">
          <div class="form-group">
            <label>房型名稱</label>
            <input v-model="typeForm.name" class="form-input" required />
          </div>
          <div class="form-group">
            <label>容量 (人)</label>
            <input v-model.number="typeForm.capacity" type="number" class="form-input" required />
          </div>
          <div class="form-group">
            <label>基本價格</label>
            <input v-model.number="typeForm.base_price" type="number" class="form-input" required />
          </div>
          <div class="form-group">
            <label>說明</label>
            <input v-model="typeForm.description" class="form-input" />
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-outline" @click="showTypeModal = false">取消</button>
            <button type="submit" class="btn btn-primary">儲存</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
