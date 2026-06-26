# Testing

## Current state ⚠️

**No test files exist in this repository.**

The project was not developed with a testing framework. There are no:
- Unit tests
- Integration tests
- End-to-end tests
- Test configuration files (`pytest.ini`, `conftest.py`, `pyproject.toml` test settings)

Testing has been entirely manual: running the server, sending requests via the Streamlit UI or curl, and checking the results.

## Testing philosophy (inferred from code structure)

While no tests exist, the codebase is structured in a way that suggests the intended testing approach:

- **Server (`main.py`):** Each tool is a pure(ish) function that takes parameters and returns a JSON string. The database helper functions (`query`, `execute`, `insert`) are separated from the tool logic, making it possible to mock or replace the database layer.
- **Frontend (`streamlit_app.py`):** The agent logic is in `run_agent()` and `build_system_message()`, which could be tested in isolation. The Streamlit UI rendering is not easily testable without Streamlit's testing framework.

## How tests would be organised

Based on the project structure, tests would live in a `tests/` directory at the project root:

```
expense-tracker-mcp/
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Fixtures (test database, test client)
│   ├── test_tools.py        # Tests for each MCP tool
│   ├── test_database.py     # Tests for query/execute/insert helpers
│   ├── test_auth.py         # Tests for authenticated()
│   └── test_adapt.py        # Tests for _adapt() SQL conversion
└── ...
```

## How to run tests (once they exist)

```bash
# Install testing dependencies
uv add --dev pytest

# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run a single test file
uv run pytest tests/test_tools.py

# Run a single test function
uv run pytest tests/test_tools.py::test_add_expense_success -v

# Run with coverage
uv run pytest --cov=main --cov-report=term-missing
```

## What the tests should cover

### Unit tests for `main.py`

| Test area | What to test | Example test cases |
|-----------|-------------|-------------------|
| `authenticated()` | API key validation | No key configured → always passes; correct key → passes; wrong key → error message |
| `_adapt()` | SQL syntax conversion | SQLite SQL unchanged; `?` → `%s`; `AUTOINCREMENT` → `SERIAL`; `LIKE` → `ILIKE` |
| `query()` | SELECT with SQLite and mock PG | Returns list of dicts; handles empty results; closes connection |
| `execute()` | INSERT/UPDATE/DELETE | Returns row count; handles 0 affected rows |
| `insert()` | INSERT with ID return | Returns integer ID; handles PG and SQLite paths |
| `add_expense()` | Full tool logic | Success path; auth failure; with/without optional params |
| `update_expense()` | Partial update | Updates only provided fields; no fields → error; not found → error |
| `delete_expense()` | Deletion | Success; not found |
| `search_expenses()` | Keyword search | Returns matching rows; case-insensitive; empty result |
| `list_expenses()` | Date-range listing | Inclusive boundaries; ordering |
| `summarize()` | Aggregation | With/without category filter; empty range |
| `set_budget()` | Upsert | New category → insert; existing → update |
| `budget_status()` | Comparison | Budgets exist + spending exists; budgets exist + no spending; spending without budget |
| `export_csv()` | CSV generation | CSV format; row count; filename format; empty range |
| `budget_status()` with date defaults | Default to current month | No month/year → uses `datetime.now()` |

### Integration tests

| Test area | What to test |
|-----------|-------------|
| Tool → DB round trip | Call `add_expense`, then `get_expense` — verify the stored data matches |
| Full workflow | Add expense, verify it appears in `list_expenses`, `summarize`, `budget_status` |
| Dual database | Run the same test suite against both SQLite and PostgreSQL (if available) |

### Frontend tests

| Test area | What to test |
|-----------|-------------|
| `build_system_message()` | Returns correct categories, date format, currency, API key instruction |
| `run_agent()` tool wrapping | Tool output is wrapped as `(content_string, raw_artifact)` tuple |

## What the tests would NOT cover (honest assessment)

- **Streamlit UI rendering:** The `st.*` calls and custom CSS are not tested. These require Streamlit's testing framework (`st.testing`) or a browser-based e2e tool like Playwright.
- **MCP protocol compliance:** The project assumes FastMCP handles JSON-RPC correctly. There are no tests verifying the raw HTTP request/response format against the MCP specification.
- **LLM behaviour:** The LangChain agent's decisions (which tool to call, how to interpret results) are not tested. These depend on Groq's LLaMA 3.1 model, which is non-deterministic.
- **Performance and load:** No tests measure response times, concurrent request handling, or database connection pool behaviour.

## How to write a new test (example)

Following the existing code patterns, here is how you would write a test for `add_expense`:

```python
# tests/test_tools.py
import json
import pytest
from main import add_expense


def test_add_expense_success(monkeypatch):
    """add_expense returns success with a new ID when all fields are valid."""

    # Mock the insert function to return a fixed ID without touching the DB
    def mock_insert(sql, params):
        return 42  # pretend the new row has ID 42

    monkeypatch.setattr("main.insert", mock_insert)

    result = json.loads(add_expense(
        date="11/06/2026",
        amount=350.0,
        category="food",
        subcategory="groceries",
        note="Weekly shopping",
    ))

    assert result["status"] == "success"
    assert result["id"] == 42


def test_add_expense_auth_failure():
    """add_expense returns an error when the API key is wrong."""
    result = json.loads(add_expense(
        date="11/06/2026",
        amount=350.0,
        category="food",
        api_key="wrong-key",
    ))

    assert result["status"] == "error"
    assert "api_key" in result["message"].lower()
```

This test:
1. Uses `monkeypatch` to replace the real `insert()` with a mock that returns a known ID
2. Calls `add_expense()` exactly as the MCP server would
3. Parses the JSON string result (because `@json_response` wraps it)
4. Asserts on the expected fields
