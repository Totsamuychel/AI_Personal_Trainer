@echo off
set PYTHONPATH=.
set DATABASE_URL=sqlite+aiosqlite:///./test.db
C:\ProgramData\anaconda3\python.exe ai_trainer/bot/main.py
pause
