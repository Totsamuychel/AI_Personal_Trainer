from typing import TypedDict, Annotated, List, Union
import operator
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from loguru import logger
import os
from ai_trainer.db import crud, database, models
from sqlalchemy import select

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    user_id: str
    user_profile: dict
    personal_records: List[dict]
    recent_workouts: List[dict]
    retrieved_context: str
    current_plan: dict
    action_type: str  # workout_log / nutrition_log / plan_gen / tip / analysis

def get_llm():
    """Retrieve the LLM based on environment configuration."""
    provider = os.getenv("LLM_PROVIDER", "ollama")
    if provider == "openai":
        return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    else:
        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )

async def load_user_profile_node(state: AgentState):
    """Load user profile, personal records, and workout history from the database."""
    logger.info(f"Loading real profile for user {state['user_id']}")
    
    async with database.db_session() as db:
        user = await crud.get_user_by_telegram_id(db, state['user_id'])
        
        if not user:
            logger.warning(f"User {state['user_id']} not found in DB")
            return {
                "user_profile": {"name": "Guest", "goal": "unknown"},
                "personal_records": [],
                "recent_workouts": []
            }
        
        # Convert user object to dict for state
        profile = {
            "name": user.name,
            "age": user.age,
            "height": user.height_cm,
            "weight": user.weight_kg,
            "goal": user.goal.value if user.goal else "N/A",
            "level": user.level,
            "preferred_split": user.preferred_split,
            "injuries": user.injuries
        }
        
        # Load PRs
        pr_result = await db.execute(select(models.PersonalRecord).filter(models.PersonalRecord.user_id == user.id))
        prs = pr_result.scalars().all()
        pr_list = [
            {"exercise": pr.exercise, "weight": pr.weight_kg, "reps": pr.reps, "1rm": pr.one_rm_est}
            for pr in prs
        ]
        
        # Load recent workouts
        history = await crud.get_workout_history(db, user.id, limit=5)
        workout_list = [
            {"date": w.date.isoformat(), "type": w.workout_type, "notes": w.notes}
            for w in history
        ]
        
        return {
            "user_profile": profile,
            "personal_records": pr_list,
            "recent_workouts": workout_list
        }

async def run_agent_node(state: AgentState):
    """Construct system message with user profile and invoke the LLM."""
    llm = get_llm()
    
    # Construct system message with user profile
    profile = state.get('user_profile', {})
    prs = state.get('personal_records', [])
    history = state.get('recent_workouts', [])
    
    system_prompt = f"""
    Ты — AI персональный тренер.
    Клиент: {profile.get('name', 'N/A')}
    Цель: {profile.get('goal', 'N/A')}
    Вес: {profile.get('weight', 'N/A')} кг
    Травмы: {profile.get('injuries', 'Нет')}
    
    Личные рекорды: {prs}
    Последние тренировки: {history}
    
    Помогай клиенту достигать целей, будь профессионален и мотивируй!
    """
    
    messages = [SystemMessage(content=system_prompt)] + state['messages']
    response = await llm.ainvoke(messages)
    return {"messages": [response]}

def build_trainer_graph():
    """Build and compile the LangGraph workflow for the trainer agent."""
    workflow = StateGraph(AgentState)

    workflow.add_node("load_profile", load_user_profile_node)
    workflow.add_node("agent", run_agent_node)

    workflow.set_entry_point("load_profile")
    workflow.add_edge("load_profile", "agent")
    workflow.add_edge("agent", END)

    return workflow.compile()
