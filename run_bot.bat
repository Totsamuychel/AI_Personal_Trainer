@echo off
set PYTHONPATH=.
set DATABASE_URL=sqlite+aiosqlite:///./test.db
python ai_trainer/bot/main.py
pause
