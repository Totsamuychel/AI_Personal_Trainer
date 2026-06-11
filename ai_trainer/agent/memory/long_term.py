import os
from pathlib import Path
from datetime import datetime
from typing import List

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

MEMORY_DIR = Path(__file__).parent.parent.parent / "data" / "memory_db"

class UserMemoryStore:
    def __init__(self, user_id: str):
        self.user_id = str(user_id)
        
        # Ensure memory directory exists
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        user_dir = MEMORY_DIR / self.user_id
        
        self.embeddings = OllamaEmbeddings(
            model=os.getenv("EMBEDDING_MODEL", "nomic-embed-text"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
        
        self.vectorstore = Chroma(
            persist_directory=str(user_dir),
            embedding_function=self.embeddings,
            collection_name=f"user_{self.user_id}_memory"
        )

    def save_memory(self, fact: str, memory_type: str = "general"):
        """Saves a fact about the user into semantic memory."""
        logger.info(f"Saving memory for user {self.user_id}: {fact}")
        doc = Document(
            page_content=fact,
            metadata={
                "user_id": self.user_id, 
                "type": memory_type, 
                "timestamp": datetime.now().isoformat()
            }
        )
        self.vectorstore.add_documents([doc])

    def recall(self, query: str, k: int = 5) -> List[str]:
        """Retrieves relevant memories based on a query."""
        results = self.vectorstore.similarity_search(
            query, k=k,
            filter={"user_id": self.user_id}
        )
        return [doc.page_content for doc in results]

    def extract_and_save_facts(self, conversation: str, llm):
        """Uses LLM to extract important facts from conversation and saves them."""
        prompt = f"""
        Из следующего разговора с пользователем извлеки важные факты 
        для персонализации тренировок (например: травмы, предпочтения, жалобы на боль, любимые упражнения).
        Не выводи ничего кроме фактов. Выведи список фактов, по одному на строку.
        Если важных фактов нет, верни пустое сообщение.
        
        Разговор: 
        {conversation}
        """
        response = llm.invoke(prompt)
        facts_text = response.content.strip()
        
        if not facts_text or facts_text.lower() in ["нет", "нет фактов", "none"]:
            return
            
        facts = facts_text.split("\n")
        for fact in facts:
            fact = fact.strip("- *").strip()
            if fact:
                self.save_memory(fact, memory_type="extracted")
