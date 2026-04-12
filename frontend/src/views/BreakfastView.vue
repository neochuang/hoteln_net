<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { BreakfastRecord, BreakfastStats, Reservation, Guest } from '../types'

const auth = useAuthStore()
const todayMeals = ref<BreakfastRecord[]>([])
const stats = ref<BreakfastStats[]>([])
const reservations = ref<Reservation[]>([])
const guests = ref<Guest[]>([])
const tab = ref<'today' | 'stats'>('today')
const message = ref('')

const recordForm = ref({ reservation_id: '', guest_id: '' })
const purchaseForm = ref({ reservation_id: '', guest_id: '', extra_price: 200 })
const showRecordModal = ref(false)
const showPurchaseModal = ref(false)

async function loadData() {
  const [mealsRes, statsRes, resRes, guestsRes] = await Promise.all([
    api.get('/breakfast/today'),
    api.get('/breakfast/stats'),
    api.get('/reservations', { params: { status: 'checked_in' } }),
    api.get('/guests'),
  ])
  todayMeals.value = mealsRes.data
  stats.value = statsRes.data
  reservations.value = resRes.data
  guests.value = guestsRes.data
}

onMounted(loadData)

function guestName(id: string) {
  const g = guests.value.find(g => g.id === id)
  return g ? `${g.last_name}${g.first_name}` : '-'
}

async function recordMeal() {
  try {
    await api.post('/breakfast/record', recordForm.value)
    message.value = '用餐打卡成功'
    showRecordModal.value = false
    await loadData()
  } catch (err: any) {
    message.value = err.response?.data?.detail || '打卡失敗'
  }
}

async function purchaseBreakfast() {
  try {
    await api.post('/breakfast/purchase', purchaseForm.value)
    message.value = '加購早餐成功'
    showPurchaseModal.value = false
    await loadData()
  } catch (err: any) {
    message.value = err.response?.data?.detail || '加購失敗'
  }
}

function openRecord() {
  recordForm.value = {
    reservation_id: reservations.value[0]?.id || '',
    guest_id: reservations.value[0]?.guest_id || '',
  }
  showRecordModal.value = true
}

function openPurchase() {
  purchaseForm.value = {
    reservation_id: reservations.value[0]?.id || '',
    guest_id: reservations.value[0]?.guest_id || '',
    extra_price: 200,
  }
  showPurchaseModal.value = true
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1>早餐管理</h1>
      <div v-if="auth.canEdit" style="display: flex; gap: 8px">
        <button class="btn btn-primary" @click="openRecord">用餐打卡</button>
        <button class="btn btn-outline" @click="openPurchase">加購早餐</button>
      </div>
    </div>

    <div v-if="message" class="card" style="background: #f0fdf4; border-color: #bbf7d0; margin-bottom: 16px">
      {{ message }}
      <button class="btn btn-sm btn-outline" style="margin-left: 12px" @click="message = ''">關閉</button>
    </div>

    <div style="display: flex; gap: 8px; margin-bottom: 16px">
      <button :class="['btn', tab === 'today' ? 'btn-primary' : 'btn-outline']" @click="tab = 'today'">
        今日用餐 ({{ todayMeals.length }})
      </button>
      <button :class="['btn', tab === 'stats' ? 'btn-primary' : 'btn-outline']" @click="tab = 'stats'">
        統計報表
      </button>
    </div>

    <div v-if="tab === 'today'" class="card">
      <table>
        <thead>
          <tr>
            <th>旅客</th>
            <th>用餐時間</th>
            <th>類型</th>
            <th>加購金額</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in todayMeals" :key="m.id">
            <td>{{ guestName(m.guest_id) }}</td>
            <td>{{ new Date(m.meal_time).toLocaleTimeString('zh-TW') }}</td>
            <td>
              <span :class="m.is_extra_purchase ? 'badge badge-maintenance' : 'badge badge-available'">
                {{ m.is_extra_purchase ? '加購' : '含餐' }}
              </span>
            </td>
            <td>{{ m.extra_price ? `NT$ ${m.extra_price}` : '-' }}</td>
          </tr>
          <tr v-if="todayMeals.length === 0">
            <td colspan="4" style="text-align: center; color: var(--text-light)">今日尚無用餐記錄</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="tab === 'stats'" class="card">
      <table>
        <thead>
          <tr>
            <th>日期</th>
            <th>總用餐數</th>
            <th>含餐</th>
            <th>加購</th>
            <th>加購收入</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in stats" :key="s.date">
            <td>{{ s.date }}</td>
            <td>{{ s.total_meals }}</td>
            <td>{{ s.included_meals }}</td>
            <td>{{ s.extra_purchases }}</td>
            <td>NT$ {{ s.extra_revenue }}</td>
          </tr>
          <tr v-if="stats.length === 0">
            <td colspan="5" style="text-align: center; color: var(--text-light)">尚無統計資料</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Record Meal Modal -->
    <div v-if="showRecordModal" class="modal-overlay" @click.self="showRecordModal = false">
      <div class="modal">
        <div class="modal-header"><h2>用餐打卡</h2></div>
        <form @submit.prevent="recordMeal">
          <div class="form-group">
            <label>訂房 (已入住)</label>
            <select v-model="recordForm.reservation_id" class="form-input" required @change="recordForm.guest_id = reservations.find(r => r.id === recordForm.reservation_id)?.guest_id || ''">
              <option v-for="r in reservations" :key="r.id" :value="r.id">
                {{ guestName(r.guest_id) }} - {{ r.check_in_date }}
              </option>
            </select>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-outline" @click="showRecordModal = false">取消</button>
            <button type="submit" class="btn btn-primary">打卡</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Purchase Modal -->
    <div v-if="showPurchaseModal" class="modal-overlay" @click.self="showPurchaseModal = false">
      <div class="modal">
        <div class="modal-header"><h2>加購早餐</h2></div>
        <form @submit.prevent="purchaseBreakfast">
          <div class="form-group">
            <label>訂房 (已入住)</label>
            <select v-model="purchaseForm.reservation_id" class="form-input" required @change="purchaseForm.guest_id = reservations.find(r => r.id === purchaseForm.reservation_id)?.guest_id || ''">
              <option v-for="r in reservations" :key="r.id" :value="r.id">
                {{ guestName(r.guest_id) }} - {{ r.check_in_date }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>加購金額</label>
            <input v-model.number="purchaseForm.extra_price" type="number" class="form-input" required />
          </div>
          <div class="modal-actions">
            <button type="button" class="btn btn-outline" @click="showPurchaseModal = false">取消</button>
            <button type="submit" class="btn btn-primary">確認加購</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
