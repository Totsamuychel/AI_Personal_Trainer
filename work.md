[x] ai_trainer/agent/llm.py — 🔴 КРИТИЧЕСКИЙ БАГ
Файл содержит реальный баг типа UnboundLocalError :

python
# ПРОБЛЕМА: base_url объявляется только в ветке 'ollama'
if provider == "openai":
    model = settings.openai_model
    api_key = settings.openai_api_key
    # base_url здесь НЕ объявлен!
else:
    model = settings.ollama_model
    base_url = settings.ollama_base_url  # только здесь

# Но ниже используется для обоих провайдеров:
settings_str = f"{provider}:{model}:{base_url if provider == 'ollama' else ''}"
# ^ Если provider == 'openai' и первый раз — base_url не определён → NameError
Если provider == "openai" при первом вызове, переменная base_url не будет определена в строке формирования settings_str. Это приведёт к падению приложения при первом обращении к OpenAI-провайдеру.

Исправление:

python
base_url = ""  # инициализировать перед блоком if/else
if provider == "openai":
    ...
else:
    base_url = settings.ollama_base_url
Дополнительные проблемы в этом файле:

get_llm() — синхронная функция, открывающая DB-сессию — при вызове из async-контекста (LangGraph agent) блокирует event loop

Глобальный singleton _llm — не thread-safe, при многопоточности возможен race condition

Нет возврата _llm в конце функции после основного блока — при исключении без ранее закэшированного _llm функция вернёт None

[x] ai_trainer/db/crud.py — 🟡 ПРОБЛЕМЫ ПРОИЗВОДИТЕЛЬНОСТИ
N+1 проблема в get_volume_history :

python
# ПЛОХО: для каждой сессии — отдельный SELECT в базу
for session in sessions:
    ex_result = await db.execute(
        select(models.ExerciseLog).filter(...)
    )
При 30 сессиях это генерирует 31 запрос (1 для сессий + 30 для упражнений). Правильное решение — использовать selectinload:

python
# ХОРОШО
from sqlalchemy.orm import selectinload

result = await db.execute(
    select(models.WorkoutSession)
    .options(selectinload(models.WorkoutSession.exercises))
    .filter(...)
    .limit(limit)
)
Импорты внутри функций — антипаттерн :

python
# Внутри get_system_settings:
import os          # должен быть вверху файла

# Внутри get_exercise_progress_with_dates:
from sqlalchemy import func  # уже импортировано вверху как select, update

# Внутри get_user_exercises:
from sqlalchemy import distinct  # аналогично
Дублирование кода sync/async — вся нижняя половина файла дублирует верхнюю для sync-вариантов. Можно было бы использовать один набор helpers и адаптеры для sync/async.

ai_trainer/db/models.py — 🟡 ДИЗАЙН БД
Использование Integer вместо Boolean :

python
# ПЛОХО
morning_tip_enabled = Column(Integer, default=1)  # 0/1 маскируется под Integer
is_active = Column(Integer, default=1)

# ЛУЧШЕ
from sqlalchemy import Boolean
morning_tip_enabled = Column(Boolean, default=True)
is_active = Column(Boolean, default=True)
Отсутствие индексов на часто запрашиваемых полях :

python
# Рекомендуется добавить:
user_id = Column(Integer, ForeignKey("users.id"), index=True)
date = Column(DateTime, default=..., index=True)
name = Column(String, index=True)  # в ExerciseLog — фильтрация по имени упражнения
Нет каскадного удаления — если удалить пользователя, его WorkoutSession, ExerciseLog, PersonalRecord останутся в БД как "сироты":

python
# Добавить cascade:
workouts = relationship("WorkoutSession", back_populates="user", cascade="all, delete-orphan")
PersonalRecord не имеет обратной связи с User — не критично, но неконсистентно с остальными моделями.

ai_trainer/db/database.py — 🟡 КОНФИГУРАЦИЯ
Движок PostgreSQL создаётся без пула соединений :

python
# Для production добавить параметры пула:
_engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,  # переподключение каждые 30 мин
)
В db_session есть избыточный await session.commit() в блоке try — при исключении коммит не выполнится, но наличие его здесь создаёт ложное ощущение двойного коммита.

ai_trainer/agent/trainer_agent.py — 🟡 АРХИТЕКТУРА
Прямые SQL-запросы в load_user_profile_node нарушают абстракцию CRUD-слоя :

python
# ПЛОХО — дублирует логику crud.get_active_weekly_plan
plan_result = await db.execute(
    select(models.WeeklyPlan).filter(
        models.WeeklyPlan.user_id == user.id,
        models.WeeklyPlan.is_active == 1
    )
)

# ЛУЧШЕ
plan = await crud.get_active_weekly_plan(db, user.id)
store_memory_node вызывает синхронный LLM из async-контекста :

python
memory_store.extract_and_save_facts(conv_history, llm)  # sync call → блокирует event loop
Если extract_and_save_facts внутри вызывает синхронный LLM (ChatOllama/ChatOpenAI), это заблокирует asyncio loop. Нужно либо использовать asyncio.get_event_loop().run_in_executor(), либо сделать метод async.

Небезопасное форматирование промпта — ручная замена {} через .replace() работает, но не защищена от коллизий (если в тексте промпта встречается паттерн вида {some_key}, он будет заменён на N/A). Лучше использовать string.Template с $-синтаксисом.

ai_trainer/bot/handlers/start.py — 🟡 СТРУКТУРА
Импорты внутри функций — серьёзный антипаттерн :

python
@router.callback_query(...)
async def process_goal_callback(callback, state):
    # Эти импорты выполняются при КАЖДОМ вызове:
    from ai_trainer.bot.keyboards.main_menu import get_main_menu
    from ai_trainer.agent.trainer_agent import build_trainer_graph
    from ai_trainer.agent.tools.plan_tools import generate_weekly_plan_tool
Все импорты должны быть вверху файла. Импорты внутри функций замедляют работу и затрудняют понимание зависимостей.

sheets = SheetsClient() создаётся на уровне модуля — при недоступных credentials Google Sheets весь бот упадёт при старте.

ai_trainer/bot/handlers/workout.py — 🔴 ЯЗЫКОВАЯ НЕПОСЛЕДОВАТЕЛЬНОСТЬ
Весь файл workout.py написан только на русском языке , тогда как start.py, settings.py поддерживают два языка (RU/EN). Пользователь с language="en" увидит русский текст во всём workout-флоу.

python
# ПЛОХО — только русский:
await message.answer("Прежде чем начнем, как твое самочувствие сегодня?")

# ДОЛЖНО БЫТЬ — с учётом языка пользователя
data = await state.get_data()
lang = data.get("language", "ru")
msg = "Before we start, how are you feeling today?" if lang == "en" else "Как твое самочувствие?"
await message.answer(msg)
Некорректная логика PR при записи упражнения :

python
# ПРОБЛЕМА: использует max(weight) и min(reps) независимо
await crud.update_personal_record(db, user.id, ex['name'], max(ex['weight_kg']), min(ex['reps']))
max(weight) и min(reps) могут соответствовать разным подходам — правильная 1RM формула Epley требует парных значений (вес, повторения одного подхода). Следует пройтись по всем парам (weight[i], reps[i]) и выбрать лучший расчётный 1RM.

Незавершённый код :

python
class WorkoutStates(StatesGroup):
    waiting_for_feeling = State()
    waiting_for_pain = State()
    # ... (rest of states)  ← комментарий-заглушка в production-коде
ai_trainer/bot/handlers/progress.py — 🟡 ОПТИМИЗАЦИЯ
Дублирование функции 1RM — _calculate_1rm_from_log() в progress.py полностью дублирует calculate_1rm() из crud.py. Нарушение принципа DRY. Вынести в отдельный utils.py.

Множественные открытия сессий в cmd_progress — функция открывает сессию, получает пользователя и упражнения, закрывает, потом снова открывает для записей. Это 2 отдельных подключения, которые легко объединить в одно:

python
async with database.db_session() as db:
    user = await crud.get_user_by_telegram_id(db, telegram_id)
    exercises = await crud.get_user_exercises(db, user.id)
    records = await crud.get_all_personal_records(db, user.id)
_setup_dark_style() изменяет глобальные plt.rcParams при каждом вызове — это не thread-safe и может влиять на другие потоки/процессы.

Dockerfile и docker-compose.yml — 🟡 SECURITY & DEVOPS
Dockerfile запускает процесс от root — нарушение security best practices:

text
# Добавить:
RUN useradd -m appuser
USER appuser
Отсутствуют важные ENV-переменные :

text
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
CMD указывает на python bot/main.py но файл находится по пути ai_trainer/bot/main.py — команда не сработает без правильного PYTHONPATH.

docker-compose.yml — в сервисе bot отсутствует DATABASE_URL, хотя бот обращается к БД напрямую через crud.py. Сервис ollama не имеет healthcheck и resource limits.

ai_trainer/bot/main.py — 🟢 В ЦЕЛОМ ХОРОШО
Структура чистая . Единственные замечания:

MemoryStorage — при рестарте все FSM-состояния (незавершённые регистрации, диалоги) теряются. Для production рекомендуется RedisStorage из aiogram-redis.

sys.path.insert(0, ...) — антипаттерн. Правильнее установить пакет через pip install -e . с pyproject.toml или setup.py.
