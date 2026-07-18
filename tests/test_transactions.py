"""
test_transactions.py — Unit tests for the financial business logic.

These tests run in full isolation: they use an in-memory SQLite database
and never touch the real database.db file.
"""

import sys
import os
import sqlite3
import unittest
from unittest.mock import patch, MagicMock
from werkzeug.security import generate_password_hash

# ── Make BACKEND importable ───────────────────────────────────────────────────
BACKEND_DIR = os.path.join(os.path.dirname(__file__), "..", "BACKEND")
sys.path.insert(0, os.path.abspath(BACKEND_DIR))

# ─────────────────────────────────────────────────────────────────────────────
# Non-closing connection wrapper
# sqlite3.Connection.close is read-only in Python 3.14+; we wrap instead.
# ─────────────────────────────────────────────────────────────────────────────

class _NoCloseConn:
    """Thin proxy around a sqlite3.Connection that ignores close() calls."""

    def __init__(self, conn):
        self._conn = conn

    def close(self):
        pass  # intentional no-op

    # Delegate everything else to the real connection
    def __getattr__(self, name):
        return getattr(self._conn, name)


def _make_in_memory_db():
    """Return a wrapped in-memory SQLite connection pre-populated with one test account."""
    real = sqlite3.connect(":memory:")
    real.row_factory = sqlite3.Row
    real.executescript("""
        CREATE TABLE customers (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            username      TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            balance       REAL    NOT NULL DEFAULT 0.0
        );
        CREATE TABLE transactions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id      INTEGER NOT NULL,
            transaction_type TEXT    NOT NULL,
            amount           REAL    NOT NULL,
            created_at       TEXT    NOT NULL
        );
    """)
    real.execute(
        "INSERT INTO customers (name, username, password_hash, balance) VALUES (?,?,?,?)",
        ("Test User", "testuser", generate_password_hash("testpass"), 500.00),
    )
    real.commit()
    return _NoCloseConn(real)


# ─────────────────────────────────────────────────────────────────────────────
# Import the modules under test AFTER path is set up
# ─────────────────────────────────────────────────────────────────────────────
import transactions as txn_module
import models


# ─────────────────────────────────────────────────────────────────────────────
# Amount parsing / validation  (unit tests — no DB needed)
# ─────────────────────────────────────────────────────────────────────────────

class TestParseAmount(unittest.TestCase):

    def test_empty_string_rejected(self):
        amount, err = txn_module._parse_amount("")
        self.assertIsNone(amount)
        self.assertIn("required", err.lower())

    def test_whitespace_only_rejected(self):
        amount, err = txn_module._parse_amount("   ")
        self.assertIsNone(amount)
        self.assertIn("required", err.lower())

    def test_non_numeric_rejected(self):
        amount, err = txn_module._parse_amount("abc")
        self.assertIsNone(amount)
        self.assertIn("valid number", err.lower())

    def test_zero_rejected(self):
        amount, err = txn_module._parse_amount("0")
        self.assertIsNone(amount)
        self.assertIn("greater than zero", err.lower())

    def test_negative_rejected(self):
        amount, err = txn_module._parse_amount("-50")
        self.assertIsNone(amount)
        self.assertIn("greater than zero", err.lower())

    def test_valid_integer_accepted(self):
        amount, err = txn_module._parse_amount("100")
        self.assertEqual(amount, 100.0)
        self.assertIsNone(err)

    def test_valid_decimal_accepted(self):
        amount, err = txn_module._parse_amount("  99.99  ")
        self.assertEqual(amount, 99.99)
        self.assertIsNone(err)

    def test_exceeds_max_rejected(self):
        large = str(txn_module.MAX_TRANSACTION_AMOUNT + 1)
        amount, err = txn_module._parse_amount(large)
        self.assertIsNone(amount)
        self.assertIn("limit", err.lower())


# ─────────────────────────────────────────────────────────────────────────────
# Deposit service (uses a real in-memory DB via patching)
# ─────────────────────────────────────────────────────────────────────────────

class TestDepositService(unittest.TestCase):

    def setUp(self):
        self._conn = _make_in_memory_db()
        self._patcher  = patch.object(txn_module, "_get_connection", return_value=self._conn)
        self._patcher2 = patch.object(models,     "_get_connection", return_value=self._conn)
        self._patcher.start()
        self._patcher2.start()

    def tearDown(self):
        self._patcher.stop()
        self._patcher2.stop()

    def test_valid_deposit_increases_balance(self):
        success, result = txn_module.process_deposit(1, "200")
        self.assertTrue(success)
        self.assertAlmostEqual(result, 700.00)

    def test_zero_deposit_rejected(self):
        success, result = txn_module.process_deposit(1, "0")
        self.assertFalse(success)

    def test_empty_deposit_rejected(self):
        success, result = txn_module.process_deposit(1, "")
        self.assertFalse(success)

    def test_non_numeric_deposit_rejected(self):
        success, result = txn_module.process_deposit(1, "hello")
        self.assertFalse(success)


# ─────────────────────────────────────────────────────────────────────────────
# Withdrawal service
# ─────────────────────────────────────────────────────────────────────────────

class TestWithdrawalService(unittest.TestCase):

    def setUp(self):
        self._conn = _make_in_memory_db()
        self._patcher  = patch.object(txn_module, "_get_connection", return_value=self._conn)
        self._patcher2 = patch.object(models,     "_get_connection", return_value=self._conn)
        self._patcher.start()
        self._patcher2.start()

    def tearDown(self):
        self._patcher.stop()
        self._patcher2.stop()

    def test_valid_withdrawal_decreases_balance(self):
        success, result = txn_module.process_withdrawal(1, "100")
        self.assertTrue(success)
        self.assertAlmostEqual(result, 400.00)

    def test_withdrawal_exact_balance_succeeds(self):
        success, result = txn_module.process_withdrawal(1, "500")
        self.assertTrue(success)
        self.assertAlmostEqual(result, 0.00)

    def test_insufficient_funds_rejected(self):
        success, message = txn_module.process_withdrawal(1, "501")
        self.assertFalse(success)
        self.assertIn("insufficient", message.lower())

    def test_zero_withdrawal_rejected(self):
        success, _ = txn_module.process_withdrawal(1, "0")
        self.assertFalse(success)

    def test_negative_withdrawal_rejected(self):
        success, _ = txn_module.process_withdrawal(1, "-10")
        self.assertFalse(success)


# ─────────────────────────────────────────────────────────────────────────────
# Password hashing (Werkzeug)
# ─────────────────────────────────────────────────────────────────────────────

class TestPasswordHashing(unittest.TestCase):

    def test_correct_password_passes(self):
        from werkzeug.security import generate_password_hash, check_password_hash
        hashed = generate_password_hash("mypassword")
        self.assertTrue(check_password_hash(hashed, "mypassword"))

    def test_wrong_password_fails(self):
        from werkzeug.security import generate_password_hash, check_password_hash
        hashed = generate_password_hash("mypassword")
        self.assertFalse(check_password_hash(hashed, "wrongpassword"))

    def test_hash_differs_from_plaintext(self):
        from werkzeug.security import generate_password_hash
        hashed = generate_password_hash("mypassword")
        self.assertNotEqual(hashed, "mypassword")


if __name__ == "__main__":
    unittest.main()
