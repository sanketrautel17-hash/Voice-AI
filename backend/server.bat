@echo off
REM Voice AI Server Management Script

echo ========================================
echo Voice AI Server Manager
echo ========================================
echo.

:menu
echo [1] Start Server
echo [2] Stop Server
echo [3] Restart Server
echo [4] Check Server Status
echo [5] Exit
echo.
set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" goto start
if "%choice%"=="2" goto stop
if "%choice%"=="3" goto restart
if "%choice%"=="4" goto status
if "%choice%"=="5" goto end

echo Invalid choice. Please try again.
goto menu

:start
echo.
echo Starting Voice AI server...
cd /d "%~dp0"
.\venv\Scripts\python.exe run.py
goto menu

:stop
echo.
echo Stopping Voice AI server...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000') do (
    taskkill /F /PID %%a 2>nul
    if errorlevel 1 (
        echo No server running on port 8000
    ) else (
        echo Server stopped successfully!
    )
)
goto menu

:restart
echo.
echo Restarting Voice AI server...
call :stop
timeout /t 2 /nobreak >nul
call :start
goto menu

:status
echo.
echo Checking server status...
netstat -ano | findstr :8000
if errorlevel 1 (
    echo [STATUS] Server is NOT running
) else (
    echo [STATUS] Server is RUNNING on port 8000
    echo.
    echo To test: curl http://localhost:8000/calls
)
echo.
goto menu

:end
echo.
echo Goodbye!
exit /b
