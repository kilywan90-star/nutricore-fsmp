@echo off
cd /d "%~dp0"
title NewsAgent-Gen

if not exist "dataaw_cache.json" (
    echo [ERROR] Cache not found. Run 1-collect.bat first with VPN.
    pause
    exit /b 1
)

echo ============================================
echo   News Agent - STEP 2: Generate
echo   From cache, no VPN, ~2-3 hours
echo ============================================
echo.

python -m news_agent --from-cache

pause
