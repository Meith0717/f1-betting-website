"""Production WSGI entry point — run with: gunicorn wsgi:app"""

from app import create_app

app = create_app()
