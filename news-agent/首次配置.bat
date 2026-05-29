@echo off
chcp 65001 >nul
title 新闻智能体 - 首次配置

echo ============================================
echo   新闻智能体 - 首次配置
echo ============================================
echo.
python --version 2>nul
if errorlevel 1 (
    echo   [错误] 未检测到 Python，请先安装 Python 3.12+
    echo   下载: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo.

if not exist ".env" copy .env.example .env >nul

echo   接下来请编辑 .env 文件，填入3个API密钥:
echo.
echo     DEEPSEEK_API_KEY     DeepSeek改写服务
echo     ARK_API_KEY          火山引擎豆包配图
echo     NEWSAPI_KEY          NewsAPI新闻采集
echo.
echo   获取地址:
echo     DeepSeek : https://platform.deepseek.com/api_keys
echo     火山引擎 : https://console.volcengine.com/ark/region:ark+cn-beijing/apikey
echo     NewsAPI  : https://newsapi.org/register (免费)
echo.

start notepad .env
echo   编辑保存后关闭，然后双击 "运行.bat" 即可
pause
