@echo off
set PYTHONPATH=.
set DATABASE_URL=sqlite+aiosqlite:///./test.db
C:\ProgramData\anaconda3\python.exe -m uvicorn ai_trainer.api.app:app --host 0.0.0.0 --port 8000 --reload
pause
