# SecureBank — Banking Web Application

A lightweight browser-based banking app built with **Python Flask**, **SQLite**, and **Bootstrap 5**.

## Features

- Customer login with hashed-password authentication
- Session management with automatic 30-minute timeout
- Dashboard with real-time account balance
- Deposit and withdrawal with full input validation and atomic DB writes
- Transaction history (10 most recent)
- Responsive UI (desktop & tablet)

---

## Project Structure

```
banking-workshop/
├── BACKEND/
│   ├── app.py              ← Flask entry point & all routes
│   ├── auth.py             ← Login / logout / session guard decorator
│   ├── transactions.py     ← Deposit & withdrawal business logic
│   ├── models.py           ← All SQLite queries (single source of truth)
│   ├── requirements.txt    ← Python dependencies
│   └── database.db         ← Auto-created SQLite file (gitignored)
├── FRONTEND/
│   ├── templates/
│   │   ├── base.html       ← Shared layout (navbar, flash messages, footer)
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── deposit.html
│   │   └── withdraw.html
│   └── static/
│       └── css/style.css
├── tests/
│   ├── test_transactions.py  ← Unit tests (amount parsing, deposit, withdrawal)
│   └── test_app.py           ← Integration tests (Flask test client)
└── README.md
```

---

## Quick Start

### 1. Prerequisites

- Python 3.9 or higher
- pip (comes with Python)

### 2. Create and activate a virtual environment

```powershell
# Windows (PowerShell)
cd banking-workshop
python -m venv venv
.\venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
cd banking-workshop
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r BACKEND/requirements.txt
```

### 4. Run the application

```bash
cd BACKEND
python app.py
```

The server starts at **http://127.0.0.1:5000**.

> The database (`database.db`) is created automatically on first run with two demo accounts pre-seeded.

### 5. Demo accounts

| Username | Password     | Starting Balance |
|----------|-------------|-----------------|
| alice    | password123 | £1,500.00       |
| bob      | securepass  | £250.75         |

---

## Running Tests

From the **project root** (with the virtual environment active):

```bash
# Run all tests
pytest tests/ -v

# Unit tests only
pytest tests/test_transactions.py -v

# Integration tests only
pytest tests/test_app.py -v
```

---

## Environment Variables

| Variable   | Purpose                        | Default (dev only)                          |
|------------|-------------------------------|---------------------------------------------|
| `SECRET_KEY` | Flask session signing key  | `dev-secret-key-change-in-production-abc123` |

Set in production:

```bash
export SECRET_KEY="your-very-long-random-secret-key-here"
```

On Windows PowerShell:

```powershell
$env:SECRET_KEY = "your-very-long-random-secret-key-here"
```

> **Never** commit a real `SECRET_KEY` to source control.

---

## Security Notes

- Passwords are stored as **Werkzeug bcrypt hashes** — plaintext is never persisted.
- All SQL queries use **parameterised statements** — SQL injection is not possible.
- Balance updates and transaction inserts are **atomic** — a crash mid-operation cannot leave the account in an inconsistent state.
- Sessions are **cleared on logout** — the browser's Back button cannot restore access.

---

## Production Checklist

- [ ] Set `SECRET_KEY` from a secure random source (e.g., `python -c "import secrets; print(secrets.token_hex(32))"`)
- [ ] Remove `debug=True` from `app.run()` or use `FLASK_ENV=production`
- [ ] Serve with **Gunicorn** (Linux) or **Waitress** (Windows) instead of the dev server
- [ ] Put **Nginx** or **Apache** in front as a reverse proxy
- [ ] Enable **HTTPS** with a TLS certificate (Let's Encrypt is free)
- [ ] Set `SESSION_COOKIE_SECURE=True` and `SESSION_COOKIE_HTTPONLY=True`
- [ ] Add `database.db` to `.gitignore` (already done)
- [ ] Take regular backups of `database.db`
