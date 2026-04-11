<script setup lang="ts">
import { ref } from 'vue'
import axios from 'axios'

const API = 'http://localhost:8000/api/self-checkin'

type Step = 'lookup' | 'confirm' | 'done'
const step = ref<Step>('lookup')
const idNumber = ref('')
const error = ref('')
const loading = ref(false)

// Lookup result
const guestName = ref('')
const reservations = ref<any[]>([])

// Confirm result
const checkInResult = ref<any>(null)

async function lookup() {
  error.value = ''
  loading.value = true
  try {
    const res = await axios.post(`${API}/lookup`, { id_number: idNumber.value })
    guestName.value = res.data.guest_name
    reservations.value = res.data.reservations
    step.value = 'confirm'
  } catch (err: any) {
    error.value = err.response?.data?.detail || '查詢失敗，請確認證件號碼'
  } finally {
    loading.value = false
  }
}

async function confirm(reservationId: string) {
  error.value = ''
  loading.value = true
  try {
    const res = await axios.post(`${API}/confirm`, {
      reservation_id: reservationId,
      id_number: idNumber.value,
    })
    checkInResult.value = res.data
    step.value = 'done'
  } catch (err: any) {
    error.value = err.response?.data?.detail || '報到失敗，請洽櫃台'
  } finally {
    loading.value = false
  }
}

function reset() {
  step.value = 'lookup'
  idNumber.value = ''
  error.value = ''
  guestName.value = ''
  reservations.value = []
  checkInResult.value = null
}
</script>

<template>
  <div class="self-checkin">
    <div class="self-checkin-header">
      <h1>旅客自助報到</h1>
      <p>Self Check-in</p>
    </div>

    <!-- Step 1: Lookup -->
    <div v-if="step === 'lookup'" class="self-checkin-card">
      <h2>請輸入您的證件號碼</h2>
      <div v-if="error" class="self-error">{{ error }}</div>
      <form @submit.prevent="lookup">
        <input
          v-model="idNumber"
          class="self-input"
          placeholder="身分證字號 / 護照號碼"
          required
          autofocus
        />
        <button class="self-btn" :disabled="loading || !idNumber">
          {{ loading ? '查詢中...' : '查詢訂房' }}
        </button>
      </form>
    </div>

    <!-- Step 2: Confirm -->
    <div v-if="step === 'confirm'" class="self-checkin-card">
      <h2>{{ guestName }} 您好</h2>
      <p class="self-subtitle">請確認您的訂房資訊</p>
      <div v-if="error" class="self-error">{{ error }}</div>

      <div v-for="r in reservations" :key="r.id" class="reservation-card">
        <div class="reservation-info">
          <div class="info-row">
            <span class="info-label">房型</span>
            <span class="info-value">{{ r.room_type_name }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">入住日期</span>
            <span class="info-value">{{ r.check_in_date }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">退房日期</span>
            <span class="info-value">{{ r.check_out_date }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">人數</span>
            <span class="info-value">{{ r.num_guests }} 人</span>
          </div>
          <div class="info-row">
            <span class="info-label">早餐</span>
            <span class="info-value">{{ r.includes_breakfast ? `含 ${r.breakfast_guests} 人份` : '未含' }}</span>
          </div>
        </div>
        <button class="self-btn" :disabled="loading" @click="confirm(r.id)">
          {{ loading ? '處理中...' : '確認報到' }}
        </button>
      </div>

      <button class="self-btn-outline" @click="reset">返回</button>
    </div>

    <!-- Step 3: Done -->
    <div v-if="step === 'done' && checkInResult" class="self-checkin-card done-card">
      <div class="success-icon">&#10003;</div>
      <h2>報到完成！</h2>

      <div class="room-number-display">
        <span class="room-label">您的房間</span>
        <span class="room-number">{{ checkInResult.room_number }}</span>
        <span class="room-floor">{{ checkInResult.floor }}F ・ {{ checkInResult.room_type_name }}</span>
      </div>

      <div class="info-cards">
        <div class="info-card">
          <div class="info-card-label">退房日期</div>
          <div class="info-card-value">{{ checkInResult.check_out_date }}</div>
        </div>
        <div class="info-card">
          <div class="info-card-label">早餐</div>
          <div class="info-card-value">{{ checkInResult.breakfast_info }}</div>
        </div>
        <div class="info-card">
          <div class="info-card-label">WiFi 密碼</div>
          <div class="info-card-value">{{ checkInResult.wifi_password }}</div>
        </div>
      </div>

      <button class="self-btn-outline" style="margin-top: 32px" @click="reset">完成</button>
    </div>
  </div>
</template>

<style scoped>
.self-checkin {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 20px;
}

.self-checkin-header {
  text-align: center;
  margin-bottom: 32px;
}

.self-checkin-header h1 {
  font-size: 36px;
  font-weight: 700;
  color: white;
  margin: 0;
}

.self-checkin-header p {
  font-size: 18px;
  color: rgba(255,255,255,0.8);
  margin-top: 4px;
}

.self-checkin-card {
  background: white;
  border-radius: 16px;
  padding: 40px;
  width: 520px;
  max-width: 90vw;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
}

.self-checkin-card h2 {
  font-size: 24px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 8px;
  text-align: center;
}

.self-subtitle {
  text-align: center;
  color: #64748b;
  margin-bottom: 24px;
  font-size: 16px;
}

.self-input {
  width: 100%;
  padding: 16px 20px;
  font-size: 20px;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  outline: none;
  margin: 20px 0;
  text-align: center;
  letter-spacing: 2px;
  box-sizing: border-box;
}

.self-input:focus {
  border-color: #667eea;
}

.self-btn {
  width: 100%;
  padding: 16px;
  font-size: 18px;
  font-weight: 600;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: background 0.2s;
}

.self-btn:hover:not(:disabled) {
  background: #5a67d8;
}

.self-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.self-btn-outline {
  width: 100%;
  padding: 12px;
  font-size: 16px;
  background: transparent;
  color: #64748b;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  cursor: pointer;
  margin-top: 12px;
}

.self-error {
  background: #fee2e2;
  color: #991b1b;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 16px;
  text-align: center;
  margin-bottom: 16px;
}

.reservation-card {
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
}

.reservation-info {
  margin-bottom: 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 16px;
}

.info-label {
  color: #64748b;
}

.info-value {
  font-weight: 600;
  color: #1e293b;
}

/* Done card */
.done-card {
  text-align: center;
}

.success-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #22c55e;
  color: white;
  font-size: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}

.room-number-display {
  margin: 24px 0;
}

.room-label {
  display: block;
  font-size: 14px;
  color: #64748b;
  margin-bottom: 4px;
}

.room-number {
  display: block;
  font-size: 72px;
  font-weight: 800;
  color: #667eea;
  line-height: 1;
}

.room-floor {
  display: block;
  font-size: 18px;
  color: #64748b;
  margin-top: 4px;
}

.info-cards {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
  margin-top: 24px;
}

.info-card {
  background: #f8fafc;
  border-radius: 10px;
  padding: 16px;
}

.info-card-label {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 4px;
}

.info-card-value {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
}
</style>
