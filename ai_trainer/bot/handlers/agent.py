from aiogram import Router, types
from ai_trainer.agent.trainer_agent import build_trainer_graph
from loguru import logger

router = Router()

@router.message()
async def chat_with_agent(message: types.Message):
    """Handle all other messages by passing them to the AI agent."""
    if not message.text:
        return

    # Check if the user is in a state (not handled here, but as a fallback)
    # This handler will be registered last to act as a fallback.
    
    try:
        # Prepare state for the agent
        # Note: In a real scenario, we'd fetch profile/history here if not using nodes
        # But our graph has nodes for that.
        initial_state = {
            "messages": [message.text],
            "user_id": str(message.from_user.id),
            "profile": {},
            "workout_history": [],
            "personal_records": [],
            "retrieved_context": "",
            "current_plan": {},
            "action_type": "analysis" # Default
        }
        
        # Build and run the graph
        app = build_trainer_graph()
        result = await app.ainvoke(initial_state)
        
        # Get the last message from the agent
        if result and "messages" in result and result["messages"]:
            response = result["messages"][-1]
            await message.answer(response.content)
        else:
            await message.answer("Извини, я не смог обработать твой запрос.")
            
    except Exception as e:
        logger.error(f"Error in agent handler: {e}")
        await message.answer("Произошла ошибка при общении с ИИ-тренером.")
