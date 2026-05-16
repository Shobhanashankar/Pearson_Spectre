@echo off
echo ============================================
echo  SPECTRE BACKEND — Windows Setup Script
echo ============================================

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.13 from python.org
    pause
    exit /b 1
)

echo [1/5] Creating virtual environment...
python -m venv venv

echo [2/5] Activating venv...
call venv\Scripts\activate.bat

echo [3/5] Installing dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo [4/5] Copying .env template...
if not exist .env (
    copy .env.example .env
    echo [ACTION NEEDED] Open .env and fill in your GEMINI_API_KEY
) else (
    echo .env already exists, skipping.
)

echo [5/5] Creating uploads folder...
if not exist uploads mkdir uploads

echo.
echo ============================================
echo  Setup complete!
echo  Next steps:
echo    1. Edit .env and add your GEMINI_API_KEY
echo    2. Run: venv\Scripts\activate
echo    3. Run: python -m app.db.seed
echo    4. Run: uvicorn main:app --reload
echo    5. Open: http://localhost:8000/docs
echo ============================================
pause
