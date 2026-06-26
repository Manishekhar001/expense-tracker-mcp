# Workflow: Application Startup

## Purpose

Describes what happens when the MCP server starts up and when the Streamlit frontend initialises and connects to it. Understanding this flow is essential for debugging deployment issues and for understanding the lazy-initialisation pattern in the frontend.

---

## Workflow A: MCP Server Startup

## Trigger

The server process starts. On Render, this is triggered by the `Procfile` (`web: python main.py`). Locally, it is `uv run python main.py`.

**Entry point:** `main.py:1` (file executes from top to bottom)

## Step-by-Step Execution

### Step 1 — Imports and constants

- **File:** `main.py:1-9`
- **What happens:** All modules are imported (`csv`, `functools`, `io`, `json`, `os`, `datetime`, `fastmcp`). Constants are initialised:
  - `DATABASE_URL = os.environ.get("DATABASE_URL", "")` — checks for PostgreSQL config
  - `MCP_API_KEY = os.environ.get("MCP_API_KEY", "")` — checks for authentication config
  - `CATEGORIES_PATH` — resolves path to `categories.json`
- **Side effects:** None (imports only)

### Step 2 — PostgreSQL fallback check

- **File:** `main.py:13-19`
- **What happens:** If `DATABASE_URL` is set but `psycopg2` cannot be imported, a warning is printed to stderr and `DATABASE_URL` is reset to `""` (falls back to SQLite). This prevents the server from failing to start when `psycopg2` is unavailable.

### Step 3 — Helper functions defined

- **File:** `main.py:22-90`
- **Functions defined (not executed yet):**
  - `_is_pg()` — returns `True` if using PostgreSQL
  - `_adapt(sql)` — converts SQLite SQL to PostgreSQL syntax
  - `get_conn()` — opens the appropriate database connection
  - `query(sql, params)` — SELECT wrapper, returns list of dicts
  - `execute(sql, params)` — INSERT/UPDATE/DELETE wrapper, returns row count
  - `insert(sql, params)` — INSERT wrapper that returns the new row ID

### Step 4 — Auth and response decorators defined

- **File:** `main.py:99-120`
- **Functions defined:**
  - `authenticated(api_key)` — returns error string if auth fails, `None` if ok
  - `json_response(func)` — decorator that wraps return value in `json.dumps()`

### Step 5 — FastMCP server created

- **File:** `main.py:126`
- **What happens:** `mcp = FastMCP(name="Expense Tracker")` creates the MCP server instance. No network activity yet — this is just object instantiation.

### Step 6 — Database initialised

- **File:** `main.py:129-163`
- **Function:** `init_db()` called immediately at module level
- **What happens:** Three `CREATE TABLE IF NOT EXISTS` statements are executed:
  1. `expenses` — id, date, amount, category, subcategory, note
  2. `budgets` — id, category (UNIQUE), amount, period
  3. `recurring_expenses` — id, description, amount, category, subcategory, day_of_month, start_date, active
- **Side effects:** Creates `expense_tracker.db` (SQLite) or creates tables in PostgreSQL

### Step 7 — Decorators register tools, resources, and prompts

- **File:** `main.py:169-420`
- **What happens:** Python processes all decorators (`@mcp.tool`, `@mcp.resource`, `@mcp.prompt`) which register each function in FastMCP's internal registry. The order is:
  1. Tools (12): `add_expense` → `list_recurring_expenses`
  2. Resources (3): `expense://categories`, `expense://stats`, `expense://monthly/{month}/{year}`
  3. Prompts (2): `monthly_review`, `budget_check`

### Step 8 — HTTP server starts

- **File:** `main.py:427-430`
- **What happens:**
  ```python
  if __name__ == "__main__":
      port = int(os.environ.get("PORT", 8000))
      mcp.run(transport="streamable-http", host="0.0.0.0", port=port)
  ```
  - FastMCP starts an HTTP server listening on `0.0.0.0:PORT`
  - The `/mcp` endpoint becomes available for JSON-RPC requests
  - The server is now ready to accept connections

## Success Outcome

The MCP server is listening for HTTP connections on port 8000 (or the `PORT` env var). It can respond to `tools/list`, `tools/call`, `resources/read`, and `prompts/get` JSON-RPC methods.

## Failure Modes

| Error Condition | How it is handled | Consequence |
|-----------------|-------------------|-------------|
| `psycopg2` not imported (with DATABASE_URL set) | Falls back to SQLite with stderr warning | Local only — no PostgreSQL available |
| Database file unwritable (SQLite) | `sqlite3.connect()` raises an exception | Server crashes on startup |
| Port already in use | FastMCP raises a socket error | Server fails to start; choose a different port |
| `PORT` env var is not a number | `int("")` raises `ValueError` | Server crashes on startup |

---

## Workflow B: Streamlit Frontend Startup and Connection

## Trigger

The Streamlit app starts: `uv run streamlit run streamlit_app.py`

**Entry point:** `streamlit_app.py:1`

## Step-by-Step Execution

### Step 1 — Page config (must be first Streamlit command)

- **File:** `streamlit_app.py:33-38`
- **What happens:** `st.set_page_config()` sets page title, icon, wide layout, and expanded sidebar. This must be the first Streamlit command in the file.
- **Side effects:** Configures the browser tab title and layout.

### Step 2 — Custom CSS injected

- **File:** `streamlit_app.py:42-145`
- **What happens:** A large `<style>` block is injected via `st.markdown(unsafe_allow_html=True)`. Defines the dark gradient theme (`#0f0c29` → `#24243e`), tool card styling, chat message styling, button hover effects, and responsive metric containers.

### Step 3 — Groq API key check

- **File:** `streamlit_app.py:148-152`
- **What happens:** If `GROQ_API_KEY` is not set in the environment, a warning message is displayed asking the user to add it to `.env`.

### Step 4 — Session state initialisation

- **File:** `streamlit_app.py:155-161`
- **What happens:** Default values are set for session state keys if not already present:
  - `messages: []` — chat history
  - `tool_calls: []` — all MCP tool calls made
  - `connected: False` — MCP server connection status
  - `first_turn: True` — whether the next user message is the first

### Step 5 — Sidebar rendered

- **File:** `streamlit_app.py:189-253`
- **What happens:** The sidebar UI is rendered with:
  - Title and subtitle
  - Connection status badge (green "Connected" or amber "Disconnected")
  - Connect/Reconnect button
  - Tool call log section (initially shows placeholder text)
  - Stats metrics (Calls, Done, Unique — all starting at 0)
  - Clear All button

### Step 6 — Main chat area rendered

- **File:** `streamlit_app.py:257-290`
- **What happens:** The main chat area displays:
  - Header banner with title and description
  - Four example buttons (if connected)
  - Welcome message from the assistant (if no messages yet and connected)
  - Chat message input (disabled if not connected)

### Step 7 — User clicks "Connect & Start Demo"

- **File:** `streamlit_app.py:211-222`
- **What happens:**
  1. Button click triggers an async function `_test()` that creates a `MultiServerMCPClient` and calls `get_tools()`
  2. If successful, `n_tools` (the count of discovered tools) is stored
  3. `st.session_state.connected = True` is set
  4. A success message "✅ 12 MCP tools available" is shown
  5. `st.rerun()` triggers a UI refresh, now showing "Connected" badge and enabled input

### Step 8 — First user question (lazy agent initialisation)

- **File:** `streamlit_app.py:119-138`
- **What happens:** This is where the real agent is built (not at connect time):
  1. `MultiServerMCPClient({...})` is created with the MCP URL
  2. `await client.get_tools()` discovers all tools from the server
  3. Each tool's `coroutine` and `func` are wrapped to produce `(content_string, raw_artifact)` tuples
  4. `ChatGroq(model="llama-3.1-8b-instant", temperature=0)` is initialised
  5. `MemorySaver()` is created for conversation memory
  6. `create_react_agent(llm, tools, checkpointer=memory)` builds the ReAct agent
  7. Everything is saved to `st.session_state` so subsequent questions reuse the same agent

## Success Outcome

The Streamlit app is fully connected and ready. The user can type questions and the agent will call MCP tools against the live server.

## Failure Modes

| Error Condition | How it is handled | What the user sees |
|-----------------|-------------------|--------------------|
| MCP server is down | `_test()` raises connection error | "❌ Connection failed: [error]" displayed |
| GROQ_API_KEY not set | Warning banner shown at startup | "⚠️ GROQ_API_KEY not set" warning |
| MCP server returns no tools | `get_tools()` succeeds but returns empty list | "✅ 0 MCP tools available" — agent will fail at runtime |
