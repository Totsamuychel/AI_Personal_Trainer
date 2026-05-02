from typing import TypedDict, Annotated, List, Union, Optional
import operator
import json
import os
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from loguru import logger
from sqlalchemy import select

from ai_trainer.db import crud, database, models
from ai_trainer.rag.knowledge_base import FitnessKnowledgeBase
from ai_trainer.agent.llm import get_llm
from ai_trainer.agent.memory.long_term import UserMemoryStore

# Import tools
from ai_trainer.agent.tools.nutrition_tools import calculate_macros_from_text, log_nutrition_tool
from ai_trainer.agent.tools.workout_tools import log_workout_session_tool, get_workout_history_tool
from ai_trainer.agent.tools.plan_tools import generate_weekly_plan_tool, get_current_plan_tool

# Initialize knowledge base
kb = FitnessKnowledgeBase()

# Define tools list
tools = [
    calculate_macros_from_text, 
    log_nutrition_tool,
    log_workout_session_tool, 
    get_workout_history_tool,
    generate_weekly_plan_tool, 
    get_current_plan_tool
]

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    user_id: str
    user_profile: dict
    personal_records: List[dict]
    recent_workouts: List[dict]
    retrieved_context: str
    user_memories: List[str]
    current_plan: dict
    action_type: str  # workout_log / nutrition_log / plan_gen / tip / analysis

# Singletons
_trainer_graph = None

def get_bound_llm():
    """Retrieve the LLM bound with tools."""
    llm = get_llm()
    return llm.bind_tools(tools)

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
        
        # Load current plan
        plan_result = await db.execute(
            select(models.WeeklyPlan).filter(models.WeeklyPlan.user_id == user.id, models.WeeklyPlan.is_active == 1)
        )
        plan = plan_result.scalars().first()
        plan_dict = plan.plan_data if plan else {}
        
        return {
            "user_profile": profile,
            "personal_records": pr_list,
            "recent_workouts": workout_list,
            "current_plan": plan_dict
        }

async def retrieve_context_node(state: AgentState):
    """Retrieves context from RAG (books) and User Memory (personal facts)."""
    last_message = ""
    for msg in reversed(state['messages']):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break
    
    if not last_message:
        return {"retrieved_context": "", "user_memories": []}

    logger.info(f"Retrieving context and memory for user {state['user_id']}")

    # 1. Поиск по общей базе знаний (RAG)
    topic = _detect_topic(last_message)
    docs = kb.search(last_message, k=2, topic=topic)

    context_parts = []
    for doc in docs:
        source    = doc.metadata.get("book_title", doc.metadata.get("source", "База знаний"))
        page_num  = doc.metadata.get("page_number", "")
        author    = doc.metadata.get("author", "")
        
        source_label = f"{source} ({author})" if author else source
        if page_num:
            source_label += f" [стр. {page_num}]"
            
        context_parts.append(f"[Источник: {source_label}]\n{doc.page_content}")

    # 2. Поиск по памяти пользователя
    memory_store = UserMemoryStore(state['user_id'])
    memories = memory_store.recall(last_message, k=3)

    return {
        "retrieved_context": "\n\n---\n\n".join(context_parts),
        "user_memories": memories
    }

def _detect_topic(query: str) -> str:
    """Определяет тему запроса по ключевым словам."""
    query_lower = query.lower()

    nutrition_keywords = [
        "белок", "протеин", "калори", "питани", "еда", "рацион",
        "углевод", "жир", "нутриент", "диет", "кало", "protein",
        "calories", "nutrition", "diet", "carbs", "fat", "macro"
    ]
    anatomy_keywords = [
        "мышц", "анатоми", "сустав", "связк", "боль", "травм",
        "muscle", "anatomy", "joint", "injury", "pain", "spine"
    ]
    training_keywords = [
        "тренировк", "упражнени", "программ", "подход", "повторени",
        "силов", "гипертрофи", "workout", "exercise", "sets", "reps",
        "program", "strength", "hypertrophy", "periodization"
    ]

    nutrition_score = sum(1 for kw in nutrition_keywords if kw in query_lower)
    anatomy_score   = sum(1 for kw in anatomy_keywords   if kw in query_lower)
    training_score  = sum(1 for kw in training_keywords  if kw in query_lower)

    scores = {
        "nutrition": nutrition_score,
        "anatomy":   anatomy_score,
        "training":  training_score,
    }

    best_topic = max(scores, key=scores.get)
    return best_topic if scores[best_topic] > 0 else None  # None = без фильтра

async def run_agent_node(state: AgentState):
    """Construct system message with user profile and retrieved context, then invoke the LLM."""
    llm = get_bound_llm()
    
    # Construct system message with user profile
    profile = state.get('user_profile', {})
    prs = state.get('personal_records', [])
    history = state.get('recent_workouts', [])
    context = state.get('retrieved_context', "")
    memories = state.get('user_memories', [])
    plan = state.get('current_plan', {})
    
    # Load system prompt from file
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts", "system_prompt.txt")
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt_template = f.read()
    except Exception as e:
        logger.error(f"Failed to load system prompt from {prompt_path}: {e}")
        system_prompt_template = "You are a fitness assistant. Name: {name}, Goal: {goal}. Context: {retrieved_context}. Memories: {user_memories}"
    
    # Форматируем персональные факты
    memories_text = "\n".join([f"- {m}" for m in memories]) if memories else "Нет сохраненных фактов."

    system_prompt = system_prompt_template.format(
        name=profile.get('name', 'N/A'),
        age=profile.get('age', 'N/A'),
        height=profile.get('height', 'N/A'),
        weight=profile.get('weight', 'N/A'),
        goal=profile.get('goal', 'N/A'),
        level=profile.get('level', 'N/A'),
        preferred_split=profile.get('preferred_split', 'N/A'),
        week_type=plan.get('week_type', 'N/A'),
        injuries=profile.get('injuries', 'None'),
        telegram_id=state['user_id'],
        personal_records=json.dumps(prs, ensure_ascii=False, indent=2),
        recent_workouts=json.dumps(history, ensure_ascii=False, indent=2),
        current_plan=json.dumps(plan, ensure_ascii=False, indent=2),
        retrieved_context=context,
        user_memories=memories_text
    )
    
    messages = [SystemMessage(content=system_prompt)] + state['messages']
    response = await llm.ainvoke(messages)
    return {"messages": [response]}

def should_continue(state: AgentState):
    """Determines whether the agent should continue to tools or end the conversation."""
    last_message = state['messages'][-1]
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    return "store_memory"

async def store_memory_node(state: AgentState):
    """Extract and save new facts from the conversation."""
    # Берем последние 2-3 сообщения для анализа
    conv_history = ""
    for msg in state['messages'][-3:]:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        conv_history += f"{role}: {content}\n"
    
    logger.info(f"Extracting memories for user {state['user_id']}")
    memory_store = UserMemoryStore(state['user_id'])
    
    # Используем get_llm() напрямую для анализа (без инструментов)
    llm = get_llm()
    memory_store.extract_and_save_facts(conv_history, llm)
    
    return state

def build_trainer_graph():
    """Build and compile the LangGraph workflow for the trainer agent (Singleton)."""
    global _trainer_graph
    if _trainer_graph is not None:
        return _trainer_graph
        
    workflow = StateGraph(AgentState)

    workflow.add_node("load_profile", load_user_profile_node)
    workflow.add_node("retrieve_context", retrieve_context_node)
    workflow.add_node("agent", run_agent_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.add_node("store_memory", store_memory_node)

    workflow.set_entry_point("load_profile")
    workflow.add_edge("load_profile", "retrieve_context")
    workflow.add_edge("retrieve_context", "agent")
    
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "store_memory": "store_memory"
        }
    )
    
    workflow.add_edge("tools", "agent")
    workflow.add_edge("store_memory", END)

    _trainer_graph = workflow.compile()
    return _trainer_graph
