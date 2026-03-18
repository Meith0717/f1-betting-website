"""
Requests package - Contains all HTTP request handlers for the application.

This package follows a clean separation:
- main_requests.py: Main application routes (public facing)
- admin_requests.py: Admin routes (protected)
- auth_requests.py: Authentication routes (login, register, logout)
"""

# Import all request handlers to make them available
from .auth_requests import *
from .main_requests import *
from .admin_requests import *