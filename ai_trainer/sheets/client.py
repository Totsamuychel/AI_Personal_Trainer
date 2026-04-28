import os
import gspread
from google.oauth2.service_account import Credentials
from loguru import logger
from datetime import datetime

class SheetsClient:
    def __init__(self):
        self.scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        self.creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
        self.spreadsheet_id = os.getenv("GOOGLE_SHEET_TEMPLATE_ID")
        self.client = self._authenticate()

    def _authenticate(self):
        if not os.path.exists(self.creds_path):
            logger.warning(f"Credentials file not found at {self.creds_path}. Sheets integration disabled.")
            return None
        
        try:
            creds = Credentials.from_service_account_file(self.creds_path, scopes=self.scopes)
            return gspread.authorize(creds)
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Sheets: {e}")
            return None

    def get_spreadsheet(self, spreadsheet_id: str = None):
        sid = spreadsheet_id or self.spreadsheet_id
        if not self.client or not sid:
            logger.error("Sheets client not authenticated or Spreadsheet ID missing")
            return None
        try:
            return self.client.open_by_key(sid)
        except Exception as e:
            logger.error(f"Error opening spreadsheet {sid}: {e}")
            return None

    def log_workout(self, user_name: str, session_data: dict):
        """Записывает тренировку на лист '📈 Прогресс нагрузок'."""
        try:
            ss = self.get_spreadsheet()
            if not ss: return
            
            ws = ss.worksheet("📈 Прогресс нагрузок")
            rows = []
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            
            for ex in session_data.get("exercises", []):
                # Row format: Date, User, Exercise, Type, Weight, Sets, Reps, 1RM
                max_weight = max(ex.get("weight_kg", [0]))
                reps = ex.get("reps", [0])
                avg_reps = sum(reps)/len(reps) if reps else 0
                one_rm = round(max_weight * (1 + avg_reps / 30), 2)
                
                rows.append([
                    date_str,
                    user_name,
                    ex.get("name"),
                    session_data.get("workout_type", "N/A"),
                    max_weight,
                    ex.get("sets"),
                    str(reps),
                    one_rm
                ])
            
            if rows:
                ws.append_rows(rows)
                logger.info(f"Logged {len(rows)} exercises for {user_name}")
        except Exception as e:
            logger.error(f"Error logging workout to sheets: {e}")

    def log_nutrition(self, user_name: str, meal_data: dict):
        """Записывает питание на лист '🥗 Питание'."""
        try:
            ss = self.get_spreadsheet()
            if not ss: return
            
            ws = ss.worksheet("🥗 Питание")
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            row = [
                date_str,
                user_name,
                meal_data.get("meal_name"),
                meal_data.get("description"),
                meal_data.get("calories"),
                meal_data.get("protein"),
                meal_data.get("carbs"),
                meal_data.get("fat")
            ]
            ws.append_row(row)
            logger.info(f"Logged nutrition for {user_name}")
        except Exception as e:
            logger.error(f"Error logging nutrition to sheets: {e}")

    def update_profile(self, profile_data: dict):
        """Обновляет лист '📋 Профиль'."""
        try:
            ss = self.get_spreadsheet()
            if not ss: return
            ws = ss.worksheet("📋 Профиль")
            # Clear and update or find specific user row
            # For MVP: simple append or overwrite fixed cells
            ws.update('B2', profile_data.get('name'))
            ws.update('B3', profile_data.get('weight_kg'))
            ws.update('B4', profile_data.get('goal'))
        except Exception as e:
            logger.error(f"Error updating profile in sheets: {e}")
