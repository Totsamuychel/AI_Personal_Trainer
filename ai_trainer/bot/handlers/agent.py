from aiogram import Router, types
from ai_trainer.agent.trainer_agent import build_trainer_graph
from langchain_core.messages import HumanMessage
from loguru import logger

router = Router()

TELEGRAM_MAX_LEN = 4096


def _normalize_content(content) -> str:
    """LLM message content may be a str or a list of content blocks; flatten to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(block.get("text", ""))
        return "".join(parts)
    return str(content) if content is not None else ""


async def _send_chunked(message: types.Message, text: str):
    """Send text respecting Telegram's 4096-character per-message limit."""
    for start in range(0, len(text), TELEGRAM_MAX_LEN):
        await message.answer(text[start:start + TELEGRAM_MAX_LEN])

@router.message()
async def chat_with_agent(message: types.Message):
    """Handle all other messages by passing them to the AI agent."""
    if not message.text:
        return

    try:
        initial_state = {
            "messages": [HumanMessage(content=message.text)],
            "user_id": str(message.from_user.id),
            "user_profile": {},
            "personal_records": [],
            "recent_workouts": [],
            "retrieved_context": "",
            "user_memories": [], # Обязательное поле для AgentState
            "current_plan": {},
            "action_type": "analysis"
        }
        
        logger.info(f"Sending message to AI agent from {message.from_user.id}")
        app = build_trainer_graph()
        result = await app.ainvoke(initial_state)
        
        if result and "messages" in result and result["messages"]:
            response = result["messages"][-1]
            text = _normalize_content(getattr(response, "content", "")).strip()
            if text:
                await _send_chunked(message, text)
            else:
                await message.answer("Извини, я не смог обработать твой запрос.")
        else:
            await message.answer("Извини, я не смог обработать твой запрос.")
            
    except Exception as e:
        logger.error(f"Error in agent handler: {e}")
        await message.answer("Произошла ошибка при общении с ИИ-тренером.")

