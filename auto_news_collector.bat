@echo off
echo ========================================
echo NewsBasedTradingSystem Auto News Collector
echo ========================================
echo.

cd /d "C:\Users\iida\Documents\MetaTrader"

:LOOP
echo [%date% %time%] Starting news collection...
python enhanced_news_collector_v2.py

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] News collection failed
    echo Retrying in 5 minutes...
    timeout /t 300
    goto LOOP
)

echo [%date% %time%] Collection complete. Waiting 60 seconds...
timeout /t 60
goto LOOP