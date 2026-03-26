@echo off
setlocal enabledelayedexpansion

:: F1 Betting Website Build Script for Windows
:: Automates virtual environment setup and application launch

echo ▶ Checking for Python 3...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Python not found. Please install Python 3 and add it to your PATH.
    pause
    exit /b 1
)

set VENV_DIR=.venv
set APP_FILE=run.py

:: 1. Create virtual environment if missing
echo ▶ Checking virtual environment...
if not exist "%VENV_DIR%" (
    echo ▶ Creating virtual environment in %VENV_DIR%...
    python -m venv %VENV_DIR%
    if %ERRORLEVEL% neq 0 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
) else (
    echo ▶ Virtual environment already exists
)

:: 2. Activate virtual environment
echo ▶ Activating virtual environment...
call %VENV_DIR%\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo ❌ Failed to activate virtual environment
    pause
    exit /b 1
)

:: 3. Upgrade pip
echo ▶ Upgrading pip...
python -m pip install --upgrade pip
if %ERRORLEVEL% neq 0 (
    echo ⚠️ Failed to upgrade pip, continuing anyway...
)

:: 4. Install requirements
echo ▶ Checking for requirements.txt...
if exist "requirements.txt" (
    echo ▶ Installing requirements...
    pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo ❌ Failed to install requirements
        pause
        exit /b 1
    )
) else (
    echo ⚠️ requirements.txt not found, installing Flask manually...
    pip install flask flask-cors
    if %ERRORLEVEL% neq 0 (
        echo ❌ Failed to install Flask
        pause
        exit /b 1
    )
)

:: 5. Run the application
echo ▶ Starting Python app: %APP_FILE%...
if exist "%APP_FILE%" (
    python "%APP_FILE%"
) else (
    echo ❌ %APP_FILE% not found
    pause
    exit /b 1
)

endlocal