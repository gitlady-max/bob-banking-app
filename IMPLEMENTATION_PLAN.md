# Banking Web Application — Implementation Plan

> **Document Type:** High-Level Planning  
> **Version:** 1.0  
> **Scope:** Planning only — no schema, SQL, API contracts, or code.

---

## 1. Solution Overview

### 1.1 Objective

Deliver a lightweight, browser-based banking application that allows registered customers to securely log in, view their account balance, and perform basic transactions (deposit and withdrawal) through a clean, responsive interface.

### 1.2 Scope

| In Scope | Out of Scope |
|---|---|
| Customer login and logout | Admin panel / bank staff portal |
| View current account balance | Multi-currency support |
| Deposit and withdraw funds | Inter-account transfers |
| Session-based security | Card management |
| Responsive web UI | Mobile native app |

### 1.3 Users

| Role | Description |
|---|---|
| **Customer** | An existing bank customer who authenticates and manages their account online. |

### 1.4 Functional Requirements

1. **Authentication** — Customers must log in with a username and password. Sessions must be maintained across pages and terminated on logout.
2. **Dashboard** — After login, the customer lands on a personalised dashboard showing their name and a summary of account information.
3. **View Balance** — Customers can view their current account balance at any time from the dashboard.
4. **Deposit Funds** — Customers can enter an amount and deposit it into their account; the balance updates immediately.
5. **Withdraw Funds** — Customers can enter an amount and withdraw from their account; the system must reject withdrawals that exceed the current balance.
6. **Logout** — Customers can explicitly end their session, which clears server-side session data and redirects to the login page.

### 1.5 Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Security** | Passwords stored as hashed values; sessions invalidated on logout; no sensitive data in URLs. |
| **Usability** | Responsive layout usable on desktop and tablet; clear error messages for invalid input. |
| **Reliability** | All transactions must be atomic — a deposit or withdrawal either fully succeeds or fully rolls back. |
| **Maintainability** | Clear separation of concerns between frontend, backend, and data layers. |
| **Performance** | Page responses under 500 ms for standard operations on a local/development deployment. |

### 1.6 Assumptions

- A small, single-user-at-a-time development environment is the primary target; production scaling is out of scope.
- Each customer has exactly one bank account.
- Customer records are pre-seeded; there is no self-registration flow.
- SQLite is acceptable for persistence at this scale; no migration to a server-based RDBMS is planned.
- The application runs on a single server (no load balancing or distributed session store required).

---

## 2. High-Level Architecture

### 2.1 Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                        BROWSER                          │
│                                                         │
│   ┌──────────────────────────────────────────────────┐  │
│   │          FRONTEND  (HTML + Bootstrap)            │  │
│   │                                                  │  │
│   │  Login Page  │  Dashboard  │  Transaction Pages  │  │
│   └────────────────────┬─────────────────────────────┘  │
└────────────────────────│────────────────────────────────┘
                         │  HTTP Requests (form POST / GET)
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   BACKEND  (Python Flask)                │
│                                                         │
│   ┌──────────┐  ┌───────────┐  ┌─────────────────────┐ │
│   │  Routes  │  │  Business │  │   Session Manager   │ │
│   │ /login   │  │   Logic   │  │  (Flask sessions)   │ │
│   │ /logout  │  │ Deposit / │  │                     │ │
│   │/dashboard│  │ Withdraw  │  └─────────────────────┘ │
│   │/deposit  │  │ Balance   │                           │
│   │/withdraw │  └─────┬─────┘                           │
│   └──────────┘        │                                 │
└───────────────────────│─────────────────────────────────┘
                        │  Read / Write
                        ▼
┌─────────────────────────────────────────────────────────┐
│                  DATABASE  (SQLite)                      │
│                                                         │
│         customers table  │  transactions table          │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Frontend → Backend → Database Interaction

```
Browser                    Flask Backend              SQLite
   │                            │                       │
   │── POST /login ────────────►│                       │
   │                            │── Query customer ────►│
   │                            │◄─ Customer record ────│
   │◄─ Redirect /dashboard ─────│                       │
   │                            │                       │
   │── GET /dashboard ─────────►│                       │
   │                            │── Query balance ──────►│
   │                            │◄─ Balance value ───────│
   │◄─ Render dashboard ────────│                       │
   │                            │                       │
   │── POST /deposit ──────────►│                       │
   │                            │── Update balance ─────►│
   │                            │◄─ Confirmation ────────│
   │◄─ Redirect /dashboard ─────│                       │
```

### 2.3 Request Lifecycle

1. **Browser** sends an HTTP request (GET for page loads, POST for form submissions).
2. **Flask Router** matches the URL path to the appropriate route handler.
3. **Route Handler** validates the session (redirects to login if unauthenticated) and passes control to business logic.
4. **Business Logic** reads or writes data via the SQLite layer.
5. **Flask** renders the appropriate HTML template (Jinja2) or issues a redirect.
6. **Browser** displays the rendered page.

---

## 3. Component Design

### 3.1 Frontend Responsibilities

- Render all pages as server-side HTML templates (Jinja2, served by Flask).
- Use **Bootstrap** for responsive layout, form styling, and alert messages.
- Present login, dashboard, deposit, and withdrawal forms.
- Display dynamic data (balance, customer name, error/success messages) injected by the backend at render time.
- Provide client-side input validation (e.g., prevent empty or negative amounts) as a UX convenience — not a security control.

### 3.2 Backend Responsibilities

- Expose URL routes for every user-facing action.
- Manage customer sessions (login state, session expiry, logout).
- Enforce all business rules (e.g., insufficient funds check before withdrawal).
- Hash and verify passwords; never expose plaintext credentials.
- Interact with SQLite through Python database calls and return results to templates.
- Handle error states gracefully and surface user-friendly messages.

### 3.3 Database Responsibilities

- Persist customer identity and credentials.
- Persist current account balance per customer.
- Persist a log of all transactions (deposit / withdrawal) for audit purposes.
- Guarantee atomic updates so that a balance change and its transaction record are always written together.

---

## 4. Folder Structure

```
banking-workshop/
│
├── FRONTEND/                        # All browser-facing assets
│   ├── templates/                   # Jinja2 HTML templates (served by Flask)
│   │   ├── login.html               # Login page
│   │   ├── dashboard.html           # Main customer dashboard
│   │   ├── deposit.html             # Deposit funds form
│   │   └── withdraw.html            # Withdraw funds form
│   └── static/                      # Static assets
│       ├── css/                     # Custom stylesheet overrides
│       └── images/                  # Logo and UI imagery
│
├── BACKEND/                         # All server-side Python code
│   ├── app.py                       # Flask application entry point & route definitions
│   ├── auth.py                      # Authentication helpers (login, logout, session)
│   ├── transactions.py              # Deposit and withdrawal business logic
│   ├── models.py                    # Database access layer (queries and updates)
│   ├── database.db                  # SQLite database file (auto-created at init)
│   └── requirements.txt             # Python dependencies (Flask, etc.)
│
├── IMPLEMENTATION_PLAN.md           # This document
└── README.md                        # Project setup and run instructions
```

| Folder / File | Responsibility |
|---|---|
| `FRONTEND/templates/` | HTML page definitions; data binding via Jinja2 |
| `FRONTEND/static/` | Bootstrap CSS and any custom styles or images |
| `BACKEND/app.py` | App factory, route registration, request entry point |
| `BACKEND/auth.py` | Session creation, password verification, logout logic |
| `BACKEND/transactions.py` | Business rules for deposit and withdrawal operations |
| `BACKEND/models.py` | All SQL read/write operations; single source of truth for DB access |
| `BACKEND/database.db` | SQLite binary data file; not committed to source control |

---

## 5. Module Breakdown

### 5.1 Authentication Module

**Purpose:** Control access to the application. All other modules depend on a valid session established here.

| Concern | Description |
|---|---|
| Login | Accept username/password, verify against stored hash, create session on success |
| Session Guard | Middleware check on every protected route; redirect to login if no session |
| Logout | Destroy session data server-side and redirect to login page |
| Password Security | Passwords stored as bcrypt/Werkzeug hashes; plaintext never persisted |

### 5.2 Dashboard Module

**Purpose:** Central landing page after login; provides the customer with an at-a-glance account summary and navigation.

| Concern | Description |
|---|---|
| Balance Display | Retrieve and render the customer's current balance |
| Customer Greeting | Display the authenticated customer's name |
| Navigation | Links to Deposit, Withdraw, and Logout actions |

### 5.3 Account Management Module

**Purpose:** Read account state for the authenticated customer.

| Concern | Description |
|---|---|
| Balance Retrieval | Query the database for the current balance of the logged-in customer |
| Customer Profile | Retrieve display name and account identifier for rendering |

### 5.4 Transactions Module

**Purpose:** Process financial operations and update account state.

| Concern | Description |
|---|---|
| Deposit | Accept a positive amount, add it to the balance, record the transaction |
| Withdrawal | Accept a positive amount, verify sufficient funds, deduct from balance, record the transaction |
| Validation | Reject zero, negative, or non-numeric amounts before any DB operation |
| Insufficient Funds | Return a descriptive error if the withdrawal amount exceeds the current balance |
| Transaction Logging | Write a record of every successful operation for auditability |

---

## 6. Implementation Roadmap

### 6.1 Development Phases

#### Phase 1 — Project Scaffolding *(~0.5 day)*
- Set up folder structure (`FRONTEND/`, `BACKEND/`).
- Install Python, Flask, and Bootstrap dependencies.
- Create Flask application entry point and confirm server starts.
- Connect SQLite database and confirm connection.

> **Dependency:** None — starting point.

---

#### Phase 2 — Authentication *(~1 day)*
- Build the login HTML template with Bootstrap form.
- Implement login route, password hashing, and session creation.
- Implement session guard decorator for protected routes.
- Implement logout route and session teardown.

> **Dependency:** Phase 1 complete.

---

#### Phase 3 — Dashboard & Balance View *(~0.5 day)*
- Build the dashboard HTML template.
- Implement the dashboard route (session-guarded).
- Retrieve and display customer name and current balance.

> **Dependency:** Phase 2 (session must exist to access dashboard).

---

#### Phase 4 — Deposit & Withdrawal *(~1 day)*
- Build deposit and withdrawal HTML form templates.
- Implement deposit route with input validation and balance update.
- Implement withdrawal route with insufficient-funds check and balance update.
- Add transaction logging for all successful operations.
- Surface success and error messages on the UI.

> **Dependency:** Phase 3 (dashboard is the hub for transaction navigation).

---

#### Phase 5 — Integration & Testing *(~0.5 day)*
- End-to-end walkthrough of the full user journey (login → dashboard → deposit → withdraw → logout).
- Verify edge cases: wrong password, insufficient funds, empty form submission.
- Review UI on desktop and tablet viewport sizes.
- Final clean-up of templates and route responses.

> **Dependency:** Phases 2–4 complete.

---

### 6.2 Estimated Effort Summary

| Phase | Description | Effort |
|---|---|---|
| 1 | Project Scaffolding | 0.5 day |
| 2 | Authentication | 1.0 day |
| 3 | Dashboard & Balance View | 0.5 day |
| 4 | Deposit & Withdrawal | 1.0 day |
| 5 | Integration & Testing | 0.5 day |
| **Total** | | **~3.5 days** |

### 6.3 Dependencies Summary

```
Phase 1 (Scaffolding)
    └── Phase 2 (Authentication)
            └── Phase 3 (Dashboard)
                    └── Phase 4 (Transactions)
                                └── Phase 5 (Integration & Testing)
```

Each phase is a prerequisite for the next. No phases can be parallelised in a solo-developer context. In a two-developer team, Phase 3 frontend templates could be built in parallel with Phase 2 backend logic.

---

*This document covers planning scope only. Database schema, API contracts, SQL scripts, and detailed implementation steps are intentionally excluded.*
