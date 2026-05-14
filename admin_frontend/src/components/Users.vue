<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { MessageSquare, Send, BarChart2, RefreshCw, Radio } from 'lucide-vue-next'
import UserStats from './UserStats.vue'

const API_BASE = '/admin'
const users = ref<any[]>([])
const loading = ref(true)
const selectedUser = ref<any>(null)
const viewingStats = ref<any>(null)
const messageText = ref('')
const sending = ref(false)
const broadcastMode = ref(false)

const fetchUsers = async () => {
  loading.value = true
  try {
    const res = await axios.get(`${API_BASE}/users`)
    users.value = res.data
  } catch (err) {
    console.error('Failed to fetch users', err)
  } finally {
    loading.value = false
  }
}

const openMessage = (user: any) => {
  broadcastMode.value = false
  selectedUser.value = user
  messageText.value = ''
}

const openBroadcast = () => {
  broadcastMode.value = true
  selectedUser.value = { name: 'всем пользователям' }
  messageText.value = ''
}

const sendMessage = async () => {
  if (!messageText.value.trim()) return
  sending.value = true
  try {
    if (broadcastMode.value) {
      const res = await axios.post(`${API_BASE}/broadcast`, { text: messageText.value })
      alert(`Отправлено: ${res.data.sent}, ошибок: ${res.data.failed}`)
    } else {
      await axios.post(`${API_BASE}/users/${selectedUser.value.telegram_id}/message`, { text: messageText.value })
      alert('Сообщение отправлено!')
    }
    selectedUser.value = null
  } catch (err) {
    console.error('Failed to send message', err)
    alert('Ошибка при отправке сообщения')
  } finally {
    sending.value = false
  }
}

const goalLabel: Record<string, string> = {
  strength: '💪 Сила',
  hypertrophy: '🏗️ Гипертрофия',
  fat_loss: '📉 Похудение',
  endurance: '🏃 Выносливость',
}

onMounted(fetchUsers)
</script>

<template>
  <div v-if="viewingStats">
    <UserStats :user="viewingStats" @back="viewingStats = null" />
  </div>

  <div v-else class="bg-white rounded-xl shadow-md overflow-hidden">
    <div class="p-4 border-b bg-gray-50 flex justify-between items-center">
      <h2 class="text-xl font-semibold">
        База пользователей
        <span class="ml-2 text-sm font-normal text-gray-400">{{ users.length }}</span>
      </h2>
      <div class="flex gap-2">
        <button
          @click="openBroadcast"
          class="flex items-center gap-1.5 text-sm bg-amber-100 text-amber-700 px-3 py-1.5 rounded-lg hover:bg-amber-200 transition"
        >
          <Radio :size="16" /> Broadcast
        </button>
        <button
          @click="fetchUsers"
          class="flex items-center gap-1.5 text-sm text-indigo-600 hover:underline px-2 py-1.5"
        >
          <RefreshCw :size="15" /> Обновить
        </button>
      </div>
    </div>

    <div v-if="loading" class="p-10 text-center text-gray-500">Загрузка...</div>
    <div v-else-if="users.length === 0" class="p-10 text-center text-gray-500">Пользователей пока нет.</div>

    <table v-else class="w-full text-left border-collapse">
      <thead>
        <tr class="bg-gray-100 text-gray-500 text-xs uppercase">
          <th class="p-4">ID</th>
          <th class="p-4">Имя</th>
          <th class="p-4">Telegram ID</th>
          <th class="p-4">Цель</th>
          <th class="p-4">Уровень</th>
          <th class="p-4">Зарегистрирован</th>
          <th class="p-4 text-center">Действия</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="user in users" :key="user.id"
          class="border-t hover:bg-indigo-50 transition cursor-pointer"
          @click="viewingStats = user"
        >
          <td class="p-4 text-gray-400 text-sm">{{ user.id }}</td>
          <td class="p-4 font-medium">{{ user.name }}</td>
          <td class="p-4 font-mono text-sm text-gray-500">{{ user.telegram_id }}</td>
          <td class="p-4 text-sm">{{ goalLabel[user.goal] ?? user.goal ?? '—' }}</td>
          <td class="p-4 text-sm capitalize">{{ user.level ?? '—' }}</td>
          <td class="p-4 text-sm text-gray-400">
            {{ user.created_at ? new Date(user.created_at).toLocaleDateString('ru') : '—' }}
          </td>
          <td class="p-4">
            <div class="flex justify-center gap-2">
              <button
                @click.stop="viewingStats = user"
                class="bg-indigo-100 text-indigo-700 p-2 rounded-lg hover:bg-indigo-200 transition"
                title="Статистика"
              >
                <BarChart2 :size="16" />
              </button>
              <button
                @click.stop="openMessage(user)"
                class="bg-green-100 text-green-700 p-2 rounded-lg hover:bg-green-200 transition"
                title="Написать"
              >
                <MessageSquare :size="16" />
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Message Modal -->
    <div v-if="selectedUser" class="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-xl shadow-2xl max-w-md w-full p-6">
        <h3 class="text-lg font-bold mb-1">Сообщение</h3>
        <p class="text-sm text-gray-500 mb-4">
          {{ broadcastMode ? 'Рассылка всем пользователям' : `Получатель: ${selectedUser.name}` }}
        </p>
        <textarea
          v-model="messageText"
          class="w-full border rounded-lg p-3 h-32 focus:ring-2 focus:ring-indigo-500 outline-none resize-none"
          placeholder="Введите сообщение..."
        />
        <div class="flex justify-end gap-3 mt-4">
          <button
            @click="selectedUser = null"
            class="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
          >
            Отмена
          </button>
          <button
            @click="sendMessage"
            :disabled="sending || !messageText.trim()"
            class="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
          >
            <Send v-if="!sending" :size="16" />
            <span>{{ sending ? 'Отправка...' : 'Отправить' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
