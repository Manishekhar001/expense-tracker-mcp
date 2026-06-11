import csv
import io
import json
import os
from datetime import datetime

from fastmcp import FastMCP

# ── Database Configuration ──────────────────────────────────────────────────
# Set DATABASE_URL env var (e.g. from Render Postgres) to use PostgreSQL.
# Otherwise falls back to local SQLite.
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if DATABASE_URL:
    import psycopg2
    import psycopg2.extras


def _is_pg():
    return bool(DATABASE_URL)


def _adapt(sql):
    """Convert SQLite-style SQL to PostgreSQL syntax when needed."""
    if not _is_pg():
        return sql
    sql = sql.replace("?", "%s")
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    return sql


def get_conn():
    if _is_pg():
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        return conn
    else:
        import sqlite3

        db_path = os.path.join(os.path.dirname(__file__), "expense_tracker.db")
        return sqlite3.connect(db_path)


def query(sql, params=None):
    """SELECT: returns list of dicts."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(_adapt(sql), params or ())
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        conn.close()


def execute(sql, params=None):
    """INSERT / UPDATE / DELETE: returns the number of affected rows."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(_adapt(sql), params or ())
        return cur.rowcount
    finally:
        conn.close()


def insert(sql, params=None):
    """INSERT: returns the new row's ID (portable across SQLite and PG)."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        if _is_pg():
            cur.execute(_adapt(sql) + " RETURNING id", params or ())
            return cur.fetchone()[0]
        else:
            cur.execute(_adapt(sql), params or ())
            return cur.lastrowid
    finally:
        conn.close()


# ── Paths ────────────────────────────────────────────────────────────────────
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

# ── Server ───────────────────────────────────────────────────────────────────
mcp = FastMCP(name="Expense Tracker")


# ── Database Setup ───────────────────────────────────────────────────────────
def init_db():
    """Create all tables if they don't exist yet."""
    execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT    NOT NULL,
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            subcategory TEXT    DEFAULT '',
            note        TEXT    DEFAULT ''
        )
    """)
    execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT    NOT NULL UNIQUE,
            amount   REAL    NOT NULL,
            period   TEXT    NOT NULL DEFAULT 'monthly'
        )
    """)
    execute("""
        CREATE TABLE IF NOT EXISTS recurring_expenses (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            description   TEXT    NOT NULL,
            amount        REAL    NOT NULL,
            category      TEXT    NOT NULL,
            subcategory   TEXT    DEFAULT '',
            day_of_month  INTEGER NOT NULL,
            start_date    TEXT    NOT NULL,
            active        INTEGER DEFAULT 1
        )
    """)


init_db()


# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS  (exposed to the LLM via MCP)
# ═══════════════════════════════════════════════════════════════════════════════

# ── 1. Add Expense ─────────────────────────────────────────────────────────────

@mcp.tool
def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = "",
):
    """
    Add a new expense to the tracker.
    - date: must be DD/MM/YYYY  (e.g. 11/06/2026)
    - amount: in Rupees         (e.g. 250.0)
    - category: must match one of the keys in categories.json
    - subcategory: optional subcategory from categories.json
    - note: optional free-text note
    """
    new_id = insert(
        "INSERT INTO expenses (date, amount, category, subcategory, note) VALUES (?, ?, ?, ?, ?)",
        (date, amount, category, subcategory, note),
    )
    return {"status": "success", "id": new_id}


# ── 2. Get Expense (single) ────────────────────────────────────────────────────

@mcp.tool
def get_expense(expense_id: int):
    """
    Fetch a single expense by its ID.
    - expense_id: the numeric ID of the expense
    """
    results = query("SELECT * FROM expenses WHERE id = ?", (expense_id,))
    if not results:
        return {"status": "error", "message": f"No expense found with id {expense_id}"}
    return results[0]


# ── 3. Update Expense ──────────────────────────────────────────────────────────

@mcp.tool
def update_expense(
    expense_id: int,
    date: str = None,
    amount: float = None,
    category: str = None,
    subcategory: str = None,
    note: str = None,
):
    """
    Update one or more fields of an existing expense.
    - expense_id: the ID of the expense to update
    - date: optional — new date (DD/MM/YYYY)
    - amount: optional — new amount
    - category: optional — new category
    - subcategory: optional — new subcategory
    - note: optional — new note
    Only the fields you provide will be changed.
    """
    fields = []
    params = []
    for field, value in [
        ("date", date),
        ("amount", amount),
        ("category", category),
        ("subcategory", subcategory),
        ("note", note),
    ]:
        if value is not None:
            fields.append(f"{field} = ?")
            params.append(value)

    if not fields:
        return {"status": "error", "message": "No fields to update"}

    params.append(expense_id)
    changed = execute(
        f"UPDATE expenses SET {', '.join(fields)} WHERE id = ?", params
    )

    if changed == 0:
        return {"status": "error", "message": f"No expense found with id {expense_id}"}
    return {
        "status": "success",
        "updated_id": expense_id,
        "changed_fields": [f.split("=")[0].strip() for f in fields],
    }


# ── 4. Delete Expense ──────────────────────────────────────────────────────────

@mcp.tool
def delete_expense(expense_id: int):
    """
    Delete an expense by its ID.
    - expense_id: the ID of the expense to delete
    """
    rows = execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    if rows == 0:
        return {"status": "error", "message": f"No expense found with id {expense_id}"}
    return {"status": "success", "deleted_id": expense_id}


# ── 5. Search Expenses ─────────────────────────────────────────────────────────

@mcp.tool
def search_expenses(keyword: str):
    """
    Search expenses by keyword across notes, categories, and subcategories.
    - keyword: the text to search for (case-insensitive)
    """
    pattern = f"%{keyword}%"
    return query(
        "SELECT * FROM expenses "
        "WHERE note LIKE ? OR category LIKE ? OR subcategory LIKE ? "
        "ORDER BY date DESC, id DESC",
        (pattern, pattern, pattern),
    )


# ── 6. List Expenses ───────────────────────────────────────────────────────────

@mcp.tool
def list_expenses(start_date: str, end_date: str):
    """
    Fetch all expenses between start_date and end_date (inclusive).
    Both dates must be in DD/MM/YYYY format.
    """
    return query(
        "SELECT * FROM expenses WHERE date BETWEEN ? AND ? ORDER BY id ASC",
        (start_date, end_date),
    )


# ── 7. Summarize ───────────────────────────────────────────────────────────────

@mcp.tool
def summarize(start_date: str, end_date: str, category: str = None):
    """
    Summarize total spending grouped by category within a date range.
    Optionally filter to a single category.
    Both dates must be in DD/MM/YYYY format.
    """
    sql = "SELECT category, SUM(amount) AS total_amount FROM expenses WHERE date BETWEEN ? AND ?"
    params = [start_date, end_date]

    if category:
        sql += " AND category = ?"
        params.append(category)

    sql += " GROUP BY category ORDER BY category ASC"
    return query(sql, params)


# ── 8. Set Budget ──────────────────────────────────────────────────────────────

@mcp.tool
def set_budget(category: str, amount: float, period: str = "monthly"):
    """
    Set or update a budget for a specific category.
    - category: the expense category (must match categories.json keys)
    - amount: the budget amount in Rupees
    - period: 'monthly' or 'weekly' (default: monthly)
    """
    existing = query("SELECT id FROM budgets WHERE category = ?", (category,))
    if existing:
        execute(
            "UPDATE budgets SET amount = ?, period = ? WHERE category = ?",
            (amount, period, category),
        )
    else:
        execute(
            "INSERT INTO budgets (category, amount, period) VALUES (?, ?, ?)",
            (category, amount, period),
        )
    return {"status": "success", "category": category, "amount": amount, "period": period}


# ── 9. Budget Status ───────────────────────────────────────────────────────────

@mcp.tool
def budget_status(month: str = None, year: str = None):
    """
    Check how actual spending compares to budgets for each category.
    - month: optional — month as two digits (e.g. '06'). Defaults to current month.
    - year: optional — year as four digits (e.g. '2026'). Defaults to current year.
    """
    today = datetime.now()
    month = month or today.strftime("%m")
    year = year or str(today.year)

    pattern = f"%/{month}/{year}"

    budgets = query("SELECT * FROM budgets ORDER BY category")
    actuals = query(
        "SELECT category, SUM(amount) AS spent FROM expenses "
        "WHERE date LIKE ? GROUP BY category ORDER BY category",
        (pattern,),
    )

    actual_map = {r["category"]: r["spent"] for r in actuals}
    result = []

    for b in budgets:
        spent = float(actual_map.get(b["category"], 0))
        remaining = float(b["amount"]) - spent
        result.append({
            "category": b["category"],
            "budget": float(b["amount"]),
            "spent": spent,
            "remaining": remaining,
            "status": "over" if remaining < 0 else "under",
        })

    # Also include categories with spending but no budget
    for a in actuals:
        if a["category"] not in [b["category"] for b in budgets]:
            result.append({
                "category": a["category"],
                "budget": 0,
                "spent": float(a["spent"]),
                "remaining": -float(a["spent"]),
                "status": "over",
            })

    return result


# ── 10. Export CSV ────────────────────────────────────────────────────────────

@mcp.tool
def export_csv(start_date: str, end_date: str):
    """
    Export expenses in CSV format (ready to open in Excel / Google Sheets).
    - start_date: DD/MM/YYYY
    - end_date: DD/MM/YYYY
    Returns the CSV content as a string.
    """
    rows = query(
        "SELECT id, date, amount, category, subcategory, note "
        "FROM expenses WHERE date BETWEEN ? AND ? ORDER BY id ASC",
        (start_date, end_date),
    )

    if not rows:
        return {"status": "error", "message": "No expenses found in that date range"}

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "date", "amount", "category", "subcategory", "note"])
    writer.writeheader()
    writer.writerows(rows)

    return {
        "status": "success",
        "csv": output.getvalue(),
        "row_count": len(rows),
        "filename": f"expenses_{start_date.replace('/', '-')}_to_{end_date.replace('/', '-')}.csv",
    }


# ── 11. Add Recurring Expense ──────────────────────────────────────────────────

@mcp.tool
def add_recurring_expense(
    description: str,
    amount: float,
    category: str,
    subcategory: str = "",
    day_of_month: int = 1,
    start_date: str = "",
):
    """
    Register a recurring (monthly) expense.
    - description: name of the recurring expense (e.g. 'Netflix subscription')
    - amount: amount in Rupees
    - category: expense category
    - subcategory: optional subcategory
    - day_of_month: day of month to apply (1-31, default 1)
    - start_date: first occurrence date in DD/MM/YYYY (defaults to today)
    """
    if not start_date:
        start_date = datetime.now().strftime("%d/%m/%Y")

    new_id = insert(
        "INSERT INTO recurring_expenses (description, amount, category, subcategory, day_of_month, start_date) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (description, amount, category, subcategory, day_of_month, start_date),
    )
    return {
        "status": "success",
        "id": new_id,
        "description": description,
        "day_of_month": day_of_month,
    }


# ── 12. List Recurring Expenses ────────────────────────────────────────────────

@mcp.tool
def list_recurring_expenses():
    """
    List all active recurring expenses (subscriptions, EMIs, etc.).
    """
    return query(
        "SELECT * FROM recurring_expenses WHERE active = 1 ORDER BY day_of_month ASC"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# RESOURCES  (read-only data the LLM / client can look up)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.resource("expense://categories", mime_type="application/json")
def categories() -> str:
    """
    Full category / subcategory list from categories.json.
    Re-reads from disk on every call so edits take effect immediately.
    """
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()


@mcp.resource("expense://stats", mime_type="application/json")
def stats() -> str:
    """
    Overall spending statistics: total count, total amount,
    average per day, and most-spent category.
    """
    totals = query("SELECT COUNT(*) AS cnt, SUM(amount) AS total FROM expenses")
    row = totals[0] if totals else {"cnt": 0, "total": 0}

    top = query(
        "SELECT category, SUM(amount) AS total FROM expenses "
        "GROUP BY category ORDER BY total DESC LIMIT 1"
    )
    top_cat = top[0] if top else {"category": None, "total": 0}

    return json.dumps(
        {
            "total_expenses": row["cnt"],
            "total_amount": float(row["total"]) if row["total"] else 0,
            "top_category": top_cat["category"],
            "top_category_amount": float(top_cat["total"]) if top_cat["total"] else 0,
        },
        indent=2,
    )


@mcp.resource("expense://monthly/{month}/{year}", mime_type="application/json")
def monthly_breakdown(month: str, year: str) -> str:
    """
    Spending breakdown by category for a given month and year.
    - month: two-digit month (e.g. '06')
    - year: four-digit year (e.g. '2026')
    Dates are expected in DD/MM/YYYY format.
    """
    pattern = f"%/{month}/{year}"
    results = query(
        "SELECT category, SUM(amount) AS total, COUNT(*) AS count "
        "FROM expenses WHERE date LIKE ? "
        "GROUP BY category ORDER BY total DESC",
        (pattern,),
    )

    total_all = sum(r["total"] for r in results)

    return json.dumps(
        {
            "month": month,
            "year": year,
            "total_spent": float(total_all),
            "categories": [
                {
                    "category": r["category"],
                    "total": float(r["total"]),
                    "count": r["count"],
                }
                for r in results
            ],
        },
        indent=2,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPTS  (templates the LLM can invoke for structured tasks)
# ═══════════════════════════════════════════════════════════════════════════════

@mcp.prompt()
def monthly_review(month: str, year: str) -> str:
    """
    Review your spending for a specific month and year.
    Provide month (two digits, e.g. 06) and year (four digits, e.g. 2026).
    """
    return (
        f"Please review my expenses for {month}/{year}.\n\n"
        f"1. Fetch the monthly breakdown from expense://monthly/{month}/{year}\n"
        f"2. Call budget_status(month='{month}', year='{year}') to compare against budgets\n"
        f"3. Give me a friendly summary:\n"
        f"   - How much I spent in total\n"
        f"   - Top spending categories\n"
        f"   - Which categories are over / under budget\n"
        f"   - One actionable insight to save money next month"
    )


@mcp.prompt()
def budget_check() -> str:
    """
    Check your current budget status — which categories are over or under budget.
    """
    return (
        "Please check my current budget status.\n\n"
        "1. Call budget_status() to see how much I've spent vs my budgeted amounts\n"
        "2. Summarize:\n"
        "   - Which categories are over budget (by how much)\n"
        "   - Which categories are under budget (by how much)\n"
        "   - Total spent vs total budgeted\n"
        "   - Any recommendations to get back on track"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
