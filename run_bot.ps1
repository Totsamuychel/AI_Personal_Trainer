$env:PYTHONPATH = "."
$env:DATABASE_URL = "sqlite+aiosqlite:///./test.db"
python ai_trainer/bot/main.py
