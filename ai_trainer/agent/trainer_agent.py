from typing import TypedDict, Annotated, List, Union
import operator
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_community.llms import Ollama
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from loguru import logger
import os

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    user_id: str
    user_profile: dict
    retrieved_context: str
    current_plan: dict
    action_type: str  # workout_log / nutrition_log / plan_gen / tip / analysis

def get_llm():
    provider = os.getenv("LLM_PROVIDER", "ollama")
    if provider == "openai":
        return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    else:
        return Ollama(
            model=os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        )

def load_user_profile_node(state: AgentState):
    logger.info(f"Loading profile for user {state['user_id']}")
    # logic to load from DB
    return {"user_profile": {"name": "User", "goal": "strength"}}

def run_agent_node(state: AgentState):
    llm = get_llm()
    # Simplified agent logic
    prompt = "Ты AI Тренер. Помоги пользователю."
    messages = [SystemMessage(content=prompt)] + state['messages']
    response = llm.invoke(messages)
    return {"messages": [response]}

def build_trainer_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("load_profile", load_user_profile_node)
    workflow.add_node("agent", run_agent_node)

    workflow.set_entry_point("load_profile")
    workflow.add_edge("load_profile", "agent")
    workflow.add_edge("agent", END)

    return workflow.compile()

# Example usage
# trainer_agent = build_trainer_graph()
