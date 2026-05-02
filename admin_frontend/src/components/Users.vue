<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { MessageSquare, Send } from 'lucide-vue-next'

const API_BASE = 'http://localhost:8000/admin'
const users = ref<any[]>([])
const loading = ref(true)
const selectedUser = ref<any>(null)
const messageText = ref('')
const sending = ref(false)

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

const openMessageModal = (user: any) => {
  selectedUser.value = user
  messageText.value = ''
}

const sendMessage = async () => {
  if (!messageText.value.trim() || !selectedUser.value) return
  
  sending.value = true
  try {
    await axios.post(`${API_BASE}/users/${selectedUser.value.telegram_id}/message`, {
      text: messageText.value
    })
    alert('Сообщение отправлено!')
    selectedUser.value = null
  } catch (err) {
    console.error('Failed to send message', err)
    alert('Ошибка при отправке сообщения')
  } finally {
    sending.value = false
  }
}

onMounted(fetchUsers)
</script>

<template>
  <div class="bg-white rounded-xl shadow-md overflow-hidden">
    <div class="p-4 border-b bg-gray-50 flex justify-between items-center">
      <h2 class="text-xl font-semibold">База пользователей</h2>
      <button @click="fetchUsers" class="text-sm text-indigo-600 hover:underline">Обновить</button>
    </div>

    <div v-if="loading" class="p-10 text-center text-gray-500">
      Загрузка...
    </div>

    <div v-else-if="users.length === 0" class="p-10 text-center text-gray-500">
      Пользователей пока нет.
    </div>

    <table v-else class="w-full text-left border-collapse">
      <thead>
        <tr class="bg-gray-100 text-gray-600 text-sm uppercase">
          <th class="p-4">ID</th>
          <th class="p-4">Имя</th>
          <th class="p-4">Telegram ID</th>
          <th class="p-4">Цель</th>
          <th class="p-4">Уровень</th>
          <th class="p-4 text-center">Действия</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.id" class="border-t hover:bg-gray-50">
          <td class="p-4">{{ user.id }}</td>
          <td class="p-4 font-medium">{{ user.name }}</td>
          <td class="p-4 font-mono text-sm">{{ user.telegram_id }}</td>
          <td class="p-4">{{ user.goal }}</td>
          <td class="p-4 capitalize">{{ user.level }}</td>
          <td class="p-4 text-center">
            <button 
              @click="openMessageModal(user)"
              class="bg-indigo-100 text-indigo-700 p-2 rounded-lg hover:bg-indigo-200 transition flex items-center gap-2 mx-auto"
            >
              <MessageSquare :size="16" /> Написать
            </button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Modal -->
    <div v-if="selectedUser" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div class="bg-white rounded-xl shadow-2xl max-w-md w-full p-6">
        <h3 class="text-lg font-bold mb-4">Написать пользователю {{ selectedUser.name }}</h3>
        <textarea 
          v-model="messageText"
          class="w-full border rounded-lg p-3 h-32 focus:ring-2 focus:ring-indigo-500 outline-none"
          placeholder="Введите ваше сообщение..."
        ></textarea>
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
            <Send v-if="!sending" :size="18" />
            <span v-else>Отправка...</span>
            {{ !sending ? 'Отправить' : '' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
