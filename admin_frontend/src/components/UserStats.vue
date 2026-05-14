<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { adminHttp } from '../api/adminHttp'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Line, Bar } from 'vue-chartjs'
import { ArrowLeft, Activity, Utensils, Trophy, Dumbbell } from 'lucide-vue-next'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend)

const props = defineProps<{ user: any }>()
const emit = defineEmits(['back'])

const API_BASE = '/admin'
const activeTab = ref<'volume' | 'records' | 'workouts' | 'nutrition'>('volume')

const stats = ref<any>(null)
const nutrition = ref<any[]>([])
const records = ref<any[]>([])
const workouts = ref<any[]>([])
const loading = ref(true)

const fetchData = async () => {
  loading.value = true
  try {
    const [statsRes, nutritionRes, recordsRes, workoutsRes] = await Promise.all([
      adminHttp.get(`${API_BASE}/users/${props.user.id}/stats`),
      adminHttp.get(`${API_BASE}/users/${props.user.id}/nutrition`),
      adminHttp.get(`${API_BASE}/users/${props.user.id}/records`),
      adminHttp.get(`${API_BASE}/users/${props.user.id}/workouts`),
    ])
    stats.value = statsRes.data
    nutrition.value = nutritionRes.data
    records.value = recordsRes.data
    workouts.value = workoutsRes.data
  } catch (err) {
    console.error('Failed to fetch user data', err)
  } finally {
    loading.value = false
  }
}

const volumeChartData = computed(() => {
  const history = stats.value?.volume_history
  if (!history?.length) return null
  return {
    labels: history.map((h: any) => new Date(h.date).toLocaleDateString('ru')),
    datasets: [{
      label: 'Объём (кг)',
      backgroundColor: 'rgba(99,102,241,0.3)',
      borderColor: '#6366f1',
      data: history.map((h: any) => h.total_volume),
      tension: 0.3,
      fill: true,
    }],
  }
})

const nutritionChartData = computed(() => {
  if (!nutrition.value.length) return null
  const sorted = [...nutrition.value].reverse()
  return {
    labels: sorted.map((h: any) => new Date(h.date).toLocaleDateString('ru')),
    datasets: [
      {
        label: 'Калории',
        backgroundColor: '#f59e0b',
        data: sorted.map((h: any) => h.calories ?? 0),
      },
      {
        label: 'Белок (г)',
        backgroundColor: '#10b981',
        data: sorted.map((h: any) => h.protein_g ?? 0),
      },
    ],
  }
})

const chartOptions = { maintainAspectRatio: false, plugins: { legend: { position: 'top' as const } } }

const formatDate = (iso: string) => iso ? new Date(iso).toLocaleDateString('ru', { day: '2-digit', month: '2-digit', year: '2-digit' }) : '—'

onMounted(fetchData)
</script>

<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="flex items-center gap-4">
      <button @click="$emit('back')" class="p-2 hover:bg-gray-200 rounded-full transition">
        <ArrowLeft :size="22" />
      </button>
      <div>
        <h2 class="text-2xl font-bold">{{ user.name }}</h2>
        <p class="text-sm text-gray-500">ID: {{ user.telegram_id }} · {{ user.goal }} · {{ user.level }}</p>
      </div>
    </div>

    <!-- Profile Cards -->
    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
      <div class="bg-white rounded-xl shadow-sm p-4">
        <div class="text-xs text-gray-400 uppercase mb-1">Возраст</div>
        <div class="text-xl font-bold">{{ user.age ?? '—' }} <span class="text-sm font-normal text-gray-400">лет</span></div>
      </div>
      <div class="bg-white rounded-xl shadow-sm p-4">
        <div class="text-xs text-gray-400 uppercase mb-1">Вес</div>
        <div class="text-xl font-bold">{{ user.weight_kg ?? '—' }} <span class="text-sm font-normal text-gray-400">кг</span></div>
      </div>
      <div class="bg-white rounded-xl shadow-sm p-4">
        <div class="text-xs text-gray-400 uppercase mb-1">Рост</div>
        <div class="text-xl font-bold">{{ user.height_cm ?? '—' }} <span class="text-sm font-normal text-gray-400">см</span></div>
      </div>
      <div class="bg-white rounded-xl shadow-sm p-4">
        <div class="text-xs text-gray-400 uppercase mb-1">Сплит</div>
        <div class="text-xl font-bold">{{ user.preferred_split ?? '—' }}</div>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-1 bg-gray-100 p-1 rounded-xl w-fit">
      <button v-for="tab in [
        { id: 'volume',    label: 'Объём',      icon: Activity },
        { id: 'records',   label: 'Рекорды',    icon: Trophy },
        { id: 'workouts',  label: 'Тренировки', icon: Dumbbell },
        { id: 'nutrition', label: 'Питание',    icon: Utensils },
      ]" :key="tab.id"
        @click="activeTab = tab.id as any"
        :class="['flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition',
          activeTab === tab.id ? 'bg-white shadow text-indigo-600' : 'text-gray-500 hover:text-gray-700']"
      >
        <component :is="tab.icon" :size="15" />
        {{ tab.label }}
      </button>
    </div>

    <div v-if="loading" class="bg-white rounded-xl shadow-md p-16 text-center text-gray-400">
      Загрузка...
    </div>

    <template v-else>
      <!-- Volume Tab -->
      <div v-if="activeTab === 'volume'" class="bg-white rounded-xl shadow-md p-6">
        <h3 class="font-semibold mb-4">Тренировочный объём (тоннаж)</h3>
        <div class="h-72" v-if="volumeChartData">
          <Line :data="volumeChartData" :options="chartOptions" />
        </div>
        <div v-else class="h-72 flex items-center justify-center text-gray-400">Нет данных о тренировках</div>
      </div>

      <!-- Records Tab -->
      <div v-if="activeTab === 'records'" class="bg-white rounded-xl shadow-md overflow-hidden">
        <div class="p-4 border-b bg-gray-50">
          <h3 class="font-semibold">Личные рекорды (1RM)</h3>
        </div>
        <div v-if="records.length === 0" class="p-10 text-center text-gray-400">Рекорды не установлены</div>
        <table v-else class="w-full text-sm">
          <thead>
            <tr class="bg-gray-50 text-gray-500 text-xs uppercase">
              <th class="p-3 text-left">Упражнение</th>
              <th class="p-3 text-right">1RM (кг)</th>
              <th class="p-3 text-right">Подход</th>
              <th class="p-3 text-right">Дата</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in records" :key="r.exercise" class="border-t hover:bg-gray-50">
              <td class="p-3 font-medium">{{ r.exercise }}</td>
              <td class="p-3 text-right font-bold text-indigo-600">{{ r.one_rm_est }}</td>
              <td class="p-3 text-right text-gray-600">{{ r.weight_kg }} × {{ r.reps }}</td>
              <td class="p-3 text-right text-gray-400">{{ formatDate(r.date) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Workouts Tab -->
      <div v-if="activeTab === 'workouts'" class="space-y-3">
        <div v-if="workouts.length === 0" class="bg-white rounded-xl shadow-md p-10 text-center text-gray-400">
          Нет записанных тренировок
        </div>
        <div v-for="w in workouts" :key="w.id" class="bg-white rounded-xl shadow-md overflow-hidden">
          <div class="flex items-center justify-between p-4 bg-gray-50 border-b">
            <div class="flex items-center gap-2">
              <span class="font-semibold">{{ w.workout_type }}</span>
              <span class="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full">{{ w.duration_min }} мин</span>
            </div>
            <span class="text-sm text-gray-400">{{ formatDate(w.date) }}</span>
          </div>
          <div class="p-3 space-y-1">
            <div v-for="ex in w.exercises" :key="ex.name"
              class="flex items-center justify-between text-sm px-2 py-1 rounded hover:bg-gray-50">
              <span class="font-medium">{{ ex.name }}</span>
              <span class="text-gray-500">
                {{ ex.sets }} × [{{ (ex.weight_kg ?? []).join(', ') }}] кг
              </span>
            </div>
          </div>
          <div v-if="w.notes" class="px-4 pb-3 text-xs text-gray-400 italic">{{ w.notes }}</div>
        </div>
      </div>

      <!-- Nutrition Tab -->
      <div v-if="activeTab === 'nutrition'" class="space-y-4">
        <div class="bg-white rounded-xl shadow-md p-6">
          <h3 class="font-semibold mb-4">Калории и белок</h3>
          <div class="h-64" v-if="nutritionChartData">
            <Bar :data="nutritionChartData" :options="chartOptions" />
          </div>
          <div v-else class="h-64 flex items-center justify-center text-gray-400">Нет данных о питании</div>
        </div>
        <div class="bg-white rounded-xl shadow-md overflow-hidden">
          <div class="p-4 border-b bg-gray-50">
            <h3 class="font-semibold">Дневник питания</h3>
          </div>
          <div v-if="nutrition.length === 0" class="p-10 text-center text-gray-400">Нет записей</div>
          <table v-else class="w-full text-sm">
            <thead>
              <tr class="bg-gray-50 text-gray-500 text-xs uppercase">
                <th class="p-3 text-left">Дата</th>
                <th class="p-3 text-left">Приём</th>
                <th class="p-3 text-right">Ккал</th>
                <th class="p-3 text-right">Белок</th>
                <th class="p-3 text-right">Углев.</th>
                <th class="p-3 text-right">Жиры</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="n in nutrition" :key="n.id" class="border-t hover:bg-gray-50">
                <td class="p-3 text-gray-400">{{ formatDate(n.date) }}</td>
                <td class="p-3 font-medium">{{ n.meal_name }}</td>
                <td class="p-3 text-right font-bold text-amber-600">{{ n.calories ?? '—' }}</td>
                <td class="p-3 text-right text-green-600">{{ n.protein_g ?? '—' }}г</td>
                <td class="p-3 text-right text-blue-500">{{ n.carbs_g ?? '—' }}г</td>
                <td class="p-3 text-right text-orange-500">{{ n.fat_g ?? '—' }}г</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </div>
</template>
