@echo off
setlocal

schtasks /Create /F /SC ONLOGON /TN "RentenPilot Command Center" /TR "C:\AI\rentenpilot-command-center\start_rentenpilot.bat"

endlocal
