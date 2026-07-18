"""
transactions.py — Financial Business Logic
This module knows nothing about HTTP, Flask, or HTML.
It receives validated inputs, enforces business rules, and delegates
all database writes to models.py.
"""

from models import _get_connection, get_account_balance, update_balance, record_transaction

# Maximum single-transaction amount (adjust as needed)
MAX_TRANSACTION_AMOUNT = 100_000.00


def _parse_amount(raw: str):
    """
    Convert the raw string from a form field to a float.
    Returns (float, None) on success, (None, error_message) on failure.
    """
    if raw is None or raw.strip() == "":
        return None, "Amount is required."
    try:
        amount = float(raw.strip())
    except ValueError:
        return None, "Amount must be a valid number."
    if amount <= 0:
        return None, "Amount must be greater than zero."
    if amount > MAX_TRANSACTION_AMOUNT:
        return None, f"Amount exceeds the single-transaction limit of £{MAX_TRANSACTION_AMOUNT:,.2f}."
    return amount, None


def process_deposit(customer_id: int, raw_amount: str):
    """
    Deposit *raw_amount* into the account identified by *customer_id*.

    Returns (True, new_balance) on success.
    Returns (False, error_message) on validation or processing failure.
    """
    amount, error = _parse_amount(raw_amount)
    if error:
        return False, error

    # Atomic: fetch current balance, update balance, record transaction
    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT balance FROM customers WHERE id = ?", (customer_id,))
        row = cur.fetchone()
        if row is None:
            conn.close()
            return False, "Account not found."

        current_balance = float(row["balance"])
        new_balance = round(current_balance + amount, 2)

        update_balance(customer_id, new_balance, conn=conn)
        record_transaction(customer_id, "deposit", amount, conn=conn)
        conn.commit()
        return True, new_balance
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def process_withdrawal(customer_id: int, raw_amount: str):
    """
    Withdraw *raw_amount* from the account identified by *customer_id*.

    Returns (True, new_balance) on success.
    Returns (False, error_message) on validation or processing failure.
    """
    amount, error = _parse_amount(raw_amount)
    if error:
        return False, error

    # Atomic: fetch current balance, check funds, update, record
    conn = _get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT balance FROM customers WHERE id = ?", (customer_id,))
        row = cur.fetchone()
        if row is None:
            conn.close()
            return False, "Account not found."

        current_balance = float(row["balance"])

        if amount > current_balance:
            conn.close()
            return False, f"Insufficient funds. Available balance: £{current_balance:,.2f}"

        new_balance = round(current_balance - amount, 2)

        update_balance(customer_id, new_balance, conn=conn)
        record_transaction(customer_id, "withdrawal", amount, conn=conn)
        conn.commit()
        return True, new_balance
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
