@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo   Landlord System - Start
echo ========================================

echo [1/2] Starting backend (port 8005)...
start "Backend-8005" /d "%~dp0backend" cmd /k "python -m uvicorn main:app --host 0.0.0.0 --port 8005 --reload"
timeout /t 3 >nul

echo [2/2] Starting frontend (port 5173)...
start "Frontend" /d "%~dp0frontend" cmd /k "npx vite --host 0.0.0.0 --port 5173"
timeout /t 4 >nul

echo.
echo ========================================
echo   Frontend : http://localhost:5173
echo   Backend  : http://localhost:8005
echo   API Docs : http://localhost:8005/docs
echo ========================================
echo.
pause
