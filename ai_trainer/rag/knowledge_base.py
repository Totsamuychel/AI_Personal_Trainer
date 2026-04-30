import os
import json
from pathlib import Path
from typing import Optional

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Папка с книгами относительно корня проекта
BOOKS_DIR = Path(__file__).parent / "data" / "books"
CHROMA_DIR = Path(__file__).parent / "data" / "chroma_db"

# Размер чанков — баланс между контекстом и точностью поиска
CHUNK_SIZE    = 500   # уменьшено для стабильности
CHUNK_OVERLAP = 50    # уменьшено пропорционально


class FitnessKnowledgeBase:
    def __init__(self, persist_dir: Optional[str] = None):
        # Используем mxbai-embed-large как более современную альтернативу
        self.embeddings = OllamaEmbeddings(
            model=os.getenv("EMBEDDING_MODEL", "mxbai-embed-large"),
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
    # Загрузка упражнений из JSON
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
    # Поиск
    # ─────────────────────────────────────────────

    def search(self, query: str, k: int = 3, topic: Optional[str] = None):
        """
        Семантический поиск по векторной базе.
        """
        if topic:
            results = self.vectorstore.similarity_search(
                query,
                k=k,
                filter={"topic": topic}
            )
        else:
            results = self.vectorstore.similarity_search(query, k=k)

        return results

    def search_with_score(self, query: str, k: int = 5):
        """Поиск с оценкой релевантности."""
        return self.vectorstore.similarity_search_with_score(query, k=k)

    def get_stats(self) -> dict:
        """Возвращает статистику по векторной БД."""
        collection = self.vectorstore._collection
        count = collection.count()
        return {"total_chunks": count}
