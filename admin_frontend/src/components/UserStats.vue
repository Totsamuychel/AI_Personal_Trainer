<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { 
  Chart as ChartJS, 
  CategoryScale, 
  LinearScale, 
  PointElement, 
  LineElement, 
  Title, 
  Tooltip, 
  Legend,
  BarElement
} from 'chart.js'
import { Line, Bar } from 'vue-chartjs'
import { ArrowLeft, Activity, Utensils } from 'lucide-vue-next'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend
)

const props = defineProps<{
  user: any
}>()

const emit = defineProps(['back'])

const API_BASE = 'http://localhost:8000/admin'
const stats = ref<any>(null)
const nutrition = ref<any[]>([])
const loading = ref(true)

const fetchData = async () => {
  loading.value = true
  try {
    const [statsRes, nutritionRes] = await Promise.all([
      axios.get(`${API_BASE}/users/${props.user.id}/stats`),
      axios.get(`${API_BASE}/users/${props.user.id}/nutrition`)
    ])
    stats.value = statsRes.data
    nutrition.value = nutritionRes.data
  } catch (err) {
    console.error('Failed to fetch user data', err)
  } finally {
    loading.value = false
  }
}

const volumeChartData = computed(() => {
  if (!stats.value?.volume_history) return null
  
  const history = stats.value.volume_history
  return {
    labels: history.map((h: any) => new Date(h.date).toLocaleDateString()),
    datasets: [
      {
        label: 'Общий объем (кг)',
        backgroundColor: '#6366f1',
        borderColor: '#6366f1',
        data: history.map((h: any) => h.total_volume),
        tension: 0.3
      }
    ]
  }
})

const nutritionChartData = computed(() => {
  if (!nutrition.value.length) return null
  
  // Group by date and average
  const sorted = [...nutrition.value].reverse()
  return {
    labels: sorted.map((h: any) => new Date(h.date).toLocaleDateString()),
    datasets: [
      {
        label: 'Калории',
        backgroundColor: '#f59e0b',
        data: sorted.map((h: any) => h.calories)
      },
      {
        label: 'Белок (г)',
        backgroundColor: '#10b981',
        data: sorted.map((h: any) => h.protein_g)
      }
    ]
  }
})

onMounted(fetchData)
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center gap-4">
      <button @click="$emit('back')" class="p-2 hover:bg-gray-200 rounded-full transition">
        <ArrowLeft :size="24" />
      </button>
      <h2 class="text-2xl font-bold">Прогресс пользователя: {{ user.name }}</h2>
    </div>

    <div v-if="loading" class="p-20 text-center text-gray-500">Загрузка данных...</div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Volume Chart -->
      <div class="bg-white p-6 rounded-xl shadow-md">
        <h3 class="text-lg font-semibold mb-4 flex items-center gap-2">
          <Activity class="text-indigo-600" /> Тренировочный объем
        </h3>
        <div class="h-64" v-if="volumeChartData">
          <Line :data="volumeChartData" :options="{ maintainAspectRatio: false }" />
        </div>
        <div v-else class="h-64 flex items-center justify-center text-gray-400">Нет данных о тренировках</div>
      </div>

      <!-- Nutrition Chart -->
      <div class="bg-white p-6 rounded-xl shadow-md">
        <h3 class="text-lg font-semibold mb-4 flex items-center gap-2">
          <Utensils class="text-amber-500" /> Питание (последние записи)
        </h3>
        <div class="h-64" v-if="nutritionChartData">
          <Bar :data="nutritionChartData" :options="{ maintainAspectRatio: false }" />
        </div>
        <div v-else class="h-64 flex items-center justify-center text-gray-400">Нет данных о питании</div>
      </div>

      <!-- User Info Card -->
      <div class="bg-white p-6 rounded-xl shadow-md md:col-span-2">
        <h3 class="text-lg font-semibold mb-4">Подробная информация</h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="bg-gray-50 p-3 rounded-lg">
            <div class="text-xs text-gray-500 uppercase">Возраст</div>
            <div class="font-bold">{{ user.age || '—' }} лет</div>
          </div>
          <div class="bg-gray-50 p-3 rounded-lg">
            <div class="text-xs text-gray-500 uppercase">Вес</div>
            <div class="font-bold">{{ user.weight_kg || '—' }} кг</div>
          </div>
          <div class="bg-gray-50 p-3 rounded-lg">
            <div class="text-xs text-gray-500 uppercase">Цель</div>
            <div class="font-bold capitalize">{{ user.goal }}</div>
          </div>
          <div class="bg-gray-50 p-3 rounded-lg">
            <div class="text-xs text-gray-500 uppercase">Уровень</div>
            <div class="font-bold capitalize">{{ user.level }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
