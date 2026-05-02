@echo off
title AI Personal Trainer - Master Launcher
echo ==================================================
echo    🚀 AI Personal Trainer Master Launcher 🚀
echo ==================================================
echo.

:: 1. Launch Backend API
echo [1/3] Starting Backend API (Port 8000)...
start "AI-Trainer: API" cmd /k "set PYTHONPATH=. & set DATABASE_URL=sqlite+aiosqlite:///./test.db & C:\ProgramData\anaconda3\python.exe -m uvicorn ai_trainer.api.app:app --host 0.0.0.0 --port 8000"

:: 2. Launch Telegram Bot
echo [2/3] Starting Telegram Bot...
start "AI-Trainer: Bot" cmd /k "set PYTHONPATH=. & set DATABASE_URL=sqlite+aiosqlite:///./test.db & C:\ProgramData\anaconda3\python.exe ai_trainer/bot/main.py"

:: 3. Launch Admin Frontend
echo [3/3] Starting Admin Panel (Vite)...
start "AI-Trainer: Admin" cmd /k "cd admin_frontend && npm run dev"

echo.
echo ==================================================
echo ✅ All services are starting!
echo.
echo - API: http://localhost:8000
echo - Admin: http://localhost:5173
echo - Bot: Check your Telegram
echo ==================================================
echo.
echo Keep this window open to track launch status.
pause
