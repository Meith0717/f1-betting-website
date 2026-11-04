# F1 Betting Platform

A **private Formula 1 prediction game** built with **Flask**: users place bets on race outcomes (podium + fastest lap), earn points for correct predictions, and compete on a leaderboard. Includes user authentication, race management, an admin dashboard, and **Web Push Notifications** for automatic race alerts. Mobile-first design with a bottom tab bar, installable as a PWA.

> **Vibe-coded:** This project was generated with **Mistral Vibe** (AI coding agent) as an experiment, and **reviewed, tested and approved by Thierry Meiers**, who is responsible for it.

---

## Features

| Category | Description |
|----------|-------------|
| **User Authentication** | Login/registration with PBKDF2 password hashing, invite-only registration password, user & admin roles, self-service account deletion. |
| **Race Management** | Full F1 season schedule with session timings, fetched live from the Jolpica API; race cancellation support. |
| **Betting System** | Bet on the next race's podium (top 3) + fastest lap. Bets close automatically when the race starts. Privacy-first: "My Bets" shows only your own bets; per-race details and full history are one click away. |
| **Scoring System** | Up to 8 points per race: +1 per correct driver, +1 per correct team (per position), +1 fastest lap, +1 perfect-podium bonus. Ties broken by who reached the score first. |
| **Leaderboard** | Ranked standings with podium highlighting (gold/silver/bronze) + latest race's bets. |
| **Admin Dashboard** | Stats overview, user management (promote/demote/delete, test notification), race cancel/reactivate, manual & API race resolution, data updates, point reset, log viewer. |
| **Web Push Notifications** | VAPID-based alerts for qualifying, race start, and 1-hour betting reminders; opt-in toggle in the profile; stale subscriptions auto-removed. Requires HTTPS (localhost works for dev). |
| **Live Countdowns** | Countdown timers for the next session and the betting deadline. |
| **Progressive Web App (PWA)** | Installable on mobile (iOS/Android) for an app-like experience. |
| **Modern UI** | Dark, mobile-first design system: bottom tab bar on mobile, SVG icon set, collapsible race/session lists, compact bet rows, toast-style flash messages. |

---

## Installation

### Prerequisites
- Docker + Docker Compose (production)
- Python 3.12+ and Git (local testing only)

### Production — Docker (recommended)

```bash
git clone https://github.com/Meith0717/f1-betting-website.git
cd f1-betting-website
docker compose up -d --build     # builds and starts on port 8080
```

- Data (`src/app/data/`) and runtime state (`src/instance/` — logs + secret key) are Docker volumes (`f1-data`, `f1-instance`) and persist across restarts.
- VAPID keys are read from `.env` at the repo root (copied into the image at build time). Override with `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` environment variables in `docker-compose.yml` if preferred.
- Put the container behind a **reverse proxy with HTTPS** — required for push notifications. Then open `https://your-host/`.

### Local testing / debugging only — `src/build.sh`

Sets up a virtualenv, installs dev dependencies, generates VAPID keys, and starts the Flask dev server with debug ON:

```bash
cd src
chmod +x build.sh
./build.sh            # http://localhost:5000, debug ON
./build.sh --port X   # custom port
```

(`./build.sh --prod` just prints a reminder that production runs via Docker.)

---

## Project Structure

```
├── Dockerfile, docker-compose.yml, .dockerignore
├── .env                          # VAPID keys, SECRET_KEY, registration password (gitignored)
├── src/
│   ├── wsgi.py                   # gunicorn entry point (production)
│   ├── run.py                    # dev server entry (debug mode)
│   ├── build.sh                  # local test/debug setup script
│   ├── requirements.txt          # + requirements-dev.txt (pytest)
│   ├── app/
│   │   ├── __init__.py           # app factory, blueprints, Jinja filters, static cache-busting
│   │   ├── core/                 # config, JsonStore (atomic JSON + backup), logger, ScoringEngine
│   │   ├── services/             # bet_service, user_service, resolution_service, notification_service, view_models
│   │   ├── routes/               # main, auth, betting, admin, notifications, system (blueprints)
│   │   ├── race_data_manager.py  # races/drivers/cancellations + Jolpica API client
│   │   ├── push_manager.py       # Web Push subscriptions & sending
│   │   ├── event_manager.py      # scheduled race notifications (background thread)
│   │   ├── timezone_utils.py, auth_decorators.py
│   │   ├── data/                 # races.json, users.json, bets.json, drivers.json, race_results.json, ... (volume)
│   │   ├── static/               # css/ (design system), js/, icons/, sw.js, manifest.json
│   │   └── templates/            # base, welcome, overview, leaderboard, races, betting/*, admin/*, user/*, _icons.html, _page_header.html
│   └── tests/                    # pytest suite (isolated from real data via temp files)
└── instance/                     # logs/ + .secret_key (volume)
```

---

## Usage

### User Roles
- **Regular users**: see their rank/score on the home page, bet on the next race, manage notifications in the profile, delete their own account (password-confirmed, purges all their data).
- **Admins**: everything above plus the Admin Dashboard (from the profile page): user management, race resolution (manual or via API), data updates, log viewer.

### Betting Rules
- Only the **next upcoming race** is open for betting; bets close when the race starts.
- Predict the **top 3** and the **fastest lap** driver.
- Scoring (max 8 pts/race): +1 correct driver per position, +1 correct team per position, +1 fastest lap, +1 perfect-podium bonus.
- Equal total scores: the player who reached the score first ranks higher.
- Race results are resolved automatically from the Jolpica API (or manually by an admin); points and leaderboard update instantly.

---

## Data Files

JSON file storage in `src/app/data/` (atomic writes with backup/restore, mode 0600):

- `races.json` — season schedule + sessions (race IDs are preserved across API updates)
- `users.json` — accounts, scores, score history
- `bets.json` — all bets grouped by race
- `drivers.json` — drivers + teams
- `race_results.json` — cached API results per race
- `push_subscriptions.json` — push subscriptions per user
- `canceled.json` — canceled race IDs

`src/app/data/` and `instance/` are gitignored / Docker volumes — never commit real user data.

---

## Development

### Running Tests
```bash
cd src
./build.sh                 # or: python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest tests/    # 20 tests; singleton stores are redirected to temp files, real data is never touched
```

### Code Style
- **PEP 8**, Flask blueprints per feature, service layer (`app/services/`) free of Flask imports
- Pure scoring engine in `app/core/scoring.py`; data shaping in `services/view_models.py`
- One logging pattern: module-level `get_logger(__name__)`, root logger configured once (`core/logger.py`), ANSI codes stripped from files
- Unified logging level via `LOG_LEVEL` env var (default INFO); rotating log at `instance/logs/app.log`

### External Data
Race schedule, drivers and results come from the free, open-source **Jolpica F1 API** (`api.jolpi.ca`, Ergast-compatible). Update via Admin → "Update Races" / "Update Drivers", or resolve a race via API from the betting pages.

---

## API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/` | Home (login + welcome when logged out, dashboard when logged in) | optional |
| GET | `/races` | Race calendar (upcoming/past, collapsible sessions) | login |
| GET | `/leaderboard` | Standings + latest race bets | login |
| GET | `/betting` | My Bets (own bets only) | login |
| GET | `/betting/history` | All users' bets per race | login |
| GET | `/betting/race/<race_id>` | All bets for one race (back respects origin via `?back=`) | login |
| GET/POST | `/betting/place/<race_id>`, `/betting/edit/<race_id>`, `/betting/cancel/<race_id>` | Bet management | login |
| GET | `/profile`, `/profile/delete` | Profile, notifications toggle, account deletion | login |
| GET | `/admin/` | Admin dashboard | admin |
| GET | `/help`, `/legal-notice` | Help & legal notice | public |
| GET | `/api/vapid-public-key` | VAPID public key | public |
| POST | `/api/save-subscription`, `/api/remove-subscription`, `/api/remove-all-subscriptions` | Push subscription management | login |
| GET | `/api/my-subscriptions` | List own subscriptions | login |
| POST | `/api/admin/send-test`, `/api/admin/send-all` | Push to one/all users | admin |
| GET | `/_debug` | Debug info | public |

---

## Push Notifications

1. VAPID keys are configured in `.env` (auto-generated by `build.sh` or `generate_vapid_keys.py`).
2. The user enables notifications via the toggle in **Profile** and approves the browser prompt.
3. The subscription is stored server-side per username; the service worker (`/sw.js`) displays alerts.
4. The in-process event manager schedules qualifying/race-start/1-hour reminders for every race.
5. Stale subscriptions (expired or key-mismatched, HTTP 400/404/410) are removed automatically.

**HTTPS is required** in production (localhost works for development). Supported: Chrome, Firefox, Safari (macOS 10.13+/iOS 11.3+), Edge.

---

## PWA Installation

- **Android (Chrome):** Menu → "Add to Home Screen"
- **iOS (Safari):** Share → "Add to Home Screen"

Icons: 72–512px PNGs + apple-touch-icon in `src/app/static/icons/`; manifest at `static/manifest.json`.

---

## Security
- Passwords hashed with **PBKDF2-SHA256** (100k iterations); legacy plaintext migrated on login
- Session auth with a **persistent `SECRET_KEY`** (env var or `instance/.secret_key`, 0600, gitignored)
- Admin routes protected by decorators; last admin cannot be deleted/demoted
- Self-service account deletion requires password confirmation and purges the user's bets + push subscriptions
- Registration gated by an admin-rotatable registration password
- CSRF-safe session cookies; JSON stores written atomically with backup/restore
- Production served by **gunicorn** inside Docker, behind an HTTPS reverse proxy

---

## Support
- In-app **Legal Notice** (`/legal-notice`) — terms, privacy (GDPR), scoring, AI/vibe-coding disclosure
- Logs: `instance/logs/app.log` (viewable in Admin → Logs)
- Issues: [GitHub repository](https://github.com/Meith0717/f1-betting-website)

---

*Built for Formula 1 fans — vibe-coded with Mistral Vibe, reviewed by a human.*
