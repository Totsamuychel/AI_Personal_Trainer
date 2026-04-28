from langchain.tools import tool
from ai_trainer.agent.trainer_agent import get_llm
from ai_trainer.db import crud, database
from langchain_core.prompts import PromptTemplate
from loguru import logger
import json
import re

@tool
def calculate_macros_from_text(description: str) -> str:
    """
    Calculates macronutrients based on a textual description of food.
    Returns a JSON string with keys: calories, protein, carbs, fat, meal_name.
    """
    llm = get_llm()
    prompt = PromptTemplate.from_template(
        "Ты профессиональный диетолог. Посчитай КБЖУ для следующего приема пищи: {description}.\n"
        "Обязательно верни ответ ТОЛЬКО в формате валидного JSON без лишнего текста.\n"
        "Формат: {{\"calories\": float, \"protein\": float, \"carbs\": float, \"fat\": float, \"meal_name\": \"название блюда\"}}"
    )
    chain = prompt | llm
    
    try:
        response = chain.invoke({"description": description})
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Clean up the response to extract JSON
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            return json_match.group(0)
        return content
    except Exception as e:
        logger.error(f"Error calculating macros: {e}")
        return f"Error: {str(e)}"

@tool
def log_nutrition_tool(telegram_id: str, meal_description: str, macros_json: str) -> str:
    """
    Saves nutrition data to the database.
    Expects macros_json to be a JSON string from calculate_macros_from_text.
    """
    try:
        # Parse JSON data
        data = json.loads(macros_json)
        
        # Prepare data for DB
        nutrition_data = {
            "meal_name": data.get("meal_name", "Unknown meal"),
            "description": meal_description,
            "calories": float(data.get("calories", 0)),
            "protein_g": float(data.get("protein", 0)),
            "carbs_g": float(data.get("carbs", 0)),
            "fat_g": float(data.get("fat", 0))
        }
        
        with database.db_session() as db:
            user = crud.get_user_by_telegram_id(db, telegram_id)
            if not user:
                return "Error: User not found."
            
            crud.create_nutrition_log(db, user.id, nutrition_data)
            
        return (
            f"✅ Nutrition logged: {nutrition_data['meal_name']}\n"
            f"🔥 Calories: {nutrition_data['calories']} kcal\n"
            f"🥩 P: {nutrition_data['protein_g']}g | 🍞 C: {nutrition_data['carbs_g']}g | 🥑 F: {nutrition_data['fat_g']}g"
        )
    except Exception as e:
        logger.error(f"Error logging nutrition: {e}")
        return f"❌ Error saving nutrition log: {str(e)}"
