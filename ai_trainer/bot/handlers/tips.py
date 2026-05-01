from aiogram import Router, types, F
from aiogram.filters import CommandObject, Command
from loguru import logger
from ai_trainer.rag.knowledge_base import FitnessKnowledgeBase

router = Router()
kb = FitnessKnowledgeBase()

@router.message(Command("tip"))
async def cmd_tip(message: types.Message, command: CommandObject):
    """Retrieves technique tips from the RAG knowledge base for a specific exercise."""
    if not command.args:
        await message.answer("ℹ️ Использование: `/tip [название упражнения]`\n\nПример: `/tip жим лежа`", parse_mode="Markdown")
        return
        
    exercise_name = command.args
    await message.answer(f"⏳ Ищу технику для '{exercise_name}' в базе знаний...")
    
    try:
        # Search the knowledge base
        results = kb.search(exercise_name, k=2, topic="exercise")
        
        if not results:
            # Fallback to general search
            results = kb.search(exercise_name, k=2)
            
        if not results:
            await message.answer(f"К сожалению, я не нашел упражнение '{exercise_name}' в своей базе.")
            return
            
        text = f"💡 **Техника: {exercise_name}**\n\n"
        for i, doc in enumerate(results):
            # Limit the content length slightly
            content = doc.page_content
            if len(content) > 500:
                content = content[:500] + "..."
            text += f"{content}\n\n"
            
        await message.answer(text, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error searching tips: {e}")
        await message.answer("Произошла ошибка при поиске информации.")
