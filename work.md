# AI Personal Trainer — Статус проекта
_Обновлено: 2026-06-11_

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
- [x] `GET /admin/users` — список пользователей (полная сериализация)
- [x] `POST /admin/users/{telegram_id}/message` — отправка сообщения пользователю
- [x] `POST /admin/broadcast` — рассылка всем пользователям
- [x] `GET/PUT /admin/settings` — настройки LLM
- [x] `GET /admin/users/{id}/stats` — объём тренировок
- [x] `GET /admin/users/{id}/records` — личные рекорды
- [x] `GET /admin/users/{id}/workouts` — история тренировок с упражнениями
- [x] `GET /admin/users/{id}/nutrition` — дневник питания

### Admin Frontend (Vue 3 + Vite + Tailwind)
- [x] Таблица пользователей с кнопками (статистика, написать)
- [x] Рассылка broadcast всем пользователям
- [x] `UserStats` — 4 вкладки: Объём, Рекорды, Тренировки, Питание
- [x] Графики (Chart.js): тренировочный объём, калории/белок
- [x] Таблица личных рекордов (1RM) с датой
- [x] История тренировок с раскрытием упражнений
- [x] Дневник питания (КБЖУ)
- [x] Настройки LLM (Ollama / OpenAI)
- [x] Vite proxy для dev-режима
- [x] nginx.conf + Dockerfile для production
- [x] Сервис `frontend` в docker-compose (порт 3000)

### Инфраструктура
- [x] `Dockerfile`: non-root user (`appuser`), `PYTHONDONTWRITEBYTECODE`, `PYTHONPATH=/app`, правильный `CMD`
- [x] `docker-compose.yml`: healthcheck для postgres и ollama, `DATABASE_URL` в боте, лимит памяти ollama (8G), Redis-сервис
- [x] `bot/main.py`: `RedisStorage` с fallback на `MemoryStorage` (если Redis недоступен)
- [x] `.env.example` с полным набором переменных

---

## Баги

### 🔴 Критические

_Нет открытых критических багов._

### 🟡 Средние

_Нет открытых средних багов._

### ✅ Исправлено (2026-06-11)

- [x] `get_workout_history` не делал eager-load `exercises` → `MissingGreenlet` при доступе из `get_workout_history_tool`. Добавлен `selectinload`.
- [x] `llm.py`: смена OpenAI API-ключа не пересоздавала singleton (ключ не входил в cache-key). Добавлен sha256-fingerprint ключа в `settings_str`.
- [x] `sheets/client.py`: блокирующие вызовы gspread в `async`-методах стопорили event loop. Тела вынесены в `_*_sync` и вызываются через `run_in_executor`.
- [x] `bot/handlers/agent.py`: ответ агента отправлялся без нормализации (`content` мог быть list), без проверки на пустоту и без разбивки на куски >4096 символов. Добавлены `_normalize_content` и `_send_chunked`.
- [x] `nutrition_tools.py`: удалён мёртвый `chain = prompt | llm`.
- [x] Добавлен `.dockerignore` — `credentials.json`, `.env`, `*.db` больше не попадают в образ.

---

### Тесты
- [x] `test_crud.py` — 17 тестов: 1RM формула (3), User CRUD (4), Workout (4), Personal Records (2), Nutrition (1), SystemSettings (2), Volume history (1)
- [x] `test_api.py` — 10 тестов: root, публичные user-эндпоинты (4), admin-эндпоинты (4), проверка auth (1)
- [x] Все 27 тестов проходят на SQLite in-memory без PostgreSQL

### Seed-данные
- [x] `scripts/seed_test_db.py` — реалистичный тестовый пользователь: 10 тренировок за 28 дней, 10 записей питания, личные рекорды, план на неделю

---

## Что не реализовано (out of scope / roadmap)

- **QLoRA fine-tuning** — ML pipeline, roadmap v2
- **Компьютерное зрение** — MediaPipe для анализа техники, roadmap v1.1
