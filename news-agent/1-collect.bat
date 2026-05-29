@echo off
cd /d "%~dp0"
title NewsAgent

echo ============================================
echo   News Agent - STEP 1: Collect Cache
echo   Needs proxy/VPN, takes ~20s
echo ============================================
echo.

python -m news_agent --collect-only

pause
