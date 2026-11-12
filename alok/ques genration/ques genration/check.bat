@echo off
echo ===================================================
echo [1/2] Checking Gemini AI Connectivity...
echo ===================================================
.\venv\Scripts\python.exe check_ai.py %*
echo.
echo ===================================================
echo [2/2] Checking Supabase Cloud Connectivity...
echo ===================================================
.\venv\Scripts\python.exe check_supabase.py %*
