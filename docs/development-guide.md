# Development Guide

## Local Setup

### Prerequisites

- **Python 3.13+** — the project uses `requires-python = ">=3.13"`
- **uv** (recommended) or **pip** — Python package manager
- **A Groq API key** — [free to obtain](https://console.groq.com/keys)

### Step-by-step setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd expense-tracker-mcp

# 2. Create and activate a virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# 3. Install dependencies
uv sync

# 4. Create .env file
echo "GROQ_API_KEY=gsk_your_key_here" > .env

# 5. (Optional) Enable MCP auth for testing
echo "MCP_API_KEY=test-key-123" >> .env
```

## Running the Application

### Run the MCP Server (backend)

```bash
uv run python main.py
```

The server starts at `http://localhost:8000/mcp`. It listens for JSON-RPC 2.0 requests over HTTP (streamable-http transport).

### Run the Streamlit Frontend

```bash
uv run streamlit run streamlit_app.py
```

Opens `http://localhost:8501` in your browser.

**To use a local MCP server instead of the Render endpoint:**

Edit `streamlit_app.py` line 24:
```python
# Change this line:
MCP_URL = "https://expense-tracker-mcp.onrender.com/mcp"
# To:
MCP_URL = "http://localhost:8000/mcp"
```

### Run both locally with hot-reload

Start the MCP server in one terminal:
```bash
uv run python main.py
```

Start the Streamlit frontend in another terminal:
```bash
uv run streamlit run streamlit_app.py
```

Streamlit has built-in hot reload — changes to `streamlit_app.py` are reflected after a browser refresh. The MCP server (`main.py`) must be restarted manually after changes.

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v
```

> ⚠️ **No test files currently exist** in the repository. See [Testing](testing.md) for details and guidance on adding tests.

## Code Style

The project does not currently enforce any code style tools. There is no:
- No linter (no `ruff`, `flake8`, `pylama` configured)
- No formatter (no `black`, `ruff format` configured)
- No type checker (no `mypy`, `pyright` configured)

**Consistent conventions observed in the existing code:**

1. **Type hints** are used on all function parameters and return types in `main.py` (e.g., `def add_expense(date: str, amount: float, ...) -> dict:`).
2. **Docstrings** exist on all tools, resources, prompts, and helper functions — triple-quoted strings describing purpose, parameters, and return values.
3. **Constants** are UPPER_CASE (`DATABASE_URL`, `MCP_API_KEY`, `CATEGORIES_PATH`).
4. **Private helpers** are prefixed with underscore (`_is_pg`, `_adapt`).
5. **Imports** follow: standard library first, then third-party, with a blank line separator.

## Git Workflow

The existing commit history shows a single-author project with descriptive commit messages (e.g., `feat: replace CLI agent with Streamlit MCP demo frontend`, `fix: gracefully fall back to SQLite when psycopg2 not installed`).

**Conventional Commits** format is used:
- `feat:` — new feature
- `fix:` — bug fix
- `docs:` — documentation changes
- `style:` — UI or styling changes
- Prefix the commit subject with lowercase after the colon

**Branch naming:** No conventions are enforced — the repository has only a `main` branch.

## How to Add a New Feature

To add a new feature (e.g., a new MCP tool), follow these steps:

### 1. Add a new tool function in `main.py`

```python
@mcp.tool
@json_response
def my_new_tool(param1: str, param2: int = 0, api_key: str = ""):
    """
    Description of what this tool does.
    - param1: description
    - param2: description (default: 0)
    - api_key: required if MCP_API_KEY is set
    """
    auth_error = authenticated(api_key)
    if auth_error:
        return {"status": "error", "message": auth_error}
    # ... business logic ...
    return {"status": "success", ...}
```

### 2. Update the system prompt in `streamlit_app.py`

If the new tool changes how the LLM should behave, update `build_system_message()` in `streamlit_app.py:82-94`.

### 3. Test manually

Run the MCP server locally and send a test call via the Streamlit frontend or a tool like `curl`:

```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "my_new_tool", "arguments": {"param1": "...", "api_key": "test-key-123"}}, "id": "test-1"}'
```

### 4. Add tests

See [Testing](testing.md) for guidance.

## How to Add a New API Endpoint

Since this is an MCP server (not a REST API), "adding an endpoint" means:

### Add a new MCP tool

Follow the steps above.

### Add a new MCP resource

```python
@mcp.resource("expense://my-resource/{param}", mime_type="application/json")
def my_resource(param: str) -> str:
    """Description of the resource."""
    data = query("SELECT ... WHERE col = ?", (param,))
    return json.dumps(data)
```

### Add a new MCP prompt

```python
@mcp.prompt()
def my_prompt(param: str) -> str:
    """Description of the prompt."""
    return (
        f"Instructions for the LLM using {param}.\n"
        f"1. Call tool_x()\n"
        f"2. Summarize the result"
    )
```

## Common Errors During Local Setup

| Error | Likely cause | Fix |
|-------|-------------|-----|
| `ModuleNotFoundError: No module named 'fastmcp'` | Dependencies not installed | Run `uv sync` |
| `GROQ_API_KEY not set` warning in Streamlit | Missing `.env` file | Create `.env` with `GROQ_API_KEY=gsk_...` |
| `ValueError: missing PORT` or connection refused | MCP server not running | Start with `uv run python main.py` |
| Streamlit connects but agent returns errors | `MCP_URL` still points to Render | Change to `http://localhost:8000/mcp` for local server |
| `psycopg2 not installed` stderr message | `DATABASE_URL` is set but `psycopg2` is not installed | Either install `psycopg2-binary` or unset `DATABASE_URL` to use SQLite |
