@echo off
cd /d "%~dp0"
title News Agent - Collect Cache

echo ============================================
echo   News Agent v0.2 - STEP 1: Collect Cache
echo   Fetches 800+ articles via Google News RSS
echo   Needs proxy/VPN, takes ~20 seconds
echo ============================================
echo.

python -m news_agent --collect-only

pause
