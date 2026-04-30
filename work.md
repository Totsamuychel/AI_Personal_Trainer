# 📋 План работ — AI Personal Trainer

## ✅ Выполнено
- [x] Убрать `test.db` из репо и добавить в `.gitignore`
- [x] Защитить `open(prompt_path)` в агенте через `try/except`
- [x] Вынести `get_llm()` и `build_trainer_graph()` как синглтоны
- [x] Исправить `IndexError` в парсинге reps в `workout.py`
- [x] Добавить handler в боте для вызова агента (любое текстовое сообщение вне FSM)
- [x] Реализовать scheduler для утренних советов/напоминаний (используется `apscheduler`)

---

# 📚 RAG система — подключение книг к нейросети

## Что такое RAG и зачем это нужно

RAG (Retrieval-Augmented Generation) — это механизм, при котором перед каждым ответом нейросеть
получает **релевантные фрагменты из твоих книг** и использует их как контекст.

Без RAG: LLM отвечает только из своих весов (может галлюцинировать).
С RAG: LLM читает нужную страницу из "Sport Nutrition" или "Starting Strength" и отвечает точно.

**Пример:**
Пользователь спрашивает: *"Сколько белка нужно для роста мышц?"*
→ RAG достаёт из книги Jeukendrup точный абзац про 1.6–2.2 г/кг
→ LLM даёт ответ, опираясь на научный источник

---

## 🗂️ Структура папок для книг

```
ai_trainer/rag/data/
├── books/
│   ├── nutrition/
│   │   ├── sport_nutrition_jeukendrup.pdf
│   │   ├── renaissance_diet_israetel.pdf
│   │   ├── nutrient_timing_ivy.pdf
│   │   └── practical_sports_nutrition_burke.pdf
│   ├── training/
│   │   ├── starting_strength_rippetoe.pdf
│   │   ├── science_practice_strength_zatsiorsky.pdf
│   │   ├── periodization_bompa.pdf
│   │   ├── supertraining_siff.pdf
│   │   └── muscle_strength_pyramid_helms.pdf
│   └── anatomy/
│       ├── human_anatomy_physiology_marieb.pdf
│       ├── exercise_physiology_mcardle.pdf
│       ├── anatomy_of_movement_calais.pdf
│       └── trail_guide_body_biel.pdf
├── exercises/
│   └── exercises_db.json
└── chroma_db/               ← векторная БД (создаётся автоматически, не коммитить)
```

> **Важно:** папку `chroma_db/` добавь в `.gitignore` — она создаётся локально при индексации.

---

## 📦 Зависимости — установить

```bash
pip install pypdf langchain-community chromadb sentence-transformers
# Если используешь Ollama embeddings (уже стоит):
# ollama pull nomic-embed-text
```

Добавь в `requirements.txt`:
```
pypdf>=4.0.0
langchain-community>=0.2.0
chromadb>=0.5.0
sentence-transformers>=3.0.0
```

---

## 🔧 Шаг 1 — Обновить `knowledge_base.py`

Текущий `knowledge_base.py` умеет читать только `.txt` и `.json`.
Нужно добавить поддержку **PDF** (все книги в PDF формате).

Замени содержимое файла `ai_trainer/rag/knowledge_base.py`:

```python
import os
import json
from pathlib import Path
from typing import Optional

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_community.document_loaders import PyPDFLoader
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Папка с книгами относительно корня проекта
BOOKS_DIR = Path(__file__).parent / "data" / "books"
CHROMA_DIR = Path(__file__).parent / "data" / "chroma_db"

# Размер чанков — баланс между контекстом и точностью поиска
CHUNK_SIZE    = 700   # токенов примерно
CHUNK_OVERLAP = 100   # перекрытие чтобы не терять смысл на границах


class FitnessKnowledgeBase:
    def __init__(self, persist_dir: Optional[str] = None):
        self.embeddings = OllamaEmbeddings(
            model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
        self.vectorstore = Chroma(
            persist_directory=persist_dir or str(CHROMA_DIR),
            embedding_function=self.embeddings
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
        )

    # ─────────────────────────────────────────────
    # Загрузка PDF книги
    # ─────────────────────────────────────────────

    def load_pdf_book(self, pdf_path: str, topic: str = "general", metadata: dict = None):
        """
        Загружает PDF книгу, разбивает на чанки и индексирует в ChromaDB.

        Аргументы:
            pdf_path: путь к PDF файлу
            topic:    категория ('nutrition' / 'training' / 'anatomy')
            metadata: доп. метаданные (author, year, etc.)
        """
        path = Path(pdf_path)
        if not path.exists():
            logger.error(f"PDF не найден: {pdf_path}")
            return

        logger.info(f"Загрузка PDF: {path.name} (тема: {topic})")

        loader = PyPDFLoader(str(path))
        pages  = loader.load()   # каждый элемент = одна страница

        # Разбиваем на чанки
        chunks = self.text_splitter.split_documents(pages)

        # Добавляем метаданные к каждому чанку
        book_name = metadata.get("title", path.stem) if metadata else path.stem
        author    = metadata.get("author", "Unknown") if metadata else "Unknown"

        for i, chunk in enumerate(chunks):
            chunk.metadata.update({
                "source":       path.name,
                "book_title":   book_name,
                "author":       author,
                "topic":        topic,
                "chunk_index":  i,
                "type":         "book_pdf",
            })

        self.vectorstore.add_documents(chunks)
        logger.success(f"Проиндексировано {len(chunks)} чанков из '{book_name}'")

    # ─────────────────────────────────────────────
    # Загрузка всех книг из папки автоматически
    # ─────────────────────────────────────────────

    def load_all_books(self, books_dir: Optional[str] = None):
        """
        Автоматически сканирует папку data/books/ и индексирует все PDF.
        Подпапки используются как topic: nutrition / training / anatomy.

        Структура:
            books/nutrition/book.pdf  → topic='nutrition'
            books/training/book.pdf   → topic='training'
            books/anatomy/book.pdf    → topic='anatomy'
        """
        base = Path(books_dir) if books_dir else BOOKS_DIR

        if not base.exists():
            logger.error(f"Папка с книгами не найдена: {base}")
            return

        pdf_files = list(base.rglob("*.pdf"))
        if not pdf_files:
            logger.warning(f"PDF файлы не найдены в {base}")
            return

        logger.info(f"Найдено {len(pdf_files)} PDF файлов для индексации")

        for pdf_path in pdf_files:
            # Определяем topic по имени подпапки
            topic = pdf_path.parent.name  # nutrition / training / anatomy
            if topic not in ("nutrition", "training", "anatomy"):
                topic = "general"

            # Метаданные из имени файла (snake_case → красивое название)
            book_title = pdf_path.stem.replace("_", " ").title()

            self.load_pdf_book(
                pdf_path=str(pdf_path),
                topic=topic,
                metadata={"title": book_title}
            )

        logger.success(f"Индексация завершена. Всего файлов: {len(pdf_files)}")

    # ─────────────────────────────────────────────
    # Загрузка упражнений из JSON (существующий метод)
    # ─────────────────────────────────────────────

    def load_exercises_from_json(self, json_path: str):
        """Загружает базу упражнений из JSON файла."""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        docs = []
        for ex in data.get('exercises', []):
            content = (
                f"Упражнение: {ex['name']}\n"
                f"Основные мышцы: {', '.join(ex['muscles_primary'])}\n"
                f"Вспомогательные мышцы: {', '.join(ex['muscles_secondary'])}\n"
                f"Оборудование: {ex['equipment']}\n"
                f"Техника: {ex['technique']}\n"
                f"Ошибки: {', '.join(ex['common_errors'])}\n"
                f"Советы: {ex['tips']}"
            )
            docs.append(Document(
                page_content=content,
                metadata={"name": ex['name'], "topic": "exercise", "type": "exercise"}
            ))

        self.vectorstore.add_documents(docs)
        logger.success(f"Загружено {len(docs)} упражнений из {json_path}")

    # ─────────────────────────────────────────────
    # Поиск с фильтрацией по теме
    # ─────────────────────────────────────────────

    def search(self, query: str, k: int = 3, topic: Optional[str] = None):
        """
        Семантический поиск по векторной базе.

        Аргументы:
            query: поисковый запрос (вопрос пользователя)
            k:     количество результатов
            topic: фильтр по теме ('nutrition' / 'training' / 'anatomy')
        """
        if topic:
            # Поиск только по конкретной теме
            results = self.vectorstore.similarity_search(
                query,
                k=k,
                filter={"topic": topic}
            )
        else:
            results = self.vectorstore.similarity_search(query, k=k)

        return results

    def search_with_score(self, query: str, k: int = 5):
        """Поиск с оценкой релевантности (0.0 — идеально, 1.0 — нерелевантно)."""
        return self.vectorstore.similarity_search_with_score(query, k=k)

    def get_stats(self) -> dict:
        """Возвращает статистику по векторной БД."""
        collection = self.vectorstore._collection
        count = collection.count()
        return {"total_chunks": count}
```

---

## 🔧 Шаг 2 — Создать скрипт индексации `build_index.py`

Создай файл `ai_trainer/rag/build_index.py`:

```python
"""
build_index.py — скрипт для первичной индексации всех книг.

Запуск:
    python -m ai_trainer.rag.build_index
    python -m ai_trainer.rag.build_index --topic nutrition
    python -m ai_trainer.rag.build_index --pdf path/to/book.pdf --topic training
    python -m ai_trainer.rag.build_index --stats
"""
import argparse
from pathlib import Path
from loguru import logger
from ai_trainer.rag.knowledge_base import FitnessKnowledgeBase


def main():
    parser = argparse.ArgumentParser(description="Индексация книг для RAG системы")
    parser.add_argument("--pdf",    type=str, help="Путь к конкретному PDF файлу")
    parser.add_argument("--topic",  type=str, default="general",
                        choices=["nutrition", "training", "anatomy", "general"],
                        help="Тема книги")
    parser.add_argument("--author", type=str, default="", help="Автор книги")
    parser.add_argument("--title",  type=str, default="", help="Название книги")
    parser.add_argument("--all",    action="store_true",
                        help="Проиндексировать все книги из папки data/books/")
    parser.add_argument("--stats",  action="store_true",
                        help="Показать статистику ChromaDB")
    args = parser.parse_args()

    kb = FitnessKnowledgeBase()

    if args.stats:
        stats = kb.get_stats()
        print(f"\n📊 ChromaDB статистика:")
        print(f"   Всего чанков в базе: {stats['total_chunks']}")
        return

    if args.all:
        logger.info("Индексация всех книг из data/books/...")
        kb.load_all_books()

    elif args.pdf:
        meta = {}
        if args.title:  meta["title"]  = args.title
        if args.author: meta["author"] = args.author
        kb.load_pdf_book(args.pdf, topic=args.topic, metadata=meta)

    else:
        logger.info("Используй --all для индексации всех книг или --pdf для одной книги")
        logger.info("Пример: python -m ai_trainer.rag.build_index --all")
        logger.info("Пример: python -m ai_trainer.rag.build_index --pdf books/nutrition/sport_nutrition.pdf --topic nutrition --author Jeukendrup")


if __name__ == "__main__":
    main()
```

---

## 🔧 Шаг 3 — Улучшить `trainer_agent.py`

Текущий `retrieve_context_node` делает простой поиск без фильтрации.
Добавь **умное определение темы** по запросу пользователя:

```python
# В файле ai_trainer/agent/trainer_agent.py
# Заменить функцию retrieve_context_node на эту:

async def retrieve_context_node(state: AgentState):
    """Retrieves relevant context from the RAG knowledge base with topic filtering."""
    last_message = state['messages'][-1].content if state['messages'] else ""
    logger.info(f"Retrieving context for query: {last_message[:50]}...")

    # Определяем тему по ключевым словам для более точного поиска
    topic = _detect_topic(last_message)
    logger.debug(f"Detected topic: {topic}")

    # Ищем с фильтрацией по теме (3 релевантных чанка)
    docs = kb.search(last_message, k=3, topic=topic)

    # Форматируем контекст с указанием источника
    context_parts = []
    for doc in docs:
        source    = doc.metadata.get("book_title", doc.metadata.get("source", "База знаний"))
        author    = doc.metadata.get("author", "")
        source_label = f"{source} ({author})" if author else source
        context_parts.append(f"[Источник: {source_label}]\n{doc.page_content}")

    context_text = "\n\n---\n\n".join(context_parts)
    return {"retrieved_context": context_text}


def _detect_topic(query: str) -> str:
    """Определяет тему запроса по ключевым словам."""
    query_lower = query.lower()

    nutrition_keywords = [
        "белок", "протеин", "калори", "питани", "еда", "рацион",
        "углевод", "жир", "нутриент", "диет", "кало", "protein",
        "calories", "nutrition", "diet", "carbs", "fat", "macro"
    ]
    anatomy_keywords = [
        "мышц", "анатоми", "сустав", "связк", "боль", "травм",
        "muscle", "anatomy", "joint", "injury", "pain", "spine"
    ]
    training_keywords = [
        "тренировк", "упражнени", "программ", "подход", "повторени",
        "силов", "гипертрофи", "workout", "exercise", "sets", "reps",
        "program", "strength", "hypertrophy", "periodization"
    ]

    nutrition_score = sum(1 for kw in nutrition_keywords if kw in query_lower)
    anatomy_score   = sum(1 for kw in anatomy_keywords   if kw in query_lower)
    training_score  = sum(1 for kw in training_keywords  if kw in query_lower)

    scores = {
        "nutrition": nutrition_score,
        "anatomy":   anatomy_score,
        "training":  training_score,
    }

    best_topic = max(scores, key=scores.get)
    return best_topic if scores[best_topic] > 0 else None  # None = без фильтра
```

---

## 🔧 Шаг 4 — Добавить в `.gitignore`

```gitignore
# RAG векторная база (пересоздаётся локально)
ai_trainer/rag/data/chroma_db/
chroma_fitness_db/

# Книги (большие файлы, не хранить в git)
ai_trainer/rag/data/books/**/*.pdf
ai_trainer/rag/data/books/**/*.epub
```

---

## 🚀 Порядок запуска (с нуля)

### 1. Скопировать книги в нужные папки
```bash
# Создать структуру папок
mkdir -p ai_trainer/rag/data/books/nutrition
mkdir -p ai_trainer/rag/data/books/training
mkdir -p ai_trainer/rag/data/books/anatomy

# Скопировать скачанные PDF
cp ~/Downloads/sport_nutrition_jeukendrup.pdf ai_trainer/rag/data/books/nutrition/
cp ~/Downloads/starting_strength_rippetoe.pdf ai_trainer/rag/data/books/training/
cp ~/Downloads/human_anatomy_marieb.pdf       ai_trainer/rag/data/books/anatomy/
```

### 2. Запустить Ollama с моделью эмбеддингов
```bash
ollama pull nomic-embed-text
ollama serve
```

### 3. Проиндексировать все книги (разово)
```bash
python -m ai_trainer.rag.build_index --all
```

### 4. Проверить что всё работает
```bash
python -m ai_trainer.rag.build_index --stats
# Вывод: 📊 ChromaDB статистика: Всего чанков в базе: 12847
```

### 5. Запустить бота
```bash
python -m ai_trainer.bot.main
```

---

## 🔄 Добавление новой книги (после первичной индексации)

```bash
# Скопировать новую книгу
cp ~/Downloads/renaissance_diet.pdf ai_trainer/rag/data/books/nutrition/

# Проиндексировать только её
python -m ai_trainer.rag.build_index \
  --pdf ai_trainer/rag/data/books/nutrition/renaissance_diet.pdf \
  --topic nutrition \
  --author "Mike Israetel" \
  --title "The Renaissance Diet 2.0"
```

---

## 🧪 Тест RAG вручную

```python
# Запустить в Python консоли для проверки
from ai_trainer.rag.knowledge_base import FitnessKnowledgeBase

kb = FitnessKnowledgeBase()

# Тест поиска по питанию
results = kb.search("сколько белка нужно для набора мышечной массы", k=3, topic="nutrition")
for r in results:
    print(f"\n[{r.metadata.get('book_title')}]")
    print(r.page_content[:300])

# Тест поиска по тренировкам
results = kb.search("как строить периодизацию тренировок", k=2, topic="training")
for r in results:
    print(f"\n[{r.metadata.get('book_title')}]")
    print(r.page_content[:300])
```

---

## ⚡ Производительность и советы

| Параметр | Рекомендация |
|---|---|
| `CHUNK_SIZE` | 700 — хорошо для книг. Уменьши до 400 если ответы слишком длинные |
| `CHUNK_OVERLAP` | 100 — предотвращает потерю смысла на границах чанков |
| `k=3` в search | 3 чанка = ~2100 символов контекста, не перегружает промпт |
| Embedding модель | `nomic-embed-text` (локально) или `text-embedding-3-small` (OpenAI) |
| ChromaDB | Хранит на диске, загружается мгновенно при следующем старте |

---

## 📋 Будущие задачи RAG

- [ ] Обновить `knowledge_base.py` — добавить `load_pdf_book()` и `load_all_books()`
- [ ] Создать `build_index.py` скрипт
- [ ] Обновить `trainer_agent.py` — добавить `_detect_topic()` и умный поиск
- [ ] Скачать и положить книги по питанию в `data/books/nutrition/`
- [ ] Скачать и положить книги по тренировкам в `data/books/training/`
- [ ] Скачать и положить книги по анатомии в `data/books/anatomy/`
- [ ] Первичная индексация `python -m ai_trainer.rag.build_index --all`
- [ ] Добавить `chroma_db/` и `*.pdf` в `.gitignore`
- [ ] Добавить поддержку голосовых сообщений (Whisper API)
- [ ] Реализовать аналитику прогресса за месяц в виде графиков
- [ ] Интеграция с Google Calendar для планирования тренировок
