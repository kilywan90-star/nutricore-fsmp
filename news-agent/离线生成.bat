@echo off
cd /d "%~dp0"
title News Agent - Generate from Cache

echo ============================================
echo   News Agent v0.2 - STEP 2: Generate
echo   Reads from data/raw_cache.json
echo   DeepSeek rewrite + Seedream images
echo   No VPN needed, ~2-3 hours
echo ============================================
echo.

if not exist "data\raw_cache.json" (
    echo   [ERROR] Cache not found: data\raw_cache.json
    echo   Run STEP 1 first: 采集缓存.bat (with VPN on)
    pause
    exit /b 1
)

python -m news_agent --from-cache

pause
