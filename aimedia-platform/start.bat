@echo off
chcp 65001 >nul
cd /d %~dp0

echo ============================================
echo   AI Media Platform - Setup &amp; Start
echo ============================================

REM --- Python check ---
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

REM --- .env ---
if not exist .env (
    echo [INFO] Creating .env from template ...
    copy .env.example .env >nul
    echo [OK] .env created
)

REM --- Backend deps ---
echo [INFO] Installing backend dependencies ...
cd backend
pip install -q -r requirements.txt 2>nul
pip install -q aiosqlite httpx "python-jose[cryptography]" "passlib[bcrypt]" bcrypt==4.0.1 2>nul

REM --- DB init ---
echo [INFO] Initializing database ...
python -m alembic upgrade head 2>nul
python -m app.core.seed 2>nul

REM --- Frontend deps ---
echo [INFO] Installing frontend dependencies ...
cd ..\frontend
if not exist node_modules (
    call npm install --registry https://registry.npmmirror.com 2>nul
)

echo.
echo ============================================
echo   Starting services:
echo   Backend:  http://localhost:8000/docs
echo   Frontend: http://localhost:5173
echo   Login:    admin / admin123
echo ============================================

start "AI-Media-Backend" cmd /c "cd /d %~dp0backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
start "AI-Media-Frontend" cmd /c "cd /d %~dp0frontend && npx vite --host 0.0.0.0 --port 5173"

echo Services started. Close this window or press any key.
pause >nul
