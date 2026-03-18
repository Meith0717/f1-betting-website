# Intimacy Project Structure

## 📁 Clean & Organized Codebase

```
app/
├── __init__.py          # Flask app initialization & blueprint registration
├── decorators.py        # Authentication decorators (@admin_required)
├── utils.py             # Core utilities (user management, password hashing, data storage)
├── requests/            # All HTTP request handlers (clean separation)
│   ├── __init__.py      # Package initialization
│   ├── auth_requests.py # Authentication routes (login, register, logout)
│   ├── main_requests.py # Main application routes (index, dashboard)
│   └── admin_requests.py # Admin routes (dashboard, user management)
├── data/
│   └── users.json       # User database with secure storage
└── templates/
    ├── base.html        # Base template with navigation (shows admin link when applicable)
    ├── dashboard.html  # User dashboard (shows account info + admin section if admin)
    ├── index.html       # Welcome page for non-logged-in users
    ├── login.html       # Login form
    ├── register.html    # Registration form
    └── admin/
        ├── dashboard.html # Admin dashboard with statistics
        └── users.html     # User management interface
```

## ✅ Cleanup & Organization Completed

### Removed Unnecessary Files
- `forms.py` (empty placeholder)
- `models.py` (empty placeholder)
- Python cache files (`__pycache__`, `*.pyc`)

### Improved Organization
- **Separated decorators** into `decorators.py` (better separation of concerns)
- **Restored missing index route** with proper welcome page
- **Fixed admin dashboard access** with clear navigation
- **Proper template organization** with logical structure
- **Session management improvements** for better security

### Security Features
- **PBKDF2 Password Hashing** - Secure storage with unique salts
- **Session Management** - Admin status stored securely in session
- **File Permissions** - Restrictive 600 permissions on data files
- **Atomic Writes** - Prevent data corruption during writes
- **Role-Based Access** - `@admin_required` decorator for protected routes

### Key Components

#### 1. Authentication System (`routes.py`)
- `/login` - Secure login with password verification
- `/register` - User registration with automatic admin promotion for first user
- `/logout` - Session cleanup
- `/` - User dashboard with admin access

#### 2. Admin System (`admin.py`)
- `/admin/` - Admin dashboard (protected)
- `/admin/users` - User management interface
- `/admin/users/<username>/promote` - Promote to admin
- `/admin/users/<username>/demote` - Demote from admin

#### 3. Utility Functions (`utils.py`)
- `load_users()` - Load users from JSON with error handling
- `save_users()` - Save users with atomic writes and permissions
- `hash_password()` - PBKDF2 password hashing
- `verify_password()` - Password verification
- `ensure_first_admin()` - Automatic admin promotion for first user

#### 4. Data Storage (`data/users.json`)
```json
{
  "users": {
    "username": {
      "password": "pbkdf2_sha256$...",
      "email": "user@example.com",
      "created_at": "2024-03-19T12:00:00",
      "last_login": "2024-03-19T12:30:00",
      "is_admin": true/false
    }
  }
}
```

## 🎯 Improved Code Organization

### Separation of Concerns
The project now follows better software engineering principles:

**Before:**
```
admin.py
├── @admin_required decorator (mixed with routes)
└── Admin route definitions

routes.py
├── Index route
├── Login route
├── Register route
└── Logout route
```

**After:**
```
requests/
├── auth_requests.py  # Authentication routes (login, register, logout)
├── main_requests.py  # Main routes (index, dashboard)
└── admin_requests.py # Admin routes (dashboard, user management)

decorators.py
└── @admin_required decorator (reusable, separate)
```

### Benefits
- ✅ **Single Responsibility Principle** - Each file has one clear purpose
- ✅ **Logical Grouping** - Related routes are grouped together
- ✅ **Better Reusability** - Decorators and utils can be used anywhere
- ✅ **Easier Testing** - Components can be tested independently
- ✅ **Clearer Code** - Each file is focused and easy to understand
- ✅ **Better Maintainability** - Changes are isolated to specific areas
- ✅ **Scalability** - Easy to add new route categories

## 🚀 How to Use

### Run the Application
```bash
cd /home/thierry/Documents/git/Intimacy/src
source .venv/bin/activate
python run.py
```

### Access the Application
- **Main App**: `http://localhost:21212/`
- **Login**: `http://localhost:21212/login`
- **Register**: `http://localhost:21212/register`
- **Admin Dashboard**: `http://localhost:21212/admin/` (admin only)

### First User
The first user to register automatically becomes an administrator.

## 🔧 Development Notes

### Dependencies
- Flask
- Python 3.8+

### Security Considerations
- Passwords are hashed using PBKDF2 with SHA-256
- Session data is encrypted using Flask's secret key
- File permissions are set to restrictive values
- Admin routes are protected with decorators

### Future Enhancements
- Add email verification
- Implement password reset functionality
- Add activity logging
- Support for user profiles
- Database migration (SQLite/PostgreSQL)

## ✨ Project Status
- ✅ Clean and organized codebase
- ✅ Secure authentication system
- ✅ Functional admin interface
- ✅ Proper error handling
- ✅ Responsive templates
- ✅ Ready for development use

**Last Updated**: 2024-03-19
**Structure**: Clean & Organized 🎉