@echo off
TITLE Job Application Dashboard
echo.
echo ============================================
echo   Job Application Dashboard - Launcher
echo ============================================
echo.

SET SCRIPT_DIR=%~dp0
SET APP=%SCRIPT_DIR%job_tracker_app.py
SET FETCH=%SCRIPT_DIR%job_tracker_fetch.py

REM Find Python - tries Anaconda first, then system Python
SET PYTHON=
IF EXIST "C:\anaconda3\python.exe"         SET PYTHON=C:\anaconda3\python.exe
IF EXIST "C:\ProgramData\anaconda3\python.exe" SET PYTHON=C:\ProgramData\anaconda3\python.exe
IF "%PYTHON%"=="" FOR /F "delims=" %%i IN ('where python 2^>nul') DO IF "%PYTHON%"=="" SET PYTHON=%%i

IF "%PYTHON%"=="" (
    echo [ERROR] Python not found. Install Anaconda or add Python to PATH.
    pause & exit /b 1
)
echo [INFO] Using Python: %PYTHON%

REM Check if Streamlit already running
netstat -ano | findstr :8501 >nul 2>&1
IF %ERRORLEVEL% EQU 0 (
    echo [INFO] Streamlit already running on port 8501
    echo [INFO] Opening browser...
    start "" "http://localhost:8501"
) ELSE (
    echo [INFO] Starting Streamlit...
    start "" "%PYTHON%" -m streamlit run "%APP%" --server.port 8501
    timeout /t 4 /nobreak >nul
    start "" "http://localhost:8501"
)

echo.
echo Dashboard running at http://localhost:8501
echo.
pause
