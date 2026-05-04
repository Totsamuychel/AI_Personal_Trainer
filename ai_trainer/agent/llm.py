import os
import asyncio
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from ai_trainer.db import database

# Singletons
_llm = None
_last_settings = None
_llm_lock = asyncio.Lock()

async def get_llm():
    """Retrieve the LLM based on database configuration (Singleton)."""
    global _llm, _last_settings
    
    async with _llm_lock:
        try:
            async with database.db_session() as db:
                from ai_trainer.db import models
                from sqlalchemy.future import select
                
                result = await db.execute(select(models.SystemSettings))
                settings = result.scalars().first()
                
                base_url = ""
                api_key = None
                
                if not settings:
                    # Fallback to env or create defaults if table is empty
                    provider = os.getenv("LLM_PROVIDER", "ollama")
                    if provider == "openai":
                        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
                        api_key = os.getenv("OPENAI_API_KEY")
                    else:
                        model = os.getenv("OLLAMA_MODEL", "gpt-oss:20b")
                        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
                else:
                    provider = settings.llm_provider
                    if provider == "openai":
                        model = settings.openai_model
                        api_key = settings.openai_api_key
                    else:
                        model = settings.ollama_model
                        base_url = settings.ollama_base_url

                # Check if settings changed to recreate LLM
                settings_str = f"{provider}:{model}:{base_url if provider == 'ollama' else ''}"
                if _llm is not None and _last_settings == settings_str:
                    return _llm
                
                _last_settings = settings_str
                
                if provider == "openai":
                    _llm = ChatOpenAI(model=model, openai_api_key=api_key or os.getenv("OPENAI_API_KEY"))
                else:
                    _llm = ChatOllama(
                        model=model,
                        base_url=base_url,
                        num_ctx=4096,
                        temperature=0.7,
                        timeout=120 # Увеличиваем таймаут до 2 минут для 20b модели
                    )
        except Exception as e:
            # Fallback to basic env if DB fails
            if _llm is not None: 
                return _llm
            provider = os.getenv("LLM_PROVIDER", "ollama")
            if provider == "openai":
                _llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
            else:
                _llm = ChatOllama(
                    model=os.getenv("OLLAMA_MODEL", "gpt-oss:20b"),
                    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
                )
        
        if _llm is None:
            raise RuntimeError("Failed to initialize LLM.")

        return _llm
