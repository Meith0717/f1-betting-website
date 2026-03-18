#!/usr/bin/env bash

set -e # exit on any error 

VENV_DIR=".venv"
APP_FILE="src/run.py"

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
    python "$APP_FILE"
else
    echo "❌ $APP_FILE not found"
    exit 1
fi
