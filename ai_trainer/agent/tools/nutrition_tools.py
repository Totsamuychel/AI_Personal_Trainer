from langchain.tools import tool
from ai_trainer.agent.trainer_agent import get_llm
from ai_trainer.db import crud, database
from ai_trainer.sheets.client import SheetsClient
from langchain_core.prompts import PromptTemplate
from loguru import logger
import json
import re
import asyncio

sheets = SheetsClient()

@tool
async def calculate_macros_from_text(description: str) -> str:
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
        response = await llm.ainvoke(prompt.format(description=description))
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
async def log_nutrition_tool(telegram_id: str, meal_description: str, macros_json: str) -> str:
    """
    Saves nutrition data to the database and Google Sheets.
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
            "protein": float(data.get("protein", 0)), # Note: SheetsClient expects 'protein'
            "carbs": float(data.get("carbs", 0)),
            "fat": float(data.get("fat", 0))
        }
        
        # Database log (using async session)
        async with database.db_session() as db:
            user = await crud.get_user_by_telegram_id(db, telegram_id)
            if not user:
                return "Error: User not found."
            
            # Map for DB (which uses protein_g, carbs_g, fat_g)
            db_data = {
                "meal_name": nutrition_data["meal_name"],
                "description": nutrition_data["description"],
                "calories": nutrition_data["calories"],
                "protein_g": nutrition_data["protein"],
                "carbs_g": nutrition_data["carbs"],
                "fat_g": nutrition_data["fat"]
            }
            await crud.create_nutrition_log(db, user.id, db_data)
            
            # Sync to Sheets
            await sheets.log_nutrition(user.name, nutrition_data)
            
        return (
            f"✅ Nutrition logged: {nutrition_data['meal_name']}\n"
            f"🔥 Calories: {nutrition_data['calories']} kcal\n"
            f"🥩 P: {nutrition_data['protein']}g | 🍞 C: {nutrition_data['carbs']}g | 🥑 F: {nutrition_data['fat']}g"
        )
    except Exception as e:
        logger.error(f"Error logging nutrition: {e}")
        return f"❌ Error saving nutrition log: {str(e)}"
