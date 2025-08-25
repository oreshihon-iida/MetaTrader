@echo off
echo ========================================
echo Starting Demo Trading System
echo ========================================
echo.

echo Step 1: Generating initial signals...
python generate_initial_signals.py

echo.
echo Step 2: Starting continuous news collection...
echo Press Ctrl+C to stop
echo.
start auto_news_collector.bat

echo.
echo ========================================
echo Demo trading system is now running!
echo 1. Open MT5
echo 2. Apply EA to USD/JPY H1 chart
echo 3. Enable AutoTrading (green button)
echo ========================================
pause