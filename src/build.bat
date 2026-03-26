@echo off
setlocal enabledelayedexpansion

:: F1 Betting Website Build Script for Windows
:: Automates virtual environment setup and application launch

:: Default configuration
set VENV_DIR=.venv
set APP_FILE=run.py
set ENVIRONMENT=production
set CUSTOM_PORT=

:: Parse command line arguments
:parse_args
if "%~1"=="" goto end_parse
if "%~1"=="--test" (
    set ENVIRONMENT=test
    shift
    goto parse_args
)
if "%~1"=="-t" (
    set ENVIRONMENT=test
    shift
    goto parse_args
)
if "%~1"=="--prod" (
    set ENVIRONMENT=production
    shift
    goto parse_args
)
if "%~1"=="-p" (
    set ENVIRONMENT=production
    shift
    goto parse_args
)
if "%~1"=="--port" (
    set CUSTOM_PORT=%~2
    shift
    shift
    goto parse_args
)
if "%~1"=="-P" (
    set CUSTOM_PORT=%~2
    shift
    shift
    goto parse_args
)
:end_parse

echo ▶ Starting in %ENVIRONMENT% mode
if defined CUSTOM_PORT (
    echo ▶ Using custom port: %CUSTOM_PORT%
)

echo ▶ Checking for Python 3...
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ❌ Python not found. Please install Python 3 and add it to your PATH.
    pause
    exit /b 1
)

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
if exist "%VENV_DIR%\Scripts\activate.bat" (
    call %VENV_DIR%\Scripts\activate.bat
) else if exist "%VENV_DIR%\bin\activate" (
    call %VENV_DIR%\bin\activate
) else (
    echo ❌ Failed to activate virtual environment
    echo ❌ Neither Scripts\activate.bat nor bin\activate found
    pause
    exit /b 1
)
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
    if "%ENVIRONMENT%" == "test" (
        echo ▶ Running in TEST mode (port 5000, debug=True)
        set FLASK_ENV=development
        set FLASK_DEBUG=1
        if exist "%VENV_DIR%\Scripts\python.exe" (
            "%VENV_DIR%\Scripts\python.exe" "%APP_FILE%"
        ) else if exist "%VENV_DIR%\bin\python" (
            "%VENV_DIR%\bin\python" "%APP_FILE%"
        ) else (
            python "%APP_FILE%"
        )
    ) else (
        if defined CUSTOM_PORT (
            echo ▶ Running in PRODUCTION mode with custom port %CUSTOM_PORT%
            set APP_PORT=%CUSTOM_PORT%
        ) else (
            echo ▶ Running in PRODUCTION mode (port 8080, debug=False)
        )
        if exist "%VENV_DIR%\Scripts\python.exe" (
            "%VENV_DIR%\Scripts\python.exe" "%APP_FILE%"
        ) else if exist "%VENV_DIR%\bin\python" (
            "%VENV_DIR%\bin\python" "%APP_FILE%"
        ) else (
            python "%APP_FILE%"
        )
    )
) else (
    echo ❌ %APP_FILE% not found
    pause
    exit /b 1
)

endlocal