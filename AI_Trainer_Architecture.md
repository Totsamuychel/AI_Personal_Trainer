
# 🏋️ AI Personal Trainer — Полная документация разработки

> **Версия:** 1.0 MVP  
> **Платформа:** Desktop (PC) → Mobile (v2.0)  
> **Язык:** Python 3.11+  
> **Интерфейс:** Telegram Bot + Google Sheets  

---

## 📋 Содержание

1. [Концепция и цели](#концепция-и-цели)
2. [Системная архитектура](#системная-архитектура)
3. [Технологический стек](#технологический-стек)
4. [Структура проекта](#структура-проекта)
5. [База данных](#база-данных)
6. [AI Agent Core](#ai-agent-core)
7. [RAG и Fine-tuning](#rag-и-fine-tuning)
8. [Система памяти](#система-памяти)
9. [Telegram Bot](#telegram-bot)
10. [Google Sheets интеграция](#google-sheets-интеграция)
11. [Периодизация и планирование](#периодизация-и-планирование)
12. [API и Backend](#api-и-backend)
13. [Docker и деплой](#docker-и-деплой)
14. [Переменные окружения](#переменные-окружения)
15. [Полный план разработки](#полный-план-разработки)
16. [Тестирование](#тестирование)
17. [Roadmap](#roadmap)

---

## Концепция и цели

### Что делает приложение

AI Personal Trainer — интеллектуальный агент, который:

- **Записывает тренировки** через Telegram Bot
- **Анализирует прогресс** и адаптирует нагрузку под пользователя
- **Генерирует планы** с периодизацией (сила → гипертрофия → объём → разгрузка)
- **Записывает питание** и считает КБЖУ через описание текстом
- **Помнит контекст** о пользователе (травмы, слабые места, предпочтения)
- **Ведёт таблицы** в Google Sheets с прогрессом нагрузок
- **Даёт советы** по технике выполнения упражнений

### Ключевые принципы

```
Персонализация > Универсальность
Прогрессия нагрузки > Случайные тренировки
Долгосрочная память > Забывание контекста
Локальная модель + RAG > Полный fine-tuning (для MVP)
```

---

## Системная архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                        ПОЛЬЗОВАТЕЛЬ                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │ Telegram
┌──────────────────────────▼──────────────────────────────────────┐
│                      TELEGRAM BOT                               │
│              aiogram 3.x + FSM состояния                        │
│  /workout  /nutrition  /plan  /progress  /tip  /profile         │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP
┌──────────────────────────▼──────────────────────────────────────┐
│                      FASTAPI BACKEND                            │
│                   REST API + маршруты                           │
│         /api/workout  /api/plan  /api/nutrition                 │
└──────┬───────────────────┬────────────────────┬─────────────────┘
       │                   │                    │
┌──────▼──────┐   ┌────────▼────────┐  ┌───────▼───────────────┐
│ PostgreSQL  │   │   AI AGENT      │  │   GOOGLE SHEETS       │
│             │   │   CORE          │  │                       │
│ • Users     │   │ LangGraph +     │  │ • Профиль             │
│ • Workouts  │   │ LangChain       │  │ • Прогресс нагрузок   │
│ • Nutrition │◄──│                 │  │ • Планы недели        │
│ • Plans     │   │ ┌─────────────┐ │  │ • Дневник питания     │
│ • Progress  │   │ │  LLM Layer  │ │  └───────────────────────┘
└─────────────┘   │ │ OpenAI API  │ │
                  │ │    или      │ │
┌─────────────┐   │ │  Ollama     │ │
│  ChromaDB   │   │ │ (локально)  │ │
│             │◄──│ └─────────────┘ │
│ • RAG база  │   │                 │
│   знаний    │   │ ┌─────────────┐ │
│ • Семант.   │   │ │   TOOLS     │ │
│   память    │   │ │ plan_gen    │ │
│   юзера     │   │ │ progress    │ │
└─────────────┘   │ │ nutrition   │ │
                  │ │ exercise    │ │
┌─────────────┐   │ └─────────────┘ │
│ APScheduler │──►│                 │
│             │   └─────────────────┘
│ • Понедел.  │
│   генерация │
│   плана     │
│ • Напомин.  │
└─────────────┘
```

### Поток данных

```
[Пользователь пишет в TG] 
    → [Bot парсит сообщение]
    → [FastAPI роут]
    → [AI Agent получает запрос]
    → [Agent читает профиль из PostgreSQL]
    → [Agent делает RAG-запрос в ChromaDB]
    → [LLM генерирует ответ с контекстом]
    → [Agent записывает результат в PostgreSQL]
    → [Agent обновляет Google Sheets]
    → [Agent обновляет семантическую память в ChromaDB]
    → [Ответ возвращается в Telegram]
```

---

## Технологический стек

| Категория | Технология | Версия | Назначение |
|---|---|---|---|
| **Python** | Python | 3.11+ | Основной язык |
| **Bot** | aiogram | 3.x | Telegram Bot Framework |
| **Backend** | FastAPI | 0.110+ | REST API |
| **ASGI** | uvicorn | latest | Сервер для FastAPI |
| **ORM** | SQLAlchemy | 2.x | Работа с БД |
| **Миграции** | Alembic | latest | Схема БД |
| **БД** | PostgreSQL | 15+ | Основная база данных |
| **Векторная БД** | ChromaDB | latest | RAG + семант. память |
| **AI Framework** | LangChain | 0.2+ | Цепочки и инструменты |
| **Agent Graph** | LangGraph | latest | Граф агента с памятью |
| **LLM (онлайн)** | OpenAI API | GPT-4o | Облачная модель |
| **LLM (локально)** | Ollama | latest | Запуск локальных моделей |
| **Локал. модель** | Llama 3.1 8B | Q4_K_M | Основная локальная LLM |
| **Embeddings** | nomic-embed-text | latest | Векторизация текста |
| **Fine-tuning** | Unsloth + QLoRA | latest | Дообучение модели |
| **Google Sheets** | gspread | latest | Интеграция таблиц |
| **Планировщик** | APScheduler | 3.x | Авто-задачи |
| **Валидация** | Pydantic | 2.x | Схемы данных |
| **Логи** | loguru | latest | Логирование |
| **Тесты** | pytest + pytest-asyncio | latest | Тестирование |
| **Контейнеры** | Docker + Compose | latest | Деплой |

### Выбор LLM модели

```
Для разработки/тестирования:
  └── Ollama + Llama 3.1 8B (Q4_K_M) — бесплатно, локально, 8GB VRAM

Для production MVP:
  └── OpenAI GPT-4o-mini — баланс качества и цены (~$0.15/1M токенов)

После накопления данных (v2.0):
  └── QLoRA fine-tuned Llama 3.1 8B — своя модель через Unsloth
```

---

## Структура проекта

```
ai_trainer/
│
├── 📁 bot/                          # Telegram Bot
│   ├── 📁 handlers/
│   │   ├── __init__.py
│   │   ├── start.py                 # /start, регистрация
│   │   ├── profile.py               # /profile, редактирование профиля
│   │   ├── workout.py               # /workout, запись тренировки
│   │   ├── nutrition.py             # /nutrition, запись питания
│   │   ├── plan.py                  # /plan, показ плана
│   │   ├── progress.py              # /progress, прогресс
│   │   └── tips.py                  # /tip, советы по технике
│   ├── 📁 keyboards/
│   │   ├── __init__.py
│   │   ├── inline.py                # Inline клавиатуры
│   │   └── reply.py                 # Reply клавиатуры
│   ├── 📁 states/
│   │   ├── __init__.py
│   │   ├── workout_states.py        # FSM для тренировки
│   │   ├── nutrition_states.py      # FSM для питания
│   │   └── profile_states.py        # FSM для профиля
│   ├── middlewares.py               # Middleware (auth, rate limit)
│   └── main.py                      # Запуск бота
│
├── 📁 agent/                        # AI Agent Core
│   ├── __init__.py
│   ├── trainer_agent.py             # Основной LangGraph агент
│   ├── 📁 tools/
│   │   ├── __init__.py
│   │   ├── user_tools.py            # get_profile, update_profile
│   │   ├── workout_tools.py         # log_workout, get_history
│   │   ├── plan_tools.py            # generate_plan, get_current_plan
│   │   ├── nutrition_tools.py       # calc_calories, log_nutrition
│   │   ├── progress_tools.py        # analyze_progress, get_1rm
│   │   ├── sheets_tools.py          # write_to_sheets
│   │   └── exercise_tools.py        # get_exercise_info, technique_tips
│   ├── 📁 prompts/
│   │   ├── system_prompt.txt        # Основной системный промпт
│   │   ├── plan_template.txt        # Шаблон генерации плана
│   │   ├── nutrition_prompt.txt     # Промпт для питания
│   │   └── analysis_prompt.txt      # Промпт для анализа прогресса
│   └── 📁 memory/
│       ├── __init__.py
│       ├── short_term.py            # Буфер текущей сессии
│       ├── long_term.py             # ChromaDB семантическая память
│       └── profile_memory.py        # Структурированный профиль
│
├── 📁 db/                           # База данных
│   ├── __init__.py
│   ├── database.py                  # Подключение, сессия
│   ├── models.py                    # SQLAlchemy модели
│   ├── crud.py                      # CRUD операции
│   └── 📁 migrations/               # Alembic миграции
│       ├── env.py
│       └── 📁 versions/
│
├── 📁 rag/                          # RAG система
│   ├── __init__.py
│   ├── knowledge_base.py            # Загрузка и индексация
│   ├── retriever.py                 # Поиск по базе знаний
│   └── 📁 data/                     # Источники знаний
│       ├── exercises/               # JSON с упражнениями
│       ├── programs/                # Программы тренировок
│       └── nutrition/               # Данные по питанию
│
├── 📁 sheets/                       # Google Sheets
│   ├── __init__.py
│   ├── client.py                    # Авторизация gspread
│   ├── workout_sheet.py             # Запись тренировок
│   ├── plan_sheet.py                # Запись планов
│   ├── nutrition_sheet.py           # Запись питания
│   └── progress_sheet.py            # Прогресс нагрузок
│
├── 📁 api/                          # FastAPI Backend
│   ├── __init__.py
│   ├── app.py                       # Создание FastAPI app
│   ├── dependencies.py              # Зависимости (db, auth)
│   └── 📁 routes/
│       ├── __init__.py
│       ├── users.py                 # /api/users
│       ├── workouts.py              # /api/workouts
│       ├── nutrition.py             # /api/nutrition
│       └── plans.py                 # /api/plans
│
├── 📁 scheduler/                    # Планировщик задач
│   ├── __init__.py
│   ├── jobs.py                      # Задачи (генерация плана и т.д.)
│   └── scheduler.py                 # Настройка APScheduler
│
├── 📁 fine_tuning/                  # Fine-tuning (опционально)
│   ├── prepare_dataset.py           # Подготовка датасета
│   ├── train.py                     # QLoRA обучение через Unsloth
│   ├── evaluate.py                  # Оценка модели
│   └── 📁 datasets/
│       ├── fitness_qa.jsonl          # QA пары по фитнесу
│       └── user_interactions.jsonl   # Реальные взаимодействия
│
├── 📁 tests/                        # Тесты
│   ├── conftest.py
│   ├── test_agent.py
│   ├── test_db.py
│   ├── test_sheets.py
│   └── test_bot.py
│
├── 📁 scripts/                      # Утилиты
│   ├── add_user.py
│   ├── seed_settings.py
│   ├── seed_test_db.py
│   └── fix_model.py / fix_model_name.py
│
├── 📁 ai_trainer/rag/
│   └── build_index.py               # CLI: первичная индексация RAG (--exercises, --all, …)
│
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .gitignore
├── requirements.txt
├── alembic.ini
└── README.md
```

---

## База данных

### Схема таблиц (SQLAlchemy models.py)

```python
from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

class GoalType(enum.Enum):
    strength    = "strength"
    hypertrophy = "hypertrophy"
    fat_loss    = "fat_loss"
    endurance   = "endurance"

class WeekType(enum.Enum):
    strength    = "strength"     # 4-6 повторов, 85-90% 1RM
    hypertrophy = "hypertrophy"  # 8-12 повторов, 70-75% 1RM
    volume      = "volume"       # 12-15 повторов, 60-65% 1RM
    deload      = "deload"       # 10-12 повторов, 50% 1RM

class User(Base):
    __tablename__ = "users"
    id              = Column(Integer, primary_key=True)
    telegram_id     = Column(String, unique=True, nullable=False)
    name            = Column(String)
    age             = Column(Integer)
    height_cm       = Column(Float)
    weight_kg       = Column(Float)
    goal            = Column(Enum(GoalType))
    level           = Column(String)           # beginner / intermediate / advanced
    preferred_split = Column(String)           # PPL / Upper-Lower / Full Body
    injuries        = Column(JSON, default=[]) # ["боль в колене", ...]
    created_at      = Column(DateTime)
    workouts        = relationship("WorkoutSession", back_populates="user")
    plans           = relationship("WeeklyPlan", back_populates="user")
    nutrition_logs  = relationship("NutritionLog", back_populates="user")

class WorkoutSession(Base):
    __tablename__ = "workout_sessions"
    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id"))
    date         = Column(DateTime)
    workout_type = Column(String)              # Push / Pull / Legs / Full Body
    week_type    = Column(Enum(WeekType))
    duration_min = Column(Integer)
    notes        = Column(String)
    user         = relationship("User", back_populates="workouts")
    exercises    = relationship("ExerciseLog", back_populates="session")

class ExerciseLog(Base):
    __tablename__ = "exercise_logs"
    id         = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("workout_sessions.id"))
    name       = Column(String)
    sets       = Column(Integer)
    reps       = Column(JSON)   # [5, 5, 4] — повторы в каждом подходе
    weight_kg  = Column(JSON)   # [80, 80, 77.5] — вес в каждом подходе
    rpe        = Column(Float)  # Rate of Perceived Exertion (1-10)
    notes      = Column(String)
    session    = relationship("WorkoutSession", back_populates="exercises")

class PersonalRecord(Base):
    __tablename__ = "personal_records"
    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id"))
    exercise    = Column(String)
    weight_kg   = Column(Float)
    reps        = Column(Integer)
    one_rm_est  = Column(Float)  # Расчётный 1RM по формуле Epley
    date        = Column(DateTime)

class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"
    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("users.id"))
    week_number = Column(Integer)
    week_type   = Column(Enum(WeekType))
    start_date  = Column(DateTime)
    plan_data   = Column(JSON)   # Полный план в JSON
    is_active   = Column(Integer, default=1)
    user        = relationship("User", back_populates="plans")

class NutritionLog(Base):
    __tablename__ = "nutrition_logs"
    id           = Column(Integer, primary_key=True)
    user_id      = Column(Integer, ForeignKey("users.id"))
    date         = Column(DateTime)
    meal_name    = Column(String)
    description  = Column(String)      # Исходный текст пользователя
    calories     = Column(Float)
    protein_g    = Column(Float)
    carbs_g      = Column(Float)
    fat_g        = Column(Float)
    user         = relationship("User", back_populates="nutrition_logs")
```

### Расчёт 1RM (формула Epley)

```python
def calculate_1rm(weight: float, reps: int) -> float:
    """Формула Epley: 1RM = weight × (1 + reps/30)"""
    if reps == 1:
        return weight
    return round(weight * (1 + reps / 30), 2)
```

---

## AI Agent Core

### Граф агента (LangGraph)

```python
# agent/trainer_agent.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from typing import TypedDict, Annotated
import operator

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    user_id: str
    user_profile: dict
    retrieved_context: str
    current_plan: dict
    action_type: str  # workout_log / nutrition_log / plan_gen / tip / analysis

def build_trainer_graph():
    graph = StateGraph(AgentState)

    # Узлы графа
    graph.add_node("load_profile",    load_user_profile)
    graph.add_node("retrieve_context", retrieve_rag_context)
    graph.add_node("plan_node",       plan_action)
    graph.add_node("agent",           run_agent)
    graph.add_node("save_results",    save_to_db_and_sheets)
    graph.add_node("update_memory",   update_user_memory)

    # Рёбра
    graph.set_entry_point("load_profile")
    graph.add_edge("load_profile",     "retrieve_context")
    graph.add_edge("retrieve_context", "plan_node")
    graph.add_conditional_edges("plan_node", route_to_action, {
        "workout": "agent",
        "nutrition": "agent",
        "plan_gen": "agent",
        "tip": "agent",
    })
    graph.add_edge("agent",         "save_results")
    graph.add_edge("save_results",  "update_memory")
    graph.add_edge("update_memory", END)

    # Персистентная память через PostgreSQL checkpointer
    memory = PostgresSaver.from_conn_string(DATABASE_URL)
    return graph.compile(checkpointer=memory)
```

### Системный промпт

```
# agent/prompts/system_prompt.txt

Ты — AI персональный тренер с опытом 15 лет в силовом тренинге.
Ты специализируешься на составлении индивидуальных программ с периодизацией.

## Профиль клиента
- Имя: {name}
- Возраст: {age} лет
- Рост: {height} см / Вес: {weight} кг
- Цель: {goal}
- Уровень: {level}
- Предпочтительный сплит: {preferred_split}
- Текущая неделя цикла: {week_type} (неделя #{week_number} из 4)
- Травмы/ограничения: {injuries}

## Рекорды клиента (расчётный 1RM)
{personal_records}

## История последних 4 тренировок
{recent_workouts}

## Текущий план
{current_plan}

## Твои принципы работы
1. Всегда учитывай травмы и ограничения клиента
2. Применяй линейную прогрессию нагрузки (до +2.5-5 кг когда выполнены все повторы)
3. Чередуй типы недель строго по циклу: сила → гипертрофия → объём → разгрузка
4. Давай конкретные цифры: вес, подходы, повторы — не общие слова
5. Объясняй ПОЧЕМУ такая нагрузка, не просто что делать
6. Если клиент пишет об усталости или боли — снижай интенсивность
```

### Инструменты агента (Tools)

```python
# agent/tools/workout_tools.py
from langchain.tools import tool

@tool
def log_workout_session(
    workout_type: str,
    exercises: list[dict],
    duration_minutes: int,
    notes: str = ""
) -> str:
    """
    Записывает тренировку в БД.
    exercises: [{"name": "Жим лёжа", "sets": 4, "reps": [5,5,5,4], "weight": [80,80,80,80]}]
    """
    # ... сохранение в PostgreSQL + вызов sheets_tools
    return f"Тренировка записана. Выполнено {len(exercises)} упражнений."

@tool
def get_workout_history(user_id: str, last_n: int = 8) -> str:
    """Возвращает историю последних N тренировок пользователя."""
    # ... запрос из PostgreSQL
    return formatted_history

@tool
def get_personal_records(user_id: str, exercise: str = None) -> str:
    """Возвращает личные рекорды. Если exercise=None, возвращает все."""
    # ... 
    return formatted_records

@tool
def analyze_progress(user_id: str, exercise: str, weeks: int = 8) -> str:
    """Анализирует прогресс нагрузки за последние N недель."""
    # Считает динамику: средний вес, объём, тренд 1RM
    return analysis_text

# agent/tools/plan_tools.py
@tool
def generate_weekly_plan(user_id: str) -> str:
    """
    Генерирует план тренировок на следующую неделю.
    Автоматически определяет тип недели из цикла (сила/гипертрофия/объём/разгрузка).
    """
    # Логика периодизации + вызов LLM для составления плана
    return plan_json

@tool
def get_current_plan(user_id: str) -> str:
    """Возвращает активный план тренировок на текущую неделю."""
    return current_plan_formatted

# agent/tools/nutrition_tools.py
@tool
def calculate_nutrition(food_description: str) -> str:
    """
    Считает КБЖУ по текстовому описанию еды.
    Пример: "гречка 200г, куриная грудка 150г, огурец"
    """
    # Используем LLM + база USDA/FoodData для расчёта
    return "Калории: 520 ккал | Белки: 48г | Углеводы: 65г | Жиры: 6г"

@tool
def get_daily_nutrition_summary(user_id: str, date: str) -> str:
    """Возвращает сводку по питанию за день: итого КБЖУ и все приёмы пищи."""
    return daily_summary

# agent/tools/exercise_tools.py
@tool
def get_exercise_technique(exercise_name: str) -> str:
    """
    Возвращает подробное описание техники упражнения из RAG базы знаний.
    Включает: постановку, движение, типичные ошибки, варианты.
    """
    return rag_retriever.get(exercise_name)
```

---

## RAG и Fine-tuning

### RAG — База знаний по тренировкам

```python
# rag/knowledge_base.py
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    JSONLoader, PyPDFLoader, DirectoryLoader
)

class FitnessKnowledgeBase:
    def __init__(self, persist_dir: str = "./chroma_fitness_db"):
        self.embeddings = OllamaEmbeddings(model="nomic-embed-text")
        self.vectorstore = Chroma(
            persist_directory=persist_dir,
            embedding_function=self.embeddings
        )

    def load_exercises(self, json_path: str):
        """Загружает базу упражнений в формате JSON."""
        # Формат: {"name": "Жим лёжа", "muscles": [...], "technique": "...", "errors": [...]}
        loader = JSONLoader(json_path, jq_schema=".exercises[]")
        docs = loader.load()
        self._add_documents(docs)

    def load_pdfs(self, pdf_dir: str):
        """Загружает PDF книги по тренингу."""
        loader = DirectoryLoader(pdf_dir, glob="*.pdf", loader_cls=PyPDFLoader)
        docs = loader.load()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". "]
        )
        chunks = splitter.split_documents(docs)
        self._add_documents(chunks)

    def search(self, query: str, k: int = 5) -> list[str]:
        """Семантический поиск по базе знаний."""
        results = self.vectorstore.similarity_search(query, k=k)
        return [doc.page_content for doc in results]

    def _add_documents(self, docs):
        self.vectorstore.add_documents(docs)
        self.vectorstore.persist()
```

### Источники данных для RAG

```
rag/data/exercises/
├── push_exercises.json     # Жим, отжимания, дипы, дельты
├── pull_exercises.json     # Подтягивания, тяги, бицепс
├── legs_exercises.json     # Приседания, становая, икры
└── core_exercises.json     # Пресс, планка, стабилизация

Формат файла упражнений:
{
  "exercises": [
    {
      "name": "Жим штанги лёжа",
      "muscles_primary": ["грудь большая"],
      "muscles_secondary": ["трицепс", "передняя дельта"],
      "equipment": "штанга, скамья",
      "technique": "Лягте на скамью, лопатки сведены...",
      "common_errors": ["отрыв поясницы", "опускание локтей ниже 45°"],
      "variations": ["узкий хват", "наклонный жим", "жим гантелей"],
      "tips": "Для роста грудных — медленное опускание 3-4 секунды..."
    }
  ]
}
```

### QLoRA Fine-tuning (после MVP)

```python
# fine_tuning/train.py
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments
from datasets import load_dataset

# Загрузка базовой модели с 4-bit квантизацией
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = "unsloth/llama-3.1-8b-bnb-4bit",
    max_seq_length = 2048,
    load_in_4bit = True,
)

# Добавление LoRA адаптеров
model = FastLanguageModel.get_peft_model(
    model,
    r = 16,
    lora_alpha = 16,
    lora_dropout = 0.05,
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj",
                      "gate_proj", "up_proj", "down_proj"],
    bias = "none",
    use_gradient_checkpointing = True,
)

# Датасет
dataset = load_dataset("json", data_files="datasets/fitness_qa.jsonl")

trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset["train"],
    dataset_text_field = "text",
    max_seq_length = 2048,
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_steps = 10,
        num_train_epochs = 3,
        learning_rate = 2e-4,
        fp16 = True,
        output_dir = "outputs/trainer_lora",
    ),
)

trainer.train()

# Сохранение в GGUF для Ollama
model.save_pretrained_gguf(
    "outputs/trainer_model",
    tokenizer,
    quantization_method = "q4_k_m"
)
```

### Формат датасета для fine-tuning

```jsonl
{"text": "<|system|>Ты персональный тренер.<|user|>Клиент 80 кг, жим 70 кг. Силовая неделя.<|assistant|>На силовой неделе (85% от 1RM ≈ 60 кг):
- Жим лёжа: 4×5 @ 60 кг, отдых 3 мин
- Жим под углом: 3×5 @ 52 кг
Цель — чистые 5 повторов во всех подходах. Если сделаешь — следующая силовая +2.5 кг."}
{"text": "<|system|>Ты персональный тренер.<|user|>Болит колено при приседаниях. Что делать?<|assistant|>При боли в колене исключи глубокие приседания. Замени на: жим ногами (неглубокий), болгарские выпады (контролируй колено), разгибания в тренажёре с малым весом. Нужно выяснить причину — боль спереди (пателлярная), сбоку (IT-band) или сзади?"}
```

---

## Система памяти

### Трёхуровневая архитектура памяти

```
Уровень 1: Краткосрочная память (сессия)
    └── LangGraph конфигурация thread_id=user_id
    └── Хранит: текущий диалог (последние 20 сообщений)
    └── Живёт: только во время разговора

Уровень 2: Долгосрочная семантическая (ChromaDB)
    └── Хранит: важные факты о пользователе в виде текста
    └── Обновляется: агентом после каждой сессии
    └── Примеры записей:
        "Иван жалуется на боль в правом плече при жиме"
        "Лучший результат в приседе — 120 кг × 3 от 2025-03-15"
        "Предпочитает тренироваться утром, плохо восстанавливается при 4+ днях"
        "Не любит кардио, хорошо реагирует на суперсеты"

Уровень 3: Структурированный профиль (PostgreSQL)
    └── Хранит: числовые данные, текущие параметры
    └── Обновляется: при каждой тренировке
```

```python
# agent/memory/long_term.py
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

class UserMemoryStore:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.vectorstore = Chroma(
            persist_directory=f"./memory_db/{user_id}",
            embedding_function=OllamaEmbeddings(model="nomic-embed-text"),
            collection_name=f"user_{user_id}_memory"
        )

    def save_memory(self, fact: str, memory_type: str = "general"):
        """Сохраняет факт о пользователе в векторную память."""
        from langchain.schema import Document
        doc = Document(
            page_content=fact,
            metadata={"user_id": self.user_id, "type": memory_type, 
                      "timestamp": datetime.now().isoformat()}
        )
        self.vectorstore.add_documents([doc])

    def recall(self, query: str, k: int = 5) -> list[str]:
        """Извлекает релевантные воспоминания по запросу."""
        results = self.vectorstore.similarity_search(
            query, k=k,
            filter={"user_id": self.user_id}
        )
        return [doc.page_content for doc in results]

    def extract_and_save_facts(self, conversation: str, llm):
        """Агент сам извлекает важные факты из разговора и сохраняет."""
        prompt = f"""
        Из следующего разговора с пользователем извлеки важные факты 
        для персонализации тренировок. Выведи список фактов, по одному на строку.
        Разговор: {conversation}
        """
        facts = llm.invoke(prompt).content.strip().split("\n")
        for fact in facts:
            if fact.strip():
                self.save_memory(fact.strip(), memory_type="extracted")
```

---

## Telegram Bot

### Архитектура хендлеров

```python
# bot/handlers/workout.py
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

router = Router()

class WorkoutStates(StatesGroup):
    choosing_type     = State()  # Выбор типа тренировки
    logging_exercise  = State()  # Ввод упражнения
    entering_sets     = State()  # Количество подходов
    entering_weight   = State()  # Вес
    entering_reps     = State()  # Повторы
    adding_more       = State()  # Добавить ещё упражнение?
    confirming        = State()  # Подтверждение и сохранение

@router.message(F.text == "/workout")
async def start_workout(message: Message, state: FSMContext):
    await state.set_state(WorkoutStates.choosing_type)
    await message.answer(
        "Выбери тип тренировки:",
        reply_markup=workout_type_keyboard()  # Push/Pull/Legs/Full Body
    )

@router.message(WorkoutStates.choosing_type)
async def choose_type(message: Message, state: FSMContext):
    await state.update_data(workout_type=message.text, exercises=[])
    await state.set_state(WorkoutStates.logging_exercise)
    await message.answer("Введи название первого упражнения:")

@router.message(WorkoutStates.logging_exercise)
async def log_exercise(message: Message, state: FSMContext):
    await state.update_data(current_exercise=message.text)
    await state.set_state(WorkoutStates.entering_sets)
    await message.answer("Сколько подходов выполнил?")

# ... остальные состояния

@router.message(WorkoutStates.confirming, F.text == "✅ Сохранить")
async def save_workout(message: Message, state: FSMContext):
    data = await state.get_data()
    # Вызов агента для сохранения + анализа
    result = await agent.invoke({
        "action_type": "workout_log",
        "workout_data": data,
        "user_id": str(message.from_user.id)
    })
    await state.clear()
    await message.answer(f"✅ Тренировка сохранена!\n\n{result['summary']}")
```

### Команды бота

```
/start       — Регистрация, ввод профиля (рост, вес, возраст, цель, уровень)
/workout     — Начать запись тренировки (FSM: тип → упражнения → подходы/вес/повторы)
/nutrition   — Записать приём пищи текстом ("гречка 200г + курица 150г")
/plan        — Показать план на текущую неделю
/progress    — Прогресс по упражнениям (таблица + тренд)
/tip         — Совет по технике упражнения (поиск по RAG базе)
/records     — Личные рекорды (1RM по основным упражнениям)
/settings    — Изменить профиль, вес, цели
/report      — Недельный/месячный отчёт
```

---

## Google Sheets интеграция

### Структура таблицы

```
Таблица: "AI Trainer — [Имя пользователя]"

Лист 1: "📋 Профиль"
    A: Параметр | B: Значение
    Рост, вес, цель, уровень, текущая фаза, дата старта

Лист 2: "📈 Прогресс нагрузок"
    A: Дата | B: Упражнение | C: Тип недели | D: Вес | E: Подходы | F: Повторы | G: Расч. 1RM

Лист 3: "📅 Планы недель"
    A: Неделя # | B: Тип | C: День | D: Упражнение | E: Подходы×Повторы | F: Целевой вес

Лист 4: "🥗 Питание"
    A: Дата | B: Приём пищи | C: Описание | D: Ккал | E: Белки | F: Углеводы | G: Жиры

Лист 5: "📊 Дашборд"
    Графики: динамика 1RM, объём тренировок, калории по дням (auto-generated)
```

```python
# sheets/workout_sheet.py
import gspread
from google.oauth2.service_account import Credentials

class WorkoutSheetManager:
    SCOPES = ["https://spreadsheets.google.com/feeds",
              "https://www.googleapis.com/auth/drive"]

    def __init__(self, credentials_path: str, spreadsheet_id: str):
        creds = Credentials.from_service_account_file(
            credentials_path, scopes=self.SCOPES
        )
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open_by_key(spreadsheet_id)

    def log_workout(self, session_data: dict):
        """Записывает тренировку на лист 'Прогресс нагрузок'."""
        ws = self.sheet.worksheet("📈 Прогресс нагрузок")
        for ex in session_data["exercises"]:
            row = [
                session_data["date"],
                ex["name"],
                session_data["week_type"],
                max(ex["weight"]),
                ex["sets"],
                str(ex["reps"]),
                calculate_1rm(max(ex["weight"]), min(ex["reps"]))
            ]
            ws.append_row(row)

    def write_weekly_plan(self, plan: dict, week_number: int):
        """Записывает план на неделю."""
        ws = self.sheet.worksheet("📅 Планы недель")
        for day in plan["days"]:
            for ex in day["exercises"]:
                row = [week_number, plan["week_type"], day["name"],
                       ex["name"], f"{ex['sets']}×{ex['reps']}", ex["target_weight"]]
                ws.append_row(row)
```

---

## Периодизация и планирование

### 4-недельный цикл (Linear Periodization)

```python
# agent/tools/plan_tools.py

PERIODIZATION_CYCLE = [
    {
        "week_type": "strength",
        "name": "💪 Силовая неделя",
        "intensity": "85-90% от 1RM",
        "sets": 4,
        "reps_range": "4-6",
        "rest_sec": 180,
        "description": "Тяжёлые веса, мало повторов, полное восстановление между подходами"
    },
    {
        "week_type": "hypertrophy",
        "name": "🏗️ Гипертрофия",
        "intensity": "70-75% от 1RM",
        "sets": 4,
        "reps_range": "8-12",
        "rest_sec": 90,
        "description": "Умеренный вес, умеренное количество повторов, умеренный отдых"
    },
    {
        "week_type": "volume",
        "name": "📦 Объёмная неделя",
        "intensity": "60-65% от 1RM",
        "sets": 3,
        "reps_range": "12-15",
        "rest_sec": 60,
        "description": "Лёгкий вес, много повторов, короткий отдых"
    },
    {
        "week_type": "deload",
        "name": "🔄 Разгрузочная неделя",
        "intensity": "50% от 1RM",
        "sets": 2,
        "reps_range": "10-12",
        "rest_sec": 60,
        "description": "Снижение нагрузки для восстановления ЦНС и суставов"
    },
]

def get_next_week_type(current_week_number: int) -> dict:
    """Возвращает параметры для следующей недели цикла."""
    return PERIODIZATION_CYCLE[current_week_number % 4]

def calculate_training_weight(one_rm: float, week_type: str) -> float:
    """Считает рабочий вес от 1RM."""
    intensity_map = {
        "strength": 0.875,    # 85-90% — среднее 87.5%
        "hypertrophy": 0.725, # 70-75% — среднее 72.5%
        "volume": 0.625,      # 60-65% — среднее 62.5%
        "deload": 0.50,       # 50%
    }
    raw_weight = one_rm * intensity_map[week_type]
    # Округляем до ближайших 2.5 кг
    return round(raw_weight / 2.5) * 2.5

def check_progression(exercise_logs: list) -> float:
    """
    Автопрогрессия: если в последних 3 силовых сессиях выполнены все повторы
    в верхней части диапазона — рекомендует +2.5 кг на следующей силовой неделе.
    """
    # Логика анализа истории
    ...
```

---

## API и Backend

### FastAPI роуты

```python
# api/app.py
from fastapi import FastAPI
from api.routes import users, workouts, nutrition, plans

app = FastAPI(title="AI Trainer API", version="1.0.0")

app.include_router(users.router,    prefix="/api/users")
app.include_router(workouts.router, prefix="/api/workouts")
app.include_router(nutrition.router,prefix="/api/nutrition")
app.include_router(plans.router,    prefix="/api/plans")

# api/routes/workouts.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db.database import get_db

router = APIRouter()

@router.post("/log")
async def log_workout(workout_data: WorkoutCreate, db: Session = Depends(get_db)):
    """Принимает данные тренировки, сохраняет и запускает анализ агента."""
    session = crud.create_workout_session(db, workout_data)
    await agent.process_workout(session)
    return {"status": "ok", "session_id": session.id}

@router.get("/{user_id}/history")
async def get_history(user_id: int, limit: int = 10, db: Session = Depends(get_db)):
    return crud.get_workout_history(db, user_id, limit)
```

---

## Docker и деплой

### docker-compose.yml

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: ai_trainer
      POSTGRES_USER: trainer_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U trainer_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build: .
    command: uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
    environment:
      - DATABASE_URL=postgresql://trainer_user:${POSTGRES_PASSWORD}@postgres:5432/ai_trainer
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - .:/app
      - ./chroma_fitness_db:/app/chroma_fitness_db
      - ./memory_db:/app/memory_db
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy

  bot:
    build: .
    command: python bot/main.py
    environment:
      - TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
      - API_URL=http://api:8000
    volumes:
      - .:/app
    depends_on:
      - api

  ollama:
    image: ollama/ollama
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    # Для GPU (NVIDIA):
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

volumes:
  postgres_data:
  ollama_data:
```

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot/main.py"]
```

### Первый запуск

```bash
# 1. Клонируем репозиторий
git clone https://github.com/yourname/ai-trainer && cd ai-trainer

# 2. Копируем и заполняем переменные окружения
cp .env.example .env && nano .env

# 3. Поднимаем инфраструктуру
docker-compose up -d postgres ollama

# 4. Загружаем модель в Ollama
docker-compose exec ollama ollama pull llama3.1:8b
docker-compose exec ollama ollama pull nomic-embed-text

# 5. Применяем миграции БД
docker-compose run --rm api alembic upgrade head

# 6. Инициализируем RAG (упражнения из JSON; опционально — PDF из data/books)
docker-compose run --rm api python ai_trainer/rag/build_index.py --exercises
# docker-compose run --rm api python ai_trainer/rag/build_index.py --all

# 7. Запускаем всё
docker-compose up -d
```

---

## Переменные окружения

```bash
# .env.example

# Telegram
TELEGRAM_TOKEN=your_bot_token_here

# База данных
POSTGRES_PASSWORD=strong_password_here
DATABASE_URL=postgresql://trainer_user:strong_password@localhost:5432/ai_trainer

# LLM — выбери один вариант
LLM_PROVIDER=ollama             # "ollama" или "openai"
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
OPENAI_API_KEY=sk-...           # если LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini

# Embeddings
EMBEDDING_MODEL=nomic-embed-text

# Google Sheets
GOOGLE_CREDENTIALS_PATH=./credentials.json
GOOGLE_SHEET_TEMPLATE_ID=your_template_spreadsheet_id

# Приложение
APP_ENV=development             # development / production
LOG_LEVEL=INFO
SECRET_KEY=your_secret_key_here

# Админка FastAPI (/admin/*): если задан — требуется заголовок X-Admin-API-Key или Authorization: Bearer …
ADMIN_API_KEY=generate_a_long_random_string
```

---

## Полный план разработки

### Phase 0 — Настройка (День 1-2)
- [ ] Создать репозиторий GitHub
- [ ] Настроить структуру папок проекта
- [ ] Создать виртуальное окружение и `requirements.txt`
- [ ] Настроить `docker-compose.yml` (PostgreSQL + Ollama)
- [ ] Заполнить `.env` файл
- [ ] Создать бота в BotFather, получить токен
- [ ] Подключить Google Cloud → включить Sheets API → скачать `credentials.json`
- [ ] Установить Ollama локально, загрузить `llama3.1:8b` и `nomic-embed-text`

### Phase 1 — База данных (День 3-5)
- [ ] Написать все SQLAlchemy модели (`models.py`)
- [ ] Настроить Alembic, создать первую миграцию
- [ ] Написать все CRUD операции (`crud.py`)
- [ ] Написать `seed_exercises.py` — заполнение начального словаря упражнений
- [ ] Протестировать все CRUD через Python консоль

### Phase 2 — RAG Knowledge Base (День 6-8)
- [ ] Собрать/спарсить данные по упражнениям (JSON формат)
- [ ] Написать `knowledge_base.py` с загрузкой и индексацией
- [ ] Написать `retriever.py` с семантическим поиском
- [ ] Запустить `python ai_trainer/rag/build_index.py --exercises`, проверить поиск
- [ ] Тест: задать вопрос → получить релевантный ответ из RAG

### Phase 3 — AI Agent Core (День 9-14)
- [ ] Написать все Tools агента (workout, plan, nutrition, exercise)
- [ ] Написать системный промпт (`system_prompt.txt`)
- [ ] Построить граф агента LangGraph (`trainer_agent.py`)
- [ ] Настроить трёхуровневую память (short-term, long-term, profile)
- [ ] Тест агента через Python REPL с тестовым профилем
- [ ] Тест генерации плана тренировок на неделю
- [ ] Тест расчёта КБЖУ по текстовому описанию

### Phase 4 — Google Sheets (День 15-17)
- [ ] Настроить `gspread` клиент с сервисным аккаунтом
- [ ] Создать шаблон таблицы вручную в Google Sheets
- [ ] Написать все менеджеры листов (workout, plan, nutrition, progress)
- [ ] Тест записи данных тренировки → проверить в таблице
- [ ] Тест записи плана недели

### Phase 5 — Telegram Bot (День 18-22)
- [ ] Создать FastAPI app и базовые роуты
- [ ] Написать все FSM состояния (workout, nutrition, profile)
- [ ] Написать все хендлеры с inline клавиатурами
- [ ] Написать middleware (проверка регистрации пользователя)
- [ ] Интегрировать вызов агента из хендлеров
- [ ] Полный тест: /start → профиль → /workout → запись → /plan → просмотр плана

### Phase 6 — Планировщик (День 23-24)
- [ ] Настроить APScheduler
- [ ] Задача: каждый понедельник — генерация плана + запись в Sheets + уведомление в TG
- [ ] Задача: ежедневно 8:00 — напоминание записать завтрак
- [ ] Задача: ежедневно 21:00 — сводка по питанию за день
- [ ] Логика авто-прогрессии нагрузки

### Phase 7 — Деплой MVP (День 25-27)
- [ ] Финальный `docker-compose.yml`
- [ ] `Dockerfile`
- [ ] Написать `README.md` с инструкцией установки
- [ ] Тестирование полного цикла с реальным пользователем
- [ ] Исправление багов

---

## Тестирование

```python
# tests/test_agent.py
import pytest
from agent.trainer_agent import build_trainer_graph

@pytest.mark.asyncio
async def test_plan_generation():
    """Тест генерации плана на неделю."""
    agent = build_trainer_graph()
    result = await agent.ainvoke({
        "action_type": "plan_gen",
        "user_id": "test_user_1",
        "messages": [{"role": "user", "content": "Составь план на эту неделю"}]
    }, config={"configurable": {"thread_id": "test_1"}})

    assert "plan_data" in result
    assert len(result["plan_data"]["days"]) >= 3

@pytest.mark.asyncio
async def test_nutrition_calculation():
    """Тест расчёта КБЖУ."""
    # ...

@pytest.mark.asyncio
async def test_periodization_logic():
    """Тест чередования типов недель."""
    from agent.tools.plan_tools import get_next_week_type
    assert get_next_week_type(0)["week_type"] == "strength"
    assert get_next_week_type(1)["week_type"] == "hypertrophy"
    assert get_next_week_type(4)["week_type"] == "strength"  # цикл повторяется
```

---

## Roadmap

### v1.0 — MVP (текущий план, ~4 недели)
- Telegram Bot + FSM логирование
- AI Agent с LangGraph
- RAG база знаний по упражнениям
- PostgreSQL + Google Sheets
- Периодизация 4-недельный цикл
- Расчёт КБЖУ

### v1.1 — Улучшения (после релиза)
- [ ] Графики прогресса прямо в Telegram (matplotlib → PNG)
- [ ] Анализ фото еды через GPT-4o Vision
- [ ] Экспорт PDF отчёта за месяц
- [ ] Уведомления-напоминания о тренировках
- [ ] Оценка техники: видео → анализ поз (MediaPipe)

### v1.2 — Fine-tuning
- [ ] Сбор датасета из реальных взаимодействий
- [ ] QLoRA дообучение Llama 3.1 8B через Unsloth
- [ ] Деплой кастомной модели через Ollama
- [ ] A/B тест: fine-tuned vs базовая модель

### v2.0 — Мобильное приложение
- [ ] React Native / Flutter фронтенд
- [ ] FastAPI backend уже готов — просто подключить
- [ ] Push-уведомления через Firebase
- [ ] Offline режим с локальной моделью (llama.cpp на телефоне)
- [ ] Apple Health / Google Fit интеграция

---

*Документ создан для AI Personal Trainer проекта. Обновляется по мере разработки.*
