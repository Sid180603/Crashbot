@echo off
REM ============================================
REM Crashbot Setup Script for Windows
REM ============================================

echo.
echo ========================================
echo    Crashbot Setup Script
echo ========================================
echo.

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

REM Check for Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

REM Check for Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Docker not found. Docker setup will be skipped.
    set DOCKER_AVAILABLE=0
) else (
    set DOCKER_AVAILABLE=1
)

echo [INFO] Prerequisites checked successfully
echo.

REM Setup environment file
if not exist .env (
    echo [INFO] Creating .env file from template...
    copy .env.example .env
    echo [INFO] Please edit .env file with your API keys
    echo.
)

REM Ask user for setup type
echo Choose setup type:
echo 1. Local Development (Python + Node.js)
echo 2. Docker (Recommended)
echo 3. Both
echo.
set /p SETUP_TYPE="Enter choice (1/2/3): "

if "%SETUP_TYPE%"=="1" goto local_setup
if "%SETUP_TYPE%"=="2" goto docker_setup
if "%SETUP_TYPE%"=="3" goto both_setup
goto invalid_choice

:local_setup
echo.
echo ========================================
echo    Setting up Local Development
echo ========================================
echo.

REM Backend setup
echo [1/4] Setting up backend...
cd backend

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate

echo Installing dependencies...
pip install -r requirements.txt

cd ..
echo [INFO] Backend setup complete
echo.

REM Frontend setup
echo [2/4] Setting up frontend...
cd frontend

if not exist node_modules (
    echo Installing dependencies...
    call npm install
)

cd ..
echo [INFO] Frontend setup complete
echo.

REM Database setup
echo [3/4] Database setup...
echo Please ensure PostgreSQL is running on localhost:5435 (Docker) or 5432 (local)
echo Default credentials: crashbot/crashbot_password
echo.

REM Storage directories
echo [4/4] Creating storage directories...
if not exist storage\dumps mkdir storage\dumps
if not exist storage\symbols mkdir storage\symbols
if not exist storage\chroma_db mkdir storage\chroma_db
if not exist logs mkdir logs
echo [INFO] Storage directories created
echo.

echo ========================================
echo    Local Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Edit .env file with your API keys
echo 2. Start PostgreSQL server
echo 3. Run 'start_local.bat' to start the application
echo.
pause
exit /b 0

:docker_setup
if "%DOCKER_AVAILABLE%"=="0" (
    echo [ERROR] Docker is not available. Please install Docker first.
    pause
    exit /b 1
)

echo.
echo ========================================
echo    Setting up Docker Environment
echo ========================================
echo.

echo [INFO] Building Docker images...
docker-compose build

echo.
echo ========================================
echo    Docker Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Edit .env file with your API keys
echo 2. Run 'docker-compose up' to start
echo.
pause
exit /b 0

:both_setup
call :local_setup
call :docker_setup
exit /b 0

:invalid_choice
echo [ERROR] Invalid choice. Please run the script again.
pause
exit /b 1
