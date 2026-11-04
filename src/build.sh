#!/usr/bin/env bash

# Local development / testing ONLY.
# For production deployment use Docker:  docker compose up -d --build  (see ../README.md)

set -e # exit on any error

VENV_DIR=".venv"
APP_FILE="run.py"
CUSTOM_PORT=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port|-P)
            CUSTOM_PORT="$2"
            shift 2
            ;;
        --prod|-p)
            echo "ℹ️  Production runs via Docker only:  docker compose up -d --build  (from the repo root)"
            exit 0
            ;;
        -*|--*)
            echo "Unknown option: $1"
            echo "Usage: ./build.sh [--port PORT]   (local test/debug on port 5000)"
            exit 1
            ;;
        *)
            shift
            ;;
    esac
done

PORT="${CUSTOM_PORT:-5000}"
echo "▶ Local TEST mode (debug server on port $PORT)"
echo "▶ For production use Docker: docker compose up -d --build"

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
    pip install -r requirements-dev.txt
else
    echo "⚠️ requirements.txt not found, installing Flask manually..."
    pip install flask flask-cors
fi

# 4.5 Generate VAPID keys for Web Push notifications
if [ -f "app/generate_vapid_keys.py" ]; then
    echo "▶ Generating VAPID keys for Web Push notifications"
    python app/generate_vapid_keys.py
else
    echo "⚠️ generate_vapid_keys.py not found, skipping VAPID key generation"
fi

# 5 Run the app in debug mode
echo "▶ Starting dev server: $APP_FILE (port $PORT, debug=True)"
export FLASK_ENV=development
export FLASK_DEBUG=1
export APP_PORT="$PORT"
python "$APP_FILE"
