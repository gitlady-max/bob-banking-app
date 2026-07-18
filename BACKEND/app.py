"""
app.py — Flask Application Entry Point
Defines the Flask app object, configuration, and all URL routes.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
)

# ── Path helpers ──────────────────────────────────────────────────────────────
BACKEND_DIR  = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "FRONTEND")

# ── Allow sibling-module imports (auth, models, transactions) ─────────────────
sys.path.insert(0, BACKEND_DIR)

from models       import init_db, get_account_balance, get_transaction_history
from auth         import login_customer, logout_customer, login_required
from transactions import process_deposit, process_withdrawal

# ─────────────────────────────────────────────────────────────────────────────
# Flask app factory
# ─────────────────────────────────────────────────────────────────────────────

app = Flask(
    __name__,
    template_folder=os.path.join(FRONTEND_DIR, "templates"),
    static_folder=os.path.join(FRONTEND_DIR, "static"),
)

# Secret key — read from environment or fall back to a dev placeholder
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production-abc123")

# Session lifetime: 30 minutes of inactivity
app.permanent_session_lifetime = timedelta(minutes=30)

# Security: prevent JavaScript from reading the session cookie
app.config["SESSION_COOKIE_HTTPONLY"] = True
# SameSite=Lax prevents CSRF on cross-site form submissions
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# ── Initialise the database (creates tables and seeds data if needed) ─────────
with app.app_context():
    init_db()


# ─────────────────────────────────────────────────────────────────────────────
# Jinja2 filter — format currency values
# ─────────────────────────────────────────────────────────────────────────────

@app.template_filter("currency")
def currency_filter(value):
    """Render a float as £1,234.56"""
    try:
        return f"£{float(value):,.2f}"
    except (ValueError, TypeError):
        return "£0.00"


@app.context_processor
def inject_now():
    """Make `now` available in every Jinja2 template (used by the footer)."""
    return {"now": datetime.now(timezone.utc)}


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

# ── GET / ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if "customer_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# ── GET /login  ──────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET"])
def login():
    if "customer_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")


# ── POST /login ──────────────────────────────────────────────────────────────
@app.route("/login", methods=["POST"])
def login_post():
    username = request.form.get("username", "")
    password = request.form.get("password", "")

    success, error = login_customer(username, password)
    if success:
        return redirect(url_for("dashboard"))
    return render_template("login.html", error=error), 401


# ── GET /dashboard ───────────────────────────────────────────────────────────
@app.route("/dashboard")
@login_required
def dashboard():
    customer_id   = session["customer_id"]
    customer_name = session["customer_name"]
    balance       = get_account_balance(customer_id)
    history       = get_transaction_history(customer_id)
    return render_template(
        "dashboard.html",
        name=customer_name,
        balance=balance,
        history=history,
    )


# ── GET /deposit ─────────────────────────────────────────────────────────────
@app.route("/deposit", methods=["GET"])
@login_required
def deposit():
    balance = get_account_balance(session["customer_id"])
    return render_template("deposit.html", balance=balance)


# ── POST /deposit ────────────────────────────────────────────────────────────
@app.route("/deposit", methods=["POST"])
@login_required
def deposit_post():
    raw_amount = request.form.get("amount", "")
    success, result = process_deposit(session["customer_id"], raw_amount)
    if success:
        flash(f"Deposit successful! New balance: £{result:,.2f}", "success")
        return redirect(url_for("dashboard"))
    balance = get_account_balance(session["customer_id"])
    return render_template("deposit.html", error=result, balance=balance), 422


# ── GET /withdraw ────────────────────────────────────────────────────────────
@app.route("/withdraw", methods=["GET"])
@login_required
def withdraw():
    balance = get_account_balance(session["customer_id"])
    return render_template("withdraw.html", balance=balance)


# ── POST /withdraw ───────────────────────────────────────────────────────────
@app.route("/withdraw", methods=["POST"])
@login_required
def withdraw_post():
    raw_amount = request.form.get("amount", "")
    success, result = process_withdrawal(session["customer_id"], raw_amount)
    if success:
        flash(f"Withdrawal successful! New balance: £{result:,.2f}", "success")
        return redirect(url_for("dashboard"))
    balance = get_account_balance(session["customer_id"])
    return render_template("withdraw.html", error=result, balance=balance), 422


# ── GET /logout ──────────────────────────────────────────────────────────────
@app.route("/logout")
def logout():
    logout_customer()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ─────────────────────────────────────────────────────────────────────────────
# Error handlers
# ─────────────────────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404, message="Page not found."), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500, message="Something went wrong on our end."), 500


# ─────────────────────────────────────────────────────────────────────────────
# Development server entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
