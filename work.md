# 📋 План работ — AI Personal Trainer

## ✅ Выполнено
- [x] Убрать `test.db` из репо и добавить в `.gitignore`
- [x] Защитить `open(prompt_path)` в агенте через `try/except`
- [x] Вынести `get_llm()` и `build_trainer_graph()` как синглтоны
- [x] Исправить `IndexError` в парсинге reps в `workout.py`
- [x] Добавить handler в боте для вызова агента (любое текстовое сообщение вне FSM)
- [x] Реализовать scheduler для утренних советов/напоминаний (используется `apscheduler`)
- [x] Обновить `knowledge_base.py` — добавить `load_pdf_book()` и `load_all_books()`
- [x] Создать `build_index.py` скрипт
- [x] Обновить `trainer_agent.py` — добавить `_detect_topic()` и умный поиск
- [x] Первичная индексация `python -m ai_trainer.rag.build_index --all`
- [x] Добавить `chroma_db/` и `*.pdf` в `.gitignore`
- [x] Интеграция инструментов (Tools) в агента: Nutrition, Workouts, Plans
- [x] Синхронизация инструментов агента с Google Sheets

---

# 📚 RAG система — подключение книг к нейросети

## Что такое RAG и зачем это нужно

RAG (Retrieval-Augmented Generation) — это механизм, при котором перед каждым ответом нейросеть
получает **релевантные фрагменты из твоих книг** и использует их как контекст.

---

## 📋 Будущие задачи

- [ ] Скачать и положить книги по анатомии в `data/books/anatomy/`
- [ ] Добавить поддержку голосовых сообщений (Whisper API)
- [ ] Реализовать аналитику прогресса за месяц в виде графиков
- [ ] Интеграция с Google Calendar для планирования тренировок
