"""
build_index.py — скрипт для первичной индексации всех книг и упражнений.
"""
import argparse
from pathlib import Path
from loguru import logger
from ai_trainer.rag.knowledge_base import FitnessKnowledgeBase


def main():
    parser = argparse.ArgumentParser(description="Индексация книг для RAG системы")
    parser.add_argument("--pdf",    type=str, help="Путь к конкретному PDF файлу")
    parser.add_argument("--topic",  type=str, default="general",
                        choices=["nutrition", "training", "anatomy", "general", "exercise"],
                        help="Тема книги/данных")
    parser.add_argument("--author", type=str, default="", help="Автор книги")
    parser.add_argument("--title",  type=str, default="", help="Название книги")
    parser.add_argument("--all",    action="store_true",
                        help="Проиндексировать все книги из папки data/books/")
    parser.add_argument("--exercises", action="store_true",
                        help="Проиндексировать все упражнения из data/exercises/")
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

    if args.exercises:
        logger.info("Индексация упражнений из data/exercises/...")
        exercises_dir = Path(__file__).parent / "data" / "exercises"
        for json_path in exercises_dir.glob("*.json"):
            kb.load_exercises_from_json(str(json_path))

    if args.pdf:
        meta = {}
        if args.title:  meta["title"]  = args.title
        if args.author: meta["author"] = args.author
        kb.load_pdf_book(args.pdf, topic=args.topic, metadata=meta)

    if not (args.all or args.exercises or args.pdf or args.stats):
        logger.info("Используй --all для индексации всех книг или --exercises для упражнений")
        logger.info("Пример: python -m ai_trainer.rag.build_index --all --exercises")


if __name__ == "__main__":
    main()
