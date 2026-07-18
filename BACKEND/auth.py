"""
auth.py — Authentication helpers
Handles login verification, session management, and the login-required
decorator used to protect routes from unauthenticated access.
"""

from functools import wraps
from flask import session, redirect, url_for, flash
from werkzeug.security import check_password_hash
from models import get_customer_by_username


def login_customer(username: str, password: str):
    """
    Attempt to authenticate a customer.

    Returns (True, None) on success — the caller is responsible for the
    redirect; session data is stored here.
    Returns (False, error_message) on any failure.
    """
    # ── Basic presence check ──────────────────────────────────────────────────
    if not username or not username.strip():
        return False, "Username and password are required."
    if not password:
        return False, "Username and password are required."

    # ── Database lookup ───────────────────────────────────────────────────────
    customer = get_customer_by_username(username.strip())
    if customer is None:
        return False, "Invalid credentials."

    # ── Password verification ─────────────────────────────────────────────────
    if not check_password_hash(customer["password_hash"], password):
        return False, "Invalid credentials."

    # ── Build session ─────────────────────────────────────────────────────────
    session.clear()
    session["customer_id"] = customer["id"]
    session["customer_name"] = customer["name"]
    session.permanent = True          # honour the app's permanent_session_lifetime

    return True, None


def logout_customer():
    """Destroy the current session."""
    session.clear()


def login_required(f):
    """
    Route decorator — redirects unauthenticated requests to the login page.

    Usage::

        @app.route("/dashboard")
        @login_required
        def dashboard():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "customer_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function
