import os
import json
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from dotenv import load_dotenv

load_dotenv()

class FitnessKnowledgeBase:
    def __init__(self, persist_dir: str = "./chroma_fitness_db"):
        self.embeddings = OllamaEmbeddings(
            model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
        self.vectorstore = Chroma(
            persist_directory=persist_dir,
            embedding_function=self.embeddings
        )

    def load_exercises_from_json(self, json_path: str):
        """Loads the exercise database from a JSON file."""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        docs = []
        for ex in data.get('exercises', []):
            content = f"Упражнение: {ex['name']}\n" \
                      f"Основные мышцы: {', '.join(ex['muscles_primary'])}\n" \
                      f"Вспомогательные мышцы: {', '.join(ex['muscles_secondary'])}\n" \
                      f"Оборудование: {ex['equipment']}\n" \
                      f"Техника: {ex['technique']}\n" \
                      f"Ошибки: {', '.join(ex['common_errors'])}\n" \
                      f"Советы: {ex['tips']}"
            
            docs.append(Document(
                page_content=content,
                metadata={"name": ex['name'], "type": "exercise"}
            ))
        
        self.vectorstore.add_documents(docs)
        print(f"Loaded {len(docs)} exercises from {json_path}")

    def load_books_from_json(self, json_path: str):
        """Loads book extracts from a JSON file."""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        book_title = data.get("book_title", "Unknown Book")
        author = data.get("author", "Unknown Author")
        
        docs = []
        for extract in data.get('extracts', []):
            content = f"Источник: {book_title} ({author})\n" \
                      f"Тема: {extract['topic']}\n" \
                      f"Содержание: {extract['content']}"
            
            docs.append(Document(
                page_content=content,
                metadata={
                    "title": book_title,
                    "topic": extract['topic'],
                    "type": "book_extract",
                    "tags": extract.get("tags", [])
                }
            ))
            
        self.vectorstore.add_documents(docs)
        print(f"Loaded {len(docs)} book extracts from {json_path}")

    def load_book_chunks(self, text_path: str, metadata: dict = None):
        """Loads a large text file, splits it into chunks, and adds to vector store."""
        if not os.path.exists(text_path):
            print(f"Error: File not found {text_path}")
            return

        with open(text_path, 'r', encoding='utf-8') as f:
            text = f.read()

        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
        )
        chunks = text_splitter.split_text(text)
        
        docs = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata.update({"chunk_index": i, "type": "book_chunk"})
            
            docs.append(Document(
                page_content=chunk,
                metadata=chunk_metadata
            ))
            
        self.vectorstore.add_documents(docs)
        print(f"Added {len(docs)} chunks from {text_path} to vector store")

    def search(self, query: str, k: int = 3):
        """Semantic search in the knowledge base."""
        return self.vectorstore.similarity_search(query, k=k)
