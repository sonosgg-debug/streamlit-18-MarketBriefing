@echo off
title Market Briefing Dashboard
echo ====================================================
echo   Market Briefing Dashboard - KRX and US
echo ====================================================
echo.
echo [1/2] Checking required packages...
python -m pip install -r requirements.txt --quiet

echo.
echo [2/2] Launching Dashboard web app...
echo Press Ctrl+C to stop the server.
echo.

python -m streamlit run app.py
pause
