<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'
import type { CleaningRecord, Room } from '../types'

const records = ref<CleaningRecord[]>([])
const rooms = ref<Room[]>([])
const filterRoomId = ref('')
const filterType = ref('')
const filterDateFrom = ref('')
const filterDateTo = ref('')

async function loadData() {
  const [roomsRes] = await Promise.all([api.get('/rooms')])
  rooms.value = roomsRes.data
  await loadRecords()
}

async function loadRecords() {
  const params: Record<string, string> = {}
  if (filterRoomId.value) params.room_id = filterRoomId.value
  if (filterType.value) params.cleaning_type = filterType.value
  if (filterDateFrom.value) params.date_from = filterDateFrom.value
  if (filterDateTo.value) params.date_to = filterDateTo.value

  const res = await api.get('/housekeeping/cleaning-records', { params })
  records.value = res.data
}

function roomNumber(roomId: string): string {
  const room = rooms.value.find((r) => r.id === roomId)
  return room ? room.room_number : roomId.slice(0, 8)
}

function formatDate(d: string | null) {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-TW')
}

function duration(record: CleaningRecord): string {
  if (!record.completed_at) return '進行中'
  const start = new Date(record.started_at).getTime()
  const end = new Date(record.completed_at).getTime()
  const mins = Math.round((end - start) / 60000)
  if (mins < 60) return `${mins} 分鐘`
  return `${Math.floor(mins / 60)} 小時 ${mins % 60} 分鐘`
}

const typeLabel: Record<string, string> = { checkout: '退房清潔', daily: '每日清潔' }
const viaLabel: Record<string, string> = { device: '裝置', staff: '前台人員' }

onMounted(loadData)
</script>

<template>
  <div>
    <div class="page-header">
      <h2>清潔紀錄</h2>
    </div>

    <div style="display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap">
      <select v-model="filterRoomId" @change="loadRecords">
        <option value="">全部房間</option>
        <option v-for="room in rooms" :key="room.id" :value="room.id">{{ room.room_number }}</option>
      </select>
      <select v-model="filterType" @change="loadRecords">
        <option value="">全部類型</option>
        <option value="checkout">退房清潔</option>
        <option value="daily">每日清潔</option>
      </select>
      <input type="date" v-model="filterDateFrom" @change="loadRecords" placeholder="開始日期" />
      <input type="date" v-model="filterDateTo" @change="loadRecords" placeholder="結束日期" />
    </div>

    <table>
      <thead>
        <tr>
          <th>房號</th>
          <th>清潔類型</th>
          <th>回報來源</th>
          <th>開始時間</th>
          <th>完成時間</th>
          <th>耗時</th>
          <th>清潔人員</th>
          <th>備註</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in records" :key="r.id">
          <td>{{ roomNumber(r.room_id) }}</td>
          <td>
            <span :class="['badge', r.cleaning_type === 'checkout' ? 'badge-maintenance' : 'badge-available']">
              {{ typeLabel[r.cleaning_type] || r.cleaning_type }}
            </span>
          </td>
          <td>{{ r.reported_via ? viaLabel[r.reported_via] || r.reported_via : '-' }}</td>
          <td>{{ formatDate(r.started_at) }}</td>
          <td>{{ formatDate(r.completed_at) }}</td>
          <td>{{ duration(r) }}</td>
          <td>{{ r.cleaned_by_name || '-' }}</td>
          <td>{{ r.notes || '-' }}</td>
        </tr>
        <tr v-if="records.length === 0">
          <td colspan="8" style="text-align: center; color: #888">無清潔紀錄</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
