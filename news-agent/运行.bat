@echo off
chcp 65001 >nul
title 新闻智能体
cd /d "%~dp0"

if not exist ".env" (
    echo   [提示] 未找到 .env 配置文件
    echo   请先运行 "首次配置.bat" 填入API密钥
    pause
    exit /b 1
)

echo ============================================
echo   新闻智能体 News Agent
echo   采集 -> 筛选 -> DeepSeek改写 -> 豆包配图 -> 飞书通知
echo ============================================
echo.
echo   启动: %date% %time%

python -m news_agent

echo.
echo   完成: %date% %time%
echo   草稿: drafts\
pause
