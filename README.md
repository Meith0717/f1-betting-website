# F1 Betting Platform

A comprehensive Formula 1 betting platform built with Flask, featuring user authentication, race betting, scoring system, and community features.

## 🚀 Features

### Core Functionality
- **User Authentication**: Secure login/registration with admin roles
- **Race Management**: Complete F1 season schedule with session timings
- **Betting System**: Place bets on race outcomes and fastest laps
- **Scoring System**: Automatic points calculation based on race results
- **Admin Dashboard**: User management, race resolution, and system controls

### Experimental Features
- **Community Chat**: Real-time comment section for users (marked as EXPERIMENTAL)
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
   ```bash
   chmod +x build.sh
   ./build.sh
   ```
   
   **Option 2: Manual execution**
   ```bash
   source venv/bin/activate  # Activate virtual environment
   python run.py
   ```

   The app will be available at `http://localhost:2121`

## 🛠️ Build Script

The repository includes a `build.sh` script that automates:
- Virtual environment creation
- Dependency installation
- Application startup

### Features
- **Automatic setup**: Creates venv if missing
- **Error handling**: Stops on any failure
- **Requirements installation**: Uses requirements.txt
- **Cross-platform**: Works on Linux/macOS (Windows users can use WSL)

### Usage
```bash
# Make executable (first time only)
chmod +x build.sh

# Run the build script
./build.sh
```

## 📂 Project Structure

```
app/
├── __init__.py               # Flask app factory
├── auth_decorators.py        # Authentication decorators
├── auth_utils.py             # User authentication utilities
├── betting_manager.py        # Core betting logic
├── race_data_manager.py      # Race data handling
├── messages.py              # Community chat system
├── routes/                  # Route blueprints
│   ├── main_routes.py        # Main pages
│   ├── auth_routes.py        # Authentication
│   ├── admin_routes.py       # Admin functionality
│   └── betting_routes.py     # Betting features
├── data/                    # Data files (ignored by Git)
│   ├── races.json           # Race schedules
│   ├── users.json           # User accounts
│   ├── bets.json            # Betting data
│   └── messages.txt         # Community comments
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
- **Regular Users**: Place bets, view leaderboard, comment
- **Admins**: Manage users, resolve races, update data

### Betting Rules
- Bets close when the race starts
- Points awarded for correct predictions
- Fastest lap predictions earn bonus points

### Community Chat
- Max 20 messages stored
- Newest messages appear first
- Scrollable interface with refresh button

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
- Community messages

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

## 🚧 Experimental Features

The **Community Chat** feature is marked as EXPERIMENTAL and may:
- Change significantly in future updates
- Have limited functionality
- Be removed or replaced

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
