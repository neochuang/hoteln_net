<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'
import type { Reservation, Room, BreakfastStats } from '../types'

const todayCheckIns = ref(0)
const todayCheckOuts = ref(0)
const occupiedRooms = ref(0)
const totalRooms = ref(0)
const todayBreakfasts = ref(0)
const recentReservations = ref<Reservation[]>([])

onMounted(async () => {
  const today = new Date().toISOString().split('T')[0]

  const [roomsRes, reservationsRes, breakfastRes] = await Promise.all([
    api.get('/rooms'),
    api.get('/reservations'),
    api.get('/breakfast/today'),
  ])

  const rooms: Room[] = roomsRes.data
  totalRooms.value = rooms.length
  occupiedRooms.value = rooms.filter(r => r.status === 'occupied').length

  const reservations: Reservation[] = reservationsRes.data
  todayCheckIns.value = reservations.filter(
    r => r.check_in_date === today && (r.status === 'confirmed' || r.status === 'checked_in')
  ).length
  todayCheckOuts.value = reservations.filter(
    r => r.check_out_date === today && r.status === 'checked_in'
  ).length

  todayBreakfasts.value = breakfastRes.data.length
  recentReservations.value = reservations.slice(0, 10)
})

const occupancyRate = () => {
  if (totalRooms.value === 0) return '0%'
  return Math.round((occupiedRooms.value / totalRooms.value) * 100) + '%'
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1>Dashboard</h1>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="label">今日預計入住</div>
        <div class="value">{{ todayCheckIns }}</div>
      </div>
      <div class="stat-card">
        <div class="label">今日預計退房</div>
        <div class="value">{{ todayCheckOuts }}</div>
      </div>
      <div class="stat-card">
        <div class="label">房間佔用率</div>
        <div class="value">{{ occupancyRate() }}</div>
      </div>
      <div class="stat-card">
        <div class="label">今日早餐用餐</div>
        <div class="value">{{ todayBreakfasts }}</div>
      </div>
    </div>

    <div class="card">
      <h2 style="font-size: 16px; margin-bottom: 12px">近期訂房</h2>
      <table>
        <thead>
          <tr>
            <th>入住日期</th>
            <th>退房日期</th>
            <th>人數</th>
            <th>狀態</th>
            <th>金額</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in recentReservations" :key="r.id">
            <td>{{ r.check_in_date }}</td>
            <td>{{ r.check_out_date }}</td>
            <td>{{ r.num_guests }}</td>
            <td><span :class="'badge badge-' + r.status">{{ r.status }}</span></td>
            <td>NT$ {{ r.total_price }}</td>
          </tr>
          <tr v-if="recentReservations.length === 0">
            <td colspan="5" style="text-align: center; color: var(--text-light)">尚無訂房記錄</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
