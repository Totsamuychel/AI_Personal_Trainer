<script setup lang="ts">
import { ref } from 'vue'
import Users from './components/Users.vue'
import Settings from './components/Settings.vue'
import { Users as UsersIcon, Settings as SettingsIcon } from 'lucide-vue-next'

const currentTab = ref('users')
</script>

<template>
  <div class="min-h-screen bg-gray-100 flex flex-col">
    <!-- Header -->
    <header class="bg-indigo-600 text-white shadow-lg p-4 flex justify-between items-center">
      <h1 class="text-2xl font-bold flex items-center gap-2">
        🏋️ AI Personal Trainer Admin
      </h1>
      <div class="flex gap-4">
        <button 
          @click="currentTab = 'users'"
          :class="['flex items-center gap-2 px-4 py-2 rounded-lg transition', currentTab === 'users' ? 'bg-white text-indigo-600' : 'hover:bg-indigo-500']"
        >
          <UsersIcon :size="20" /> Пользователи
        </button>
        <button 
          @click="currentTab = 'settings'"
          :class="['flex items-center gap-2 px-4 py-2 rounded-lg transition', currentTab === 'settings' ? 'bg-white text-indigo-600' : 'hover:bg-indigo-500']"
        >
          <SettingsIcon :size="20" /> Настройки LLM
        </button>
      </div>
    </header>

    <!-- Main Content -->
    <main class="flex-1 p-6 max-w-7xl mx-auto w-full">
      <Users v-if="currentTab === 'users'" />
      <Settings v-if="currentTab === 'settings'" />
    </main>
    
    <footer class="bg-white border-t p-4 text-center text-gray-500 text-sm">
      AI Personal Trainer Admin &copy; 2026
    </footer>
  </div>
</template>
