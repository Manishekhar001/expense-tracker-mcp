# Expense Tracker MCP

A personal expense tracker exposed as a **remote MCP server**, integrated with a **LangChain agent** for natural-language expense management.

## Architecture

```
LangChain Agent (local)
    ↕ MCP over HTTP (streamable-http)
FastMCP Server (Render)
    ↕ SQL
SQLite Database
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `add_expense` | Add a new expense (date, amount, category, optional subcategory/note) |
| `list_expenses` | List all expenses in a date range |
| `summarize` | Total spending grouped by category for a date range |

## Quick Start

### Run Server Locally
```bash
uv run python main.py
```
Server starts at `http://localhost:8000/mcp`

### Run Agent
```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your GROQ_API_KEY (get one free at https://console.groq.com/keys)
python agent.py
```

## Deployment
Server is deployed on [Render](https://render.com).
Live endpoint: `https://expense-tracker-mcp.onrender.com/mcp`
