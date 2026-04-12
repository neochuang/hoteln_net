<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'
import type { ApiKey, ApiKeyCreated } from '../types'

const apiKeys = ref<ApiKey[]>([])
const showCreateModal = ref(false)
const showKeyModal = ref(false)
const newKeyName = ref('')
const createdKey = ref('')

async function loadKeys() {
  const res = await api.get('/api-keys')
  apiKeys.value = res.data
}

async function createKey() {
  const res = await api.post('/api-keys', { name: newKeyName.value })
  const data: ApiKeyCreated = res.data
  createdKey.value = data.key
  showCreateModal.value = false
  newKeyName.value = ''
  showKeyModal.value = true
  await loadKeys()
}

async function toggleActive(key: ApiKey) {
  await api.patch(`/api-keys/${key.id}`, { is_active: !key.is_active })
  await loadKeys()
}

async function deleteKey(key: ApiKey) {
  if (!confirm(`確定要刪除「${key.name}」？`)) return
  await api.delete(`/api-keys/${key.id}`)
  await loadKeys()
}

function copyKey() {
  navigator.clipboard.writeText(createdKey.value)
}

function formatDate(d: string | null) {
  if (!d) return '-'
  return new Date(d).toLocaleString('zh-TW')
}

onMounted(loadKeys)
</script>

<template>
  <div>
    <div class="page-header">
      <h2>API Key 管理</h2>
      <button class="btn btn-primary" @click="showCreateModal = true">新增 API Key</button>
    </div>

    <table>
      <thead>
        <tr>
          <th>名稱</th>
          <th>Key 前綴</th>
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
          <td>
            <span :class="['badge', key.is_active ? 'badge-available' : 'badge-cancelled']">
              {{ key.is_active ? '啟用' : '停用' }}
            </span>
          </td>
          <td>{{ formatDate(key.created_at) }}</td>
          <td>{{ formatDate(key.last_used_at) }}</td>
          <td>
            <button
              :class="['btn btn-sm', key.is_active ? 'btn-danger' : 'btn-success']"
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
          <td colspan="6" style="text-align: center; color: #888">尚無 API Key</td>
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
            <input v-model="newKeyName" required placeholder="例如：3F 清潔平板" />
          </div>
          <div class="modal-actions">
            <button type="button" class="btn" @click="showCreateModal = false">取消</button>
            <button type="submit" class="btn btn-primary">建立</button>
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
