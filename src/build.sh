#!/usr/bin/env bash

set -e # exit on any error 

# Default configuration
VENV_DIR=".venv"
APP_FILE="run.py"
ENVIRONMENT="production"  # default to production
CUSTOM_PORT=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --test|-t)
            ENVIRONMENT="test"
            shift
            ;;
        --prod|-p)
            ENVIRONMENT="production"
            shift
            ;;
        --port|-P)
            CUSTOM_PORT="$2"
            shift 2
            ;;
        -*|--*)
            echo "Unknown option: $1"
            exit 1
            ;;
        *)
            shift
            ;;
    esac
done

echo "▶ Starting in $ENVIRONMENT mode"
if [ -n "$CUSTOM_PORT" ]; then
    echo "▶ Using custom port: $CUSTOM_PORT"
fi

echo "▶ Checking for Python 3..."
python3 --version

# 1 Create virtual environment if missing
if [ ! -d "$VENV_DIR" ]; then
    echo "▶ Creating virtual environment in $VENV_DIR"
    python3 -m venv "$VENV_DIR"
else
    echo "▶ Virtual environment already exists"
fi

# 2 Activate virtual environment
echo "▶ Activating virtual environment"
source "$VENV_DIR/bin/activate"

# 3 Upgrade pip
echo "▶ Upgrading pip"
pip install --upgrade pip

# 4 Install requirements
if [ -f "requirements.txt" ]; then
    echo "▶ Installing requirements"
    pip install -r requirements.txt
else
    echo "⚠️ requirements.txt not found, installing Flask manually..."
    pip install flask flask-cors
fi

# 5 Run the app
if [ -f "$APP_FILE" ]; then
    echo "▶ Starting Python app: $APP_FILE"
    
    if [ "$ENVIRONMENT" = "test" ]; then
        echo "▶ Running in TEST mode (port 5000, debug=True)"
        export FLASK_ENV=development
        export FLASK_DEBUG=1
        python "$APP_FILE"
    else
        if [ -n "$CUSTOM_PORT" ]; then
            echo "▶ Running in PRODUCTION mode with custom port $CUSTOM_PORT"
            # Pass custom port to the application
            export APP_PORT="$CUSTOM_PORT"
        else
            echo "▶ Running in PRODUCTION mode (port 8080, debug=False)"
        fi
        python "$APP_FILE"
    fi
else
    echo "❌ $APP_FILE not found"
    exit 1
fi
