<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import api from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { CleaningRequest, CleaningStatusRoom } from '../types'

const auth = useAuthStore()
const pending = ref<CleaningRequest[]>([])
const inProgress = ref<CleaningStatusRoom[]>([])
const completeTarget = ref<CleaningStatusRoom | null>(null)
const cleanedByName = ref('')
const completeNotes = ref('')
const errorMessage = ref('')
let timer: number | undefined

async function load() {
  errorMessage.value = ''
  try {
    const [pRes, iRes] = await Promise.all([
      api.get('/housekeeping/cleaning-requests', { params: { status: 'pending' } }),
      api.get('/housekeeping/rooms/cleaning-status'),
    ])
    pending.value = pRes.data
    inProgress.value = iRes.data
  } catch (err: any) {
    errorMessage.value = err.response?.data?.detail || '載入清潔資料失敗'
  }
}

async function startCleaning(roomNumber: string) {
  errorMessage.value = ''
  try {
    await api.post(`/housekeeping/rooms/${roomNumber}/mark-cleaning`)
    await load()
  } catch (err: any) {
    errorMessage.value = err.response?.data?.detail || '啟動清潔失敗'
  }
}

function openCompleteModal(room: CleaningStatusRoom) {
  completeTarget.value = room
  cleanedByName.value = auth.user?.full_name ?? ''
  completeNotes.value = ''
}

async function submitComplete() {
  if (!completeTarget.value) return
  errorMessage.value = ''
  try {
    await api.post(`/housekeeping/rooms/${completeTarget.value.room_number}/clean-complete`, {
      cleaned_by_name: cleanedByName.value || null,
      notes: completeNotes.value || null,
    })
    completeTarget.value = null
    await load()
  } catch (err: any) {
    errorMessage.value = err.response?.data?.detail || '送出失敗'
  }
}

function formatRelative(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime()
  const mins = Math.round(diffMs / 60000)
  if (mins < 1) return '剛剛'
  if (mins < 60) return `${mins} 分鐘前`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours} 小時前`
  return new Date(iso).toLocaleString('zh-TW')
}

onMounted(() => {
  load()
  timer = window.setInterval(load, 30000)
})
onBeforeUnmount(() => {
  if (timer) window.clearInterval(timer)
})
</script>

<template>
  <div>
    <div class="page-header">
      <h2>房務清潔</h2>
      <div v-if="errorMessage" class="error-msg">{{ errorMessage }}</div>
      <button class="btn btn-outline" @click="load">重新整理</button>
    </div>

    <section style="margin-bottom: 24px">
      <h3>待清潔請求 ({{ pending.length }})</h3>
      <table>
        <thead>
          <tr>
            <th>房號</th>
            <th>請求時間</th>
            <th>備註</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in pending" :key="p.id">
            <td>{{ p.room_number }}</td>
            <td>{{ formatRelative(p.requested_at) }}</td>
            <td>{{ p.notes || '-' }}</td>
            <td>
              <button class="btn btn-primary" @click="startCleaning(p.room_number)">啟動清潔</button>
            </td>
          </tr>
          <tr v-if="pending.length === 0">
            <td colspan="4" style="text-align:center;color:#888">目前沒有待清潔請求</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section>
      <h3>進行中 ({{ inProgress.length }})</h3>
      <table>
        <thead>
          <tr>
            <th>房號</th>
            <th>類型</th>
            <th>開始時間</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in inProgress" :key="r.room_id">
            <td>{{ r.room_number }}</td>
            <td>{{ r.cleaning_type === 'checkout' ? '退房清潔' : '每日清潔' }}</td>
            <td>{{ formatRelative(r.started_at) }}</td>
            <td>
              <button class="btn btn-primary" @click="openCompleteModal(r)">完成清潔</button>
            </td>
          </tr>
          <tr v-if="inProgress.length === 0">
            <td colspan="4" style="text-align:center;color:#888">沒有進行中的清潔</td>
          </tr>
        </tbody>
      </table>
    </section>

    <div v-if="completeTarget" class="modal-backdrop">
      <div class="modal">
        <h3>完成清潔 — 房號 {{ completeTarget.room_number }}</h3>
        <label>清潔人員</label>
        <input v-model="cleanedByName" />
        <label>備註</label>
        <textarea v-model="completeNotes"></textarea>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:12px">
          <button class="btn btn-outline" @click="completeTarget = null">取消</button>
          <button class="btn btn-primary" @click="submitComplete">送出</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center;
}
.modal {
  background: white; padding: 16px; border-radius: 6px; min-width: 320px;
  display: flex; flex-direction: column; gap: 8px;
}
</style>
