from typing import TypedDict, Annotated, List, Union, Optional
import operator
import json
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from loguru import logger
import os
from ai_trainer.db import crud, database, models
from ai_trainer.rag.knowledge_base import FitnessKnowledgeBase
from sqlalchemy import select

# Initialize knowledge base
kb = FitnessKnowledgeBase()

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    user_id: str
    user_profile: dict
    personal_records: List[dict]
    recent_workouts: List[dict]
    retrieved_context: str
    current_plan: dict
    action_type: str  # workout_log / nutrition_log / plan_gen / tip / analysis

# Singletons
_llm = None
_trainer_graph = None

def get_llm():
    """Retrieve the LLM based on environment configuration (Singleton)."""
    global _llm
    if _llm is not None:
        return _llm
        
    provider = os.getenv("LLM_PROVIDER", "ollama")
    if provider == "openai":
        _llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    else:
        _llm = ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )
    return _llm

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

async def retrieve_context_node(state: AgentState):
    """Retrieves relevant context from the RAG knowledge base."""
    last_message = state['messages'][-1].content if state['messages'] else ""
    logger.info(f"Retrieving context for query: {last_message[:50]}...")
    
    docs = kb.search(last_message, k=3)
    context_text = "\n\n".join([doc.page_content for doc in docs])
    
    return {"retrieved_context": context_text}

async def run_agent_node(state: AgentState):
    """Construct system message with user profile and retrieved context, then invoke the LLM."""
    llm = get_llm()
    
    # Construct system message with user profile
    profile = state.get('user_profile', {})
    prs = state.get('personal_records', [])
    history = state.get('recent_workouts', [])
    context = state.get('retrieved_context', "")
    plan = state.get('current_plan', {})
    
    # Load system prompt from file
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "system_prompt.txt")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt_template = f.read()
    except Exception as e:
        logger.error(f"Failed to load system prompt from {prompt_path}: {e}")
        system_prompt_template = "You are a fitness assistant. Name: {name}, Goal: {goal}. Context: {retrieved_context}"
    
    system_prompt = system_prompt_template.format(
        name=profile.get('name', 'N/A'),
        age=profile.get('age', 'N/A'),
        height=profile.get('height', 'N/A'),
        weight=profile.get('weight', 'N/A'),
        goal=profile.get('goal', 'N/A'),
        level=profile.get('level', 'N/A'),
        preferred_split=profile.get('preferred_split', 'N/A'),
        week_type="N/A", # Will be filled from current_plan if needed
        injuries=profile.get('injuries', 'None'),
        personal_records=json.dumps(prs, ensure_ascii=False, indent=2),
        recent_workouts=json.dumps(history, ensure_ascii=False, indent=2),
        current_plan=json.dumps(plan, ensure_ascii=False, indent=2),
        retrieved_context=context
    )
    
    messages = [SystemMessage(content=system_prompt)] + state['messages']
    response = await llm.ainvoke(messages)
    return {"messages": [response]}

def build_trainer_graph():
    """Build and compile the LangGraph workflow for the trainer agent (Singleton)."""
    global _trainer_graph
    if _trainer_graph is not None:
        return _trainer_graph
        
    workflow = StateGraph(AgentState)

    workflow.add_node("load_profile", load_user_profile_node)
    workflow.add_node("retrieve_context", retrieve_context_node)
    workflow.add_node("agent", run_agent_node)

    workflow.set_entry_point("load_profile")
    workflow.add_edge("load_profile", "retrieve_context")
    workflow.add_edge("retrieve_context", "agent")
    workflow.add_edge("agent", END)

    _trainer_graph = workflow.compile()
    return _trainer_graph
