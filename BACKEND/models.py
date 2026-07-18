"""
models.py — Data Access Layer
All database operations are centralised here.  Any other module that needs
to read or write data must call a function from this file.
"""

import sqlite3
import os
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash

# ── Path to the SQLite file (sits next to this module) ───────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")


# ─────────────────────────────────────────────────────────────────────────────
# Database initialisation
# ─────────────────────────────────────────────────────────────────────────────

def _get_connection():
    """Open and return a database connection with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # rows accessible as dicts
    conn.execute("PRAGMA journal_mode=WAL") # safe for concurrent reads
    return conn


def init_db():
    """
    Create tables if they do not exist and seed two demo customer accounts.
    Must be called once when the Flask app starts, before serving requests.
    """
    conn = _get_connection()
    cur = conn.cursor()

    # customers table ─────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            balance       REAL    NOT NULL DEFAULT 0.0
        )
    """)

    # transactions table ──────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id      INTEGER NOT NULL,
            transaction_type TEXT    NOT NULL CHECK(transaction_type IN ('deposit','withdrawal')),
            amount           REAL    NOT NULL,
            created_at       TEXT    NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        )
    """)

    # Seed demo accounts only if the table is empty ───────────────────────────
    cur.execute("SELECT COUNT(*) FROM customers")
    if cur.fetchone()[0] == 0:
        seed_data = [
            ("Alice Johnson", "alice", generate_password_hash("password123"), 1500.00),
            ("Bob Smith",     "bob",   generate_password_hash("securepass"),  250.75),
        ]
        cur.executemany(
            "INSERT INTO customers (name, username, password_hash, balance) VALUES (?,?,?,?)",
            seed_data,
        )

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Query functions
# ─────────────────────────────────────────────────────────────────────────────

def get_customer_by_username(username: str):
    """Return the customer row for *username*, or None if not found."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return row


def get_account_balance(customer_id: int) -> float:
    """Return the current balance (float) for the given customer ID."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute("SELECT balance FROM customers WHERE id = ?", (customer_id,))
    row = cur.fetchone()
    conn.close()
    return float(row["balance"]) if row else 0.0


def update_balance(customer_id: int, new_balance: float, conn=None) -> None:
    """
    Overwrite the stored balance with *new_balance*.
    Accepts an optional open *conn* so the caller can group this with
    record_transaction() in a single atomic commit.
    """
    own_conn = conn is None
    if own_conn:
        conn = _get_connection()
    conn.execute(
        "UPDATE customers SET balance = ? WHERE id = ?",
        (new_balance, customer_id),
    )
    if own_conn:
        conn.commit()
        conn.close()


def record_transaction(customer_id: int, transaction_type: str, amount: float, conn=None) -> None:
    """
    Insert a transaction log row.
    Accepts an optional open *conn* for atomic pairing with update_balance().
    """
    own_conn = conn is None
    if own_conn:
        conn = _get_connection()
    conn.execute(
        "INSERT INTO transactions (customer_id, transaction_type, amount, created_at) VALUES (?,?,?,?)",
        (customer_id, transaction_type, amount, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
    )
    if own_conn:
        conn.commit()
        conn.close()


def get_transaction_history(customer_id: int, limit: int = 10):
    """Return the most recent *limit* transactions for *customer_id*, newest first."""
    conn = _get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT transaction_type, amount, created_at
        FROM   transactions
        WHERE  customer_id = ?
        ORDER  BY id DESC
        LIMIT  ?
        """,
        (customer_id, limit),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
