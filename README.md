# Secure Live Tracker 🛡️

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/koppakarakesh7548-source/Secure-live-tracker)

**Secure Live Tracker** is a transparent, consent-first educational cybersecurity and security-awareness platform inspired by the operational mechanics of legitimate link-tracking and web-analytics services.

It demonstrates how link tracking and telemetry can be conducted ethically, with explicit user choice and complete privacy boundaries, without relying on covert tracking, intrusive fingerprinting, or deceptive dark patterns.

---

## 📋 Table of Contents
1. [Core Features & Privacy Principles](#core-features--privacy-principles)
2. [Workflow Architecture](#workflow-architecture)
3. [Technology Stack](#technology-stack)
4. [Responsible-Use Notice](#responsible-use-notice)
5. [Local Quickstart & Setup](#local-quickstart--setup)
6. [Environment Variables](#environment-variables)
7. [Database Setup & Migrations](#database-setup--migrations)
8. [Data Retention & Purge Automation](#data-retention--purge-automation)
9. [Automated Test Suite](#automated-test-suite)
10. [Production Deployment](#production-deployment)
11. [Security Architecture](#security-architecture)

---

## 🛡️ Core Features & Privacy Principles

### 1. Zero Covert Tracking
- When a visitor opens an active tracking link (`/track/<token>`), the server renders an explicit **Consent Gate**.
- **No client or server metrics are recorded before consent.**
- The application **never** requests camera, microphone, or precise GPS permissions.

### 2. Explicit Dual-Choice Visitor Agency
- **`[ ALLOW & CONTINUE ]`**:
  - The client transmits strictly permitted display parameters: `screen.width`, `screen.height`, `navigator.language`, and `timezone`.
  - The server records request IP address, performs an approximate IP-based location lookup, identifies the general browser and OS family, timestamps the record, and marks consent as `granted`.
  - The visitor is immediately redirected to the exact target destination.
- **`[ DENY & CONTINUE ]`**:
  - **Zero optional technical data is collected.** No IP address, no browser/OS, no screen dimensions, no language, and no approximate location are saved.
  - Only the minimal consent decision (`consent_status='denied'`) is noted.
  - The visitor is immediately redirected to the exact target destination.

### 3. Approximate Geolocation Notice
- Geolocation is derived exclusively from public IP subnet tables and is strictly labeled:
  > *"Approximate location based on IP. This is not precise GPS location."*

### 4. Prohibited Data Points
The platform strictly prohibits and never collects:
- Passwords, credentials, or session cookies
- Browser history, local files, or clipboard data
- Keystrokes or private messages
- Hidden canvas or audio fingerprinting

---

## 🔄 Workflow Architecture

```
Administrator
      │
      ▼
Admin Login (/login)
      │
      ▼
Command Center Dashboard (/dashboard)
      │
      ├─► Enter Target URL (http/https validated)
      │   Generate Cryptographic Tracking Token
      │
      ▼
Public Tracking Link (/track/:token)
      │
      ▼
Transparent Consent Gate
      │
      ├───────────────────────┬────────────────────────┐
      ▼                       ▼                        ▼
[ Allow & Continue ]    [ Deny & Continue ]     Link Expired/Disabled
      │                       │                        │
Collect Permitted Data  No Technical Data Saved    Display Educational
(Approx IP Loc, Screen, Minimal Consent Status     Terminal Page
Browser, OS, Timezone)         │
      │                       │
      └───────────┬───────────┘
                  │
                  ▼
   Redirect to Original Target Destination
```

---

## 🧰 Technology Stack

- **Backend Framework:** Python 3.12+, Flask 3.1
- **Database ORM:** SQLAlchemy 2.0+ / Flask-SQLAlchemy 3.1 (SQLite for development, PostgreSQL-ready for production)
- **Authentication & Sessions:** Flask-Login, Werkzeug password hashing (scrypt)
- **Security & Protection:** Flask-WTF (CSRF tokens), Flask-Limiter (Rate limiting)
- **Production WSGI Servers:** Waitress (Windows/Universal), Gunicorn (Linux/Containerized)
- **Frontend Architecture:** Modern semantic HTML5, cyber-themed responsive CSS3, vanilla JavaScript (no heavyweight frontend trackers)
- **Testing:** Pytest 9.x test suite

---

## ⚠️ Responsible-Use Notice

> **IMPORTANT:**
> This service is intended for authorized educational, security-testing, and security-awareness purposes. Use only with appropriate consent and authorization. Do not use this service to secretly monitor, impersonate, compromise, or collect information from people or systems without authorization.

---

## 🚀 Local Quickstart & Setup

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.12)
- Pip package manager

### 2. Installation
```bash
# Clone or navigate to the project directory
cd secure-live-tracker

# Install required dependencies
pip install -r requirements.txt
```

### 3. Initialize the Database
```bash
flask init-db
```
This initializes the database schema and creates the default administrator account:
- **Default Username:** `admin`
- **Default Password:** `AdminPass123!`

### 4. Run the Server
For production WSGI mode (powered by Waitress):
```bash
python run_server.py
```
Or for Flask development mode:
```bash
python app.py
```

The application is accessible at:
- **Public Portal:** `http://127.0.0.1:5000`
- **Admin Dashboard:** `http://127.0.0.1:5000/login`

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` to configure deployment settings:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `SECRET_KEY` | Cryptographic secret for signing sessions & CSRF | Auto-fallback (Change in prod!) |
| `FLASK_ENV` | Environment mode (`development`, `production`, `testing`) | `production` |
| `PORT` | Listening network port | `5000` |
| `HOST` | Listening host interface | `0.0.0.0` |
| `DATABASE_URL` | SQLAlchemy connection string (SQLite or PostgreSQL) | `sqlite:///database/secure_tracker.db` |
| `ADMIN_USERNAME`| Username for the primary administrator account | `admin` |
| `ADMIN_PASSWORD`| Secure password for the administrator account | `AdminPass123!` |
| `ADMIN_EMAIL` | Administrator contact email | `admin@securetracker.local` |
| `SESSION_COOKIE_SECURE` | Enforce HTTPS-only transmission of session cookies | `False` (`True` in production) |
| `DEFAULT_RETENTION_DAYS` | Default lifespan of visitor records before purge | `90` |
| `GEOLOCATION_API_KEY` | Optional key for external IP geolocation provider | None (uses public IP-API) |

---

## 🗄️ Database Setup & Migrations

The application uses SQLAlchemy abstractions compatible with SQLite, PostgreSQL, and MySQL.

To switch from SQLite to PostgreSQL in production:
```bash
export DATABASE_URL="postgresql://username:password@localhost:5432/secure_tracker"
flask init-db
```

### Database Schema Models
1. **`Admin`**: Stores administrative credentials with salted password hashes and audit timestamps.
2. **`TrackingLink`**: Stores tracking tokens, campaign names, destinations, active toggles, and optional expiration dates.
3. **`Visit`**: Stores visitor telemetry, tracking link relations, and consent decisions. Unconsented rows store `NULL` for all optional fields.
4. **`SystemSetting`**: Key-value store for application policies such as `retention_days`.
5. **`AuditLog`**: Tamper-evident ledger of administrative operations (logins, deletions, toggles).

---

## ⏳ Data Retention & Purge Automation

Data must not be stored indefinitely. Secure Live Tracker includes built-in lifecycle management:
1. **Administrative UI Control:** Under `/dashboard/privacy`, administrators can adjust the retention horizon and execute one-click purges of stale logs.
2. **Automated CLI Purge:**
   ```bash
   flask purge-data
   ```
   Add this command to your system's cron scheduler or systemd timer to run daily:
   ```cron
   0 3 * * * cd /path/to/secure-live-tracker && flask purge-data
   ```

---

## 🧪 Automated Test Suite

A complete test suite is provided in the `tests/` directory covering:
- Authentication & Session Verification
- Link Generation, URL Validation & Token Uniqueness
- Consent Workflow (Allow vs. Deny Data Capture Isolation)
- Security Headers & Permissions Policies
- Data Retention & Cascade Deletion

To execute all tests:
```bash
pytest -v
```

---

## 🚢 Production Deployment

### Option A: Standard Production WSGI (Waitress)
Waitress is installed and configured as the cross-platform WSGI server:
```bash
python wsgi.py
```

### Option B: Docker Container
Build and start the containerized service:
```bash
docker build -t secure-live-tracker .
docker run -d -p 5000:5000 \
  -e SECRET_KEY="your-strong-production-secret-key" \
  -e ADMIN_PASSWORD="YourStrongAdminPassword2026!" \
  -v secure_tracker_data:/app/database \
  --name secure-tracker \
  secure-live-tracker
```
Or via Docker Compose:
```bash
docker compose up -d
```

### Option C: PaaS Deployment (Render / Heroku / Railway)
The repository includes a ready-to-deploy `Procfile`:
```
web: python wsgi.py
```
1. Connect repository to your PaaS platform.
2. Configure environment variables (`SECRET_KEY`, `ADMIN_PASSWORD`, `DATABASE_URL`).
3. Set `SESSION_COOKIE_SECURE=True` for HTTPS.

---

## 🔒 Security Architecture

- **Strict Permissions-Policy:** Explicitly disallows browser camera, microphone, and precise geolocation APIs:
  `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- **Content Security Policy (CSP):** Restricts script and stylesheet execution, preventing XSS injection.
- **X-Frame-Options: DENY:** Prevents clickjacking and framing attacks.
- **Strict-Transport-Security (HSTS):** Automatically enforced when served over HTTPS.
- **Anti-CSRF:** Synchronizer token pattern implemented across all administrative endpoints via Flask-WTF.
- **Rate Limiting:** Protects `/login` and link generation from brute force or denial-of-service attempts.
- **SSRF Prevention:** Target URLs are validated to require valid HTTP/HTTPS schemes with strict host checking.
