<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '../api/client'
import type { CleaningTask } from '../types'

const tasks = ref<CleaningTask[]>([])
const loading = ref(true)
const error = ref('')

const fetchTasks = async () => {
  loading.value = true
  try {
    const response = await api.get('/housekeeping/my-tasks')
    tasks.value = response.data
    error.value = ''
  } catch (err: any) {
    error.value = '無法載入任務清單'
    console.error(err)
  } finally {
    loading.value = false
  }
}

const updateStatus = async (task: CleaningTask, newStatus: string) => {
  try {
    await api.put(`/housekeeping/tasks/${task.id}/status`, { status: newStatus })
    await fetchTasks()
  } catch (err: any) {
    alert('更新狀態失敗: ' + (err.response?.data?.detail || err.message))
  }
}

onMounted(fetchTasks)

const getStatusLabel = (status: string) => {
  switch (status) {
    case 'pending': return '待處理'
    case 'in_progress': return '進行中'
    case 'completed': return '已完成'
    case 'cancelled': return '已取消'
    default: return status
  }
}

const getCleaningTypeLabel = (type: string) => {
  return type === 'checkout' ? '退房清潔' : '續住清潔'
}

const activeTasks = () => tasks.value.filter(t => t.status === 'pending' || t.status === 'in_progress')
const completedTasks = () => tasks.value.filter(t => t.status === 'completed')
</script>

<template>
  <div class="cleaner-tasks">
    <div class="header">
      <h1>我的清潔任務</h1>
      <button @click="fetchTasks" class="refresh-btn">重新整理</button>
    </div>

    <div v-if="loading" class="loading">載入中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    
    <div v-else>
      <section class="task-section">
        <h2>待辦任務</h2>
        <div v-if="activeTasks().length === 0" class="empty-state">目前沒有指派的任務</div>
        <div v-else class="task-grid">
          <div v-for="task in activeTasks()" :key="task.id" class="task-card" :class="task.status">
            <div class="task-header">
              <span class="room-number">{{ task.room_number }}</span>
              <span class="task-type" :class="task.cleaning_type">{{ getCleaningTypeLabel(task.cleaning_type) }}</span>
            </div>
            <div class="task-body">
              <div class="status-info">狀態: {{ getStatusLabel(task.status) }}</div>
            </div>
            <div class="task-actions">
              <button 
                v-if="task.status === 'pending'" 
                @click="updateStatus(task, 'in_progress')"
                class="start-btn"
              >
                開始清潔
              </button>
              <button 
                v-if="task.status === 'in_progress'" 
                @click="updateStatus(task, 'completed')"
                class="complete-btn"
              >
                完成清潔
              </button>
            </div>
          </div>
        </div>
      </section>

      <section class="task-section completed">
        <h2>今日已完成</h2>
        <div v-if="completedTasks().length === 0" class="empty-state">今日尚無完成記錄</div>
        <div v-else class="completed-list">
          <div v-for="task in completedTasks()" :key="task.id" class="completed-item">
            <span class="room-number">{{ task.room_number }}</span>
            <span class="task-type">{{ getCleaningTypeLabel(task.cleaning_type) }}</span>
            <span class="time">{{ new Date(task.updated_at).toLocaleTimeString() }}</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.cleaner-tasks {
  padding: 1rem;
  max-width: 800px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.refresh-btn {
  padding: 0.5rem 1rem;
  background-color: #f0f0f0;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.task-section {
  margin-bottom: 3rem;
}

h2 {
  border-left: 4px solid #4caf50;
  padding-left: 0.5rem;
  margin-bottom: 1rem;
}

.task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.task-card {
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 1rem;
  background: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.task-card.in_progress {
  border-color: #ff9800;
  background-color: #fffde7;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.room-number {
  font-size: 1.5rem;
  font-weight: bold;
}

.task-type {
  font-size: 0.8rem;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  background: #eee;
}

.task-type.checkout {
  background: #ffebee;
  color: #c62828;
}

.task-actions {
  margin-top: 1.5rem;
}

.task-actions button {
  width: 100%;
  padding: 0.8rem;
  border: none;
  border-radius: 4px;
  font-weight: bold;
  cursor: pointer;
}

.start-btn {
  background-color: #2196f3;
  color: white;
}

.complete-btn {
  background-color: #4caf50;
  color: white;
}

.completed-list {
  background: #fafafa;
  border-radius: 8px;
  overflow: hidden;
}

.completed-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid #eee;
}

.completed-item:last-child {
  border-bottom: none;
}

.completed-item .room-number {
  font-size: 1.1rem;
}

.completed-item .time {
  color: #888;
  font-size: 0.9rem;
}

.empty-state {
  color: #888;
  text-align: center;
  padding: 2rem;
  background: #f9f9f9;
  border-radius: 8px;
}
</style>
