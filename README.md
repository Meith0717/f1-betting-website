# F1 Betting Platform

A **Formula 1 prediction game** built with **Flask**, allowing users to place bets on race outcomes, track scores, and compete on a leaderboard. The platform supports user authentication, race management, administrative controls, and **Web Push Notifications** for automatic race alerts.

---

## Features

| Category | Description |
|----------|-------------|
| **User Authentication** | Secure login, registration, and role-based access (users and admins). |
| **Race Management** | Complete F1 season schedule, including session timings and race data. |
| **Betting System** | Place bets on race outcomes (podium, fastest lap, pole) with automatic scoring. |
| **Scoring System** | Points automatically calculated based on race results and prediction accuracy. |
| **Leaderboard** | Ranked display of user scores and statistics with mobile card layout. |
| **Admin Dashboard** | Manage users, resolve races, update race data, send notifications. |
| **Web Push Notifications** | Automatic alerts for qualifying, race start, and betting deadlines via VAPID. |
| **Live Countdowns** | Timers for upcoming race sessions. |
| **Progressive Web App (PWA)** | Installable on mobile devices for an app-like experience. |

---

## Installation

### Prerequisites
- Python 3.8+
- Git

### Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Meith0717/f1-betting-website.git
   cd f1-betting-website
   ```

2. **Run the build script**:
   The build scripts automate setup: virtual environment creation, dependency installation, VAPID key generation, and running the app.

   **Linux/macOS** (`src/build.sh`):
   ```bash
   cd src
   chmod +x build.sh
   ./build.sh --test    # Port 5000, debug ON
   ./build.sh --prod   # Port 8080, debug OFF
   ./build.sh --port X # Custom port
   ```

   **Windows** (`src/build.bat`):
   ```batch
   cd src
   build.bat           # Port 8080, debug OFF
   build.bat --port X  # Custom port
   ```

   The app will start automatically and be available at `http://localhost:<port>`.

---

## Project Structure

```
src/
├── app/
│   ├── __init__.py, auth_*.py, auth_utils.py
│   ├── betting_manager.py, race_data_manager.py
│   ├── push_manager.py, event_manager.py, timezone_utils.py
│   ├── generate_vapid_keys.py
│   ├── data/                    # races.json, users.json, bets.json, drivers.json, push_subscriptions.json, canceled.json
│   ├── routes/                 # main_routes.py, auth_routes.py, admin_routes.py, betting_routes.py, notifications_routes.py
│   ├── static/                 # css/, js/, icons/, sw.js, manifest.json
│   └── templates/              # HTML templates by feature
├── run.py
├── requirements.txt
└── build.sh, build.bat
instance/
└── logs/                      # app.log (auto-created)
```

---

## Usage

### User Roles
- **Regular Users**: Place bets, view leaderboard, track scores, receive push notifications, install PWA.
- **Admins**: Manage users, resolve races, update race data, send notifications, view logs.

### Betting Rules
- Bets close when the **Race session starts** (not practice or qualifying).
- Points awarded for correct predictions (podium positions, fastest lap, pole).
- Leaderboard updates automatically after race resolution.

---

## Data Files

Create in `src/app/data/`:
- `races.json` - Race schedule and results
- `users.json` - User accounts
- `bets.json` - Betting data
- `drivers.json` - Driver information

Auto-created:
- `push_subscriptions.json` - Push notification subscriptions
- `canceled.json` - Canceled race tracking

**Note**: Add `src/app/data/` to `.gitignore` to protect user data.

---

## Development

### Running Tests
```bash
cd src
python -m pytest tests/
```

### Code Style
- Follows **PEP 8** guidelines
- Uses **Flask blueprints** for modularity
- Data stored in JSON files

### Logs
Stored in `src/instance/logs/app.log` with rotating file handler.

---

## API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/` | Home/Welcome |
| GET | `/races` | Race schedule with countdowns |
| GET | `/betting/dashboard` | User betting dashboard |
| GET | `/admin` | Admin dashboard | Admin |
| GET | `/help` | Help guide |
| GET | `/legal-notice` | Terms and conditions |
| GET | `/api/vapid-public-key` | Get VAPID public key | Public |
| POST | `/api/save-subscription` | Save push subscription | Required |
| POST | `/api/remove-subscription` | Remove push subscription | Required |
| POST | `/api/test-notification` | Test notification | Admin |
| POST | `/api/send-all` | Send to all users | Admin |
| GET | `/_debug` | Debug info | Public |

---

## Push Notifications

### How It Works
1. Generate VAPID keys (see Configuration)
2. User clicks "Enable Notifications" button in the UI
3. Browser prompts user to allow notifications
4. On approval, subscription is stored server-side by username
5. Events auto-scheduled for all race sessions (qualifying, race start, 1h reminders)
6. Service worker displays notifications

### Browser Support
- Chrome, Firefox, Safari (macOS 10.13+, iOS 11.3+), Edge (Chromium)
- **HTTPS required for production** (localhost works for development)

### Service Worker
- File: `src/app/static/sw.js`
- Served at `/sw.js` with scope `/`
- Handles caching and push events

---

## PWA Installation

### iOS
Safari → Share → Add to Home Screen

### Android
Chrome → Menu → Add to Home Screen

Icons provided: 72x72, 96x96, 128x128, 144x144, 152x152, 192x192, 384x384, 512x512, apple-touch-icon

---

## Security
- Password hashing with **PBKDF2+SHA256**
- Session-based authentication
- Admin role protection via decorators
- VAPID keys for secure Web Push
- CSRF protection via Flask

---

## Support
- Check the **Legal Notice** (`/legal-notice`) pages in the app
- Review logs in `src/instance/logs/app.log`
- Contact the repository maintainer

---

*Built for Formula 1 fans. 🏎️*
