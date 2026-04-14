@echo off
REM Resume Parser Development Server Runner (Windows)
REM Starts both the FastAPI backend and Streamlit frontend

cd /d "%~dp0"
echo.
echo ============================================================
echo 🚀 Resume Parser - Development Server (Windows)
echo ============================================================
echo.
echo This script will start:
echo   • FastAPI backend on http://localhost:8000
echo   • Streamlit frontend on http://localhost:8501
echo.
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if .env exists
if not exist ".env" (
    echo ⚠️  .env file not found
    if exist ".env.example" (
        echo Creating .env from .env.example...
        copy ".env.example" ".env" >nul
        echo ✅ Created .env file
    )
)

REM Start the development server
echo ✅ Starting development servers...
echo.
python run_dev.py

pause
