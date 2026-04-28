import os
import gspread
from google.oauth2.service_account import Credentials
from loguru import logger

class SheetsClient:
    def __init__(self):
        self.scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        self.creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
        self.client = self._authenticate()

    def _authenticate(self):
        if not os.path.exists(self.creds_path):
            logger.warning(f"Credentials file not found at {self.creds_path}. Sheets integration disabled.")
            return None
        
        creds = Credentials.from_service_account_file(self.creds_path, scopes=self.scopes)
        return gspread.authorize(creds)

    def get_spreadsheet(self, spreadsheet_id: str):
        if not self.client:
            return None
        return self.client.open_by_key(spreadsheet_id)

    def append_row(self, spreadsheet_id: str, sheet_name: str, row: list):
        try:
            ss = self.get_spreadsheet(spreadsheet_id)
            if ss:
                ws = ss.worksheet(sheet_name)
                ws.append_row(row)
                return True
        except Exception as e:
            logger.error(f"Error appending to sheet: {e}")
        return False
