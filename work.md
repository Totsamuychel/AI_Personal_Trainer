# AI Personal Trainer — Статус проекта
_Обновлено: 2026-05-13_

---

## Что уже сделано

### База данных
- [x] 8 таблиц: `User`, `WorkoutSession`, `ExerciseLog`, `PersonalRecord`, `WeeklyPlan`, `NutritionLog`, `SystemSettings`
- [x] Boolean типы для флагов (`morning_tip_enabled`, `is_active`)
- [x] Индексы на `user_id`, `date`, `exercise_name`
- [x] Cascade delete на всех связях
- [x] Connection pooling (`pool_size=5`, `max_overflow=10`, `pool_recycle=1800`)
- [x] Alembic миграции (4 версии)
- [x] `selectinload` в `get_volume_history` — N+1 проблема устранена
- [x] Все импорты (`distinct`, `func`) подняты в начало `crud.py`
- [x] Enum: `GoalType` (strength/hypertrophy/fat_loss/endurance), `WeekType` (4-недельная периодизация)

### Telegram-бот (aiogram 3.x)
- [x] `/start` — регистрация с FSM (язык → имя → возраст → рост → вес → цель → генерация первого плана)
- [x] `/workout` — логирование тренировки (тип → упражнения → подходы/вес/повторы → длительность)
- [x] `/nutrition` — запись питания с расчётом КБЖУ через агента
- [x] `/plan` — показ активного плана на неделю (парсинг JSON → форматирование)
- [x] `/progress` — интерактивное меню с графиками (inline keyboard)
- [x] `/tip [упражнение]` — поиск по RAG и показ техники
- [x] `/settings` — управление утренними советами (вкл/выкл, смена времени, перерегистрация)
- [x] Fallback handler — любой текст → агент
- [x] Двуязычность (ru/en) во всех handler'ах
- [x] Правильная PR-логика в workout.py: проход по парам `(weight[i], reps[i])` для формулы Epley

### Графики прогресса (progress.py)
- [x] График 1RM тренда (линия, аннотация последнего значения, regression trend, stats box)
- [x] График объёма тренировок (столбцы по типу тренировки + moving average)
- [x] Таблица личных рекордов (текстовый формат)
- [x] Dark premium тема без мутации глобальных `rcParams` (thread-safe)
- [x] Используется `crud.calculate_1rm` для единообразия

### AI Agent (LangGraph)
- [x] Граф: `load_profile → retrieve_context → agent → should_continue → tools / store_memory`
- [x] Инструменты: `calculate_macros_from_text`, `log_nutrition_tool`, `log_workout_session_tool`, `get_workout_history_tool`, `generate_weekly_plan_tool`, `get_current_plan_tool`, `update_sheet_workout_report_tool`
- [x] System prompt с контекстом: профиль, личные рекорды, история тренировок, RAG
- [x] 4-недельная периодизация: Strength → Hypertrophy → Volume → Deload
- [x] Безопасные шаблоны промптов (`string.Template` с `$`-синтаксисом)

### LLM-слой (llm.py)
- [x] Async singleton с `asyncio.Lock`
- [x] Поддержка двух провайдеров: OpenAI (GPT-4o-mini) и Ollama (Llama 3.1 / gpt-oss:20b)
- [x] `base_url = ""` инициализируется перед ветвлением — `UnboundLocalError` устранён
- [x] Fallback на env-переменные при недоступности БД
- [x] Инициализация из `SystemSettings` в БД

### RAG-система (ChromaDB)
- [x] Индексирование JSON-упражнений: Push, Pull, Legs
- [x] Выписки из книг: `lifting_science_extracts.json`, `nutrition_principles_extracts.json`
- [x] Поддержка PDF (постраничная загрузка)
- [x] Семантический поиск с фильтром по topic
- [x] Долгосрочная память пользователя: `save_memory`, `recall`, `extract_and_save_facts`

### Google Sheets
- [x] 5 листов: Profile, Nutrition, Monthly Plan, Weekly Plan, Workout Results
- [x] Логирование тренировок с расчётом 1RM
- [x] Логирование питания
- [x] Синхронизация плана на неделю

### Планировщик
- [x] APScheduler — проверка каждую минуту
- [x] Персональные утренние советы через агента по расписанию из профиля пользователя

### FastAPI
- [x] `GET /` — health check
- [x] `GET /api/users/{telegram_id}` — профиль
- [x] `GET /api/users/{telegram_id}/workouts` — история тренировок
- [x] `GET /api/users/{telegram_id}/plan` — текущий план
- [x] Admin: список пользователей, отправка сообщений, настройки LLM, статистика

### Инфраструктура
- [x] `Dockerfile`: non-root user (`appuser`), `PYTHONDONTWRITEBYTECODE`, `PYTHONPATH=/app`, правильный `CMD`
- [x] `docker-compose.yml`: healthcheck для postgres и ollama, `DATABASE_URL` в боте, лимит памяти ollama (8G), Redis-сервис
- [x] `bot/main.py`: `RedisStorage` с fallback на `MemoryStorage` (если Redis недоступен)
- [x] `.env.example` с полным набором переменных

---

## Баги — требуют исправления

### 🔴 Критические

_Нет открытых критических багов._

### 🟡 Средние

_Нет открытых средних багов._

---

## Что не реализовано

### ❌ Отсутствует полностью

- **Admin frontend** — папка `admin_frontend/` создана, но пустая. React/Vue панель не написана.
- **Тесты** — покрытие минимальное: 3 теста (`test_create_user`, `test_create_workout`, `test_1rm_calculation`). Нет тестов для handlers, agent, RAG, sheets, scheduler.
- **API аутентификация** — FastAPI endpoints открыты без JWT/API key.
- **QLoRA fine-tuning** — упомянут в документации, pipeline не создан.
- **Компьютерное зрение** — MediaPipe для анализа техники (в roadmap v1.1, не начат).

### Приоритетный список задач

1. **Исправить баг `plt.Rectangle`** в `progress.py:236` (ломает volume chart)
2. **Убрать синхронный вызов** в `store_memory_node` (блокировка event loop)
3. **Защитить `SheetsClient()` от краша при старте** (graceful init)
4. **Написать тесты** — минимум для handlers и agent (20+ тестов)
5. **Добавить JWT** к FastAPI admin endpoints
6. **Реализовать admin frontend** (или убрать пустую папку)
