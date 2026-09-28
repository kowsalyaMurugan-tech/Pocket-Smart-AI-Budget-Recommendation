@echo off
title PocketSmart AI - Budget Planner
cd /d "%~dp0"
echo ===================================================
echo   PocketSmart AI: Smart Budget & Recommendation
echo   Opening in your browser: http://127.0.0.1:8000
echo ===================================================
start http://127.0.0.1:8000
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload
pause
