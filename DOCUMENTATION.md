# 📘 Expense Tracker MCP — Complete Project Documentation

> **Note:** Read this document from top to bottom. Each section builds on the previous one.

---

# 1. PROJECT OVERVIEW

## 1.1 What is this project?

This is an **Expense Tracker** application that lets you:

- **Track your daily expenses** (add, view, update, delete)
- **Set monthly budgets** for different spending categories
- **Search expenses** by keywords
- **Export data** as CSV for Excel/Google Sheets
- **Ask questions in plain English** via an AI assistant

The special thing about this app is that it uses **MCP (Model Context Protocol)** — a modern way for AI assistants to communicate with backend services.

## 1.2 Who is it for?

- **For learning:** If you're studying MCP, LangChain, or Streamlit
- **For interviews:** The Streamlit UI shows MCP tool calls happening in real-time — great for demonstrating architecture knowledge
- **For personal use:** Track your expenses with a smart AI assistant

## 1.3 Key Technologies Used

| Technology | Purpose |
|---|---|
| **Python 3.13+** | Main programming language |
| **FastMCP** | Python framework for creating MCP servers |
| **LangChain + LangGraph** | AI framework for building LLM-powered agents |
| **Groq (LLaMA 3.1)** | Fast, free LLM for understanding natural language |
| **Streamlit** | Web UI framework for the demo frontend |
| **SQLite / PostgreSQL** | Database (SQLite locally, PostgreSQL on Render) |
| **Render** | Cloud hosting platform |
| **MCP Protocol** | Standard way for AI agents to call tools remotely |

---

# 2. ARCHITECTURE

## 2.1 High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    YOUR BROWSER (localhost:8501)                     │
│                                                                      │
│   ┌──────────────────────────────────────────────────────────────┐   │
│   │              Streamlit Web App (streamlit_app.py)             │   │
│   │                                                               │   │
│   │  ┌──────────┐   ┌──────────────────┐   ┌──────────────────┐  │   │
│   │  │ Chat Box │   │   LangChain      │   │  Sidebar:        │  │   │
│   │  │ (ask     │──▶│   Agent + Groq   │──▶│  Tool Call Log   │  │   │
│   │  │questions)│   │   LLM            │   │  (shows each     │  │   │
│   │  └──────────┘   └────────┬─────────┘   │   MCP call)      │  │   │
│   │                           │             └──────────────────┘  │   │
│   └───────────────────────────┼───────────────────────────────────┘   │
│                               │ MCP over HTTP (streamable-http)       │
└───────────────────────────────┼───────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      RENDER CLOUD                                    │
│                                                                      │
│   ┌─────────────────────────────────────────────────────────────┐    │
│   │              MCP Server (main.py)                            │    │
│   │                                                              │    │
│   │  ┌────────────┐    ┌──────────────┐    ┌────────────────┐   │    │
│   │  │ 12 Tools   │    │ 3 Resources  │    │ 2 Prompts      │   │    │
│   │  │ (CRUD ops) │    │ (read-only   │    │ (templates for │   │    │
│   │  │            │    │  data)       │    │  the LLM)      │   │    │
│   │  └────────────┘    └──────────────┘    └────────────────┘   │    │
│   │                          │                                   │    │
│   │                          ▼                                   │    │
│   │              ┌──────────────────────┐                        │    │
│   │              │  PostgreSQL Database  │                        │    │
│   │              │  (3 tables)          │                        │    │
│   │              └──────────────────────┘                        │    │
│   └─────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

## 2.2 Data Flow (When You Ask a Question)

Here's what happens step-by-step when you type *"How much did I spend on food last week?"*:

```
Step 1:  You type question in Streamlit chat box
              │
              ▼
Step 2:  Streamlit sends it to LangChain Agent
              │
              ▼
Step 3:  Agent formats it with a system prompt
         (telling the LLM: "You are an expense assistant...")
              │
              ▼
Step 4:  Agent sends to Groq's LLaMA 3.1 model
              │
              ▼
Step 5:  LLM understands it needs data
         Decides to call the MCP tool "summarize"
              │
              ▼
Step 6:  Agent calls summarize() via MCP protocol
         over HTTP to the Render MCP Server
              │
              ▼
Step 7:  MCP Server runs SQL query on PostgreSQL
         SELECT category, SUM(amount) FROM expenses ...
              │
              ▼
Step 8:  Result flows back:
         PostgreSQL → MCP Server → HTTP → Agent → LLM
              │
              ▼
Step 9:  LLM reads the data and writes a friendly response
         "You spent ₹2,450 on food last week..."
              │
              ▼
Step 10: Response displayed in Streamlit chat
         (and sidebar shows the tool call that was made)
```

## 2.3 MCP Architecture (The Key Concept)

```
┌──────────────────────────┐        ┌──────────────────────────────┐
│   MCP Client             │        │   MCP Server                 │
│   (LangChain Agent)      │        │   (FastMCP)                  │
│                          │        │                              │
│   Knows what tools       │  HTTP  │   Has actual tool            │
│   exist and their        │◄─────►│   implementations that       │
│   signatures             │        │   interact with the DB       │
│                          │        │                              │
│   "I need to call        │        │   "Sure, here's the           │
│    summarize() with      │        │    spending summary"         │
│    these params"         │        │                              │
└──────────────────────────┘        └──────────────────────────────┘
```

**Why MCP?** It separates the AI agent from the actual backend. The agent doesn't need to know about PostgreSQL, SQL queries, or authentication — it just calls tools by name with parameters.

---

# 3. FILE STRUCTURE

```
expense-tracker-mcp/
├── main.py              ← MCP SERVER: Backend that talks to database
├── streamlit_app.py     ← STREAMLIT UI: Frontend demo for interviews
├── categories.json      ← DATA: Valid expense categories & subcategories
├── pyproject.toml       ← CONFIG: Python project dependencies (uv)
├── requirements.txt     ← CONFIG: Legacy dependency list
├── Procfile             ← DEPLOY: Render startup command
├── README.md            ← DOCS: Quick-start guide
├── DOCUMENTATION.md     ← DOCS: This file - full explanation
├── .gitignore           ← CONFIG: Files git should ignore
├── uv.lock              ← CONFIG: Locked dependency versions (auto)
├── .python-version      ← CONFIG: Python version (3.13)
└── nul                  ← ARTIFACT: Windows trash file (can delete)
```

---

# 4. FILE-BY-FILE EXPLANATION

---

## 4.1 `main.py` — MCP Server (Backend)

### What it does

Acts as the **backend server**. It:
1. Connects to a database (SQLite locally or PostgreSQL on Render)
2. Exposes 12 tools, 3 resources, and 2 prompts via MCP protocol
3. Runs as an HTTP server that the AI agent can call

### Line-by-Line Walkthrough

```python
# ── SECTION: IMPORTS ──────────────────────────────────────────────
import csv                # For generating CSV exports
import functools          # For the @json_response decorator
import io                 # For in-memory file (CSV export)
import json               # For converting data to JSON strings
import os                 # For reading environment variables (DATABASE_URL, PORT)
from datetime import datetime  # For getting today's date

from fastmcp import FastMCP    # The MCP server framework
```

**What each import does:**
- `csv`: Python's built-in CSV library. Used in `export_csv()` to create comma-separated values that Excel/Sheets can open.
- `functools`: Provides `@functools.wraps` decorator that preserves function metadata (name, docstring) when wrapping.
- `io`: `io.StringIO` creates a fake "file" in memory — we write CSV text to it without creating an actual file on disk.
- `json`: Converts Python dictionaries (`{...}`) into JSON strings (`"{...}"`) for sending over the network.
- `os`: Reads environment variables like `DATABASE_URL` and `PORT`.
- `datetime`: Gets the current date/time for budget status and recurring expense default dates.
- `fastmcp`: The core framework. `FastMCP` creates an MCP server with one line: `mcp = FastMCP(name="Expense Tracker")`.

```python
# ── SECTION: DATABASE SETUP ───────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")
```

Reads the `DATABASE_URL` environment variable. If it's not set (empty string), we use SQLite. If it IS set (e.g., on Render), we try PostgreSQL.

```python
if DATABASE_URL:
    try:
        import psycopg2
    except ImportError:
        import sys
        print("psycopg2 not installed. Falling back to SQLite.", file=sys.stderr)
        DATABASE_URL = ""  # reset so _is_pg() returns False
```

If `DATABASE_URL` is set but `psycopg2` isn't installed, the app still works — it falls back to SQLite. This means you can develop locally without PostgreSQL installed.

```python
def _is_pg():
    return bool(DATABASE_URL)
```

Returns `True` if we're using PostgreSQL, `False` if SQLite. The underscore `_` prefix means "private" — it's only used internally by other functions in this file.

```python
def _adapt(sql):
    """Convert SQLite-style SQL to PostgreSQL syntax when needed."""
    if not _is_pg():
        return sql
    sql = sql.replace("?", "%s")
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    sql = sql.replace(" LIKE %s", " ILIKE %s")
    return sql
```

**Why this is needed:** SQLite and PostgreSQL have slightly different SQL syntax. We write all SQL using SQLite syntax (with `?` placeholders), then `_adapt()` converts it to PostgreSQL syntax when needed:
- `?` → `%s` (placeholder for parameters)
- `INTEGER PRIMARY KEY AUTOINCREMENT` → `SERIAL PRIMARY KEY` (auto-increment syntax)
- `LIKE %s` → `ILIKE %s` (case-insensitive search — `ILIKE` is PostgreSQL-specific)

```python
def get_conn():
    if _is_pg():
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        return conn
    else:
        import sqlite3
        db_path = os.path.join(os.path.dirname(__file__), "expense_tracker.db")
        return sqlite3.connect(db_path)
```

Creates a database connection. For PostgreSQL: connects using the URL. For SQLite: creates/opens `expense_tracker.db` in the same folder as `main.py`.
- `conn.autocommit = True`: Every SQL command saves immediately (no need to manually commit).

```python
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
```

**For SELECT queries.** Returns results as a list of dictionaries (e.g., `[{"id": 1, "amount": 350}, ...]`).
- `cur.description`: Contains column names from the query result
- `dict(zip(cols, row))`: Pairs column names with values into a dictionary
- `finally: conn.close()`: Always closes the connection, even if there's an error

```python
def execute(sql, params=None):
    """INSERT / UPDATE / DELETE: returns the number of affected rows."""
    ...
```

**For INSERT/UPDATE/DELETE.** Returns the number of rows that were modified (e.g., `1` if one expense was deleted).

```python
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
```

**For INSERT queries where we need the new ID.** Differences:
- PostgreSQL: Uses `RETURNING id` to get the new ID
- SQLite: Uses `cur.lastrowid` property

```python
# ── SECTION: AUTHENTICATION ────────────────────────────────────────
MCP_API_KEY = os.environ.get("MCP_API_KEY", "")
```

If you set `MCP_API_KEY` in Render's environment variables, every tool call must include the correct `api_key` parameter. If not set (local development), authentication is skipped.

```python
def json_response(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        return json.dumps(result)
    return wrapper
```

**A decorator** that automatically converts function return values to JSON strings. Example:
- Without decorator: returns `{"status": "success", "id": 42}` (a Python dict)
- With decorator: returns `'{"status": "success", "id": 42}'` (a JSON string)

This is important because the LLM expects tool outputs in a specific format.

```python
def authenticated(api_key: str = "") -> str | None:
    if MCP_API_KEY and api_key != MCP_API_KEY:
        return "Invalid or missing API key."
    return None
```

**The gatekeeper.** Every tool function calls `authenticated(api_key)` first. If it returns an error message, the tool refuses to run.

```python
# ── SECTION: SERVER INIT ──────────────────────────────────────────
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")
mcp = FastMCP(name="Expense Tracker")
```

- `CATEGORIES_PATH`: Path to `categories.json` — used by the `categories()` resource to read categories from disk.
- `mcp = FastMCP(...)`: Creates the MCP server instance. All tools will be registered on this object.

```python
def init_db():
    """Create all tables if they don't exist yet."""
    execute("""CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
        amount REAL NOT NULL, category TEXT NOT NULL,
        subcategory TEXT DEFAULT '', note TEXT DEFAULT '')""")
    execute("""CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT NOT NULL UNIQUE,
        amount REAL NOT NULL, period TEXT NOT NULL DEFAULT 'monthly')""")
    execute("""CREATE TABLE IF NOT EXISTS recurring_expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT, description TEXT NOT NULL,
        amount REAL NOT NULL, category TEXT NOT NULL,
        subcategory TEXT DEFAULT '', day_of_month INTEGER NOT NULL,
        start_date TEXT NOT NULL, active INTEGER DEFAULT 1)""")

init_db()
```

Creates **3 database tables**:

| Table | Stores |
|---|---|
| `expenses` | Each expense: date, amount, category, subcategory, note |
| `budgets` | Budget limits per category (monthly/weekly) |
| `recurring_expenses` | Recurring/subscription expenses (Netflix, rent, etc.) |

`init_db()` runs **every time the server starts** — `CREATE TABLE IF NOT EXISTS` means it only creates them if they don't exist yet.

### ── THE 12 TOOLS ──────────────────────────────────────────────

Each tool follows the same pattern:
1. `@mcp.tool` — Registers it with the MCP server
2. `@json_response` — Auto-converts return value to JSON
3. Check `authenticated(api_key)` first
4. Do the database operation
5. Return result dictionary

| Tool | SQL Operation | Purpose |
|---|---|---|
| `add_expense` | INSERT | Add a new expense |
| `get_expense` | SELECT by id | Get one expense |
| `update_expense` | UPDATE | Change fields of an expense |
| `delete_expense` | DELETE | Remove an expense |
| `search_expenses` | SELECT with LIKE | Find expenses by keyword |
| `list_expenses` | SELECT by date range | List expenses between dates |
| `summarize` | SELECT with GROUP BY | Total spending by category |
| `set_budget` | UPSERT | Set/update a budget |
| `budget_status` | SELECT + JOIN logic | Compare spending vs budget |
| `export_csv` | SELECT + CSV | Download expenses as CSV |
| `add_recurring_expense` | INSERT | Add a subscription |
| `list_recurring_expenses` | SELECT | List active subscriptions |

### ── THE 3 RESOURCES ───────────────────────────────────────────

Resources are **read-only data** that the LLM/client can look up. Unlike tools, they don't modify anything.

```python
@mcp.resource("expense://categories", ...)
def categories() -> str:
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()
```

**URI:** `expense://categories` — Returns the full category list from `categories.json`.

```python
@mcp.resource("expense://stats", ...)
def stats() -> str:
    ...
    return json.dumps({
        "total_expenses": cnt,
        "total_amount": total,
        "top_category": category,
        ...
    })
```

**URI:** `expense://stats` — Returns overall spending stats (total count, total amount, top category).

```python
@mcp.resource("expense://monthly/{month}/{year}", ...)
def monthly_breakdown(month: str, year: str) -> str:
    ...
```

**URI:** `expense://monthly/06/2026` — Returns spending breakdown for a specific month. The `{month}` and `{year}` are **path parameters** that the client fills in.

### ── THE 2 PROMPTS ─────────────────────────────────────────────

Prompts are **templates** that the LLM can invoke for structured tasks:

```python
@mcp.prompt()
def monthly_review(month: str, year: str) -> str:
    return (
        f"Please review my expenses for {month}/{year}.\n\n"
        f"1. Fetch the monthly breakdown from expense://monthly/{month}/{year}\n"
        f"2. Call budget_status(month='{month}', year='{year}')\n"
        f"3. Give me a friendly summary..."
    )
```

When the LLM calls `monthly_review("06", "2026")`, it gets a template telling it exactly which tools/resources to use and how to format the response.

### ── ENTRY POINT ──────────────────────────────────────────────

```python
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
```

- `__name__ == "__main__"`: Only runs when this file is executed directly (not imported)
- `PORT`: Render automatically sets this environment variable (defaults to 8000 locally)
- `transport="streamable-http"`: Uses modern MCP transport protocol
- `host="0.0.0.0"`: Listens on all network interfaces (required for Render)

---

## 4.2 `streamlit_app.py` — Streamlit Frontend

### What it does

Creates a **web-based chat interface** that:
1. Connects to the Render MCP server
2. Lets you type expense questions in natural language
3. Runs an AI agent that calls MCP tools
4. Shows each tool call in the sidebar so you can see MCP in action

### Line-by-Line Walkthrough

```python
# ── SECTION: IMPORTS ──────────────────────────────────────────────
import asyncio            # For running async functions (await, asyncio.run)
import json               # For parsing tool results
import os                 # For reading GROQ_API_KEY from .env
from datetime import date # For today's date in system prompt

import streamlit as st    # The web UI framework
from dotenv import load_dotenv  # Reads .env file
from langchain_core.messages import SystemMessage  # For system prompts
from langchain_groq import ChatGroq  # Groq's LLM interface
from langchain_mcp_adapters.client import MultiServerMCPClient  # MCP client
from langgraph.checkpoint.memory import MemorySaver  # Conversation memory
from langgraph.prebuilt import create_react_agent  # Ready-made AI agent
```

**Key imports explained simply:**
- `asyncio`: Python's async library. We need it because connecting to MCP and running the agent are async operations.
- `streamlit as st`: The web framework. Every `st.xxx` call puts something on the webpage.
- `ChatGroq`: Connects to Groq's API to use the free LLaMA 3.1 model.
- `MultiServerMCPClient`: Connects to the MCP server (like a web browser connecting to a website).
- `create_react_agent`: Creates a **ReAct agent** — an AI that can Reason and Act (call tools).
- `MemorySaver`: Saves conversation history so the AI remembers what you said earlier.

```python
load_dotenv()
MCP_URL = "https://expense-tracker-mcp.onrender.com/mcp"
MCP_API_KEY = os.getenv("MCP_API_KEY", "")
TODAY = date.today().strftime("%d/%m/%Y")
```

- `load_dotenv()`: Reads your `.env` file into environment variables.
- `MCP_URL`: Address of the deployed MCP server on Render.
- `TODAY`: Today's date in DD/MM/YYYY format (used in system prompt).

```python
st.set_page_config(
    page_title="Expense Tracker · MCP Demo",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)
```

**Must be the FIRST Streamlit command** in the file. Sets up the page title, icon (emoji), and two-column layout (wide = more space).

```python
for key, default in [
    ("messages", []),
    ("tool_calls", []),
    ("connected", False),
    ("first_turn", True),
]:
    if key not in st.session_state:
        st.session_state[key] = default
```

**Session state** — Streamlit's way of remembering things between page reloads:
- `messages`: Chat history (list of user & assistant messages)
- `tool_calls`: All MCP tool calls made so far (for the sidebar log)
- `connected`: Whether we've connected to the MCP server
- `first_turn`: Whether this is the first message in the conversation

```python
def build_system_message() -> str:
    """Build the system prompt with category context."""
    return (
        f"You are an expense tracking assistant. Today's date is {TODAY}.\n\n"
        f"Rules:\n"
        f"- Valid categories: food, transport, housing, utilities, health, education,...\n"
        f"- Use 'misc' if nothing else fits.\n"
        f"- Use DD/MM/YYYY format for dates.\n"
        f"- Amounts are in Indian Rupees (INR).\n"
        ...
    )
```

Creates the **system prompt** — instructions that tell the AI how to behave. This is sent to the LLM before your first message so it knows:
- What categories exist
- What date format to use
- What currency (INR)

```python
async def run_agent(query: str) -> str:
    """Run the LangChain agent, collecting tool events into session state."""
    if "agent" not in st.session_state:
        # ── First time: Connect to MCP, get tools, build agent ──
        client = MultiServerMCPClient({
            "expense_tracker": {"url": MCP_URL, "transport": "streamable_http"},
        })
        tools = await client.get_tools()
```

**Lazy initialization:** The first time you ask a question, it:
1. Connects to the MCP server on Render
2. Asks "what tools do you have?" — gets back 12 tools
3. Builds the AI agent with those tools

On subsequent questions, it reuses the same agent (saved in session state).

```python
        # Wrap tool outputs for content_and_artifact format
        for tool in tools:
            def _wrap_coro(fn):
                async def wrapped(*args, **kwargs):
                    result = await fn(*args, **kwargs)
                    return (json.dumps(result, default=str), result) if not isinstance(result, str) else result
                return wrapped
            ...
            if tool.coroutine is not None:
                tool.coroutine = _wrap_coro(tool.coroutine)
            if tool.func is not None:
                tool.func = _wrap_func(tool.func)
```

**Tool wrapping:** The LangChain agent expects tool outputs in a specific format — a tuple of `(string_content, raw_artifact)`. This wrapping ensures every tool returns that format.
- `_wrap_coro`: For async tools (most MCP tools)
- `_wrap_func`: For sync tools

```python
        llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
        memory = MemorySaver()
        agent = create_react_agent(llm, tools, checkpointer=memory)
```

- `ChatGroq`: Uses Groq's LLaMA 3.1 model (8 billion parameters, fast and free)
- `temperature=0`: Makes the AI deterministic (same input = same output, good for tool calling)
- `MemorySaver`: Saves conversation history so the AI remembers context
- `create_react_agent`: Creates the ReAct loop — the AI can think, decide to call tools, get results, and respond

```python
    if st.session_state.first_turn:
        messages = [SystemMessage(content=build_system_message()), ("human", query)]
        st.session_state.first_turn = False
    else:
        messages = [("human", query)]
```

**First turn logic:** Only sends the system prompt on the FIRST message. Subsequent messages just send the user's query. This prevents the AI from getting confused by seeing the system prompt multiple times.

```python
    st.session_state.current_tool_calls = []
    full_response = ""
    try:
        async for event in agent.astream_events(
            {"messages": messages},
            {"configurable": {"thread_id": "streamlit-demo"}},
            version="v2",
        ):
```

**The magic happens here.** `astream_events` streams events from the agent as they happen. We listen for:
- `on_chat_model_stream`: New text from the AI (builds the response character by character)
- `on_tool_start`: AI decided to call a tool (we record this for the sidebar)
- `on_tool_end`: Tool returned a result (we save it)

```python
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and isinstance(chunk.content, str):
                    full_response += chunk.content

            elif kind == "on_tool_start":
                raw = event["data"].get("input", {})
                st.session_state.current_tool_calls.append({
                    "name": event["name"],
                    "params": raw.get("kwargs", raw),
                    "result": None,
                    "status": "running",
                })

            elif kind == "on_tool_end":
                calls = st.session_state.current_tool_calls
                if calls and calls[-1]["status"] == "running":
                    out = event["data"].get("output", "")
                    if isinstance(out, (list, tuple)) and len(out) == 2:
                        out = out[0]
                    calls[-1]["result"] = out
                    calls[-1]["status"] = "done"
```

**Event handling explained:**
1. When AI generates text: We collect it into `full_response`
2. When AI starts a tool: We add a new entry to `current_tool_calls` with `status: "running"`
3. When tool finishes: We update that entry with the result and `status: "done"`

```python
    st.session_state.tool_calls.extend(st.session_state.current_tool_calls)
    st.session_state.current_tool_calls = []
    return full_response
```

After the agent finishes:
- Move `current_tool_calls` into permanent `tool_calls` history (for the sidebar)
- Return the AI's text response

```python
# ── SECTION: SIDEBAR UI ────────────────────────────────────────────
with st.sidebar:
    st.title("💰 MCP Demo")
```

The sidebar contains:
- **Connection status**: Shows if connected to MCP server
- **Connect/Reconnect button**: Manages the connection
- **Tool Call Log**: Lists every tool call with params and results
- **Stats**: Counts of total calls, done calls, unique tools
- **Clear button**: Resets everything

```python
    if st.session_state.connected:
        if st.button("🔄 Reconnect", use_container_width=True):
            for k in list(st.session_state.keys()):
                if k != "messages":
                    del st.session_state[k]
            st.rerun()
```

**Reconnect logic:** Deletes ALL session state except chat messages, forcing the app to reconnect and rebuild the agent from scratch.

```python
    else:
        if st.button("🚀 Connect & Start Demo", ...):
            with st.spinner("Connecting..."):
                try:
                    async def _test():
                        client = MultiServerMCPClient({...})
                        tools = await client.get_tools()
                        return len(tools)
                    n_tools = asyncio.run(_test())
                    st.session_state.connected = True
```

**Connect button:** Pings the MCP server to check if it's reachable. If successful, marks `connected = True`. The actual agent is built lazily on the first question.

```python
    # Tool Call Log
    for tc in st.session_state.tool_calls:
        icon = "✅" if tc["status"] == "done" else "⏳"
        with st.expander(f"{icon} {tc['name']}", expanded=False):
            params = tc.get("params", {})
            if isinstance(params, dict):
                for k, v in params.items():
                    st.markdown(f"**{k}:** `{v_str}`")
            ...
            if tc.get("result") is not None:
                try:
                    parsed = json.loads(tc["result"]) if isinstance(tc["result"], str) else tc["result"]
                    st.json(parsed)
```

**Tool call display:** Each tool call shown as an expandable card:
- ✅ = completed, ⏳ = running
- Shows parameters (e.g., `date: "11/06/2026"`, `amount: 350`)
- Shows result as a pretty-printed JSON

```python
# ── SECTION: MAIN CHAT AREA ────────────────────────────────────────
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    ...
    with st.chat_message("assistant"):
        with st.status("🤖 Thinking...", expanded=True) as status:
            try:
                response = asyncio.run(run_agent(prompt))
                ...
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()
```

**Query flow:**
1. User types message → appended to chat history
2. Shows a "Thinking..." status indicator
3. Runs the agent (this can take 2-10 seconds)
4. Displays the AI's response
5. Calls `st.rerun()` to refresh the sidebar with new tool calls

---

## 4.3 `categories.json`

```json
{
  "food": ["groceries", "fruits_vegetables", "dairy_bakery", "dining_out", "coffee_tea", "snacks", "delivery_fees", "other"],
  "transport": ["fuel", "public_transport", "cab_ride_hailing", "parking", "tolls", "vehicle_service", "other"],
  ...
  "misc": ["uncategorized", "rounding", "other"]
}
```

A simple **data file** that defines valid expense categories and their subcategories. The MCP server reads this file in its `categories()` resource.

Each category has subcategories:
- `"food"` → groceries, fruits & vegetables, dairy & bakery, dining out, coffee & tea, snacks, delivery fees
- `"misc"` is the fallback — use it when nothing else fits

---

## 4.4 `pyproject.toml`

```toml
[project]
name = "expense-tracker-mcp"
version = "0.1.0"
description = "Expense Tracker exposed as a remote MCP Server"
requires-python = ">=3.13"
dependencies = [
    "fastmcp>=3.2.0",
    "langchain>=1.3.7",
    ...
    "streamlit>=1.43.0",
    "uvicorn>=0.29.0",
]
```

The **modern** Python project config (used by `uv`):
- `name`: Project name on PyPI (not published, just for local use)
- `requires-python`: Minimum Python version (3.13)
- `dependencies`: All packages needed, with minimum versions

**`uv sync`** reads this file and installs everything at once.

---

## 4.5 `requirements.txt`

```
fastmcp>=3.2.0
langchain>=1.3.7
...
```

An older-style dependency list. Some platforms (like older Render setups) still use this instead of `pyproject.toml`. It's kept for compatibility.

---

## 4.6 `Procfile`

```
web: python main.py
```

**Render-specific file.** Tells Render: "When deploying, run `python main.py` as the web process." This starts the MCP server.

---

## 4.7 `.gitignore`

```
__pycache__/
*.pyc
.venv/
*.db
.env
```

Files that Git should **not** track:
- `__pycache__/`: Python compiled bytecode
- `.venv/`: Virtual environment (can be recreated)
- `*.db`: Database files (your local data stays local)
- `.env`: Secret keys (API keys, passwords)

---

# 5. WORKFLOWS

## 5.1 User Adds an Expense

```
User: "Add INR 350 for groceries"

1. Streamlit sends to LangChain Agent
2. Agent sends to Groq LLM
3. LLM understands: action = "add_expense", params = {date, amount=350, category="food", subcategory="groceries"}
4. Agent calls add_expense(date="11/06/2026", amount=350, category="food", subcategory="groceries", note="")
5. MCP Server:
   a. Checks auth (if MCP_API_KEY set)
   b. Runs: INSERT INTO expenses (date, amount, category, subcategory) VALUES (?, ?, ?, ?)
   c. Returns: {"status": "success", "id": 42}
6. LLM reads result: "Done! Added ₹350 for groceries."
7. User sees response in chat + tool call in sidebar
```

## 5.2 User Checks Spending

```
User: "How much did I spend last week?"

1. Agent sends to LLM
2. LLM: "I need to calculate dates for 'last week' and call summarize()"
3. LLM calls: summarize(start_date="04/06/2026", end_date="10/06/2026")
4. MCP Server:
   a. Runs: SELECT category, SUM(amount) FROM expenses WHERE date BETWEEN ? AND ? GROUP BY category
   b. Returns: [{"category": "food", "total_amount": 2450}, {"category": "transport", "total_amount": 800}, ...]
5. LLM reads results
6. LLM responds: "Last week you spent ₹4,520 total. Your top category was food at ₹2,450."
7. Sidebar shows: summarize(start_date=..., end_date=...) ✅
```

## 5.3 Full System Startup

```
1. Render starts → runs Procfile → python main.py
2. main.py:
   a. Reads DATABASE_URL from environment
   b. Creates database tables (expenses, budgets, recurring_expenses)
   c. Starts MCP server on port 10000 (Render's default)
3. User opens Streamlit app
4. Streamlit loads streamlit_app.py
5. User clicks "Connect & Start Demo"
6. Streamlit connects to Render MCP server
7. User types a question
8. Streamlit builds LangChain Agent (lazy init on first question)
9. Agent connects to Groq API
10. Everything is ready — user can chat
```

---

# 6. DEPLOYMENT

## 6.1 Current Deployment

| Service | Hosted On | URL |
|---|---|---|
| MCP Server | Render | `https://expense-tracker-mcp.onrender.com/mcp` |
| Database | Render PostgreSQL | Via `DATABASE_URL` env var |
| Streamlit App | Not yet deployed | Run locally via `uv run streamlit run streamlit_app.py` |

## 6.2 How Render Hosts the MCP Server

1. Render reads `Procfile`: `web: python main.py`
2. Runs `pip install uv && uv sync` to install dependencies
3. Starts `python main.py`
4. Render sets `PORT` environment variable (usually `10000`)
5. Server listens on `0.0.0.0:10000`
6. Render monitors with health checks to `/`

---

# 7. KEY CONCEPTS EXPLAINED

## MCP (Model Context Protocol)

**Think of MCP like USB for AI.** Just as USB lets you plug any device (mouse, keyboard, printer) into any computer, MCP lets you plug any AI model into any backend service.

Instead of writing custom code for every AI-backend connection, you:
1. **Server** defines tools (like `add_expense`, `search_expenses`)
2. **Client** discovers and calls those tools
3. Everything speaks the same protocol

## ReAct Agent Pattern

The LangChain agent uses the **ReAct** (Reason + Act) pattern:

```
1. THINK: "The user asked about last week's spending"
2. REASON: "I need to call list_expenses or summarize"
3. ACT: "Call summarize(start_date, end_date)"
4. OBSERVE: "Got back spending data"
5. THINK: "The user wants a friendly summary"
6. RESPOND: "You spent ₹4,520 last week..."
```

## streamable-http Transport

MCP servers can communicate in different ways:
- **stdio**: Local, direct process communication (faster but same machine)
- **streamable-http**: Over the internet via HTTP (used here for remote access)

The server uses `streamable-http` so the Streamlit app on your laptop can talk to the MCP server on Render across the internet.

---

# 8. GLOSSARY

| Term | Simple Explanation |
|---|---|
| **MCP** | Model Context Protocol — a standard for AI agents to call backend tools |
| **FastMCP** | Python library to create MCP servers easily |
| **LangChain** | Framework for building AI applications with LLMs |
| **LangGraph** | Extension of LangChain for building agent workflows |
| **Groq** | Cloud service that runs LLMs very fast (free tier available) |
| **LLaMA 3.1** | Meta's open-source AI model (8 billion parameters) |
| **ReAct Agent** | AI that can Reason and Act (call tools) |
| **Streamlit** | Python library for building web UIs without HTML/CSS |
| **Render** | Cloud hosting platform (alternative to Heroku, AWS) |
| **streamable-http** | MCP transport for communicating over the internet |
| **SQLite** | File-based database (no server needed) |
| **PostgreSQL** | Full-featured database server (used in production) |
| **System Prompt** | Instructions at the start telling the AI how to behave |
| **Tool** | A function the AI can call (add_expense, search, etc.) |
| **Resource** | Read-only data the AI can look up (categories, stats) |
| **Prompt** | A template the AI can use for structured tasks (monthly review) |
| **Session State** | Streamlit's way of remembering data between page refreshes |
| **.env file** | Text file with secret keys (never commit to Git) |
| **uv** | Fast Python package manager (alternative to pip) |

---

*Documentation generated for the Expense Tracker MCP project.*
