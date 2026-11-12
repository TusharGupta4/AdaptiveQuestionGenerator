Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "[1/2] Checking Gemini AI Connectivity..." -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
& ".\venv\Scripts\python.exe" check_ai.py $args

Write-Host "`n===================================================" -ForegroundColor Cyan
Write-Host "[2/2] Checking Supabase Cloud Connectivity..." -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan
& ".\venv\Scripts\python.exe" check_supabase.py $args
