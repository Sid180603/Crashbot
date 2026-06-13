@echo off
REM ============================================
REM Start Crashbot in Local Development Mode
REM ============================================

echo.
echo ========================================
echo    Starting Crashbot
echo ========================================
echo.

REM Check if .env exists
if not exist .env (
    echo [ERROR] .env file not found. Run setup.bat first.
    pause
    exit /b 1
)

REM Start backend in new window
echo [INFO] Starting backend server...
start "Crashbot Backend" cmd /k "cd backend && venv\Scripts\activate && python -m app.main"

REM Wait a bit for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in new window
echo [INFO] Starting frontend server...
start "Crashbot Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo    Crashbot Started!
echo ========================================
echo.
echo Frontend: http://localhost:3002
echo Backend:  http://localhost:8002
echo API Docs: http://localhost:8002/docs
echo.
echo Press any key to stop all services...
pause >nul

REM Stop services
taskkill /FI "WINDOWTITLE eq Crashbot Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Crashbot Frontend*" /F >nul 2>&1

echo.
echo [INFO] All services stopped
pause
