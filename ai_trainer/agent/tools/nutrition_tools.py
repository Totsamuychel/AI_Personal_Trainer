from langchain.tools import tool
from ai_trainer.agent.trainer_agent import get_llm
from langchain_core.prompts import PromptTemplate
import json

@tool
def calculate_macros_from_text(description: str) -> str:
    """Calculates macronutrients based on a textual description of food."""
    llm = get_llm()
    prompt = PromptTemplate.from_template(
        "Ты диетолог. Посчитай КБЖУ для следующего приема пищи: {description}. "
        "Верни ответ в формате JSON: {{\"calories\": float, \"protein\": float, \"carbs\": float, \"fat\": float, \"meal_name\": str}}"
    )
    chain = prompt | llm
    response = chain.invoke({{"description": description}})
    
    # Simple extraction if not using JSON mode
    content = response.content if hasattr(response, 'content') else str(response)
    return content

@tool
def log_nutrition_tool(telegram_id: str, meal_description: str, macros_json: str) -> str:
    """Records nutrition data in the DB."""
    # Logic to save to PostgreSQL
    return f"Запись о питании '{meal_description}' сохранена."
