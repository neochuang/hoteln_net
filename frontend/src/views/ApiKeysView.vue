<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'
import type { ApiKey, ApiKeyCreated, Room } from '../types'

const apiKeys = ref<ApiKey[]>([])
const rooms = ref<Room[]>([])
const showCreateModal = ref(false)
const showEditModal = ref(false)
const showKeyModal = ref(false)
const createdKey = ref('')
const editingId = ref<string | null>(null)

const form = ref<{ name: string; room_id: string | null }>({ name: '', room_id: null })

async function loadData() {
  const [keysRes, roomsRes] = await Promise.all([
    api.get('/api-keys'),
    api.get('/rooms'),
  ])
  apiKeys.value = keysRes.data
  rooms.value = roomsRes.data
}

function resetForm() {
  form.value = { name: '', room_id: null }
  editingId.value = null
}

function openCreate() {
  resetForm()
  showCreateModal.value = true
}

function openEdit(key: ApiKey) {
  editingId.value = key.id
  form.value = { name: key.name, room_id: key.room_id }
  showEditModal.value = true
}

async function createKey() {
  const res = await api.post('/api-keys', { name: form.value.name, room_id: form.value.room_id })
  const data: ApiKeyCreated = res.data
  createdKey.value = data.key
  showCreateModal.value = false
  resetForm()
  showKeyModal.value = true
  await loadData()
}

async function updateKey() {
  if (!editingId.value) return
  await api.patch(`/api-keys/${editingId.value}`, {
    name: form.value.name,
    room_id: form.value.room_id,
  })
  showEditModal.value = false
  resetForm()
  await loadData()
}

async function toggleActive(key: ApiKey) {
  await api.patch(`/api-keys/${key.id}`, { is_active: !key.is_active })
  await loadData()
}

async function deleteKey(key: ApiKey) {
  if (!confirm(`確定要刪除「${key.name}」？`)) return
  await api.delete(`/api-keys/${key.id}`)
  await loadData()
}

function copyKey() {
  navigator.clipboard.writeText(createdKey.value)
}

function formatDate(d: string | null) {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-TW')
}

function roomLabel(roomId: string | null) {
  if (!roomId) return '-'
  return rooms.value.find(r => r.id === roomId)?.room_number || '-'
}

onMounted(loadData)
</script>

<template>
  <div>
    <div class="page-header">
      <h2>API Key 管理</h2>
      <button class="btn btn-primary" @click="openCreate">新增 API Key</button>
    </div>

    <table>
      <thead>
        <tr>
          <th>名稱</th>
          <th>Key 前綴</th>
          <th>綁定房間</th>
          <th>狀態</th>
          <th>建立時間</th>
          <th>最後使用</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="key in apiKeys" :key="key.id">
          <td>{{ key.name }}</td>
          <td><code>{{ key.key_prefix }}...</code></td>
          <td>{{ roomLabel(key.room_id) }}</td>
          <td>
            <span :class="['badge', key.is_active ? 'badge-available' : 'badge-cancelled']">
              {{ key.is_active ? '啟用' : '停用' }}
            </span>
          </td>
          <td>{{ formatDate(key.created_at) }}</td>
          <td>{{ formatDate(key.last_used_at) }}</td>
          <td>
            <button class="btn btn-sm" @click="openEdit(key)">
              編輯
            </button>
            <button
              :class="['btn btn-sm', key.is_active ? 'btn-danger' : 'btn-success']"
              style="margin-left: 4px"
              @click="toggleActive(key)"
            >
              {{ key.is_active ? '停用' : '啟用' }}
            </button>
            <button class="btn btn-sm btn-danger" @click="deleteKey(key)" style="margin-left: 4px">
              刪除
            </button>
          </td>
        </tr>
        <tr v-if="apiKeys.length === 0">
          <td colspan="7" style="text-align: center; color: #888">尚無 API Key</td>
        </tr>
      </tbody>
    </table>

    <!-- Create Modal -->
    <div v-if="showCreateModal" class="overlay" @click.self="showCreateModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>新增 API Key</h3>
        </div>
        <form @submit.prevent="createKey">
          <div class="form-group">
            <label>裝置名稱</label>
            <input v-model="form.name" required placeholder="例如：3F 清潔平板" />
          </div>
          <div class="form-group">
            <label>綁定房間 (可留空)</label>
            <select v-model="form.room_id">
              <option :value="null">未綁定</option>
              <option v-for="r in rooms" :key="r.id" :value="r.id">{{ r.room_number }}</option>
            </select>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn" @click="showCreateModal = false">取消</button>
            <button type="submit" class="btn btn-primary">建立</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Edit Modal -->
    <div v-if="showEditModal" class="overlay" @click.self="showEditModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>編輯 API Key</h3>
        </div>
        <form @submit.prevent="updateKey">
          <div class="form-group">
            <label>裝置名稱</label>
            <input v-model="form.name" required />
          </div>
          <div class="form-group">
            <label>綁定房間 (可留空)</label>
            <select v-model="form.room_id">
              <option :value="null">未綁定</option>
              <option v-for="r in rooms" :key="r.id" :value="r.id">{{ r.room_number }}</option>
            </select>
          </div>
          <div class="modal-actions">
            <button type="button" class="btn" @click="showEditModal = false">取消</button>
            <button type="submit" class="btn btn-primary">儲存</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Key Display Modal -->
    <div v-if="showKeyModal" class="overlay">
      <div class="modal">
        <div class="modal-header">
          <h3>API Key 已建立</h3>
        </div>
        <p style="color: #dc2626; font-weight: bold">請立即複製此 Key，關閉後將無法再次查看！</p>
        <div style="background: #f3f4f6; padding: 12px; border-radius: 6px; word-break: break-all; font-family: monospace">
          {{ createdKey }}
        </div>
        <div class="modal-actions">
          <button class="btn" @click="copyKey">複製</button>
          <button class="btn btn-primary" @click="showKeyModal = false; createdKey = ''">我已複製，關閉</button>
        </div>
      </div>
    </div>
  </div>
</template>
