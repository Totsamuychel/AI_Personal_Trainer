<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { Save, Server, Key, Cpu } from 'lucide-vue-next'

const API_BASE = 'http://localhost:8000/admin'
const settings = ref<any>({})
const loading = ref(true)
const saving = ref(false)

const fetchSettings = async () => {
  loading.value = true
  try {
    const res = await axios.get(`${API_BASE}/settings`)
    settings.value = res.data
  } catch (err) {
    console.error('Failed to fetch settings', err)
  } finally {
    loading.value = false
  }
}

const saveSettings = async () => {
  saving.value = true
  try {
    await axios.put(`${API_BASE}/settings`, settings.value)
    alert('Настройки сохранены!')
  } catch (err) {
    console.error('Failed to save settings', err)
    alert('Ошибка при сохранении')
  } finally {
    saving.value = false
  }
}

onMounted(fetchSettings)
</script>

<template>
  <div class="max-w-2xl mx-auto bg-white rounded-xl shadow-md overflow-hidden">
    <div class="p-4 border-b bg-gray-50">
      <h2 class="text-xl font-semibold">Настройки LLM и API</h2>
    </div>

    <div v-if="loading" class="p-10 text-center text-gray-500">
      Загрузка...
    </div>

    <div v-else class="p-6 space-y-6">
      <!-- Provider -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2 flex items-center gap-2">
          <Cpu :size="16" /> Провайдер LLM
        </label>
        <select 
          v-model="settings.llm_provider"
          class="w-full border rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none"
        >
          <option value="ollama">Ollama (Локально)</option>
          <option value="openai">OpenAI (Облако)</option>
        </select>
      </div>

      <!-- Ollama Specific -->
      <div v-if="settings.llm_provider === 'ollama'" class="space-y-4 p-4 bg-blue-50 rounded-lg">
        <h3 class="font-bold text-blue-800 flex items-center gap-2">
          <Server :size="16" /> Настройки Ollama
        </h3>
        <div>
          <label class="block text-xs font-medium text-blue-700 uppercase">Base URL</label>
          <input 
            v-model="settings.ollama_base_url"
            type="text"
            class="w-full border rounded p-2 mt-1"
            placeholder="http://localhost:11434"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-blue-700 uppercase">Модель</label>
          <input 
            v-model="settings.ollama_model"
            type="text"
            class="w-full border rounded p-2 mt-1"
            placeholder="llama3.1:8b"
          />
        </div>
      </div>

      <!-- OpenAI Specific -->
      <div v-if="settings.llm_provider === 'openai'" class="space-y-4 p-4 bg-green-50 rounded-lg">
        <h3 class="font-bold text-green-800 flex items-center gap-2">
          <Key :size="16" /> Настройки OpenAI
        </h3>
        <div>
          <label class="block text-xs font-medium text-green-700 uppercase">API Key</label>
          <input 
            v-model="settings.openai_api_key"
            type="password"
            class="w-full border rounded p-2 mt-1"
            placeholder="sk-..."
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-green-700 uppercase">Модель</label>
          <input 
            v-model="settings.openai_model"
            type="text"
            class="w-full border rounded p-2 mt-1"
            placeholder="gpt-4o-mini"
          />
        </div>
      </div>

      <!-- Embeddings -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">Модель Embeddings</label>
        <input 
          v-model="settings.embedding_model"
          type="text"
          class="w-full border rounded-lg p-2 focus:ring-2 focus:ring-indigo-500 outline-none"
          placeholder="nomic-embed-text"
        />
      </div>

      <div class="pt-4 border-t">
        <button 
          @click="saveSettings"
          :disabled="saving"
          class="w-full bg-indigo-600 text-white py-3 rounded-lg font-bold hover:bg-indigo-700 transition flex items-center justify-center gap-2"
        >
          <Save :size="20" /> 
          {{ saving ? 'Сохранение...' : 'Сохранить настройки' }}
        </button>
      </div>
    </div>
  </div>
</template>
