import os
import sqlite3

from fastmcp import FastMCP

# ── Paths ────────────────────────────────────────────────────────────────────
# __file__ resolves to this script's location, so paths always work
# regardless of which directory you run the script from.
DB_PATH = os.path.join(os.path.dirname(__file__), "expense_tracker.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

# ── Server ───────────────────────────────────────────────────────────────────
mcp = FastMCP(name="Expense Tracker")


# ── Database Setup ───────────────────────────────────────────────────────────
def init_db():
    """Create the expenses table if it doesn't exist yet."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                date        TEXT    NOT NULL,
                amount      REAL    NOT NULL,
                category    TEXT    NOT NULL,
                subcategory TEXT    DEFAULT '',
                note        TEXT    DEFAULT ''
            )
        """)


init_db()


# ── Tools (exposed to LLM via MCP) ───────────────────────────────────────────

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
    - amount: in rupees         (e.g. 250.0)
    - category: must match one of the keys in categories.json
    - subcategory: optional
    - note: optional free text
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "INSERT INTO expenses (date, amount, category, subcategory, note) VALUES (?, ?, ?, ?, ?)",
            (date, amount, category, subcategory, note),
        )
        return {"status": "success", "id": cur.lastrowid}


@mcp.tool
def list_expenses(start_date: str, end_date: str):
    """
    Fetch all expenses between start_date and end_date (inclusive).
    Both dates must be in DD/MM/YYYY format.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT id, date, amount, category, subcategory, note "
            "FROM expenses WHERE date BETWEEN ? AND ? ORDER BY id ASC",
            (start_date, end_date),
        )
        cols = [col[0] for col in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


@mcp.tool
def summarize(start_date: str, end_date: str, category: str = None):
    """
    Summarize total spending grouped by category within a date range.
    Optionally filter to a single category.
    Both dates must be in DD/MM/YYYY format.
    """
    with sqlite3.connect(DB_PATH) as conn:
        query = (
            "SELECT category, SUM(amount) AS total_amount "
            "FROM expenses WHERE date BETWEEN ? AND ?"
        )
        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " GROUP BY category ORDER BY category ASC"

        cur = conn.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


# ── Resource (read-only data the LLM can look up) ────────────────────────────

@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    """
    Returns the full category list from categories.json.
    Re-read from disk every call so edits take effect without restarting.
    """
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # LOCAL:   runs on http://0.0.0.0:8000/mcp
    # RENDER:  Render injects PORT automatically (e.g. 10000)
    port = int(os.environ.get("PORT", 8000))

    # transport="streamable-http" is what makes this a proper network server.
    # stdio (the default) only works when the client and server are on the
    # same machine and communicate through stdin/stdout.
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
