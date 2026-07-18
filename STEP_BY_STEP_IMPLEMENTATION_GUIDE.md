# Banking Web Application — Step-by-Step Implementation Guide

> **Document Type:** Implementation Guide
> **Version:** 1.0
> **Scope:** Plain-English instructions on how to build the application — logic and reasoning, not code.

---

## Overview

This guide walks you through building a lightweight browser-based banking application using Python Flask, SQLite, and Bootstrap. You will implement customer login, a dashboard showing the account balance, and deposit/withdrawal transactions. Follow each section in order, as later sections depend on earlier ones.

---

## 1. Environment Setup

### 1.1 Prerequisites

Before writing any code, confirm the following tools are available on your machine:

- **Python 3.9 or higher** — the runtime for Flask.
- **pip** — Python's package manager, bundled with modern Python.
- **A code editor** — VS Code is recommended.
- **A terminal / command prompt** — PowerShell on Windows, Terminal on macOS/Linux.

To check, run `python --version` and `pip --version`. If either is missing, download Python from python.org; pip comes with it.

---

### 1.2 Create and Activate a Virtual Environment

A virtual environment keeps the project's dependencies isolated from the rest of your system. Think of it as a private toolbox for this project only.

**Steps:**

1. Open a terminal inside the `banking-workshop/` folder.
2. Create a virtual environment by running the create command. Python will build a hidden folder (commonly named `venv`) that holds a self-contained Python installation.
3. Activate the environment. After activation, your terminal prompt will show the environment name, confirming that any packages you install will go into this project's toolbox and not affect anything else on your machine.
4. You must activate the environment every time you open a new terminal to work on the project.

> **Why this matters:** Without a virtual environment, installing Flask would modify your system-wide Python, which can break other projects or cause version conflicts.

---

### 1.3 Install Dependencies

With the virtual environment active, install the required packages using pip:

- **Flask** — the web framework that handles HTTP requests, routing, templates, and sessions.
- **Werkzeug** — ships with Flask; provides the password hashing utilities you will use to store passwords safely.
- **flask-session** (optional) — if you want server-side sessions stored on disk instead of in a signed cookie. For a simple project, Flask's built-in cookie-based session is sufficient.

Create a file named `requirements.txt` inside `BACKEND/` and list each dependency with a pinned version. This allows any developer to reproduce your exact environment with a single install command.

After installing, run `pip list` to confirm the packages are present.

---

### 1.4 Confirm Flask is Working

Before touching any business logic, verify the installation is healthy:

1. Create a minimal `app.py` with a single route that returns "Hello World".
2. Run Flask from the terminal using the development server command.
3. Open a browser and visit `http://127.0.0.1:5000`. You should see "Hello World".
4. Stop the server (Ctrl+C) and proceed.

This sanity check ensures the environment is correct before you build on top of it.

---

## 2. Backend Implementation

### 2.1 Project Structure First

Before writing logic, create the folder layout described in the implementation plan. An organised structure makes each concern easy to find and change independently:

```
banking-workshop/
├── BACKEND/
│   ├── app.py              ← entry point, route definitions
│   ├── auth.py             ← login/logout/session logic
│   ├── transactions.py     ← deposit and withdrawal business rules
│   ├── models.py           ← all database queries
│   ├── database.db         ← SQLite file (auto-created)
│   └── requirements.txt
└── FRONTEND/
    ├── templates/          ← Jinja2 HTML files
    └── static/
        └── css/            ← custom styles
```

Create all these files as empty placeholders now so that imports between them do not fail later.

---

### 2.2 Set Up the Flask Application (`app.py`)

`app.py` is the heart of the backend. Its responsibilities are:

1. **Create the Flask app object** — this is the single instance that handles all requests.
2. **Set a secret key** — Flask uses this to sign session cookies. Use a long, random string. Store it in an environment variable rather than hardcoding it.
3. **Configure the template and static folder paths** — tell Flask where your Jinja2 templates and CSS files live (in `FRONTEND/`).
4. **Register all routes** — each URL the browser can visit must be mapped to a Python function in this file (or imported from a Blueprint).
5. **Start the development server** — the `if __name__ == "__main__"` block at the bottom starts the server when you run `python app.py` directly.

Think of `app.py` as the switchboard: every incoming request arrives here, gets matched to the right handler function, and the handler produces a response.

---

### 2.3 Database Setup and Models (`models.py`)

`models.py` is the only file that talks to SQLite. Centralising all database access here means if you ever switch from SQLite to PostgreSQL, you only change one file.

#### Database initialisation logic

Write an `init_db()` function that:

1. Opens (or creates) the `database.db` file using Python's built-in `sqlite3` module.
2. Creates a `customers` table if it does not already exist. This table needs columns for: a unique customer ID, a display name, a username used to log in, and the password hash.
3. Creates a `transactions` table if it does not already exist. This table records every deposit and withdrawal with: a transaction ID, the customer ID it belongs to, whether it was a deposit or withdrawal, the amount, and a timestamp.
4. Creates an `accounts` table (or adds a `balance` column to `customers`) to store the current balance for each customer.
5. Seeds one or two test customer records with pre-hashed passwords, since there is no self-registration flow.
6. Calls `connection.commit()` to persist all changes.

Call `init_db()` once when the Flask app starts up, before serving any requests.

#### Query functions to implement

Write one Python function for each distinct database operation:

- `get_customer_by_username(username)` — looks up a customer row by their login name. Used during login to retrieve the stored password hash.
- `get_account_balance(customer_id)` — returns the numeric balance for a given customer.
- `update_balance(customer_id, new_balance)` — overwrites the stored balance with the new value. Always called inside a transaction so it either fully saves or fully rolls back.
- `record_transaction(customer_id, transaction_type, amount)` — inserts a new row into the transactions table. Called after every successful deposit or withdrawal.
- `get_transaction_history(customer_id)` — returns a list of past transactions, ordered newest-first, for a given customer. Used if you want to show history on the dashboard.

Every function should open a database connection, run its query, commit if it wrote data, close the connection, and return the result.

---

### 2.4 Authentication Logic (`auth.py`)

`auth.py` handles everything related to who the user is.

#### Login logic

1. Receive the submitted username and password from the request form.
2. Call `get_customer_by_username()` from `models.py` to retrieve the customer record.
3. If no customer is found, return an error — do not reveal whether the username or password was wrong (say "Invalid credentials" to avoid leaking which half was incorrect).
4. Use Werkzeug's `check_password_hash()` to compare the submitted password against the stored hash. This function handles the hashing internally; you never decrypt the stored hash.
5. If the hash matches, store the customer's ID and display name in Flask's `session` dictionary. This session data is signed and stored in a browser cookie.
6. Redirect the customer to the dashboard.
7. If the hash does not match, re-render the login page with a generic error message.

#### Session guard (login required decorator)

Protect every route that should not be accessible without login by writing a helper that:

1. Checks whether `'customer_id'` exists in Flask's `session` object.
2. If it does, allow the request to proceed normally.
3. If it does not, redirect the request to the login page with a message like "Please log in to continue."

Apply this guard to the dashboard, deposit, and withdrawal routes. The login page itself must not be guarded.

#### Logout logic

1. Clear the entire `session` dictionary using `session.clear()`.
2. Redirect to the login page.
3. Nothing else is needed — once the session is cleared, all protected routes will redirect back to login automatically.

---

### 2.5 Routes (`app.py`)

Define a route function for each URL the browser can request. Each route function receives the HTTP request, calls the appropriate logic, and returns a response (a rendered HTML page or a redirect).

#### `GET /` and `GET /login`
- If the user already has an active session, redirect them to the dashboard.
- Otherwise, render the login HTML template with an empty error message.

#### `POST /login`
- Triggered when the user submits the login form.
- Read `username` and `password` from the posted form data.
- Call the login logic from `auth.py`.
- On success: redirect to `/dashboard`.
- On failure: re-render the login page with an error message passed as a template variable.

#### `GET /dashboard`
- Apply the session guard — reject unauthenticated requests.
- Retrieve the customer's display name and current balance from `models.py`.
- Render the dashboard template, passing the name and balance as variables.

#### `GET /deposit`
- Apply the session guard.
- Render the deposit form template.

#### `POST /deposit`
- Apply the session guard.
- Read the submitted amount from the form.
- Pass the amount to the deposit service in `transactions.py`.
- On success: redirect to `/dashboard` with a success flash message.
- On validation error: re-render the deposit form with the specific error message.

#### `GET /withdraw`
- Apply the session guard.
- Render the withdrawal form template.

#### `POST /withdraw`
- Apply the session guard.
- Read the submitted amount from the form.
- Pass the amount to the withdrawal service in `transactions.py`.
- On success: redirect to `/dashboard` with a success flash message.
- On failure (invalid amount or insufficient funds): re-render the withdrawal form with a descriptive error.

#### `GET /logout`
- Call the logout logic from `auth.py`.
- Redirect to `/login`.

---

### 2.6 Transaction Business Logic (`transactions.py`)

`transactions.py` contains the rules for financial operations. It does not know about HTTP or HTML — it only receives validated inputs and talks to `models.py`.

#### Deposit service

1. Receive `customer_id` and the raw `amount` string from the route handler.
2. Strip whitespace and try to convert the amount to a decimal number. If conversion fails, return an error: "Amount must be a number."
3. Check that the amount is greater than zero. If not, return an error: "Amount must be greater than zero."
4. (Optional) Check for a maximum single-transaction limit if required by business rules.
5. Fetch the customer's current balance using `get_account_balance()`.
6. Compute the new balance by adding the deposit amount to the current balance.
7. Call `update_balance()` and `record_transaction()` inside a single database transaction so both writes succeed or fail together.
8. Return a success indicator.

#### Withdrawal service

1. Receive `customer_id` and the raw `amount` string.
2. Same numeric validation as deposit (non-empty, valid number, greater than zero).
3. Fetch the customer's current balance.
4. Compare the requested withdrawal amount against the current balance.
5. If the amount exceeds the balance, return an error: "Insufficient funds. Your balance is £X."
6. Compute the new balance by subtracting the withdrawal amount.
7. Call `update_balance()` and `record_transaction()` together in a single transaction.
8. Return a success indicator.

> **Key principle:** The route handler decides what to *show* the user. The service decides whether the operation is *allowed*. Keep these responsibilities separate.

---

### 2.7 Session Management

Flask stores session data in a cryptographically signed cookie sent to the browser. Here is how to configure it correctly:

- **Secret key:** Set `app.secret_key` to a long random string (at least 24 characters). Without this, Flask cannot sign cookies. Store it in an environment variable, not in source code.
- **Session lifetime:** Optionally set `app.permanent_session_lifetime` to a `timedelta` (e.g., 30 minutes) so idle sessions expire automatically.
- **Marking sessions permanent:** Call `session.permanent = True` after login if you want the timeout to apply; otherwise, the session ends when the browser closes.
- **What to store in session:** Only the minimum — `customer_id` and `customer_name`. Never store the password or balance in the session.

---

### 2.8 Error Handling

Handle three categories of errors gracefully:

1. **User input errors** — bad amount format, empty fields, insufficient funds. These should return the user to the same form with a descriptive, friendly message (e.g., "Please enter a valid positive number").
2. **Authentication errors** — expired session, invalid credentials. Redirect to login with a neutral message.
3. **Unexpected server errors** — register a custom 500 error handler in Flask that renders a simple "Something went wrong" page. This prevents Flask's default debug output from being shown to users in production.

Use Flask's `flash()` system to pass one-time messages (success or error) from a route handler to the next rendered template. Flash messages survive a redirect and are displayed once, then cleared.

---

## 3. Frontend Implementation

### 3.1 How Jinja2 Templates Work

Flask uses Jinja2 to build HTML pages server-side. You write HTML with special placeholder tags like `{{ variable }}` for values and `{% if condition %}` for logic. When Flask renders a template, it fills in the placeholders with real data before sending the HTML to the browser.

All templates go in `FRONTEND/templates/`. Flask must be told to look there (configure `template_folder` when creating the app).

---

### 3.2 Base Layout Template

Before building individual pages, create a `base.html` template that all other pages extend. This avoids duplicating the Bootstrap `<head>` block, navbar, and footer on every page.

The base layout should contain:

- The HTML boilerplate (`<!DOCTYPE html>`, `<html>`, `<head>`, `<body>`).
- A `<link>` tag loading Bootstrap from its CDN (or from your `static/css/` folder).
- Your custom stylesheet link.
- A navbar with the bank name on the left and, if logged in, the customer name and a Logout button on the right.
- A main content area with a `{% block content %}{% endblock %}` placeholder — child templates fill this in.
- A flash message section just above the content block that loops through any `get_flashed_messages()` and renders them as Bootstrap alerts.
- A simple footer with the bank name and year.

---

### 3.3 Login Page (`login.html`)

The login page should:

- Extend `base.html`.
- Display a centred card (Bootstrap `card` component) with the bank logo or name at the top.
- Contain a form with two inputs: one for username (text), one for password (password type, so characters are hidden).
- Have a single Submit button labelled "Log In".
- Show any error message (passed from the backend as a template variable) in a red Bootstrap alert above the form.
- Not show the navbar with logout — the user is not logged in yet.

The form's `action` attribute points to `/login` and its `method` is `POST`.

---

### 3.4 Dashboard (`dashboard.html`)

The dashboard is the home page after login. It should:

- Extend `base.html` (the navbar will show the customer name and Logout button automatically).
- Display a greeting: "Welcome back, [Customer Name]."
- Show the current balance prominently — large text, currency symbol, formatted to two decimal places.
- Provide two clearly labelled buttons: **Deposit** (links to `/deposit`) and **Withdraw** (links to `/withdraw`).
- Display any flash messages (success or error) that were passed from the previous action.
- Optionally show a transaction history table at the bottom (type, amount, date), if you have the data available.

---

### 3.5 Deposit Form (`deposit.html`)

- Extend `base.html`.
- Display a single input field labelled "Amount" that accepts decimal numbers.
- Show the customer's current balance above the form as a reference: "Current balance: £X.XX".
- Provide a Submit button ("Deposit Funds") and a Cancel link back to the dashboard.
- Show validation error messages below the input field if the submitted value was invalid.
- The form `action` points to `/deposit` and `method` is `POST`.

---

### 3.6 Withdrawal Form (`withdraw.html`)

- Identical structure to the deposit form, but the labels and button read "Withdraw" instead.
- The same current balance display is especially important here — the user needs to know how much they can withdraw.
- The form `action` points to `/withdraw`.
- Error messages here may include the "Insufficient funds" message in addition to the generic validation errors.

---

### 3.7 Bootstrap Layout Principles

Follow these Bootstrap conventions throughout for a consistent, responsive UI:

- Wrap all page content in a `container` div to centre it and constrain the width.
- Use `row` and `col` divs to place elements side by side on wider screens.
- Use Bootstrap's `form-control` class on all text inputs and `btn btn-primary` on submit buttons.
- Use `alert alert-danger` for error messages and `alert alert-success` for success messages.
- Use `card` components to group related content (the login form, the balance summary).
- Bootstrap's grid is mobile-first: a layout that uses `col-md-6` will be full-width on small screens and half-width on medium and larger.

---

## 4. Integration Steps

### 4.1 Telling Flask Where the Frontend Lives

By default, Flask looks for templates in a folder named `templates/` next to `app.py`. Since your templates live in `FRONTEND/templates/`, you must pass the correct path when creating the Flask app object. Similarly, static files (CSS, images) live in `FRONTEND/static/`, so you must tell Flask where that folder is too. Both are configuration options on the Flask constructor.

---

### 4.2 Connecting Forms to Routes

Each HTML form must have:

- `method="POST"` — so data is sent in the request body, not the URL.
- `action="/route-name"` — pointing to the correct Flask route.
- Named `input` fields matching exactly what the route handler reads from `request.form`.

For example, if your login form has `<input name="username">` and `<input name="password">`, then your Flask route reads them with `request.form['username']` and `request.form['password']`. If the names do not match, the backend receives empty strings.

---

### 4.3 Passing Data from Flask to Templates

When a Flask route calls `render_template("dashboard.html", balance=balance, name=name)`, the values `balance` and `name` become available inside the template as `{{ balance }}` and `{{ name }}`. This is how the backend injects live data (retrieved from SQLite) into the HTML that the browser receives.

Plan exactly which variables each template needs and make sure the route passes them all.

---

### 4.4 Connecting Flask to SQLite

Python's standard library includes `sqlite3` — no separate installation is needed. The connection flow in every model function is:

1. Call `sqlite3.connect(path_to_database_file)` to open (or create) the `.db` file.
2. Create a cursor object from the connection to execute SQL statements.
3. Run your `SELECT`, `INSERT`, or `UPDATE` statement.
4. If you wrote data, call `connection.commit()` to save it permanently.
5. Call `connection.close()` when done, or use a `with` block to close it automatically.

Use parameterised queries (passing values as a tuple of parameters rather than string-formatting them into the SQL) to prevent SQL injection attacks. This is the only correct way to handle user-supplied values in SQL.

---

### 4.5 Atomicity for Balance Updates

When a deposit or withdrawal is processed, two things must happen: the balance is updated and a transaction record is inserted. These must be atomic — either both succeed or neither does.

Achieve this by:

1. Opening a single database connection.
2. Running both the `UPDATE` (balance) and `INSERT` (transaction log) statements.
3. Calling `commit()` only after both statements have run without error.
4. If anything fails between the two statements, calling `rollback()` to undo the first statement.

SQLite handles this naturally: no `commit()` call means no data is permanently written, even if the first statement ran.

---

## 5. Validation Rules

### 5.1 Login Validation

**On the frontend (HTML):**
- Mark both username and password fields as `required` so the browser prevents empty submissions.

**On the backend (Flask route — the authoritative check):**
- Check that both `username` and `password` are present in `request.form` and are not empty strings after stripping whitespace.
- If either is missing: re-render the login page with "Username and password are required."
- Look up the username in the database. If not found: return "Invalid credentials." (Do not say "Username not found" — that reveals which half was wrong.)
- Verify the password hash. If it does not match: return "Invalid credentials."
- Only create the session after both checks pass.

---

### 5.2 Balance Validation

- The balance stored in the database must never go below zero.
- Always fetch the current balance from the database at the moment the transaction is processed — never rely on a cached or session-stored value, as it could be stale.
- Format the balance to exactly two decimal places before displaying it in templates.

---

### 5.3 Deposit Validation

Check all of the following, in this order, before touching the database:

| Check | Error Message |
|---|---|
| Amount field is not empty | "Amount is required." |
| Amount is a valid number | "Amount must be a valid number." |
| Amount is greater than zero | "Amount must be greater than zero." |
| Amount is not unreasonably large | "Amount exceeds the single-transaction limit." (if you implement a cap) |

Only if all checks pass should you proceed to update the balance.

---

### 5.4 Withdrawal Validation

Check all of the following, in this order:

| Check | Error Message |
|---|---|
| Amount field is not empty | "Amount is required." |
| Amount is a valid number | "Amount must be a valid number." |
| Amount is greater than zero | "Amount must be greater than zero." |
| Amount does not exceed the current balance | "Insufficient funds. Available balance: £X.XX" |

The insufficient-funds check must use the live balance from the database, fetched in the same transaction.

---

## 6. Testing

### 6.1 Unit Tests

Unit tests check individual functions in isolation, without a running server or real database. Write tests in a `tests/` folder alongside the `BACKEND/` folder.

**What to unit test:**

- **Password hashing:** Confirm that hashing a password and then checking it with the same string returns True, and checking it with a different string returns False.
- **Deposit service:** Call the deposit function directly with a mock database state and assert the returned new balance is correct. Test with a zero amount and confirm it returns an error.
- **Withdrawal service:** Test a withdrawal that leaves a positive balance, one that empties the balance exactly to zero, and one that exceeds the balance — confirm each returns the expected outcome.
- **Amount validation:** Pass in empty strings, non-numeric strings, negative numbers, and zero — confirm each is rejected with the right error message.

Use Python's built-in `unittest` module or `pytest` (install via pip). Replace actual database calls with simple mock objects so tests run fast and do not touch the disk.

---

### 6.2 Integration Tests

Integration tests check that Flask routes, business logic, and the database work together correctly. Use Flask's built-in test client, which lets you send simulated HTTP requests without a real browser.

**What to integration test:**

- **Login success:** POST to `/login` with valid credentials; assert the response redirects to `/dashboard` and that the session now contains `customer_id`.
- **Login failure:** POST to `/login` with a wrong password; assert the response re-renders the login page and shows an error.
- **Session guard:** Send a GET to `/dashboard` without logging in first; assert the response redirects to `/login`.
- **Deposit flow:** Log in, then POST to `/deposit` with a valid amount; assert the balance in the database increased by that amount.
- **Withdrawal flow:** Log in, then POST to `/withdraw` with a valid amount; assert the balance decreased.
- **Insufficient funds:** POST to `/withdraw` with an amount greater than the balance; assert the route returns an error and the balance is unchanged.
- **Logout:** GET `/logout` while logged in; assert the session is cleared and the response redirects to `/login`.

Use a separate in-memory SQLite database for integration tests so they do not corrupt your development data.

---

### 6.3 Manual Testing Checklist

Before considering the application complete, walk through each of these scenarios in a real browser:

**Authentication**
- [ ] Visit the site without logging in — confirm you are redirected to login.
- [ ] Submit the login form with an empty username — confirm an error appears.
- [ ] Submit with a wrong password — confirm a generic "Invalid credentials" error appears (not which field was wrong).
- [ ] Log in with correct credentials — confirm you land on the dashboard.
- [ ] Click Logout — confirm you are redirected to login and cannot go back to the dashboard using the browser's Back button without logging in again.

**Dashboard**
- [ ] Confirm the dashboard shows your correct name and current balance.
- [ ] Confirm Deposit and Withdraw buttons are visible and navigate to the correct forms.

**Deposit**
- [ ] Submit the deposit form with a blank amount — confirm an error appears.
- [ ] Submit with a text value like "abc" — confirm a validation error.
- [ ] Submit with a negative number — confirm rejection.
- [ ] Submit with a valid amount — confirm you are redirected to the dashboard and the balance increased.

**Withdrawal**
- [ ] Submit the withdrawal form with a blank amount — confirm an error appears.
- [ ] Submit with a text value — confirm validation error.
- [ ] Submit an amount greater than the balance — confirm "Insufficient funds" error and balance is unchanged.
- [ ] Submit a valid withdrawal — confirm balance decreased on the dashboard.

**Responsive layout**
- [ ] Open browser developer tools and simulate a tablet viewport (~768px wide) — confirm forms and buttons are still usable.

---

## 7. Deployment

### 7.1 Running Locally (Development)

To run the application on your own machine:

1. Make sure the virtual environment is activated.
2. Navigate to the `BACKEND/` folder.
3. Run `python app.py`.
4. Flask will start its built-in development server, typically on `http://127.0.0.1:5000`.
5. Open that URL in a browser.

The development server automatically reloads when you save changes to Python files (debug mode). This is only suitable for local development — do not expose it to the internet.

Set `debug=True` in your `app.run()` call during development to get detailed error pages. **Remove this before any shared or production deployment.**

---

### 7.2 Environment Variables

Never hardcode sensitive values (secret keys, database paths) directly in source code. Instead:

- Store the Flask secret key in an environment variable (e.g., `SECRET_KEY`).
- Read it in `app.py` using `os.environ.get("SECRET_KEY")`.
- Provide a fallback default only for local development, and make it obviously a placeholder.

If you share the code (e.g., on GitHub), create a `.gitignore` file that excludes `database.db` and any `.env` file containing secrets.

---

### 7.3 Production Considerations

The Flask development server is not suitable for production because it is single-threaded and has no security hardening. For a real deployment, consider the following steps:

**Replace the development server with a production WSGI server:**
- Install **Gunicorn** (Linux/macOS) or **Waitress** (Windows-compatible) via pip.
- Start the app using the WSGI server command instead of `python app.py`.
- These servers handle concurrent requests properly and are designed to run continuously.

**Put a reverse proxy in front of the app:**
- Install **Nginx** or **Apache**.
- Configure it to forward requests to Gunicorn/Waitress.
- Let Nginx serve your static files (CSS, images) directly — it is much faster at this than Python.

**Harden the configuration:**
- Set `debug=False` (or remove the debug flag entirely).
- Use a strong, randomly generated secret key (at least 32 characters).
- Enable HTTPS using a TLS certificate (Let's Encrypt provides free certificates).
- Set the session cookie flags: `SESSION_COOKIE_SECURE=True` (only send over HTTPS) and `SESSION_COOKIE_HTTPONLY=True` (prevent JavaScript from reading the cookie).

**Database considerations:**
- SQLite is fine for a single-user or low-traffic application.
- If you expect multiple simultaneous users, consider migrating to **PostgreSQL** using the same `models.py` interface — you would only change the connection string and driver, not the query logic.
- Back up `database.db` regularly; it is a single file and easy to copy.

**Hosting options:**
- A simple Linux VPS (e.g., DigitalOcean Droplet, AWS EC2) running Nginx + Gunicorn is the most flexible.
- Platform-as-a-Service providers (e.g., Railway, Render, Heroku) can deploy a Flask app directly from your Git repository with minimal configuration.

---

## Summary

| Phase | What You Build | Key Principle |
|---|---|---|
| 1. Environment | Virtual env, Flask install, folder structure | Isolated, reproducible setup |
| 2. Backend | Routes, auth, transactions, models | Separate concerns; DB access in one place |
| 3. Frontend | Jinja2 templates with Bootstrap | Server-rendered HTML; data from backend |
| 4. Integration | Form → route → service → DB → template | Exact field name matching; parameterised SQL |
| 5. Validation | Input checks at every boundary | Frontend is UX; backend is the authority |
| 6. Testing | Unit + integration + manual checklist | Test the happy path and every error case |
| 7. Deployment | Gunicorn + Nginx + HTTPS | Debug off; secrets in environment variables |

Follow the phases in order. Each phase builds a stable foundation for the next. When something does not work, start by checking the phase it belongs to before looking elsewhere.

---

*This guide provides implementation logic and reasoning. Actual code, SQL schema, and configuration file contents are intentionally excluded — refer to the project source files for those details.*
