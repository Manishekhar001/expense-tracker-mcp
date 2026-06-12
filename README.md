# Expense Tracker MCP

A personal expense tracker exposed as a **remote MCP server** (hosted on Render), with a **Streamlit frontend** that visualizes tool calls in real-time — perfect for demonstrating MCP architecture in interviews.

## Architecture

```
User (Streamlit UI)
    ↕ Natural language
LangChain Agent + Groq LLM
    ↕ MCP over HTTP (streamable-http)
FastMCP Server (Render)
    ↕ PostgreSQL (Render)
Database
```

## MCP Tools (12 total)

| Tool | Description |
|------|-------------|
| `add_expense` | Add a new expense |
| `get_expense` | Fetch a single expense by ID |
| `update_expense` | Update one or more fields |
| `delete_expense` | Delete an expense |
| `search_expenses` | Keyword search across notes/categories |
| `list_expenses` | List expenses in a date range |
| `summarize` | Total spending grouped by category |
| `set_budget` | Set or update a category budget |
| `budget_status` | Compare actual spending vs budgets |
| `export_csv` | Export expenses as CSV |
| `add_recurring_expense` | Register a recurring expense |
| `list_recurring_expenses` | List active recurring expenses |

## Quick Start

### Prerequisites
- Python 3.13+
- A [Groq API key](https://console.groq.com/keys) (free)

### Setup
```bash
# Install dependencies
uv sync

# Create .env file with your API key
echo "GROQ_API_KEY=gsk_your_key_here" > .env
```

### Run the Streamlit Demo
```bash
uv run streamlit run streamlit_app.py
```

This opens a browser at `http://localhost:8501`. Click **"Connect & Start Demo"** to connect to the live MCP server on Render, then ask questions in natural language!

### Run Server Locally (optional)
```bash
uv run python main.py
```
Server starts at `http://localhost:8000/mcp`

## Deployment

- **MCP Server:** Deployed on [Render](https://render.com) using `Procfile`
- **Database:** Render PostgreSQL
- **MCP Server endpoint:** `https://expense-tracker-mcp.onrender.com/mcp`
- **Streamlit App (live demo):** [https://expense-tracker-streamlit-brjt.onrender.com/](https://expense-tracker-streamlit-brjt.onrender.com/)
