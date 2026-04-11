<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'
import type { Reservation, Room, Guest, RoomType } from '../types'

const reservations = ref<Reservation[]>([])
const rooms = ref<Room[]>([])
const guests = ref<Guest[]>([])
const roomTypes = ref<RoomType[]>([])
const tab = ref<'checkin' | 'checkout'>('checkin')
const selectedRoom = ref('')
const message = ref('')

async function loadData() {
  const [resRes, roomsRes, guestsRes, typesRes] = await Promise.all([
    api.get('/reservations'),
    api.get('/rooms'),
    api.get('/guests'),
    api.get('/rooms/types'),
  ])
  reservations.value = resRes.data
  rooms.value = roomsRes.data
  guests.value = guestsRes.data
  roomTypes.value = typesRes.data
}

onMounted(loadData)

const pendingCheckIns = () => reservations.value.filter(r => r.status === 'confirmed')
const currentlyCheckedIn = () => reservations.value.filter(r => r.status === 'checked_in')

function guestName(id: string) {
  const g = guests.value.find(g => g.id === id)
  return g ? `${g.last_name}${g.first_name}` : '-'
}

function typeName(id: string) {
  return roomTypes.value.find(t => t.id === id)?.name || '-'
}

function availableRooms(roomTypeId: string) {
  return rooms.value.filter(r => r.room_type_id === roomTypeId && r.status === 'available')
}

function roomNumber(id: string | null) {
  if (!id) return '-'
  return rooms.value.find(r => r.id === id)?.room_number || '-'
}

async function checkIn(reservation: Reservation) {
  const available = availableRooms(reservation.room_type_id)
  if (available.length === 0) {
    message.value = '沒有可用的同房型房間'
    return
  }
  const roomId = selectedRoom.value || available[0].id
  try {
    await api.post(`/reservations/${reservation.id}/check-in`, { room_id: roomId })
    message.value = `已完成報到，房間: ${rooms.value.find(r => r.id === roomId)?.room_number}`
    selectedRoom.value = ''
    await loadData()
  } catch (err: any) {
    message.value = err.response?.data?.detail || '報到失敗'
  }
}

async function checkOut(reservation: Reservation) {
  if (!confirm(`確定要為 ${guestName(reservation.guest_id)} 辦理退房嗎？`)) return
  try {
    await api.post(`/reservations/${reservation.id}/check-out`)
    message.value = '退房完成'
    await loadData()
  } catch (err: any) {
    message.value = err.response?.data?.detail || '退房失敗'
  }
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1>報到 / 退房</h1>
    </div>

    <div v-if="message" class="card" style="background: #f0fdf4; border-color: #bbf7d0; margin-bottom: 16px">
      {{ message }}
      <button class="btn btn-sm btn-outline" style="margin-left: 12px" @click="message = ''">關閉</button>
    </div>

    <div style="display: flex; gap: 8px; margin-bottom: 16px">
      <button :class="['btn', tab === 'checkin' ? 'btn-primary' : 'btn-outline']" @click="tab = 'checkin'">
        報到 ({{ pendingCheckIns().length }})
      </button>
      <button :class="['btn', tab === 'checkout' ? 'btn-primary' : 'btn-outline']" @click="tab = 'checkout'">
        退房 ({{ currentlyCheckedIn().length }})
      </button>
    </div>

    <!-- Check-in tab -->
    <div v-if="tab === 'checkin'" class="card">
      <table>
        <thead>
          <tr>
            <th>旅客</th>
            <th>房型</th>
            <th>入住日期</th>
            <th>退房日期</th>
            <th>人數</th>
            <th>分配房間</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in pendingCheckIns()" :key="r.id">
            <td>{{ guestName(r.guest_id) }}</td>
            <td>{{ typeName(r.room_type_id) }}</td>
            <td>{{ r.check_in_date }}</td>
            <td>{{ r.check_out_date }}</td>
            <td>{{ r.num_guests }}</td>
            <td>
              <select v-model="selectedRoom" class="form-input" style="width: 120px; padding: 4px 8px; font-size: 12px">
                <option v-for="room in availableRooms(r.room_type_id)" :key="room.id" :value="room.id">
                  {{ room.room_number }}
                </option>
              </select>
            </td>
            <td>
              <button class="btn btn-success btn-sm" @click="checkIn(r)">報到</button>
            </td>
          </tr>
          <tr v-if="pendingCheckIns().length === 0">
            <td colspan="7" style="text-align: center; color: var(--text-light)">目前無待報到訂房</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Check-out tab -->
    <div v-if="tab === 'checkout'" class="card">
      <table>
        <thead>
          <tr>
            <th>旅客</th>
            <th>房號</th>
            <th>房型</th>
            <th>入住日期</th>
            <th>退房日期</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in currentlyCheckedIn()" :key="r.id">
            <td>{{ guestName(r.guest_id) }}</td>
            <td>{{ roomNumber(r.room_id) }}</td>
            <td>{{ typeName(r.room_type_id) }}</td>
            <td>{{ r.check_in_date }}</td>
            <td>{{ r.check_out_date }}</td>
            <td>
              <button class="btn btn-danger btn-sm" @click="checkOut(r)">退房</button>
            </td>
          </tr>
          <tr v-if="currentlyCheckedIn().length === 0">
            <td colspan="6" style="text-align: center; color: var(--text-light)">目前無已入住旅客</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
