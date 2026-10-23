@echo off
setlocal

REM One-click launcher for Drama Agent Platform.
REM It creates a local virtual environment if needed, installs project dependencies,
REM then starts the FastAPI service.

cd /d "%~dp0"

set "HOST=127.0.0.1"
set "PORT=8000"
set "PYTHON_EXE=.venv\Scripts\python.exe"

echo ==========================================
echo Drama Agent Platform - One Click Launcher
echo Project: %CD%
echo URL: http://%HOST%:%PORT%
echo ==========================================
echo.

if not exist "%PYTHON_EXE%" (
    echo [1/4] Creating virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Failed to create venv with "py -3"; trying "python"...
        python -m venv .venv
    )
)

if not exist "%PYTHON_EXE%" (
    echo ERROR: Python virtual environment was not created.
    echo Please make sure Python 3.11+ is installed and available in PATH.
    pause
    exit /b 1
)

echo [2/4] Upgrading pip...
"%PYTHON_EXE%" -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip.
    pause
    exit /b 1
)

echo [3/4] Installing project dependencies...
"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies from requirements.txt.
    pause
    exit /b 1
)

echo [4/4] Starting API server...
echo Open test page: http://%HOST%:%PORT%/
echo API docs:       http://%HOST%:%PORT%/docs
echo Health check:   http://%HOST%:%PORT%/api/v1/health
echo Press Ctrl+C to stop the server.
echo.

"%PYTHON_EXE%" app.py --serve --host %HOST% --port %PORT%

echo.
echo Server stopped.
pause
