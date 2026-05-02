import os
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from ai_trainer.db import database, crud

# Singletons
_llm = None
_last_settings = None

def get_llm():
    """Retrieve the LLM based on database configuration (Singleton)."""
    global _llm, _last_settings
    
    # Use sync session to fetch settings
    try:
        with database.sync_db_session() as db:
            # We need a sync version of get_system_settings or just query directly
            from ai_trainer.db import models
            settings = db.query(models.SystemSettings).first()
            
            if not settings:
                # Fallback to env or create defaults if table is empty
                provider = os.getenv("LLM_PROVIDER", "ollama")
                model = os.getenv("OPENAI_MODEL", "gpt-4o-mini") if provider == "openai" else os.getenv("OLLAMA_MODEL", "gpt-oss20b")
                base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            else:
                provider = settings.llm_provider
                if provider == "openai":
                    model = settings.openai_model
                    api_key = settings.openai_api_key
                else:
                    model = settings.ollama_model
                    base_url = settings.ollama_base_url
                    api_key = None

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
        if _llm is not None: return _llm
        provider = os.getenv("LLM_PROVIDER", "ollama")
        if provider == "openai":
            _llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
        else:
            _llm = ChatOllama(
                model=os.getenv("OLLAMA_MODEL", "gpt-oss20b"),
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            )

    return _llm
