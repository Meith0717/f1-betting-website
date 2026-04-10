from app import create_app

app = create_app()

if __name__ == "__main__":
    import os

    # Get environment variables with defaults
    environment = os.environ.get("FLASK_ENV", "production")
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"

    # Determine port
    if environment == "development" or environment == "test":
        port = 5000  # Default development port
    else:
        port = int(os.environ.get("APP_PORT", "8080"))  # Default production port

    print(f"▶ Starting server in {environment} mode on port {port}")
    print(f"▶ Debug mode: {'ON' if debug else 'OFF'}")

    app.run(host="0.0.0.0", port=port, debug=debug)
