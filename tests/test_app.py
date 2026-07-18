"""
test_app.py — Integration tests for Flask routes.

Uses Flask's built-in test client with a temporary database file
so tests are isolated and do not modify the development database.db.
"""

import sys
import os
import tempfile
import sqlite3
import unittest
from werkzeug.security import generate_password_hash

# ── Make BACKEND importable ───────────────────────────────────────────────────
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "BACKEND")
sys.path.insert(0, os.path.abspath(BACKEND_DIR))

# ─────────────────────────────────────────────────────────────────────────────
# Base test case — spins up a fresh temp DB for every test method
# ─────────────────────────────────────────────────────────────────────────────

class BankingTestCase(unittest.TestCase):

    def setUp(self):
        # Create a temporary database file
        fd, self._db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        # Populate it with schema + a test user (mirrors models.init_db)
        conn = sqlite3.connect(self._db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS customers (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT    NOT NULL,
                username      TEXT    NOT NULL UNIQUE,
                password_hash TEXT    NOT NULL,
                balance       REAL    NOT NULL DEFAULT 0.0
            );
            CREATE TABLE IF NOT EXISTS transactions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id      INTEGER NOT NULL,
                transaction_type TEXT    NOT NULL,
                amount           REAL    NOT NULL,
                created_at       TEXT    NOT NULL
            );
        """)
        conn.execute(
            "INSERT INTO customers (name, username, password_hash, balance) VALUES (?,?,?,?)",
            ("Alice Johnson", "alice", generate_password_hash("password123"), 1000.00),
        )
        conn.commit()
        conn.close()

        # Point models.DB_PATH at the temp file *before* importing the app
        import models as models_module
        models_module.DB_PATH = self._db_path

        # Import (or reload) the Flask app so init_db() runs against temp DB
        import importlib
        import app as app_module
        importlib.reload(app_module)

        app_module.app.config["TESTING"]          = True
        app_module.app.config["WTF_CSRF_ENABLED"] = False
        app_module.app.secret_key                 = "test-secret-key"

        self.app    = app_module.app
        self.client = app_module.app.test_client()

    def tearDown(self):
        try:
            os.unlink(self._db_path)
        except OSError:
            pass

    # ── Convenience helpers ───────────────────────────────────────────────────

    def login(self, username="alice", password="password123"):
        return self.client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=False,
        )

    def login_and_follow(self, username="alice", password="password123"):
        return self.client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Authentication tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAuthRoutes(BankingTestCase):

    def test_root_redirects_to_login_when_not_logged_in(self):
        resp = self.client.get("/", follow_redirects=False)
        self.assertIn(resp.status_code, (301, 302))
        self.assertIn("/login", resp.headers["Location"])

    def test_login_page_renders(self):
        resp = self.client.get("/login")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Log In", resp.data)

    def test_successful_login_redirects_to_dashboard(self):
        resp = self.login()
        self.assertIn(resp.status_code, (301, 302))
        self.assertIn("/dashboard", resp.headers["Location"])

    def test_wrong_password_renders_error(self):
        resp = self.client.post(
            "/login",
            data={"username": "alice", "password": "wrongpass"},
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 401)
        self.assertIn(b"Invalid credentials", resp.data)

    def test_empty_credentials_renders_error(self):
        resp = self.client.post(
            "/login",
            data={"username": "", "password": ""},
            follow_redirects=True,
        )
        self.assertIn(b"required", resp.data.lower())

    def test_unknown_username_renders_generic_error(self):
        resp = self.client.post(
            "/login",
            data={"username": "nobody", "password": "pass"},
            follow_redirects=True,
        )
        self.assertIn(b"Invalid credentials", resp.data)

    def test_logout_clears_session(self):
        self.login()
        resp = self.client.get("/logout", follow_redirects=False)
        self.assertIn(resp.status_code, (301, 302))
        self.assertIn("/login", resp.headers["Location"])
        # After logout, dashboard must redirect to login
        dash = self.client.get("/dashboard", follow_redirects=False)
        self.assertIn("/login", dash.headers["Location"])


# ─────────────────────────────────────────────────────────────────────────────
# Session guard tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSessionGuard(BankingTestCase):

    def test_dashboard_requires_login(self):
        resp = self.client.get("/dashboard", follow_redirects=False)
        self.assertIn(resp.status_code, (301, 302))
        self.assertIn("/login", resp.headers["Location"])

    def test_deposit_requires_login(self):
        resp = self.client.get("/deposit", follow_redirects=False)
        self.assertIn(resp.status_code, (301, 302))

    def test_withdraw_requires_login(self):
        resp = self.client.get("/withdraw", follow_redirects=False)
        self.assertIn(resp.status_code, (301, 302))


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDashboard(BankingTestCase):

    def test_dashboard_shows_customer_name(self):
        self.login()
        resp = self.client.get("/dashboard")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Alice", resp.data)

    def test_dashboard_shows_balance(self):
        self.login()
        resp = self.client.get("/dashboard")
        self.assertIn(b"1,000.00", resp.data)


# ─────────────────────────────────────────────────────────────────────────────
# Deposit flow tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDepositRoute(BankingTestCase):

    def test_valid_deposit_redirects_to_dashboard(self):
        self.login()
        resp = self.client.post(
            "/deposit",
            data={"amount": "250"},
            follow_redirects=False,
        )
        self.assertIn(resp.status_code, (301, 302))
        self.assertIn("/dashboard", resp.headers["Location"])

    def test_empty_deposit_shows_error(self):
        self.login()
        resp = self.client.post(
            "/deposit",
            data={"amount": ""},
            follow_redirects=True,
        )
        self.assertIn(b"required", resp.data.lower())

    def test_non_numeric_deposit_shows_error(self):
        self.login()
        resp = self.client.post(
            "/deposit",
            data={"amount": "abc"},
            follow_redirects=True,
        )
        self.assertIn(b"valid number", resp.data.lower())

    def test_negative_deposit_rejected(self):
        self.login()
        resp = self.client.post(
            "/deposit",
            data={"amount": "-50"},
            follow_redirects=True,
        )
        self.assertIn(b"greater than zero", resp.data.lower())


# ─────────────────────────────────────────────────────────────────────────────
# Withdrawal flow tests
# ─────────────────────────────────────────────────────────────────────────────

class TestWithdrawRoute(BankingTestCase):

    def test_valid_withdrawal_redirects_to_dashboard(self):
        self.login()
        resp = self.client.post(
            "/withdraw",
            data={"amount": "200"},
            follow_redirects=False,
        )
        self.assertIn(resp.status_code, (301, 302))
        self.assertIn("/dashboard", resp.headers["Location"])

    def test_insufficient_funds_shows_error(self):
        self.login()
        resp = self.client.post(
            "/withdraw",
            data={"amount": "9999"},
            follow_redirects=True,
        )
        self.assertIn(b"insufficient", resp.data.lower())

    def test_empty_withdrawal_shows_error(self):
        self.login()
        resp = self.client.post(
            "/withdraw",
            data={"amount": ""},
            follow_redirects=True,
        )
        self.assertIn(b"required", resp.data.lower())

    def test_text_withdrawal_shows_error(self):
        self.login()
        resp = self.client.post(
            "/withdraw",
            data={"amount": "xyz"},
            follow_redirects=True,
        )
        self.assertIn(b"valid number", resp.data.lower())


if __name__ == "__main__":
    unittest.main()
