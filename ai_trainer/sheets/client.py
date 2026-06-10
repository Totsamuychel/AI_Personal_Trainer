import os
import asyncio
import gspread
from google.oauth2.service_account import Credentials
from loguru import logger
from datetime import datetime
import time

class SheetsClient:
    def __init__(self):
        self.scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        self.creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
        self.spreadsheet_id = os.getenv("GOOGLE_SHEET_TEMPLATE_ID")
        self.client = self._authenticate()
        
        # Sheet names
        self.SHEET_PROFILE = "📋 Profile"
        self.SHEET_NUTRITION = "🥗 Nutrition"
        self.SHEET_MONTHLY_PLAN = "📅 Monthly Plan"
        self.SHEET_WEEKLY_PLAN = "🗓️ Weekly Plan"
        self.SHEET_WORKOUT_LOG = "📊 Workout Results"

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
        if not self.client:
            return None
            
        if not sid or "your_template_spreadsheet_id" in sid or sid.strip() == "":
            logger.warning("Google Spreadsheet ID not configured. Skipping sheets integration.")
            return None
            
        try:
            return self.client.open_by_key(sid)
        except Exception as e:
            logger.error(f"Error opening spreadsheet {sid}: {e}")
            return None

    def setup_spreadsheet(self):
        """Initializes the spreadsheet with all necessary sheets and formatting."""
        ss = self.get_spreadsheet()
        if not ss: return
        
        existing_sheets = [s.title for s in ss.worksheets()]
        required_sheets = [
            self.SHEET_PROFILE, 
            self.SHEET_NUTRITION, 
            self.SHEET_MONTHLY_PLAN, 
            self.SHEET_WEEKLY_PLAN, 
            self.SHEET_WORKOUT_LOG
        ]
        
        for sheet_title in required_sheets:
            if sheet_title not in existing_sheets:
                ss.add_worksheet(title=sheet_title, rows="1000", cols="20")
                logger.info(f"Created worksheet: {sheet_title}")
                self._format_header(ss.worksheet(sheet_title), sheet_title)
        
        logger.success("Spreadsheet setup complete")

    def _format_header(self, ws, title):
        """Applies beautiful formatting to the header row."""
        headers = {
            self.SHEET_PROFILE: ["Parameter", "Value", "Notes"],
            self.SHEET_NUTRITION: ["Date", "Meal", "Description", "Calories", "Protein", "Carbs", "Fat"],
            self.SHEET_MONTHLY_PLAN: ["Month", "Goal", "Focus", "Notes"],
            self.SHEET_WEEKLY_PLAN: ["Week", "Type", "Day", "Workout Type", "Exercises"],
            self.SHEET_WORKOUT_LOG: ["Date", "Exercise", "Type", "Weight (kg)", "Sets", "Reps", "1RM Est", "Progress vs Prev Month"]
        }
        
        header_row = headers.get(title, [])
        if header_row:
            ws.update('A1', [header_row])
            # Apply bold and background color to header
            ws.format("A1:Z1", {
                "backgroundColor": {"red": 0.2, "green": 0.2, "blue": 0.2},
                "horizontalAlignment": "CENTER",
                "textFormat": {"foregroundColor": {"red": 1.0, "green": 1.0, "blue": 1.0}, "bold": True}
            })

    async def log_workout(self, user_name: str, session_data: dict):
        """Records a workout and calculates progress vs previous entries."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._log_workout_sync, user_name, session_data)

    def _log_workout_sync(self, user_name: str, session_data: dict):
        """Blocking gspread implementation; runs in a thread pool to avoid stalling the event loop."""
        try:
            ss = self.get_spreadsheet()
            if not ss: return
            
            ws = ss.worksheet(self.SHEET_WORKOUT_LOG)
            rows = []
            date_now = datetime.now()
            date_str = date_now.strftime("%Y-%m-%d %H:%M")
            
            # Find the last row to apply formulas
            all_values = ws.get_all_values()
            next_row = len(all_values) + 1
            
            for ex in session_data.get("exercises", []):
                max_weight = max(ex.get("weight_kg", [0]))
                reps = ex.get("reps", [0])
                avg_reps = sum(reps)/len(reps) if reps else 0
                one_rm = round(max_weight * (1 + avg_reps / 30), 2)
                
                # Formula for progress: compares current 1RM with the max 1RM of the same exercise from previous month
                # This is a complex formula for Google Sheets
                exercise_name = ex.get("name")
                
                # Simplified progress formula: compare with anything above in the same column for the same exercise
                # In a real scenario, we'd use a more targeted LOOKUP or QUERY
                progress_formula = f'=IFERROR(G{next_row} - MAXIFS(G$2:G{next_row-1}, B$2:B{next_row-1}, "{exercise_name}"), "New Record")'
                
                rows.append([
                    date_str,
                    exercise_name,
                    session_data.get("workout_type", "N/A"),
                    max_weight,
                    ex.get("sets"),
                    str(reps),
                    one_rm,
                    progress_formula
                ])
                next_row += 1
            
            if rows:
                ws.append_rows(rows, value_input_option="USER_ENTERED")
                logger.success(f"Logged {len(rows)} exercises with progress tracking for {user_name}")
        except Exception as e:
            logger.error(f"Error logging workout to sheets: {e}")

    async def log_nutrition(self, user_name: str, meal_data: dict):
        """Records nutrition on the '🥗 Nutrition' sheet."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._log_nutrition_sync, user_name, meal_data)

    def _log_nutrition_sync(self, user_name: str, meal_data: dict):
        """Blocking gspread implementation; runs in a thread pool to avoid stalling the event loop."""
        try:
            ss = self.get_spreadsheet()
            if not ss: return
            
            ws = ss.worksheet(self.SHEET_NUTRITION)
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            row = [
                date_str,
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

    async def update_monthly_plan(self, month_name: str, plan_summary: dict):
        """Updates the monthly overview."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._update_monthly_plan_sync, month_name, plan_summary)

    def _update_monthly_plan_sync(self, month_name: str, plan_summary: dict):
        """Blocking gspread implementation; runs in a thread pool to avoid stalling the event loop."""
        try:
            ss = self.get_spreadsheet()
            if not ss: return
            ws = ss.worksheet(self.SHEET_MONTHLY_PLAN)
            row = [month_name, plan_summary.get('goal'), plan_summary.get('focus'), plan_summary.get('notes')]
            ws.append_row(row)
        except Exception as e:
            logger.error(f"Error updating monthly plan in sheets: {e}")

    async def update_weekly_plan(self, week_data: dict):
        """Syncs the current weekly plan to the spreadsheet."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._update_weekly_plan_sync, week_data)

    def _update_weekly_plan_sync(self, week_data: dict):
        """Blocking gspread implementation; runs in a thread pool to avoid stalling the event loop."""
        try:
            ss = self.get_spreadsheet()
            if not ss: return
            ws = ss.worksheet(self.SHEET_WEEKLY_PLAN)
            
            # Format: Week #, Type, Day, Workout, Exercises String
            rows = []
            week_label = f"Week {week_data.get('week_number')}"
            week_type = week_data.get('week_type')
            
            for day in week_data.get('days', []):
                ex_list = ", ".join([f"{e['name']} ({e['sets']}x{e['reps']} @ {e['target_weight']}kg)" for e in day.get('exercises', [])])
                rows.append([week_label, week_type, day['day'], day['type'], ex_list])
            
            if rows:
                ws.append_rows(rows)
                logger.info(f"Synced weekly plan to sheets")
        except Exception as e:
            logger.error(f"Error updating weekly plan in sheets: {e}")
