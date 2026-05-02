<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import api from '../api/client'
import { useAuthStore } from '../stores/auth'
import type { CleaningRequest, CleaningStatusRoom, User, CleaningTask } from '../types'

const auth = useAuthStore()
const pending = ref<CleaningRequest[]>([])
const inProgress = ref<CleaningStatusRoom[]>([])
const tasks = ref<CleaningTask[]>([])
const cleaners = ref<User[]>([])

const completeTarget = ref<CleaningStatusRoom | null>(null)
const assignTarget = ref<CleaningRequest | null>(null)
const selectedCleanerId = ref('')

const cleanedByName = ref('')
const completeNotes = ref('')
const errorMessage = ref('')
let timer: number | undefined

async function load() {
  errorMessage.value = ''
  try {
    const [pRes, iRes, tRes, uRes] = await Promise.all([
      api.get('/housekeeping/cleaning-requests', { params: { status: 'pending' } }),
      api.get('/housekeeping/rooms/cleaning-status'),
      api.get('/housekeeping/tasks'),
      api.get('/users')
    ])
    pending.value = pRes.data
    inProgress.value = iRes.data
    tasks.value = tRes.data
    cleaners.value = uRes.data.filter((u: User) => u.role === 'cleaner')
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

function openAssignModal(req: CleaningRequest) {
  assignTarget.value = req
  selectedCleanerId.value = ''
}

async function submitAssign() {
  if (!assignTarget.value || !selectedCleanerId.value) return
  try {
    await api.post('/housekeeping/tasks', {
      room_id: assignTarget.value.room_id,
      assigned_to_user_id: selectedCleanerId.value,
      cleaning_type: 'daily' // Default for requests
    })
    assignTarget.value = null
    await load()
  } catch (err: any) {
    errorMessage.value = err.response?.data?.detail || '指派失敗'
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

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'pending': return '待處理'
    case 'in_progress': return '進行中'
    case 'completed': return '已完成'
    case 'cancelled': return '已取消'
    default: return status
  }
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
      <h2>房務清潔管理</h2>
      <div v-if="errorMessage" class="error-msg">{{ errorMessage }}</div>
      <button class="btn btn-outline" @click="load">重新整理</button>
    </div>

    <section style="margin-bottom: 24px">
      <h3>待處理請求 ({{ pending.length }})</h3>
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
            <td class="actions">
              <button class="btn btn-primary btn-sm" @click="startCleaning(p.room_number)">直接啟動</button>
              <button class="btn btn-secondary btn-sm" @click="openAssignModal(p)">指派人員</button>
            </td>
          </tr>
          <tr v-if="pending.length === 0">
            <td colspan="4" style="text-align:center;color:#888">目前沒有待清潔請求</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section style="margin-bottom: 24px">
      <h3>已指派任務 ({{ tasks.filter(t => t.status !== 'completed').length }})</h3>
      <table>
        <thead>
          <tr>
            <th>房號</th>
            <th>清潔人員</th>
            <th>狀態</th>
            <th>指派時間</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in tasks.filter(t => t.status !== 'completed')" :key="t.id">
            <td>{{ t.room_number }}</td>
            <td>{{ t.cleaner_name }}</td>
            <td><span class="status-badge" :class="t.status">{{ getStatusLabel(t.status) }}</span></td>
            <td>{{ formatRelative(t.created_at) }}</td>
          </tr>
          <tr v-if="tasks.filter(t => t.status !== 'completed').length === 0">
            <td colspan="4" style="text-align:center;color:#888">目前沒有進行中的指派任務</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section>
      <h3>清潔中 ({{ inProgress.length }})</h3>
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
              <button class="btn btn-primary btn-sm" @click="openCompleteModal(r)">完成清潔</button>
            </td>
          </tr>
          <tr v-if="inProgress.length === 0">
            <td colspan="4" style="text-align:center;color:#888">沒有進行中的清潔</td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- Assign Task Modal -->
    <div v-if="assignTarget" class="modal-backdrop">
      <div class="modal">
        <h3>指派清潔任務 — 房號 {{ assignTarget.room_number }}</h3>
        <label>選擇清潔人員</label>
        <select v-model="selectedCleanerId" class="form-control">
          <option value="" disabled>請選擇人員</option>
          <option v-for="c in cleaners" :key="c.id" :value="c.id">{{ c.full_name }}</option>
        </select>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">
          <button class="btn btn-outline" @click="assignTarget = null">取消</button>
          <button class="btn btn-primary" :disabled="!selectedCleanerId" @click="submitAssign">確認指派</button>
        </div>
      </div>
    </div>

    <!-- Complete Cleaning Modal -->
    <div v-if="completeTarget" class="modal-backdrop">
      <div class="modal">
        <h3>完成清潔 — 房號 {{ completeTarget.room_number }}</h3>
        <label>清潔人員</label>
        <input v-model="cleanedByName" class="form-control" />
        <label>備註</label>
        <textarea v-model="completeNotes" class="form-control"></textarea>
        <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:12px">
          <button class="btn btn-outline" @click="completeTarget = null">取消</button>
          <button class="btn btn-primary" @click="submitComplete">送出</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.actions {
  display: flex;
  gap: 8px;
}
.btn-sm {
  padding: 4px 8px;
  font-size: 0.85rem;
}
.status-badge {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.85rem;
}
.status-badge.pending { background: #fff3e0; color: #ef6c00; }
.status-badge.in_progress { background: #e3f2fd; color: #1565c0; }

.modal-backdrop {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex; align-items: center; justify-content: center;
  z-index: 100;
}
.modal {
  background: white; padding: 24px; border-radius: 8px; min-width: 400px;
  display: flex; flex-direction: column; gap: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.form-control {
  padding: 8px;
  border: 1px solid #ddd;
  border-radius: 4px;
  width: 100%;
}
</style>
