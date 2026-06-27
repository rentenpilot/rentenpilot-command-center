@echo off
setlocal

cd /d "%~dp0app"
start "" cmd /k python app.py

timeout /t 8 /nobreak >nul
start "" "http://192.168.178.101:5000"
timeout /t 4 /nobreak >nul
start "" cmd /c powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5000/api/trading/start_stream | Out-Null } catch { }"

endlocal
