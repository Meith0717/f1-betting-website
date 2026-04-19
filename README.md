# F1 Betting Platform

A comprehensive Formula 1 prediction game built with Flask, featuring user authentication, race betting, scoring system, and admin management.

## 🚀 Features

### Core Functionality
- **User Authentication**: Secure login/registration with admin roles
- **Race Management**: Complete F1 season schedule with session timings
- **Betting System**: Place bets on race outcomes and fastest laps
- **Scoring System**: Automatic points calculation based on race results
- **Admin Dashboard**: User management, race resolution, and system controls

### Features
- **Leaderboard**: Ranked user scores and statistics
- **Race Countdowns**: Live timers for upcoming sessions

## 🏁 Getting Started

### Prerequisites
- Python 3.8+
- pip (Python package manager)
- Git

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/f1-betting-website.git
   cd f1-betting-website
   ```

2. **Set up virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run the application**:
   
   **Option 1: Using the build script (recommended)**
   
   **Linux/macOS**:
   ```bash
   chmod +x build.sh
   ./build.sh
   ```
   
   **Windows**:
   ```batch
   build.bat
   ```
   
   **Option 2: Manual execution**
   
   **Linux/macOS**:
   ```bash
   source venv/bin/activate  # Activate virtual environment
   python run.py
   ```
   
   **Windows**:
   ```batch
   .\venv\Scripts\activate
   python run.py
   ```

   The app will be available at `http://localhost:2121`

## 🛠️ Build Scripts

The repository includes flexible build scripts for both platforms with environment support:

### Linux/macOS: `build.sh`

**Features**:
- Automatic virtual environment creation
- Dependency installation
- **Environment modes**: Test vs Production
- **Custom port support**: Override default ports
- Error handling with clear messages
- Requirements.txt support

**Usage**:

**Test mode (port 5000, debug=True)**:
```bash
chmod +x build.sh
./build.sh --test
# or
./build.sh -t
```

**Production mode (port 8080, debug=False)**:
```bash
./build.sh --prod
# or
./build.sh -p
```

**Custom port**:
```bash
./build.sh --port 8000
# or
./build.sh -P 8000
```

### Windows: `build.bat`

**Features**:
- Automatic virtual environment creation
- Dependency installation
- **Production mode only**: Simplified for deployment
- **Custom port support**: Override default ports
- Error handling with pause on failure
- Requirements.txt support with fallback to manual Flask install

**Usage**:

**Production mode (port 8080, debug=False)**:
```batch
build.bat
```

**Custom port**:
```batch
build.bat --port 8000
build.bat -P 8000
```

### Environment Configuration

| Mode | Port | Debug | Use Case |
|------|------|-------|----------|
| **Test** (`--test`) | 5000 | ON | Development, debugging |
| **Production** (`--prod`) | 8080 | OFF | Staging, production |
| **Custom** (`--port X`) | X | OFF | Specific port requirements |

### Common Features
- **Automatic setup**: Creates venv if missing
- **Error handling**: Stops on failures with clear messages
- **Requirements installation**: Uses requirements.txt with fallback
- **Cross-platform**: Native support for both Windows and Unix-like systems
- **Environment awareness**: Sets appropriate Flask environment variables

## 📂 Project Structure

```
app/
├── __init__.py               # Flask app factory
├── auth_decorators.py        # Authentication decorators
├── auth_utils.py             # User authentication utilities
├── betting_manager.py        # Core betting logic
├── race_data_manager.py      # Race data handling
├── routes/                  # Route blueprints
│   ├── main_routes.py        # Main pages
│   ├── auth_routes.py        # Authentication
│   ├── admin_routes.py       # Admin functionality
│   └── betting_routes.py     # Betting features
├── data/                    # Data files (ignored by Git)
│   ├── races.json           # Race schedules
│   ├── users.json           # User accounts
│   ├── bets.json            # Betting data
│   └── drivers.json         # Driver information
├── templates/               # HTML templates
└── static/                  # CSS, JS, and assets
```

## 🔧 Configuration

Create a `.env` file in the root directory:

```env
# Flask configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Registration
REGISTRATION_PASSWORD=your-registration-password

# Database (if using)
DATABASE_URL=sqlite:///app.db
```

## 🎯 Usage

### User Roles
- **Regular Users**: Place bets, view leaderboard
- **Admins**: Manage users, resolve races, update data

### Betting Rules
- Bets close when the race starts
- Points awarded for correct predictions
- Fastest lap predictions earn bonus points

## 🛠️ Development

### Running Tests
```bash
python -m pytest tests/
```

### Code Style
- Follows PEP 8 guidelines
- Uses Flask blueprints for modularity
- JSON-based data storage

### Data Management
The `app/data/` directory contains:
- Race schedules and results
- User accounts and scores
- Betting records
- Driver information

**Note**: This directory is in `.gitignore` to protect user data.

## 📊 Data Sources

Race data can be:
- Manually entered via admin interface
- Imported from JSON files
- Fetched from F1 API (if configured)

## 🔒 Security

- Password hashing with PBKDF2
- Session-based authentication
- Admin role protection
- CSRF protection via Flask

## 🎯 Features Overview

### Core Features
- **User Authentication**: Secure login/registration system
- **Race Betting**: Predict podium finishes and fastest laps
- **Scoring System**: Earn points for accurate predictions
- **Leaderboard**: Compete with other F1 fans
- **Admin Dashboard**: Manage users and races

### Help & Documentation
- **Help Page**: `/help` - Complete guide on how to play
- **Legal Notice**: `/legal-notice` - Terms and conditions
- **PWA Support**: Install as mobile app

## 📱 Mobile Installation (PWA)

The application supports Progressive Web App (PWA) installation for mobile devices:

### iOS (iPhone/iPad)
1. Open the website in Safari
2. Tap the "Share" button (square with arrow)
3. Select "Add to Home Screen"
4. Confirm the installation

### Android
1. Open the website in Chrome
2. Tap the three-dot menu
3. Select "Add to Home screen"
4. Confirm the installation

### Features
- **Home Screen Icon**: Custom F1-themed icon
- **Standalone Mode**: Runs without browser chrome
- **Offline Support**: Basic caching for improved performance
- **Full Screen**: Immersive experience

### Requirements
- iOS: Safari (iOS 11.3+)
- Android: Chrome (or other modern browsers)
- HTTPS required for service worker (use ngrok for local testing)

## 📝 License

This project is for educational and personal use. See the legal notice in the application for full details.

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request
4. Follow existing code style

## 📞 Support

For issues or questions:
- Check the application's Info page
- Review the legal notice
- Contact the repository maintainer

---

*Built with ❤️ for Formula 1 fans* 🏎️💨
