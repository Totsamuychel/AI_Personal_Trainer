import os
import asyncio
import hashlib
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from loguru import logger
from ai_trainer.db import database

# Singletons
_llm = None
_last_settings = None
_llm_lock = asyncio.Lock()

# Retry config for transient LLM/provider failures
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "2"))
LLM_RETRY_BASE_DELAY = float(os.getenv("LLM_RETRY_BASE_DELAY", "1.0"))


async def ainvoke_with_retry(model, messages, max_retries: int = LLM_MAX_RETRIES,
                             base_delay: float = LLM_RETRY_BASE_DELAY):
    """Invoke an LLM with exponential backoff on transient failures.

    Retries up to ``max_retries`` times (so ``max_retries + 1`` attempts total),
    sleeping ``base_delay * 2**attempt`` seconds between tries. The final failure
    is re-raised so callers can surface a graceful error to the user.
    """
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return await model.ainvoke(messages)
        except Exception as e:
            last_exc = e
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"LLM invocation failed (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"LLM invocation failed after {max_retries + 1} attempts: {e}")
    raise last_exc

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

                # Check if settings changed to recreate LLM.
                # Hash the api_key (don't store it raw) so rotating the OpenAI key
                # invalidates the cached singleton instead of reusing the stale client.
                effective_key = api_key or os.getenv("OPENAI_API_KEY") or ""
                key_fingerprint = hashlib.sha256(effective_key.encode()).hexdigest()[:12] if provider == "openai" else ""
                settings_str = f"{provider}:{model}:{base_url if provider == 'ollama' else ''}:{key_fingerprint}"
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
